# DiscountHub automatic feed flow

DiscountHub should not rely on manually adding products one by one.
The normal production flow is automatic:

1. Official marketplace / affiliate / partner feed URL is configured once.
2. Backend registers configured feed providers on startup.
3. Scheduler syncs enabled providers automatically.
4. Imported deals are saved into SQLite/PostgreSQL.
5. Flutter app reads deals from the API.

Manual deal management in the admin panel is only for:

- local testing;
- emergency correction;
- adding a temporary demo product;
- checking that API/database writes work.

It is not the planned main workflow.

## Where providers are configured

Use:

```text
backend/config/feed_providers.json
```

Example:

```json
{
  "providers": [
    {
      "id": "demo_feed",
      "name": "Demo provider feed",
      "url": "http://127.0.0.1:9000/provider_feed.json",
      "enabled": true,
      "replaceOnSync": false
    }
  ]
}
```

For a real provider, replace `url` with an official feed/API URL from an affiliate network or marketplace partner program.

## Automatic sync settings

By default:

```env
AUTO_REGISTER_FEED_PROVIDERS=true
FEED_SYNC_SCHEDULER_ENABLED=true
FEED_SYNC_INTERVAL_SECONDS=3600
FEED_SYNC_RUN_ON_STARTUP=true
```

This means the backend will:

- register configured providers at startup;
- start the scheduler automatically;
- run a sync on startup;
- repeat sync every 3600 seconds.

## Local demo note

The demo provider uses:

```text
http://127.0.0.1:9000/provider_feed.json
```

For this demo URL to work locally, start the demo feed server:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
.\scripts\start_provider_feed_server.ps1
```

In production this extra local demo server is not needed because provider URLs will be real internet URLs.
