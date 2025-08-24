import sys
import os
import shutil
import filecmp
import difflib
import math
import json
import mmap
import time
import logging
from datetime import datetime
from functools import partial, lru_cache
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QTextEdit, QFileDialog, QMessageBox, QFrame,
    QStackedLayout, QHeaderView, QAbstractItemView, QProgressBar, QToolTip,
    QInputDialog, QCheckBox, QSplitter, QSizePolicy, QComboBox, QProgressDialog,
    QDialog
)
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent, QPalette, QColor, QPainter, QPen, QBrush
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal, QRect, QTimer, QThreadPool, QRunnable, pyqtSlot, QMutex, QWaitCondition

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("FileManager")

# Try to import xxhash for ultra-fast hashing, fall back to hashlib if not available
try:
    import xxhash
    HAS_XXHASH = True
except ImportError:
    import hashlib
    HAS_XXHASH = False
    logger.warning("xxhash not available, using slower hashlib. Install with: pip install xxhash")

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  PERFORMANCE OPTIMIZATIONS & CONSTANTS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
COLOR_IDENTICAL = QColor(0, 128, 0, 40)      # Green for identical files
COLOR_DIFFERENT = QColor(255, 0, 0, 40)      # Red for not identical files
COLOR_SIMILAR = QColor(255, 255, 0, 40)      # Yellow for similar files that changed
COLOR_BLANK = QColor(0, 0, 0, 0)             # Transparent/blank for no highlighting

STATUS_IDENTICAL, STATUS_DIFFERENT, STATUS_SIMILAR, STATUS_BLANK = 0, 1, 2, 3
FILTER_HIGHLIGHT_STYLE = "background-color: #05B8CC; color: black;"

CHUNK_SIZE = 64 * 1024
MAX_THREADS = min(32, (os.cpu_count() or 4) * 2)
HASH_CACHE_SIZE = 10000
UI_UPDATE_INTERVAL = 100

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  CUSTOM LOG HANDLER FOR GUI
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class QtLogHandler(logging.Handler):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def emit(self, record):
        log_entry = self.format(record)
        self.signal.emit(log_entry)
        
        self.apply_results_btn = QPushButton("Apply Results to UI")
        self.apply_results_btn.clicked.connect(self.apply_results)
        button_layout.addWidget(self.apply_results_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        
class QtLogHandler(logging.Handler):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def emit(self, record):
        log_entry = self.format(record)
        self.signal.emit(log_entry)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  FAST FILE HASHER
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class FastFileHasher(QRunnable):
    def __init__(self, relative_path, full_path, callback, file_size=0):
        super().__init__()
        self.relative_path = relative_path
        self.full_path = full_path
        self.callback = callback
        self.file_size = file_size
        self._is_running = True
        self.setAutoDelete(True)

    def run(self):
        try:
            if not self._is_running:
                return
            hasher = xxhash.xxh64() if HAS_XXHASH else hashlib.md5()
            logger.debug(f"Hashing file: {self.relative_path}")
            
            if self.file_size > 1024 * 1024:
                self._hash_with_mmap(hasher)
            else:
                self._hash_regular(hasher)
                
            if self._is_running:
                logger.debug(f"Finished hashing: {self.relative_path}")
                self.callback(hasher.hexdigest(), None)
        except Exception as e:
            if self._is_running:
                logger.error(f"Error hashing file {self.relative_path}: {str(e)}")
                self.callback(None, str(e))

    def _hash_with_mmap(self, hasher):
        try:
            with open(self.full_path, 'rb') as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    bytes_processed = 0
                    while self._is_running:
                        chunk = mm.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        hasher.update(chunk)
                        bytes_processed += len(chunk)
                        # Report progress for large files
                        if self.file_size > 0 and bytes_processed % (CHUNK_SIZE * 100) == 0:
                            progress = int((bytes_processed / self.file_size) * 100)
                            logger.debug(f"Hashing {self.relative_path}: {progress}%")
        except (OSError, ValueError) as e:
            logger.warning(f"mmap failed for {self.full_path}, falling back to regular read: {str(e)}")
            self._hash_regular(hasher)

    def _hash_regular(self, hasher):
        with open(self.full_path, 'rb') as f:
            bytes_processed = 0
            while self._is_running:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)
                bytes_processed += len(chunk)
                # Report progress for large files
                if self.file_size > 0 and bytes_processed % (CHUNK_SIZE * 100) == 0:
                    progress = int((bytes_processed / self.file_size) * 100)
                    logger.debug(f"Hashing {self.relative_path}: {progress}%")

    def stop(self):
        self._is_running = False

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  WORKERS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class OptimizedSnapshotWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)

    def __init__(self, folder_path, snapshot_path, filenames_with_paths):
        super().__init__()
        self.folder_path = folder_path
        self.snapshot_path = snapshot_path
        self.filenames_with_paths = filenames_with_paths
        self._is_running = True
        self.file_hashes = {}
        self.processed_count = 0
        self.total_count = len(filenames_with_paths)
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(min(MAX_THREADS, self.total_count))
        logger.info(f"Creating snapshot worker for {self.total_count} files")

    def run(self):
        logger.info(f"[OptimizedSnapshotWorker] Hashing {self.total_count} files")
        if self.total_count == 0:
            self._finalize()
            return
        self.processed_count = 0
        self.file_hashes = {}
        batch_size = max(1, self.total_count // (MAX_THREADS * 2))
        
        logger.info(f"Processing files in batches of {batch_size}")
        for i in range(0, len(self.filenames_with_paths), batch_size):
            if not self._is_running:
                break
            batch = self.filenames_with_paths[i:i + batch_size]
            logger.debug(f"Processing batch {i//batch_size + 1}/{(len(self.filenames_with_paths)-1)//batch_size + 1}")
            for relative_path, full_path, file_size in batch:
                if not self._is_running:
                    break
                hasher = FastFileHasher(relative_path, full_path,
                                      partial(self._on_hash_result, relative_path), file_size)
                self.threadpool.start(hasher)
        self.threadpool.waitForDone()

    def _on_hash_result(self, relative_path, hash_result, error_msg=None):
        if not self._is_running:
            return
        if hash_result:
            self.file_hashes[relative_path] = hash_result
        elif error_msg:
            logger.warning(f"Hash error for {relative_path}: {error_msg}")
        self.processed_count += 1
        progress_percent = int((self.processed_count / self.total_count) * 100)
        logger.debug(f"Snapshot progress: {self.processed_count}/{self.total_count} ({progress_percent}%)")
        self.progress.emit(self.processed_count, self.total_count)

    def _finalize(self):
        if not self._is_running:
            return
        logger.info(f"[OptimizedSnapshotWorker] Prepared {len(self.file_hashes)} hashes out of {self.total_count}")
        snapshot_data = {
            'path': self.folder_path,
            'files': self.file_hashes,
            'timestamp': datetime.now().isoformat()
        }
        try:
            temp_path = self.snapshot_path + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(snapshot_data, f, separators=(',', ':'))
            os.replace(temp_path, self.snapshot_path)
            logger.info(f"Snapshot saved to {self.snapshot_path}")
            self.finished.emit()
        except Exception as e:
            logger.error(f"Error writing snapshot: {str(e)}")
            self.error.emit(str(e))

    def stop(self):
        self._is_running = False

class OptimizedContentLoaderWorker(QObject):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, folder_path, recursive, extensions=None):
        super().__init__()
        self.folder_path = folder_path
        self.recursive = recursive
        self.extensions = set(ext.lower() for ext in extensions) if extensions else None
        self._is_running = True
        logger.info(f"Content loader created for {folder_path}")

    def run(self):
        logger.info(f"[OptimizedContentLoaderWorker] Running for {self.folder_path} (Recursive: {self.recursive})")
        try:
            results = []
            files_processed = 0
            if self.recursive:
                for dirpath, dirnames, filenames in os.walk(self.folder_path):
                    if not self._is_running:
                        break
                    dirnames[:] = [d for d in dirnames if not d.startswith('.')]
                    for item_name in filenames:
                        if not self._is_running:
                            break
                        if item_name.startswith('.'):
                            continue
                        ext = os.path.splitext(item_name)[1].lower()
                        if self.extensions and ext not in self.extensions:
                            continue
                        full_path = os.path.join(dirpath, item_name)
                        try:
                            stats = os.stat(full_path)
                            relative_path = os.path.relpath(full_path, self.folder_path)
                            results.append((relative_path, stats, ext, False, full_path, stats.st_size))
                            files_processed += 1
                            if files_processed % 1000 == 0:
                                logger.debug(f"Processed {files_processed} files")
                        except (OSError, PermissionError) as e:
                            logger.warning(f"Could not access file {full_path}: {str(e)}")
                            continue
            else:
                try:
                    with os.scandir(self.folder_path) as entries:
                        for entry in entries:
                            if not self._is_running:
                                break
                            if entry.name.startswith('.'):
                                continue
                            try:
                                stats = entry.stat()
                                is_dir = entry.is_dir()
                                ext = os.path.splitext(entry.name)[1].lower() if not is_dir else ''
                                if self.extensions and not is_dir and ext not in self.extensions:
                                    continue
                                results.append((entry.name, stats, ext, is_dir, entry.path,
                                               stats.st_size if not is_dir else 0))
                                files_processed += 1
                            except (OSError, PermissionError) as e:
                                logger.warning(f"Could not access entry {entry.path}: {str(e)}")
                                continue
                except (OSError, PermissionError) as e:
                    raise Exception(f"Cannot access directory {self.folder_path}: {e}")
            if self._is_running:
                results.sort(key=lambda x: x[0].lower())
                logger.info(f"[OptimizedContentLoaderWorker] Finished for {self.folder_path}. Found {len(results)} items.")
                self.finished.emit(results)
        except Exception as e:
            logger.error(f"[OptimizedContentLoaderWorker] ERROR for {self.folder_path}: {e}")
            if self._is_running:
                self.error.emit(f"Could not load content: {e}")

    def stop(self):
        self._is_running = False

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  COMPARISON WORKERS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class SoftCompareWorker(QObject):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, left_folder, right_folder, left_files_data, right_files_data):
        super().__init__()
        self.left_files_data = left_files_data
        self.right_files_data = right_files_data
        self._is_running = True
        self.start_time = time.time()
        self.start_datetime = datetime.now()
        logger.info("Soft compare worker initialized")

    def run(self):
        try:
            if not self._is_running:
                return
            logger.info("[SoftCompareWorker] Starting soft comparison")
            left_files = {}
            for name, stats, ext, is_dir, full_path, file_size in self.left_files_data:
                if not is_dir and self._is_running:
                    left_files[name] = {'size': file_size, 'mod_time': stats.st_mtime, 'ext': ext}
            right_files = {}
            for name, stats, ext, is_dir, full_path, file_size in self.right_files_data:
                if not is_dir and self._is_running:
                    right_files[name] = {'size': file_size, 'mod_time': stats.st_mtime, 'ext': ext}
            if not self._is_running:
                return
            common_names = set(left_files.keys()) & set(right_files.keys())
            left_only = set(left_files.keys()) - set(right_files.keys())
            right_only = set(right_files.keys()) - set(left_files.keys())
            identical_files, different_files, similar_files = [], [], []
            total_files = len(common_names)
            processed_files = 0
            logger.info(f"Comparing {total_files} common files")
            for name in common_names:
                if not self._is_running:
                    break
                left_info, right_info = left_files[name], right_files[name]
                if left_info['size'] == right_info['size'] and abs(left_info['mod_time'] - right_info['mod_time']) < 1:
                    identical_files.append(name)
                elif left_info['size'] == right_info['size']:
                    similar_files.append(name)
                else:
                    different_files.append(name)
                processed_files += 1
                if processed_files % 100 == 0 or processed_files == total_files:
                    self.progress.emit(processed_files, total_files)
                    progress_percent = int((processed_files / total_files) * 100) if total_files > 0 else 0
                    logger.debug(f"Soft compare progress: {processed_files}/{total_files} ({progress_percent}%)")
                    QApplication.processEvents()
            if not self._is_running:
                return
            comparison_time = time.time() - self.start_time
            end_datetime = datetime.now()
            results = {
                'identical_files': identical_files,
                'different_files': different_files,
                'similar_files': similar_files,
                'left_only': list(left_only),
                'right_only': list(right_only),
                'comparison_time': comparison_time,
                'start_time': self.start_datetime,
                'end_time': end_datetime
            }
            if self._is_running:
                logger.info(f"[SoftCompareWorker] Finished - Identical: {len(identical_files)}, Different: {len(different_files)}, Similar: {len(similar_files)}")
                self.finished.emit(results)
        except Exception as e:
            logger.error(f"Soft compare error: {str(e)}")
            self.error.emit(str(e))

    def stop(self):
        self._is_running = False

