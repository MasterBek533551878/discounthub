import sqlite3
from datetime import datetime, timezone

DB = "data/discounthub.sqlite3"
IMAGE_URL = "https://discounthub.uz/public/images/partner-offers/owl-transfer-banner.png"

con = sqlite3.connect(DB)
cur = con.cursor()

cur.execute("""
UPDATE partner_offers
SET
    image_url = ?,
    updated_at = ?
WHERE id = 'owl-transfer'
""", (
    IMAGE_URL,
    datetime.now(timezone.utc).isoformat()
))

con.commit()

row = cur.execute("""
SELECT id, title, image_url
FROM partner_offers
WHERE id = 'owl-transfer'
""").fetchone()

print(row)

con.close()
