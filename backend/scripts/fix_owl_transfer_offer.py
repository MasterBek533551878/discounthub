import sqlite3
from datetime import datetime, timezone

DB = "data/discounthub.sqlite3"

title = "OWL Transfer"
subtitle = "Secure file sharing with PGP encryption and OneTimeView."
description = (
    "OWL Transfer is a secure file sharing platform for individuals and businesses. "
    "It helps users send large files with end-to-end PGP encryption, password protection, "
    "expiration dates, download limits, and OneTimeView technology for private one-time file viewing."
)
partner_name = "OWL Transfer"
category = "security"
tags = '["Security", "File Sharing", "Privacy", "PGP", "OneTimeView"]'
offer_text = "50% off any paid plan with code DISCOUNTHUB50 until December 31, 2026."
original_price_text = "Paid plans"
current_price_text = "50% off with code DISCOUNTHUB50"
code = "DISCOUNTHUB50"
landing_url = "https://owltransfer.com/"
checkout_url = "https://owltransfer.com/"
countries = "Global"
valid_from = "2026-07-10T00:00:00+00:00"
valid_until = "2026-12-31T23:59:59+00:00"
updated_at = datetime.now(timezone.utc).isoformat()

search_text = " ".join([
    title, subtitle, description, partner_name, category,
    "Security File Sharing Privacy PGP OneTimeView",
    offer_text, original_price_text, current_price_text, code, countries
]).lower()

con = sqlite3.connect(DB)
cur = con.cursor()

cur.execute("""
UPDATE partner_offers
SET
    title = ?,
    subtitle = ?,
    description = ?,
    partner_name = ?,
    category = ?,
    tags = ?,
    offer_text = ?,
    original_price_text = ?,
    current_price_text = ?,
    code = ?,
    landing_url = ?,
    checkout_url = ?,
    image_url = NULL,
    logo_url = NULL,
    countries = ?,
    monetization_mode = 'direct',
    valid_from = ?,
    valid_until = ?,
    featured = 1,
    verified = 1,
    updated_at = ?,
    search_text = ?
WHERE id = 'owl-transfer'
""", (
    title, subtitle, description, partner_name, category, tags,
    offer_text, original_price_text, current_price_text, code,
    landing_url, checkout_url, countries, valid_from, valid_until,
    updated_at, search_text
))

con.commit()

row = cur.execute("""
SELECT id, title, code, valid_from, valid_until, featured, verified, search_text
FROM partner_offers
WHERE id = 'owl-transfer'
""").fetchone()

print("Updated OWL Transfer:")
print(row)

con.close()