class SmartCompareWorker(QObject):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, left_folder, right_folder, left_files_data, right_files_data):
        super().__init__()
        self.left_folder = left_folder
        self.right_folder = right_folder
        self.left_files_data = left_files_data
        self.right_files_data = right_files_data
        self._is_running = True
        self.start_time = time.time()
        self.start_datetime = datetime.now()
        self.file_hashes_left = {}
        self.file_hashes_right = {}
        self.total_files_to_hash = 0
        self.hashed_files = 0
        logger.info("Smart compare worker initialized")

    def run(self):
        try:
            if not self._is_running:
                return
            logger.info("[SmartCompareWorker] Starting smart comparison")
            similar_candidates = self._find_similar_candidates()
            
            # Set up progress tracking for hashing
            self.total_files_to_hash = len(similar_candidates) * 2  # Both left and right files
            self.hashed_files = 0
            
            logger.info(f"Found {len(similar_candidates)} similar candidates to hash")
            self._hash_similar_files(similar_candidates)
            comparison_results = self._compare_hashes(similar_candidates)
            comparison_time = time.time() - self.start_time
            end_datetime = datetime.now()
            comparison_results['comparison_time'] = comparison_time
            comparison_results['start_time'] = self.start_datetime
            comparison_results['end_time'] = end_datetime
            if self._is_running:
                logger.info(f"[SmartCompareWorker] Finished - Identical: {len(comparison_results['identical_files'])}, Different: {len(comparison_results['different_files'])}")
                self.finished.emit(comparison_results)
        except Exception as e:
            logger.error(f"Smart compare error: {str(e)}")
            self.error.emit(str(e))

    def _find_similar_candidates(self):
        left_files = {name: {'size': file_size, 'full_path': full_path}
                      for name, _, _, is_dir, full_path, file_size in self.left_files_data if not is_dir}
        right_files = {name: {'size': file_size, 'full_path': full_path}
                       for name, _, _, is_dir, full_path, file_size in self.right_files_data if not is_dir}
        return [name for name in (set(left_files.keys()) & set(right_files.keys()))
                if left_files[name]['size'] == right_files[name]['size']]

    def _hash_similar_files(self, similar_files):
        if not similar_files:
            return
            
        left_threadpool = QThreadPool()
        left_threadpool.setMaxThreadCount(MAX_THREADS)
        right_threadpool = QThreadPool()
        right_threadpool.setMaxThreadCount(MAX_THREADS)
        
        logger.info(f"Hashing {len(similar_files)} similar files from each side")
        # Create hashers for left files
        for name, _, _, is_dir, full_path, file_size in self.left_files_data:
            if not is_dir and name in similar_files:
                hasher = FastFileHasher(name, full_path, 
                                      partial(self._on_left_hash_result, name), file_size)
                left_threadpool.start(hasher)
        
        # Create hashers for right files
        for name, _, _, is_dir, full_path, file_size in self.right_files_data:
            if not is_dir and name in similar_files:
                hasher = FastFileHasher(name, full_path, 
                                      partial(self._on_right_hash_result, name), file_size)
                right_threadpool.start(hasher)
        
        # Wait for all hashing to complete
        left_threadpool.waitForDone(30000)
        right_threadpool.waitForDone(30000)

    def _on_left_hash_result(self, filename, hash_result, error_msg=None):
        if not self._is_running:
            return
        if hash_result:
            self.file_hashes_left[filename] = hash_result
            logger.debug(f"Hashed left file: {filename}")
        elif error_msg:
            logger.warning(f"Hash error for left file {filename}: {error_msg}")
        self.hashed_files += 1
        # Emit progress update based on hashed files
        if self.total_files_to_hash > 0:
            progress_percent = int((self.hashed_files / self.total_files_to_hash) * 100)
            logger.debug(f"Hashing progress: {self.hashed_files}/{self.total_files_to_hash} ({progress_percent}%)")
            self.progress.emit(self.hashed_files, self.total_files_to_hash)
        else:
            self.progress.emit(self.hashed_files, 1)

    def _on_right_hash_result(self, filename, hash_result, error_msg=None):
        if not self._is_running:
            return
        if hash_result:
            self.file_hashes_right[filename] = hash_result
            logger.debug(f"Hashed right file: {filename}")
        elif error_msg:
            logger.warning(f"Hash error for right file {filename}: {error_msg}")
        self.hashed_files += 1
        # Emit progress update based on hashed files
        if self.total_files_to_hash > 0:
            progress_percent = int((self.hashed_files / self.total_files_to_hash) * 100)
            logger.debug(f"Hashing progress: {self.hashed_files}/{self.total_files_to_hash} ({progress_percent}%)")
            self.progress.emit(self.hashed_files, self.total_files_to_hash)
        else:
            self.progress.emit(self.hashed_files, 1)

    def _compare_hashes(self, similar_candidates):
        identical_files, different_files = [], []
        left_names = {name for name, _, _, is_dir, _, _ in self.left_files_data if not is_dir}
        right_names = {name for name, _, _, is_dir, _, _ in self.right_files_data if not is_dir}
        common_names = left_names & right_names
        logger.info(f"Comparing hashes for {len(similar_candidates)} files")
        for filename in similar_candidates:
            left_hash = self.file_hashes_left.get(filename)
            right_hash = self.file_hashes_right.get(filename)
            if left_hash and right_hash:
                (identical_files if left_hash == right_hash else different_files).append(filename)
        different_size_files = [name for name in common_names if name not in similar_candidates]
        different_files.extend(different_size_files)
        return {
            'identical_files': identical_files,
            'different_files': different_files,
            'similar_files': [],
            'left_only': list(left_names - right_names),
            'right_only': list(right_names - left_names)
        }

    def stop(self):
        self._is_running = False

