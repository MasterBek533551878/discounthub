# Stage 51 — eBay Catalog Expansion

Goal: increase the number of real marketplace products for the first DiscountHub version without waiting for new affiliate network approvals.

This stage keeps the working eBay Browse API pipeline and adds more official eBay Browse API providers for the US, UK and Germany.

## Added categories

- Smartphones
- Tablets
- Cameras
- Monitors
- Computer parts
- Gaming consoles
- Beauty
- Bags
- Toys
- Car accessories
- Fitness
- Home appliances

The backend category normalizer maps marketplace-specific eBay categories into stable app categories:

- Electronics
- Computers
- Fashion
- Gaming
- Home
- Auto
- Beauty
- Toys
- Sports
- Other

The Flutter app has translations for these categories in all current interface languages.

## Why eBay first

Mercado Libre currently requires a developer/access token for the search flow in our environment and the account registration hit a verification limit. Best Buy blocked access from the current region/IP. eBay is already configured, tested, and all current providers are healthy.

## Commands

Start backend in one PowerShell window:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run Stage 51 sync in another PowerShell window:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
.\scripts\stage51_sync_ebay_expansion.ps1 -TimeoutSeconds 35
```

Check result:

```powershell
.\scripts\stage51_check_ebay_expansion.ps1
Invoke-RestMethod "http://127.0.0.1:8000/deals?page_size=10&sort=newest"
```

The sync script also removes temporary `mercadolibre_*` providers from the local backend database so the scheduler does not keep retrying a source that currently needs a token.
