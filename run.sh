#!/bin/bash
# ToolStack - Launcher Menu
echo "==================================="
echo "         ToolStack Launcher"
echo "==================================="
echo ""
echo "Select a tool to run:"
echo ""
echo "1) File Mover Pro"
echo "2) Advanced File Comparing"
echo "3) Run both"
echo "0) Exit"
echo ""
read -p "Enter choice: " choice

case $choice in
    1)
        cd "$(dirname "$0")/File_Mover_Pro"
        python3 File_Mover_Pro_v2.py
        ;;
    2)
        cd "$(dirname "$0")/Advanced_Python_File_Comparing"
        python3 Advanced_Python_File_Comparing.py
        ;;
    3)
        echo "Running File Mover Pro..."
        cd "$(dirname "$0")/File_Mover_Pro"
        python3 File_Mover_Pro_v2.py
        echo ""
        echo "Running Advanced File Comparing..."
        cd "$(dirname "$0")/Advanced_Python_File_Comparing"
        python3 Advanced_Python_File_Comparing.py
        ;;
    0)
        echo "Goodbye!"
        ;;
    *)
        echo "Invalid option"
        ;;
esac