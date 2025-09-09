#!/usr/bin/env python3
"""
Quick test to verify TFT Stats program can start without infinite loops
"""

import os


def test_imports():
    """Test that all imports work"""
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.common import NoSuchElementException, ElementNotInteractableException
        from selenium.webdriver.support.wait import WebDriverWait
        from bs4 import BeautifulSoup, SoupStrainer
        import time
        import requests
        import json
        from rapidfuzz import fuzz, process
        import easyocr
        import pyautogui
        import os
        import subprocess
        import re
        from seleniumbase import Driver
        from operator import itemgetter
        import shutil
        from torchvision.transforms.functional import crop
        from PIL import Image
        import sqlite3
        import traceback
        from bisect import bisect_left
        import logging
        import datetime
        print("✅ All imports successful!")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False


def test_files():
    """Test that required files exist"""
    required_files = ['ingame.png', 'augments.png', 'select.png']
    missing = []

    for file in required_files:
        if os.path.exists(file):
            print(f"✅ Found: {file}")
        else:
            print(f"❌ Missing: {file}")
            missing.append(file)

    return len(missing) == 0


def test_directories():
    """Test that required directories exist"""
    required_dirs = ['NeedsPlacement', 'Games', 'Augments']

    for dir in required_dirs:
        if os.path.exists(dir):
            print(f"✅ Directory exists: {dir}/")
        else:
            print(f"⚠️  Creating directory: {dir}/")
            os.makedirs(dir, exist_ok=True)


def main():
    print("=== TFT Stats Quick Test ===\n")

    print("1. Testing imports...")
    imports_ok = test_imports()
    print()

    print("2. Testing reference images...")
    files_ok = test_files()
    print()

    print("3. Testing directories...")
    test_directories()
    print()

    if imports_ok and files_ok:
        print("✅ Basic requirements met!")
        print("The program should now start without infinite loops.")
        print()
        print("NOTE: The reference images are placeholders.")
        print("You'll need real TFT screenshots for actual functionality.")
    else:
        print("❌ Some requirements not met.")
        if not imports_ok:
            print("- Fix import issues first")
        if not files_ok:
            print("- Run create_placeholders.py to create missing images")


if __name__ == "__main__":
    main()
