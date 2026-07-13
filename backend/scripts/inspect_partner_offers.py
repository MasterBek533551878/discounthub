import sqlite3
import json

con = sqlite3.connect("data/discounthub.sqlite3")
con.row_factory = sqlite3.Row
cur = con.cursor()

print("COLUMNS:")
print(json.dumps(
    [dict(r) for r in cur.execute("PRAGMA table_info(partner_offers)")],
    indent=2,
    ensure_ascii=False
))

print("\nROWS:")
print(json.dumps(
    [dict(r) for r in cur.execute("SELECT * FROM partner_offers")],
    indent=2,
    ensure_ascii=False
))
