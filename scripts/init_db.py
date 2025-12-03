"""
Database initialization script for quick setup
Run: python scripts/init_db.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database_init import init_database

if __name__ == "__main__":
    print("Initializing database...")
    init_database()
    print("Database initialization complete!")
