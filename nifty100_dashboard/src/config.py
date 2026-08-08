from pathlib import Path

# Project root: D:\nifty100-capstone
BASE_DIR = Path(__file__).resolve().parent.parent

# Folders
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "core"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"

# Database
DATABASE_PATH = BASE_DIR / "db" / "nifty100.db"