#!/usr/bin/env python3
"""Quick diagnostic: list tables in compendium.sqlite"""
import sqlite3

conn = sqlite3.connect('compendium.sqlite')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cur.fetchall()

print("Tables in compendium.sqlite:")
for (name,) in tables:
    print(f"  - {name}")
    
# If verses table exists, show its schema
if any(t[0] == 'verses' for t in tables):
    print("\nExisting verses table schema:")
    cur.execute("PRAGMA table_info(verses)")
    for row in cur.fetchall():
        print(f"  {row[1]}: {row[2]}")

conn.close()
