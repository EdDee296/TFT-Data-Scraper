# TFT Data Scraper

This program automatically tracks and analyzes augment performance in Teamfight Tactics (TFT) by monitoring live games and correlating augment choices with player placements.

## 📋 Prerequisites

### Required Software

- **League of Legends/TFT Client** - Must be installed and able to spectate games
- **Windows OS** - The program uses Windows-specific automation

## 🚀 How to Run

```bash
D:\Projects\500usd\.venv\Scripts\python.exe "get-augment-stats (1).py"
```

## 📦 Installed Dependencies

- ✅ **selenium** - Web browser automation
- ✅ **seleniumbase** - Enhanced Selenium framework
- ✅ **beautifulsoup4** - HTML parsing for web scraping
- ✅ **requests** - HTTP requests
- ✅ **rapidfuzz** - Fuzzy string matching (replaces fuzzyset)
- ✅ **easyocr** - Optical Character Recognition
- ✅ **pyautogui** - Screen automation and screenshots
- ✅ **pillow** - Image processing
- ✅ **lxml** - XML/HTML parser

## 🎮 Program Overview

### What It Does

1. **Monitors Live Games** - Scrapes MetaTFT.com for spectatable games
2. **Automated Spectating** - Downloads and launches TFT spectator files
3. **Screenshot Analysis** - Takes screenshots during key game moments
4. **OCR Processing** - Reads augment names from screenshots using EasyOCR
5. **Data Correlation** - Matches players to their augment choices
6. **Statistics Tracking** - Records win rates and average placements per augment
7. **Database Storage** - Saves data to SQLite database
8. **API Generation** - Creates JSON files for web consumption

### Key Features

- **Multi-region support** (NA, EUW, etc.)
- **Fuzzy name matching** for reliable player identification
- **Automatic error recovery** and game crash handling
- **Background processing** of multiple games
- **Real-time statistics** calculation

## ⚠️ Important Notes

### Before Running

1. **Create reference images** - The program won't work without these
2. **Ensure TFT is installed** and can spectate games
3. **Check firewall settings** - Program downloads and runs game files
4. **Have stable internet** - Constantly scraping and downloading data

### Performance

- Uses significant CPU for OCR processing
- Requires screen access for screenshots
- Stores large amounts of game data
- May impact system performance during operation

## 🔍 Troubleshooting

### Getting Reference Images

1. Launch TFT and spectate a game
2. Take screenshots of the required interface elements
3. Save as PNG files with exact names: `ingame.png`, `augments.png`, `select.png`
4. Place in the project root directory

## 📊 Output Files

- **`tft.db`** - SQLite database with augment statistics
- **`data.json`** - JSON export for web API
- **`runtime.log`** - Program execution logs
- **Game folders** - Screenshots and data from processed games

