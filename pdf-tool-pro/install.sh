#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
#  PDF Tool Pro — System Installer
#  Run this ONCE to install PDF Tool Pro into your system
#  application launcher.
#
#  After running, the app appears in your app grid/menu
#  and you can right-click → Add to Favorites/Dock.
# ═══════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  PDF Tool Pro — Installer                ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Check Python & deps ──
echo "  [1/5] Checking Python..."
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &> /dev/null; then
        PYTHON="$cmd"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "  X Python not found! Install Python 3.9+ first."
    exit 1
fi
echo "  OK Python: $($PYTHON --version 2>&1)"

echo "  [2/5] Checking Python packages..."
MISSING=""
for pkg in "fitz:PyMuPDF" "pypdf:pypdf" "streamlit:streamlit"; do
    import="${pkg%%:*}"
    pip="${pkg##*:}"
    if ! "$PYTHON" -c "import $import" 2>/dev/null; then
        MISSING="$MISSING $pip"
    fi
done
if [ -n "$MISSING" ]; then
    echo "  ! Missing packages:$MISSING"
    echo "     Installing now..."
    pip3 install $MISSING --break-system-packages 2>/dev/null || \
    pip install $MISSING --break-system-packages 2>/dev/null || \
    echo "  ! Could not auto-install. Run: pip install$MISSING"
fi
echo "  OK Python packages"

# ── Make scripts executable ──
echo "  [3/5] Making launchers executable..."
chmod +x "$SCRIPT_DIR/run" "$SCRIPT_DIR/run-script.sh" "$SCRIPT_DIR/PDF-Tool-Pro.desktop" 2>/dev/null
echo "  OK Done"

# ── Install .desktop file for the app ──
echo "  [4/5] Installing to application launcher..."
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"

# Create the .desktop file with the absolute path to the run script
cat > "$APPS_DIR/pdf-tool-pro.desktop" << EOF
[Desktop Entry]
Type=Application
Name=PDF Tool Pro
Comment=Edit, compress, merge, split, rotate, crop, extract text/images, watermark, and view PDF metadata
Exec=bash -c 'cd "$SCRIPT_DIR" && ./run'
Terminal=false
Categories=Office;Utility;
StartupNotify=true
EOF

# Register the shell script runner as default for .sh files
cat > "$APPS_DIR/run-script.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=Run Shell Script
Comment=Execute shell scripts on double-click
Exec=/bin/bash -c 'cd "$(dirname "%f")" && bash "%f"'
NoDisplay=true
MimeType=application/x-shellscript;text/x-shellscript;
EOF

# Set shell scripts to be executed (not opened in editor) by default
xdg-mime default run-script.desktop application/x-shellscript 2>/dev/null || true
xdg-mime default run-script.desktop text/x-shellscript 2>/dev/null || true

# ── Add Thunar custom action: "Run Script" ──
THUNAR_DIR="$HOME/.config/Thunar"
UCA_FILE="$THUNAR_DIR/uca.xml"
mkdir -p "$THUNAR_DIR"

# Only add if not already present
if ! grep -q "Run Script" "$UCA_FILE" 2>/dev/null; then
    # Create a backup if file exists
    [ -f "$UCA_FILE" ] && cp "$UCA_FILE" "${UCA_FILE}.bak"

    # Add the custom action before </actions> or append
    if [ -f "$UCA_FILE" ]; then
        # Insert before closing tag
        sed -i 's|</actions>|<action><icon>utilities-terminal</icon><name>Run Script</name><unique-id>run-script-action</unique-id><command>bash -c '\''cd %f \&\& exec ./$(basename %f)'\''</command><description>Execute this shell script</description><patterns>*.sh;*.bash</patterns><other-location>Local</other-location></action></actions>|' "$UCA_FILE" 2>/dev/null || true
    else
        cat > "$UCA_FILE" << 'UCAEOF'
<?xml version="1.0" encoding="UTF-8"?>
<actions>
<action><icon>utilities-terminal</icon><name>Run Script</name><unique-id>run-script-action</unique-id><command>bash -c 'cd %f &amp;&amp; exec ./$(basename %f)'</command><description>Execute this shell script</description><patterns>*.sh;*.bash</patterns><other-location>Local</other-location></action>
</actions>
UCAEOF
    fi
    echo "  OK Thunar custom action added"
else
    echo "  OK Thunar custom action already exists"
fi

# Register with the desktop environment
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$APPS_DIR" 2>/dev/null || true
fi

echo "  OK Installed: $APPS_DIR/pdf-tool-pro.desktop"
echo ""

# ── Done ──
echo "╔══════════════════════════════════════════╗"
echo "║  Installation complete!                  ║"
echo "║                                          ║"
echo "║  PDF Tool Pro is now in your             ║"
echo "║  application launcher.                   ║"
echo "║                                          ║"
echo "║  Search for 'PDF Tool Pro'               ║"
echo "║  in your app menu to launch it.          ║"
echo "║                                          ║"
echo "║  Right-click the icon →                  ║"
echo "║  'Add to Favorites' to pin               ║"
echo "║  it to your dock.                        ║"
echo "║                                          ║"
echo "║  Shell scripts are now set to            ║"
echo "║  execute on double-click.                ║"
echo "║                                          ║"
echo "║  TIP: In Thunar, right-click a .sh file  ║"
echo "║  and select 'Run Script' to execute it.  ║"
echo "╚══════════════════════════════════════════╝"
echo ""
