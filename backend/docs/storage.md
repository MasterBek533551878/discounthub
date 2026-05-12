# DiscountHub Backend Storage

Stage 15 moves deals from an in-memory Python list to a local SQLite database.

## Database

Default file:

```text
data/discounthub.sqlite3
```

You can override it with:

```env
DATABASE_PATH=data/discounthub.sqlite3
```

## Startup behaviour

When the backend starts:

1. it creates the SQLite database if it does not exist;
2. it creates the `deals` table and indexes;
3. if the table is empty, it seeds demo deals from `app/data/mock_deals.py`.

## Status endpoint

```text
GET /storage/status
```

Returns database path, existence status, and deal count.

## Reset local database

PowerShell:

```powershell
cd backend
.\scripts\reset_db.ps1
```

Then restart the backend.