class DeepCompareWorker(QObject):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, left_folder, right_folder, left_files_data, right_files_data):
        super().__init__()
        self.left_folder = left_folder
        self.right_folder = right_folder
        self.left_files_data = left_files_data
        self.right_files_data = right_files_data
        self._is_running = True
        self.start_time = time.time()
        self.start_datetime = datetime.now()
        self.file_hashes_left = {}
        self.file_hashes_right = {}
        self.total_files = 0
        self.hashed_files = 0
        logger.info("Deep compare worker initialized")

    def run(self):
        try:
            if not self._is_running:
                return
            logger.info("[DeepCompareWorker] Starting deep comparison")
            
            # Count total files for progress tracking
            left_file_count = sum(1 for _, _, _, is_dir, _, _ in self.left_files_data if not is_dir)
            right_file_count = sum(1 for _, _, _, is_dir, _, _ in self.right_files_data if not is_dir)
            self.total_files = left_file_count + right_file_count
            self.hashed_files = 0
            
            logger.info(f"Hashing {left_file_count} left files and {right_file_count} right files")
            self._hash_all_files()
            comparison_results = self._compare_all_hashes()
            comparison_time = time.time() - self.start_time
            end_datetime = datetime.now()
            comparison_results['comparison_time'] = comparison_time
            comparison_results['start_time'] = self.start_datetime
            comparison_results['end_time'] = end_datetime
            if self._is_running:
                logger.info(f"[DeepCompareWorker] Finished - Identical: {len(comparison_results['identical_files'])}, Different: {len(comparison_results['different_files'])}")
                self.finished.emit(comparison_results)
        except Exception as e:
            logger.error(f"Deep compare error: {str(e)}")
            self.error.emit(str(e))

    def _hash_all_files(self):
        left_threadpool = QThreadPool()
        left_threadpool.setMaxThreadCount(MAX_THREADS)
        right_threadpool = QThreadPool()
        right_threadpool.setMaxThreadCount(MAX_THREADS)
        
        logger.info("Hashing all files...")
        # Hash left files
        for name, _, _, is_dir, full_path, file_size in self.left_files_data:
            if not is_dir:
                hasher = FastFileHasher(name, full_path, 
                                      partial(self._on_left_hash_result, name), file_size)
                left_threadpool.start(hasher)
        
        # Hash right files
        for name, _, _, is_dir, full_path, file_size in self.right_files_data:
            if not is_dir:
                hasher = FastFileHasher(name, full_path, 
                                      partial(self._on_right_hash_result, name), file_size)
                right_threadpool.start(hasher)
        
        # Wait for all hashing to complete
        left_threadpool.waitForDone(60000)
        right_threadpool.waitForDone(60000)

    def _on_left_hash_result(self, filename, hash_result, error_msg=None):
        if not self._is_running:
            return
        if hash_result:
            self.file_hashes_left[filename] = hash_result
            logger.debug(f"Hashed left file: {filename}")
        elif error_msg:
            logger.warning(f"Hash error for left file {filename}: {error_msg}")
        self.hashed_files += 1
        # Emit progress update based on hashed files
        if self.total_files > 0:
            progress_percent = int((self.hashed_files / self.total_files) * 100)
            logger.debug(f"Hashing progress: {self.hashed_files}/{self.total_files} ({progress_percent}%)")
            self.progress.emit(self.hashed_files, self.total_files)
        else:
            self.progress.emit(self.hashed_files, 1)

    def _on_right_hash_result(self, filename, hash_result, error_msg=None):
        if not self._is_running:
            return
        if hash_result:
            self.file_hashes_right[filename] = hash_result
            logger.debug(f"Hashed right file: {filename}")
        elif error_msg:
            logger.warning(f"Hash error for right file {filename}: {error_msg}")
        self.hashed_files += 1
        # Emit progress update based on hashed files
        if self.total_files > 0:
            progress_percent = int((self.hashed_files / self.total_files) * 100)
            logger.debug(f"Hashing progress: {self.hashed_files}/{self.total_files} ({progress_percent}%)")
            self.progress.emit(self.hashed_files, self.total_files)
        else:
            self.progress.emit(self.hashed_files, 1)

    def _compare_all_hashes(self):
        identical_files, different_files, similar_files = [], [], []
        left_names = set(self.file_hashes_left.keys())
        right_names = set(self.file_hashes_right.keys())
        common_names = left_names & right_names
        logger.info(f"Comparing hashes for {len(common_names)} common files")
        for filename in common_names:
            left_hash = self.file_hashes_left[filename]
            right_hash = self.file_hashes_right[filename]
            (identical_files if left_hash == right_hash else different_files).append(filename)
        left_sizes = {}
        for name, _, _, _, _, file_size in self.left_files_data:
            if not name.startswith('.') and name in self.file_hashes_left:
                left_sizes.setdefault(file_size, []).append(name)
        right_sizes = {}
        for name, _, _, _, _, file_size in self.right_files_data:
            if not name.startswith('.') and name in self.file_hashes_right:
                right_sizes.setdefault(file_size, []).append(name)
        common_sizes = set(left_sizes.keys()) & set(right_sizes.keys())
        for size in common_sizes:
            left_names_for_size = set(left_sizes[size])
            right_names_for_size = set(right_sizes[size])
            size_matches = (left_names_for_size - right_names_for_size) | (right_names_for_size - left_names_for_size)
            similar_files.extend(size_matches)
        return {
            'identical_files': identical_files,
            'different_files': different_files,
            'similar_files': similar_files,
            'left_only': list(left_names - right_names),
            'right_only': list(right_names - left_names)
        }

    def stop(self):
        self._is_running = False

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  OVERLAY WIDGETS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class CentralComparisonOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setVisible(False)
        self.angle = 0
        self.timer = QTimer(self, interval=50)
        self.timer.timeout.connect(self.update_animation)

        layout = QVBoxLayout(self)
        layout.addStretch()
        container = QWidget()
        container.setFixedSize(450, 250)
        container.setStyleSheet("background-color: rgba(42, 42, 42, 200); border-radius: 10px; border: 2px solid #05B8CC;")
        vbox = QVBoxLayout(container)

        self.title_label = QLabel("Comparing Files...")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        vbox.addWidget(self.title_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 2px solid grey; border-radius: 5px; text-align: center; background-color: #2a2a2a; color: white; height: 20px; }
            QProgressBar::chunk { background-color: #05B8CC; width: 10px; margin: 0.5px; }
        """)
        vbox.addWidget(self.progress_bar)

        self.percentage_label = QLabel("0%")
        self.percentage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.percentage_label.setStyleSheet("color: white; font-size: 14px; margin-top: 10px;")
        vbox.addWidget(self.percentage_label)

        self.cancel_button = QPushButton("Cancel Comparison")
        self.cancel_button.setStyleSheet("""
            QPushButton { background-color: #ff4444; color: white; border: none; padding: 8px 16px; border-radius: 5px; font-weight: bold; margin-top: 15px; }
            QPushButton:hover { background-color: #cc3333; }
            QPushButton:pressed { background-color: #aa2222; }
        """)
        vbox.addWidget(self.cancel_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(container, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

    def paintEvent(self, event):
        if not self.isVisible():
            return
        painter = QPainter(self)
        if painter.isActive():
            painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(self.rect())
            painter.end()

    def show_comparison(self, title="Comparing Files...", cancel_callback=None):
        self.title_label.setText(title)
        self.progress_bar.setValue(0)
        self.percentage_label.setText("0%")
        if cancel_callback:
            self.cancel_button.clicked.connect(cancel_callback)
        self.resize(self.parent().size())
        self.setVisible(True)
        self.raise_()
        self.timer.start()

    def hide_comparison(self):
        self.timer.stop()
        self.setVisible(False)
        try:
            self.cancel_button.disconnect()
        except:
            pass

    def set_progress(self, current, total):
        if total <= 0:
            return
        percentage = int((current / total) * 100)
        self.progress_bar.setValue(percentage)
        self.percentage_label.setText(f"{percentage}%")
        logger.debug(f"Progress update: {current}/{total} ({percentage}%)")

    def update_animation(self):
        self.angle = (self.angle + 12) % 360
        self.update()

class OptimizedLoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setVisible(False)
        self.angle = 0
        self.timer = QTimer(self, interval=50)
        self.timer.timeout.connect(self.update_animation)

        layout = QVBoxLayout(self)
        layout.addStretch()
        self.label = QLabel("Loading...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 2px solid grey; border-radius: 5px; text-align: center; background-color: #2a2a2a; color: white; }
            QProgressBar::chunk { background-color: #05B8CC; width: 10px; margin: 0.5px; }
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        layout.addStretch()

    def paintEvent(self, event):
        if not self.isVisible():
            return
        painter = QPainter(self)
        if painter.isActive():
            painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(self.rect())
            painter.end()

    def start_animation(self, text="Discovering..."):
        self.label.setText(text)
        self.progress_bar.setVisible(False)
        self.resize(self.parent().size())
        self.setVisible(True)
        self.raise_()
        self.timer.start()

    def stop_animation(self):
        self.timer.stop()
        self.setVisible(False)

    def set_progress(self, current, total):
        if total <= 0:
            return
        percentage = int((current / total) * 100)
        self.label.setText(f"{self.label.text().split()[0]} {percentage}%")
        if not self.progress_bar.isVisible():
            self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"{percentage}%")
        logger.debug(f"Loading progress: {current}/{total} ({percentage}%)")

    def update_animation(self):
        self.angle = (self.angle + 12) % 360
        self.update()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  TABLE ITEM & REPORT WINDOW
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class OptimizedCustomTableWidgetItem(QTableWidgetItem):
    __slots__ = ()
    def __lt__(self, other):
        try:
            data_self = self.data(Qt.ItemDataRole.UserRole)
            data_other = other.data(Qt.ItemDataRole.UserRole)
            if data_self is not None and data_other is not None:
                if type(data_self) == type(data_other):
                    return data_self < data_other
                elif isinstance(data_self, (int, float)) and isinstance(data_other, (int, float)):
                    return data_self < data_other
                elif isinstance(data_self, datetime) and isinstance(data_other, datetime):
                    return data_self < data_other
            return self.text().lower() < other.text().lower()
        except:
            return super().__lt__(other)

class OptimizedReportWindow(QWidget):
    def __init__(self, title, report_text):
        super().__init__()
        self.setWindowTitle(title)
        self.setGeometry(250, 250, 800, 600)
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Consolas", 10))
        self.text_edit.setReadOnly(True)
        self.text_edit.setPlainText(report_text)
        layout.addWidget(self.text_edit)
        hbox = QHBoxLayout()
        hbox.addStretch()
        save_button = QPushButton("Save Report")
        save_button.clicked.connect(self.save_report)
        hbox.addWidget(save_button)
        layout.addLayout(hbox)

    def save_report(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Report", "comparison_report.txt", "Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.text_edit.toPlainText())
                QMessageBox.information(self, "Success", "Report saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save report:\n{e}")

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  FILE PANEL
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class OptimizedFilePanel(QFrame):
    selection_changed = pyqtSignal()
    snapshot_ready = pyqtSignal()
    hashing_progress = pyqtSignal(int, int)
    STATUS_COLUMN = 4

    def __init__(self, side_name, main_window):
        super().__init__()
        logger.info(f"OptimizedFilePanel '{side_name}' created")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.side_name = side_name
        self.main_window = main_window
        self.content_type = None
        self.folder_path = None
        self.file_path = None
        self.snapshot_path = None
        self.thread = None
        self.worker = None
        self.is_busy = False
        self.loaded_files_data = None
        self.snapshot_finished_internal = False
        self.current_extensions = None
        self.active_filter_button = None
        self.comparison_results = None

        # Main layout
        panel_layout = QVBoxLayout(self)

        # Top buttons
        top_bar_layout = QHBoxLayout()
        panel_layout.addLayout(top_bar_layout)

        # Status filter row - moved to be clearly visible
        status_filter_layout = QHBoxLayout()
        panel_layout.addLayout(status_filter_layout)
        status_filter_layout.addWidget(QLabel("Filter by Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems([
            "All Files",
            "Identical Files",
            "Different Files",
            "Similar Files",
            f"Unique in {self.side_name}",
            f"Unique in Other"
        ])
        self.status_filter.currentTextChanged.connect(self.apply_status_filter)
        status_filter_layout.addWidget(self.status_filter)
        status_filter_layout.addStretch()

        # Extension filter row
        filter_bar_layout = QHBoxLayout()
        panel_layout.addLayout(filter_bar_layout)

        # Path label
        self.path_label = QLabel("No content loaded")
        self.path_label.setStyleSheet("padding: 4px; background-color: #2a2a2a; border-radius: 4px; font-style: italic;")
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(self.path_label)

        # Stacked widgets
        self.stacked_layout = QStackedLayout()
        self.table_widget = self._create_optimized_table_widget()
        self.text_viewer = self._create_text_viewer()
        self.add_prompt_button = self._create_prompt_button()
        self.stacked_layout.addWidget(self.table_widget)
        self.stacked_layout.addWidget(self.text_viewer)
        self.stacked_layout.addWidget(self.add_prompt_button)
        panel_layout.addLayout(self.stacked_layout)
        self.stacked_layout.setCurrentWidget(self.add_prompt_button)

        # Bottom bar - reorganized to show status clearly and avoid hiding
        bottom_layout = QHBoxLayout()
        
        # Status label - moved to be clearly visible and given more space
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-style: italic; padding: 4px;")
        self.status_label.setMinimumHeight(40)  # Increased height to accommodate multiple lines
        self.status_label.setWordWrap(True)  # Enable word wrapping
        bottom_layout.addWidget(self.status_label, 1)  # Give it stretch factor
        
        # Cancel button - moved to the far right
        self.cancel_button = QPushButton("Clear Panel")
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self.clear_panel)
        bottom_layout.addWidget(self.cancel_button)

        panel_layout.addLayout(bottom_layout)

        # Move-related controls (under the move button)
        self.move_control_widget = QWidget()
        move_layout = QHBoxLayout(self.move_control_widget)
        move_layout.setContentsMargins(0, 0, 0, 0)

        self.keep_tree_checkbox = QCheckBox("Keep folder tree")
        self.keep_tree_checkbox.setChecked(True)
        move_layout.addWidget(self.keep_tree_checkbox)

        self.move_button = QPushButton("Move →")
        self.move_button.clicked.connect(self.on_move_pressed)
        move_layout.addWidget(self.move_button)

        self.move_control_widget.setVisible(False)
        bottom_layout.addWidget(self.move_control_widget)
        panel_layout.addLayout(bottom_layout)

        # Buttons
        self._create_buttons(top_bar_layout, filter_bar_layout)

        # Overlays
        self.setAcceptDrops(True)
        self.loading_overlay = OptimizedLoadingOverlay(self)
        self.setMinimumWidth(400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def resizeEvent(self, event):
        self.loading_overlay.resize(event.size())
        super().resizeEvent(event)

    def clear_panel(self):
        logger.info(f"[{self.side_name}] Clearing panel")
        self.cleanup_thread()
        self.content_type = None
        self.folder_path = None
        self.file_path = None
        self.snapshot_path = None
        self.path_label.setText("No content loaded")
        self.status_label.setText("")
        self.loaded_files_data = None
        self.snapshot_finished_internal = False
        self.comparison_results = None
        self.stacked_layout.setCurrentWidget(self.add_prompt_button)
        self.move_button.setVisible(False)
        self.cancel_button.setVisible(False)
        self.clear_highlighting()
        self.status_filter.setCurrentText("All Files")
        self.main_window.on_panel_cleared()

    def _create_optimized_table_widget(self):
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Name", "Last Modified", "Type", "Size", "Status"])
        table.setColumnHidden(self.STATUS_COLUMN, False)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(False)
        table.setSortingEnabled(True)
        table.itemSelectionChanged.connect(self.selection_changed.emit)
        table.setWordWrap(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        return table
    
    def set_move_button_direction(self, to_right: bool):
        """Set the arrow on the move button (True = →, False = ←)"""
        self.move_button.setText("Move →" if to_right else "Move ←")

    def _create_text_viewer(self):
        viewer = QTextEdit()
        viewer.setReadOnly(True)
        viewer.setFont(QFont("Consolas", 10))
        viewer.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        return viewer

    def _create_prompt_button(self):
        button = QPushButton("+\n\nDrag & Drop Folder or Text File")
        button.setFont(QFont("Segoe UI", 18))
        button.setStyleSheet("color: #6a717b; border: 2px dashed #6a717b;")
        button.clicked.connect(self.add_folder)
        return button

    def _create_buttons(self, top_bar, filter_bar):
        self.btn_add = QPushButton("Add Folder")
        self.btn_add.clicked.connect(self.add_folder)
        top_bar.addWidget(self.btn_add)

        self.btn_save = QPushButton("Save List")
        self.btn_save.clicked.connect(self.save_file_list)
        top_bar.addWidget(self.btn_save)

        self.recursive_checkbox = QCheckBox("Subfolders")
        self.recursive_checkbox.setChecked(True)
        self.recursive_checkbox.stateChanged.connect(self.reload_content)
        filter_bar.addWidget(self.recursive_checkbox)

        filter_bar.addWidget(QLabel("File Type Filters:"))

        self.filter_buttons = {
            'all': QPushButton("All"),
            'images': QPushButton("Images"),
            'docs': QPushButton("Documents"),
            'audio': QPushButton("Audio"),
            'video': QPushButton("Video"),
            'custom': QPushButton("Custom...")
        }
        self.filter_buttons['all'].setFixedWidth(40)     # <<< NEW – make "All" narrow

        filter_extensions = {
            'images': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'],
            'docs': ['.txt', '.pdf', '.doc', '.docx', '.rtf', '.odt'],
            'audio': ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a'],
            'video': ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv']
        }

        self.filter_buttons['all'].clicked.connect(lambda: self.apply_extension_filter(self.filter_buttons['all']))
        for filter_name, extensions in filter_extensions.items():
            self.filter_buttons[filter_name].clicked.connect(
                lambda _, btn=self.filter_buttons[filter_name], ext=extensions:
                self.apply_extension_filter(btn, ext)
            )
        self.filter_buttons['custom'].clicked.connect(self.show_custom_filter_dialog)
        for btn in self.filter_buttons.values():
            filter_bar.addWidget(btn)
        filter_bar.addStretch()

    def load_content(self):
        if not self.folder_path or self.is_busy:
            return
        logger.info(f"[{self.side_name}] Starting load for: {self.folder_path}")
        self.is_busy = True
        self.main_window.on_panel_cleared()
        self.loading_overlay.start_animation("Loading...")
        self.cleanup_thread()
        self.thread = QThread()
        self.worker = OptimizedContentLoaderWorker(
            self.folder_path, self.recursive_checkbox.isChecked(), self.current_extensions
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_loading_finished)
        self.worker.error.connect(self.on_loading_error)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def on_loading_finished(self, results):
        logger.info(f"[{self.side_name}] Finished loading. {len(results)} items")
        self.table_widget.setSortingEnabled(False)
        self.table_widget.setRowCount(0)
        self.loaded_files_data = results
        self.table_widget.setRowCount(len(results))
        for row, (name, stats, ext, is_dir, full_path, file_size) in enumerate(results):
            self.add_file_to_table_at_row(row, name, stats, ext, is_dir)
        self.table_widget.setSortingEnabled(True)
        self.stacked_layout.setCurrentWidget(self.table_widget)
        self.status_label.setText(f"{len(results)} items")
        self.cancel_button.setVisible(True)
        self.is_busy = False
        self.loading_overlay.stop_animation()
        self.move_button.setVisible(True)
        if self.main_window.initial_splitter_state:
            self.main_window.splitter.restoreState(self.main_window.initial_splitter_state)
        self.main_window.update_button_states()

    def add_file_to_table_at_row(self, row, name, stats, ext, is_dir):
        mod_time = datetime.fromtimestamp(stats.st_mtime)
        name_item = OptimizedCustomTableWidgetItem(name)
        name_item.setData(Qt.ItemDataRole.UserRole, name)
        time_item = OptimizedCustomTableWidgetItem(mod_time.strftime('%Y-%m-%d %H:%M'))
        time_item.setData(Qt.ItemDataRole.UserRole, mod_time)
        type_item = OptimizedCustomTableWidgetItem("Folder" if is_dir else f"{ext.upper()} File")
        size_item = OptimizedCustomTableWidgetItem("")
        if not is_dir:
            size_item.setText(self.format_size(stats.st_size))
            size_item.setData(Qt.ItemDataRole.UserRole, stats.st_size)
        else:
            size_item.setData(Qt.ItemDataRole.UserRole, -1)
        status_item = OptimizedCustomTableWidgetItem("")
        status_item.setData(Qt.ItemDataRole.UserRole, STATUS_BLANK)

        self.table_widget.setItem(row, 0, name_item)
        self.table_widget.setItem(row, 1, time_item)
        self.table_widget.setItem(row, 2, type_item)
        self.table_widget.setItem(row, 3, size_item)
        self.table_widget.setItem(row, 4, status_item)

    def format_size(self, size_bytes):
        if size_bytes <= 0:
            return "0 B"
        size_names = ("B", "KB", "MB", "GB", "TB")
        i = min(int(math.floor(math.log(size_bytes, 1024))), len(size_names) - 1)
        p = math.pow(1024, i)
        return f"{round(size_bytes / p, 2)} {size_names[i]}"

    def on_loading_error(self, err_msg):
        logger.error(f"[{self.side_name}] Loading error: {err_msg}")
        QMessageBox.critical(self, "Error", err_msg)
        self.is_busy = False
        self.loading_overlay.stop_animation()
        self.main_window.update_button_states()

    def cleanup_thread(self):
        if self.thread:
            if self.thread.isRunning():
                if self.worker:
                    self.worker.stop()
                self.thread.quit()
                self.thread.wait(5000)
                if self.thread.isRunning():
                    self.thread.terminate()
                    self.thread.wait(2000)
            try:
                self.thread.disconnect()
            except:
                pass
            self.thread.deleteLater()
            self.thread = None
            self.worker = None

    def create_snapshot(self, loaded_files_data):
        self.snapshot_path = None
        self.cleanup_thread()
        self.snapshot_finished_internal = False
        snapshot_filename = (hashlib.md5(self.folder_path.encode()).hexdigest() if not HAS_XXHASH
                           else xxhash.xxh64(self.folder_path.encode()).hexdigest()) + ".json"
        self.snapshot_path = os.path.join(self.main_window.cache_dir, snapshot_filename)
        files_for_hashing = [(res[0], res[4], res[5]) for res in loaded_files_data if not res[3]]
        self.thread = QThread()
        self.worker = OptimizedSnapshotWorker(self.folder_path, self.snapshot_path, files_for_hashing)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_snapshot_worker_finished)
        self.worker.error.connect(self._on_snapshot_worker_error)
        self.worker.progress.connect(self.loading_overlay.set_progress)
        self.worker.progress.connect(self.hashing_progress.emit)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.start()

    def _on_snapshot_worker_finished(self):
        logger.info(f"[{self.side_name}] Snapshot worker finished")
        self.snapshot_finished_internal = True
        self.snapshot_ready.emit()

    def _on_snapshot_worker_error(self, err_msg):
        logger.error(f"[{self.side_name}] Snapshot error: {err_msg}")
        self.snapshot_path = None
        self.snapshot_finished_internal = True
        self.snapshot_ready.emit()
        QMessageBox.critical(self, "Snapshot Error", f"Error creating snapshot for {self.side_name}:\n{err_msg}")

    def load_text_file(self, file_path):
        if self.is_busy:
            return
        logger.info(f"[{self.side_name}] Loading text file: {file_path}")
        self.is_busy = True
        self.loading_overlay.start_animation("Loading text file...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.text_viewer.setPlainText(content)
            self.stacked_layout.setCurrentWidget(self.text_viewer)
            self.path_label.setText(f"Text file: {os.path.basename(file_path)}")
            self.status_label.setText(f"{len(content)} chars")
            self.cancel_button.setVisible(True)
        except Exception as e:
            logger.error(f"[{self.side_name}] Error loading text file: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not load text file:\n{e}")
        finally:
            self.is_busy = False
            self.loading_overlay.stop_animation()
            self.main_window.update_button_states()

    def add_folder(self):
        if self.is_busy:
            return
        folder_path = QFileDialog.getExistingDirectory(self, f"Select {self.side_name} Folder")
        if folder_path:
            self.load_folder(folder_path)

    def on_move_pressed(self):
        if self.side_name == "Left":
            self.main_window.move_visible_files(self, self.main_window.right_panel)
        else:
            self.main_window.move_visible_files(self, self.main_window.left_panel)

    def load_folder(self, folder_path):
        if self.is_busy:
            return
        logger.info(f"[{self.side_name}] Loading folder: {folder_path}")
        self.content_type = "folder"
        self.folder_path = folder_path
        self.path_label.setText(folder_path)
        self.load_content()

    def reload_content(self):
        if self.content_type == "folder" and self.folder_path:
            self.load_content()

    def save_file_list(self):
        if not self.loaded_files_data:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File List", f"{self.side_name}_file_list.txt", "Text Files (*.txt)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"File list for {self.folder_path}\n")
                    f.write("=" * 50 + "\n\n")
                    for name, stats, ext, is_dir, full_path, file_size in self.loaded_files_data:
                        if is_dir:
                            f.write(f"[DIR] {name}\n")
                        else:
                            f.write(f"{name}\t{self.format_size(file_size)}\t{ext}\n")
                QMessageBox.information(self, "Success", "File list saved successfully.")
            except Exception as e:
                logger.error(f"[{self.side_name}] Error saving file list: {str(e)}")
                QMessageBox.critical(self, "Error", f"Could not save file list:\n{e}")

    def apply_extension_filter(self, button, extensions=None):
        if self.is_busy:
            return
        for btn in self.filter_buttons.values():
            btn.setStyleSheet("")
        button.setStyleSheet(FILTER_HIGHLIGHT_STYLE)
        self.active_filter_button = button
        self.current_extensions = None if button == self.filter_buttons['all'] else extensions
        if self.content_type == "folder":
            self.load_content()
        # Re-apply the comparison colours/status when reloading finishes
        if self.comparison_results:
            self.apply_comparison_results(self.comparison_results)

    def show_custom_filter_dialog(self):
        if self.is_busy:
            return
        current_filter = ",".join(self.current_extensions) if self.current_extensions else ""
        extensions, ok = QInputDialog.getText(
            self, "Custom Filter",
            "Enter file extensions (comma-separated):\nExample: .txt,.csv,.json",
            text=current_filter
        )
        if ok:
            self.current_extensions = [ext.strip() for ext in extensions.split(",") if ext.strip()] if extensions.strip() else None
            for btn in self.filter_buttons.values():
                btn.setStyleSheet("")
            self.filter_buttons['custom'].setStyleSheet(FILTER_HIGHLIGHT_STYLE)
            if self.content_type == "folder":
                self.load_content()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if self.is_busy:
            return
        urls = event.mimeData().urls()
        if urls:
            url = urls[0]
            path = url.toLocalFile()
            logger.info(f"[{self.side_name}] Drop event: {path}")
            if os.path.isdir(path):
                self.load_folder(path)
            elif os.path.isfile(path):
                ext = os.path.splitext(path)[1].lower()
                if ext in ['.txt', '.csv', '.json', '.xml', '.log']:
                    self.load_text_file(path)
                else:
                    QMessageBox.warning(self, "Warning", "Only text files can be loaded directly.")

    # COMPARISON RESULTS UTILITIES
    def apply_comparison_results(self, comparison_results):
        if not self.loaded_files_data or not self.table_widget.isVisible():
            return
        logger.info(f"[{self.side_name}] Applying comparison results")
        self.comparison_results = comparison_results
        
        # Show progress indicator
        progress_dialog = QProgressDialog("Applying comparison results to UI...", "Cancel", 0, 100, self)
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setAutoClose(True)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.show()
        
        # Optimize performance for large datasets
        self.table_widget.setSortingEnabled(False)
        self.table_widget.setUpdatesEnabled(False)
        QApplication.processEvents()  # Allow UI to update before starting
        
        self.clear_highlighting()
        status_col = self.STATUS_COLUMN
        
        # Create lookup dictionaries for O(1) access instead of lists
        identical_files = set(comparison_results.get('identical_files', []))
        different_files = set(comparison_results.get('different_files', []))
        similar_files = set(comparison_results.get('similar_files', []))
        left_only = set(comparison_results.get('left_only', []))
        right_only = set(comparison_results.get('right_only', []))
        
        total_rows = self.table_widget.rowCount()
        
        # Batch update all rows at once for better performance
        for row in range(total_rows):
            # Update progress every 100 rows
            if row % 100 == 0:
                progress = int((row / total_rows) * 100)
                progress_dialog.setValue(progress)
                QApplication.processEvents()
                if progress_dialog.wasCanceled():
                    break
                    
            file_name_item = self.table_widget.item(row, 0)
            if not file_name_item:
                continue
            file_name = file_name_item.text()
            
            status_item = self.table_widget.item(row, status_col)
            if not status_item:
                status_item = QTableWidgetItem()
                self.table_widget.setItem(row, status_col, status_item)
                
            # Use set membership testing for better performance
            if file_name in identical_files:
                status_item.setText("Identical")
                status_item.setData(Qt.ItemDataRole.UserRole, STATUS_IDENTICAL)
                self.highlight_row(row, COLOR_IDENTICAL)
            elif file_name in different_files:
                status_item.setText("Different")
                status_item.setData(Qt.ItemDataRole.UserRole, STATUS_DIFFERENT)
                self.highlight_row(row, COLOR_DIFFERENT)
            elif file_name in similar_files:
                status_item.setText("Similar")
                status_item.setData(Qt.ItemDataRole.UserRole, STATUS_SIMILAR)
                self.highlight_row(row, COLOR_SIMILAR)
            elif file_name in left_only:
                status_item.setText("Unique" if self.side_name == "Left" else "Missing")
                status_item.setData(Qt.ItemDataRole.UserRole, STATUS_DIFFERENT)
                self.highlight_row(row, COLOR_DIFFERENT)
            elif file_name in right_only:
                status_item.setText("Unique" if self.side_name == "Right" else "Missing")
                status_item.setData(Qt.ItemDataRole.UserRole, STATUS_DIFFERENT)
                self.highlight_row(row, COLOR_DIFFERENT)
            else:
                status_item.setText("")
                status_item.setData(Qt.ItemDataRole.UserRole, STATUS_BLANK)

        # Update statistics
        left_unique = len(comparison_results.get('left_only', []))
        right_unique = len(comparison_results.get('right_only', []))
        self.status_label.setText(
            f"Comparison: {len(comparison_results.get('identical_files', []))} identical, "
            f"{len(comparison_results.get('different_files', []))} different, "
            f"{len(comparison_results.get('similar_files', []))} similar\n"
            f"Unique files: Left({left_unique}) Right({right_unique})"
        )
        
        # Close progress dialog
        progress_dialog.setValue(100)
        
        # Re-enable UI updates and sorting
        self.table_widget.setUpdatesEnabled(True)
        self.table_widget.setSortingEnabled(True)
        QApplication.processEvents()  # Force UI refresh
        
        logger.info(f"[{self.side_name}] Finished applying comparison results to UI")

    def apply_status_filter(self, filter_text):
        if not self.comparison_results or not self.loaded_files_data:
            return
            
        # Optimize performance for large datasets
        table = self.table_widget
        table.setUpdatesEnabled(False)
        QApplication.processEvents()  # Allow UI to update before starting
        
        # Show all rows first
        for row in range(table.rowCount()):
            table.setRowHidden(row, False)
            
        if filter_text == "All Files":
            table.setUpdatesEnabled(True)
            return
            
        # Create lookup sets for faster membership testing
        identical_files = set(self.comparison_results.get('identical_files', []))
        different_files = set(self.comparison_results.get('different_files', []))
        similar_files = set(self.comparison_results.get('similar_files', []))
        
        if self.side_name == "Left":
            unique_files = set(self.comparison_results.get('left_only', []))
            other_unique_files = set(self.comparison_results.get('right_only', []))
        else:
            unique_files = set(self.comparison_results.get('right_only', []))
            other_unique_files = set(self.comparison_results.get('left_only', []))
            
        # Hide rows that don't match the filter
        for row in range(table.rowCount()):
            file_name_item = table.item(row, 0)
            if not file_name_item:
                continue
            file_name = file_name_item.text()
            hide = True
            if filter_text == "Identical Files":
                hide = file_name not in identical_files
            elif filter_text == "Different Files":
                hide = file_name not in different_files
            elif filter_text == "Similar Files":
                hide = file_name not in similar_files
            elif filter_text == f"Unique in {self.side_name}":
                hide = file_name not in unique_files
            elif filter_text == f"Unique in Other":
                hide = file_name not in other_unique_files
            table.setRowHidden(row, hide)
            
        table.setUpdatesEnabled(True)
        QApplication.processEvents()  # Force UI refresh

    def highlight_row(self, row, color):
        # Optimize performance for large datasets
        table = self.table_widget
        table.setUpdatesEnabled(False)
        for col in range(table.columnCount()):
            item = table.item(row, col)
            if item:
                item.setBackground(color)
        table.setUpdatesEnabled(True)

    def clear_highlighting(self):
        # Optimize performance for large datasets
        table = self.table_widget
        table.setUpdatesEnabled(False)
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item:
                    item.setBackground(COLOR_BLANK)
        table.setUpdatesEnabled(True)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  MAIN WINDOW
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class OptimizedFileManager(QMainWindow):
    log_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        logger.info("OptimizedFileManager.__init__ - Start")
        self.setWindowTitle("Advanced Python File Comparing")
        self.setGeometry(100, 100, 1200, 800)
        self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"Cache directory set to: {self.cache_dir}")
        
        # Set up GUI logging
        self.log_signal = QtLogHandler(self.log_message)
        self.log_signal.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(self.log_signal)
        
        self.init_ui()
        self.comparison_thread = None
        self.comparison_worker = None
        self.last_comparison_results = None
        self.last_comparison_start_time = None
        self.last_comparison_end_time = None  # This will store the actual end time when UI is updated
        logger.info("OptimizedFileManager.__init__ - End")

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter)

        self.left_panel = OptimizedFilePanel("Left", self)
        self.right_panel = OptimizedFilePanel("Right", self)
        self.splitter.addWidget(self.left_panel)
        self.left_panel.set_move_button_direction(True)   # Left → Right
        self.splitter.addWidget(self.right_panel)
        self.right_panel.set_move_button_direction(False)  # Right → Left
        self.splitter.setSizes([600, 600])
        self.initial_splitter_state = self.splitter.saveState()

        self.central_comparison_overlay = CentralComparisonOverlay(self)

        self.report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report")
        os.makedirs(self.report_dir, exist_ok=True)
        self.central_comparison_overlay.hide()

        # Comparison buttons
        mid_layout = QHBoxLayout()
        layout.addLayout(mid_layout)
        mid_layout.addStretch()
        self.btn_soft_compare = QPushButton("Soft Compare")
        self.btn_soft_compare.clicked.connect(lambda: self.start_comparison("soft"))
        self.btn_soft_compare.setToolTip(
            "Soft Compare: quickly compares files by size and last-modified time."
        )
        mid_layout.addWidget(self.btn_soft_compare)

        self.btn_smart_compare = QPushButton("Smart Compare")
        self.btn_smart_compare.clicked.connect(lambda: self.start_comparison("smart"))
        self.btn_smart_compare.setToolTip(
            "Smart compare: compares files by size, then hashes only same-size files."
        )
        mid_layout.addWidget(self.btn_smart_compare)

        self.btn_deep_compare = QPushButton("Deep Compare")
        self.btn_deep_compare.clicked.connect(lambda: self.start_comparison("deep"))
        self.btn_deep_compare.setToolTip(
            "Deep compare: hashes every file and compares full contents."
        )
        mid_layout.addWidget(self.btn_deep_compare)

        self.btn_apply_results = QPushButton("See Results in App")
        self.btn_apply_results.clicked.connect(self.apply_comparison_results)
        self.btn_apply_results.setEnabled(False)
        self.btn_apply_results.setVisible(False)  # Initially hidden
        mid_layout.addWidget(self.btn_apply_results)

        self.btn_report = QPushButton("Generate Report")
        self.btn_report.clicked.connect(self.generate_report)
        mid_layout.addWidget(self.btn_report)
        mid_layout.addStretch()

        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        self.update_button_states()
        
        # Connect the log signal
        self.log_message.connect(self.update_log_display)

    def update_log_display(self, message):
        if hasattr(self, 'log_display') and self.log_display:
            self.log_display.append(message)
            # Auto-scroll to bottom
            scrollbar = self.log_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def update_button_states(self):
        left_ready = self.left_panel.loaded_files_data is not None
        right_ready = self.right_panel.loaded_files_data is not None
        self.btn_soft_compare.setEnabled(left_ready and right_ready)
        self.btn_smart_compare.setEnabled(left_ready and right_ready)
        self.btn_deep_compare.setEnabled(left_ready and right_ready)
        self.btn_apply_results.setEnabled(left_ready and right_ready and self.last_comparison_results is not None)
        self.btn_report.setEnabled(left_ready and right_ready and self.last_comparison_results is not None)

        self.left_panel.move_control_widget.setVisible(left_ready and right_ready)
        self.right_panel.move_control_widget.setVisible(left_ready and right_ready)

        left_total = len(self.left_panel.loaded_files_data) if self.left_panel.loaded_files_data else 0
        right_total = len(self.right_panel.loaded_files_data) if self.right_panel.loaded_files_data else 0
        self.status_bar.showMessage(
            f"Left: {left_total} files  |  Right: {right_total} files")
            
    def apply_comparison_results(self):
        """Apply the last comparison results to the UI."""
        if not self.last_comparison_results:
            QMessageBox.warning(self, "Warning", "No comparison results available.")
            return
            
        logger.info("User requested to apply comparison results to UI")
        start_time = time.time()
        self.left_panel.apply_comparison_results(self.last_comparison_results)
        logger.info(f"Applied comparison results to left panel in {time.time() - start_time:.2f} seconds")
        start_time = time.time()
        self.right_panel.apply_comparison_results(self.last_comparison_results)
        logger.info(f"Applied comparison results to right panel in {time.time() - start_time:.2f} seconds")
        QMessageBox.information(self, "Success", "Comparison results applied to UI successfully.")
        
        # Update button states
        self.update_button_states()

    def on_panel_cleared(self):
        self.update_button_states()

    def format_comparison_time(self, seconds):
        if seconds < 0:
            return "00:00:00"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def start_comparison(self, comparison_type):
        logger.info(f"Starting {comparison_type} comparison")
        self.last_comparison_start_time = datetime.now()
        self.cleanup_comparison_threads()
        self.central_comparison_overlay.show_comparison(
            f"{comparison_type.title()} Compare...", self.cancel_comparison
        )
        left_data = self.left_panel.loaded_files_data
        right_data = self.right_panel.loaded_files_data
        if not left_data or not right_data:
            QMessageBox.warning(self, "Warning", "Please load folders in both panels before comparing")
            self.central_comparison_overlay.hide_comparison()
            return
        worker = {
            "soft": SoftCompareWorker,
            "smart": SmartCompareWorker,
            "deep": DeepCompareWorker,
        }[comparison_type](self.left_panel.folder_path, self.right_panel.folder_path, left_data, right_data)
        self.comparison_thread = QThread()
        self.comparison_worker = worker
        worker.moveToThread(self.comparison_thread)
        self.comparison_thread.started.connect(worker.run)
        worker.progress.connect(self.update_comparison_progress)
        worker.finished.connect(self.on_comparison_results_ready)  # New method for immediate report
        worker.finished.connect(self.on_comparison_finished)
        worker.error.connect(self.on_comparison_error)
        self.comparison_thread.start()

    def cancel_comparison(self):
        logger.info("Cancelling comparison...")
        if self.comparison_worker:
            self.comparison_worker.stop()
        if self.comparison_thread:
            self.comparison_thread.quit()
            self.comparison_thread.wait(2000)
            if self.comparison_thread.isRunning():
                self.comparison_thread.terminate()
                self.comparison_thread.wait(1000)
        self.central_comparison_overlay.hide_comparison()
        self.status_bar.showMessage("Comparison cancelled")
        self.cleanup_comparison_threads()

    def on_comparison_results_ready(self, results):
        """Generate automated report immediately when comparison results are ready."""
        # Generate automated report with "auto_" prefix immediately
        self.generate_automated_report(results)
        
    def cleanup_comparison_threads(self):
        if hasattr(self, 'comparison_thread') and self.comparison_thread:
            if self.comparison_thread.isRunning():
                if hasattr(self, 'comparison_worker') and self.comparison_worker:
                    self.comparison_worker.stop()
                self.comparison_thread.quit()
                self.comparison_thread.wait(5000)
                if self.comparison_thread.isRunning():
                    self.comparison_thread.terminate()
                    self.comparison_thread.wait(2000)
            try:
                self.comparison_thread.disconnect()
            except:
                pass
            self.comparison_thread.deleteLater()
            self.comparison_thread = None
            self.comparison_worker = None

    def update_comparison_progress(self, current, total):
        if total <= 0:
            return
        percentage = int((current / total) * 100)
        self.central_comparison_overlay.set_progress(current, total)
        logger.debug(f"Comparison progress: {current}/{total} ({percentage}%)")

    def on_comparison_finished(self, results):
        if not self.isVisible():
            return
        # Record the end time when the comparison actually finishes
        self.last_comparison_end_time = datetime.now()
        elapsed = results.get('comparison_time', 0)
        self.last_comparison_method = self.sender().__class__.__name__.replace("Worker", "").lower()
        logger.info(f"Comparison finished in {self.format_comparison_time(elapsed)}")
        self.last_comparison_results = results
        
        # Hide comparison overlay
        self.central_comparison_overlay.hide_comparison()

        left_total = len(self.left_panel.loaded_files_data) if self.left_panel.loaded_files_data else 0
        right_total = len(self.right_panel.loaded_files_data) if self.right_panel.loaded_files_data else 0
        self.status_bar.showMessage(
            f"Comparison completed in {self.format_comparison_time(elapsed)}  |  "
            f"Left: {left_total} files  |  Right: {right_total} files")

        self.update_button_states()
        self.cleanup_comparison_threads()
        
        # Show the "See Results in App" button
        self.btn_apply_results.setVisible(True)
        
        # Update panel status labels with comparison results summary
        identical_count = len(results.get('identical_files', []))
        different_count = len(results.get('different_files', []))
        similar_count = len(results.get('similar_files', []))
        left_unique_count = len(results.get('left_only', []))
        right_unique_count = len(results.get('right_only', []))
        
        results_summary = (
            f"Comparison: {identical_count} identical, {different_count} different, {similar_count} similar\n"
            f"Unique files: Left({left_unique_count}) Right({right_unique_count})"
        )
        
        self.left_panel.status_label.setText(results_summary)
        self.right_panel.status_label.setText(results_summary)
        
        # Show a message that the comparison is complete
        auto_report_path = getattr(self, '_last_auto_report_path', "Unknown")
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Comparison Complete")
        msg_box.setText("Comparison completed successfully!")
        msg_box.setInformativeText(
            f"Comparison method: {self.last_comparison_method.title()} Compare\n"
            f"Time taken: {self.format_comparison_time(elapsed)}\n\n"
            f"Automated report saved to:\n{auto_report_path}\n\n"
            f"You can now view the results in the application or open the detailed report."
        )
        msg_box.setIcon(QMessageBox.Icon.Information)
        
        # Add buttons
        ok_button = msg_box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        see_results_button = msg_box.addButton("See Results in App", QMessageBox.ButtonRole.ActionRole)
        open_report_button = msg_box.addButton("Open Report", QMessageBox.ButtonRole.ActionRole)
        
        msg_box.exec()
        
        # Handle button clicks
        clicked_button = msg_box.clickedButton()
        if clicked_button == see_results_button:
            # Apply results to UI
            logger.info("User requested to apply comparison results to UI")
            start_time = time.time()
            self.left_panel.apply_comparison_results(results)
            logger.info(f"Applied comparison results to left panel in {time.time() - start_time:.2f} seconds")
            start_time = time.time()
            self.right_panel.apply_comparison_results(results)
            logger.info(f"Applied comparison results to right panel in {time.time() - start_time:.2f} seconds")
        elif clicked_button == open_report_button:
            # Open the automated report
            try:
                os.startfile(auto_report_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open report:\n{e}")
        
        # Log that comparison has finished applying results
        logger.info("Finished applying comparison results")

    def on_comparison_error(self, error_msg):
        if not self.isVisible():
            return
        logger.error(f"Comparison error: {error_msg}")
        QMessageBox.critical(self, "Comparison Error", f"Comparison failed: {error_msg}")
        self.central_comparison_overlay.hide_comparison()
        self.status_bar.showMessage("Comparison failed")
        self.cleanup_comparison_threads()

    def generate_report(self):
        if not self.last_comparison_results:
            QMessageBox.warning(self, "Warning", "No comparison results available.")
            return
            
        # Use the start and end times from the comparison results or fallback to stored times
        start_time = self.last_comparison_results.get('start_time', self.last_comparison_start_time)
        end_time = self.last_comparison_results.get('end_time', self.last_comparison_end_time)
        
        # Calculate total time based on actual start and end times
        if start_time and end_time:
            total_time = (end_time - start_time).total_seconds()
            formatted_start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
            formatted_end_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            # Fallback to the old method if times are not available
            total_time = self.last_comparison_results.get('comparison_time', 0)
            formatted_start_time = "Unknown"
            formatted_end_time = "Unknown"
            
        lines = [
            "File Comparison Report",
            "=" * 50,
            f"Left Folder: {self.left_panel.folder_path}",
            f"Right Folder: {self.right_panel.folder_path}",
            f"Comparison Method: {self.last_comparison_method.title()} Compare",
            f"Started: {formatted_start_time}",
            f"Finished: {formatted_end_time}",
            f"Total Time: {self.format_comparison_time(total_time)}",
            "",
            "Summary:",
            f"  Identical files: {len(self.last_comparison_results.get('identical_files', []))}",
            f"  Different files: {len(self.last_comparison_results.get('different_files', []))}",
            f"  Similar files: {len(self.last_comparison_results.get('similar_files', []))}",
            f"  Unique files in left folder: {len(self.last_comparison_results.get('left_only', []))}",
            f"  Unique files in right folder: {len(self.last_comparison_results.get('right_only', []))}",
            "",
        ]
        for kind, label in [
            ('identical_files', 'Identical Files'),
            ('different_files', 'Different Files'),
            ('similar_files', 'Similar Files'),
            ('left_only', 'Files Only in Left Folder'),
            ('right_only', 'Files Only in Right Folder')
        ]:
            files = self.last_comparison_results.get(kind, [])
            lines.append(f"{label}:")
            if files:
                lines.extend(f"  - {f}" for f in sorted(files))
            else:
                lines.append("  (none)")
            lines.append("")
        report_text = "\n".join(lines)

        base_name = f"{self.last_comparison_method}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        path, _ = QFileDialog.getSaveFileName(self, "Save Report",
                                              os.path.join(self.report_dir, f"{base_name}.txt"),
                                              "Text Files (*.txt)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            
            # Show message box with options
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Report Generated")
            msg_box.setText("Detailed report generated successfully!")
            msg_box.setInformativeText(
                f"Report saved to:\n{path}\n\n"
                f"You can now open the report or continue working."
            )
            msg_box.setIcon(QMessageBox.Icon.Information)
            
            # Add buttons
            ok_button = msg_box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
            open_report_button = msg_box.addButton("Open Report", QMessageBox.ButtonRole.ActionRole)
            
            msg_box.exec()
            
            # Handle button clicks
            clicked_button = msg_box.clickedButton()
            if clicked_button == open_report_button:
                try:
                    os.startfile(path)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Could not open report:\n{e}")

    def generate_automated_report(self, results):
        """Generate an automated report with 'auto_' prefix to check timing issues."""
        if not results:
            return
            
        # Determine the comparison method from the sender (worker)
        sender = self.sender()
        if sender:
            comparison_method = sender.__class__.__name__.replace("Worker", "").lower()
        else:
            comparison_method = "unknown"
            
        # Use the start and end times from the comparison results
        start_time = results.get('start_time')
        end_time = results.get('end_time')
        
        # Calculate total time based on actual start and end times
        if start_time and end_time:
            total_time = (end_time - start_time).total_seconds()
            formatted_start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
            formatted_end_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            # Fallback to the old method if times are not available
            total_time = results.get('comparison_time', 0)
            formatted_start_time = "Unknown"
            formatted_end_time = "Unknown"
            
        lines = [
            "File Comparison Report (Automated - UI Timing Check)",
            "=" * 50,
            f"Left Folder: {self.left_panel.folder_path}",
            f"Right Folder: {self.right_panel.folder_path}",
            f"Comparison Method: {comparison_method.title()} Compare",
            f"Started: {formatted_start_time}",
            f"Finished: {formatted_end_time}",
            f"Total Time: {self.format_comparison_time(total_time)}",
            "",
            "Summary:",
            f"  Identical files: {len(results.get('identical_files', []))}",
            f"  Different files: {len(results.get('different_files', []))}",
            f"  Similar files: {len(results.get('similar_files', []))}",
            f"  Unique files in left folder: {len(results.get('left_only', []))}",
            f"  Unique files in right folder: {len(results.get('right_only', []))}",
            "",
        ]
        for kind, label in [
            ('identical_files', 'Identical Files'),
            ('different_files', 'Different Files'),
            ('similar_files', 'Similar Files'),
            ('left_only', 'Files Only in Left Folder'),
            ('right_only', 'Files Only in Right Folder')
        ]:
            files = results.get(kind, [])
            lines.append(f"{label}:")
            if files:
                lines.extend(f"  - {f}" for f in sorted(files))
            else:
                lines.append("  (none)")
            lines.append("")
        report_text = "\n".join(lines)

        # Generate auto-named report file
        base_name = f"auto_{comparison_method}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        auto_report_path = os.path.join(self.report_dir, f"{base_name}.txt")
        try:
            with open(auto_report_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            logger.info(f"Automated report saved to: {auto_report_path}")
            # Store the path for the dialog
            self._last_auto_report_path = auto_report_path
        except Exception as e:
            logger.error(f"Failed to save automated report: {e}")
            self._last_auto_report_path = "Unknown"

    # -------------------------------------------------
    #  MOVE BUTTONS IN EACH PANEL
    # -------------------------------------------------

    def move_visible_files(self, src_panel: "OptimizedFilePanel", dst_panel: "OptimizedFilePanel"):
        """Copy the *entire* source folder into the destination folder
           (files + sub-dirs).  A progress dialog is shown."""
        if not (src_panel.folder_path and dst_panel.folder_path):
            QMessageBox.warning(self, "Warning", "Both panels must have a folder loaded.")
            return

        if src_panel.folder_path == dst_panel.folder_path:
            QMessageBox.warning(self, "Warning", "Source and destination folders must be different.")
            return

        keep_tree = src_panel.keep_tree_checkbox.isChecked()

        # Build the complete list of files inside the source folder
        all_files = []
        for dirpath, dirnames, filenames in os.walk(src_panel.folder_path):
            for fname in filenames:
                src_path = os.path.join(dirpath, fname)
                if keep_tree:
                    # Preserve folder structure
                    rel_path = os.path.relpath(src_path, src_panel.folder_path)
                    dst_path = os.path.join(dst_panel.folder_path, rel_path)
                else:
                    # Flat copy: all files land directly in destination folder
                    dst_path = os.path.join(dst_panel.folder_path, fname)
                all_files.append((src_path, dst_path))

        if not all_files:
            QMessageBox.information(self, "Info", "No files found to transfer.")
            return

        # Create progress dialog
        progress = QProgressDialog("Copying files…", "Cancel", 0, len(all_files), self)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setAutoClose(True)
        progress.setMinimumDuration(0)
        progress.show()

        copied = 0
        errors = []
        try:
            for src, dst in all_files:
                if progress.wasCanceled():
                    break
                try:
                    if keep_tree:
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                    copied += 1
                    logger.debug(f"Copied {src} to {dst}")
                except Exception as ex:
                    errors.append(f"{src} → {dst}: {ex}")
                    logger.error(f"Error copying {src} to {dst}: {ex}")
                progress.setValue(copied)
                if copied % 100 == 0:
                    QApplication.processEvents()
                    logger.debug(f"Copy progress: {copied}/{len(all_files)}")

            progress.setValue(len(all_files))
            logger.info(f"Completed copying {copied}/{len(all_files)} files")

            if errors:
                QMessageBox.warning(
                    self, "Partial Success",
                    f"Copied {copied}/{len(all_files)} files.\n\n"
                    "Errors:\n" + "\n".join(errors[:10]) + ("\n…" if len(errors) > 10 else "")
                )
            else:
                QMessageBox.information(
                    self, "Success",
                    f"Copied {copied} file(s) from\n{src_panel.folder_path}\nto\n{dst_panel.folder_path}"
                )

            # Refresh the destination panel
            if dst_panel.content_type == "folder":
                dst_panel.load_content()

        except Exception as e:
            logger.error(f"Move error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Move failed:\n{e}")

    def closeEvent(self, event):
        logger.info("Application closing, cleaning up threads...")
        self.left_panel.cleanup_thread()
        self.right_panel.cleanup_thread()
        self.cleanup_comparison_threads()
        
        # Process all pending events before closing
        QApplication.processEvents()
        
        event.accept()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  MAIN ENTRY
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = OptimizedFileManager()
    window.show()
    
    # Connect to the aboutToQuit signal to ensure cleanup
    app.aboutToQuit.connect(lambda: logger.info("Application is about to quit"))
    
    exit_code = app.exec()
    logger.info("Application exited with code: %d", exit_code)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()