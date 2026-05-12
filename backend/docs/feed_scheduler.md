# Feed sync scheduler

DiscountHub can now sync enabled feed providers automatically from the backend process.

For local development, the scheduler is disabled by default. This avoids repeated imports while you are testing.

## Environment variables

```env
FEED_SYNC_SCHEDULER_ENABLED=false
FEED_SYNC_INTERVAL_SECONDS=3600
FEED_SYNC_TIMEOUT_SECONDS=20
FEED_SYNC_RUN_ON_STARTUP=false
```

Set `FEED_SYNC_SCHEDULER_ENABLED=true` in `.env` to start it automatically when FastAPI starts.

## Admin endpoints

All endpoints require the `X-Admin-Token` header.

```text
GET  /admin/feed-providers/scheduler/status
POST /admin/feed-providers/scheduler/start
POST /admin/feed-providers/scheduler/stop
POST /admin/feed-providers/scheduler/run-once
```

`run-once` is useful for testing because it triggers `sync_all_enabled` immediately without waiting for the interval.

## PowerShell helpers

```powershell
.\scripts\feed_scheduler_status.ps1
.\scripts\feed_scheduler_run_once.ps1
.\scripts\feed_scheduler_start.ps1 -IntervalSeconds 3600
.\scripts\feed_scheduler_stop.ps1
```

## Local test flow

1. Start the main backend on port `8000`.
2. Start the demo feed server:

```powershell
.\scripts\start_provider_feed_server.ps1
```

3. Make sure a feed provider is saved and enabled:

```powershell
.\scripts\add_feed_provider.ps1
```

4. Trigger one scheduler run:

```powershell
.\scripts\feed_scheduler_run_once.ps1
```

5. Check status:

```powershell
.\scripts\feed_scheduler_status.ps1
```

The response should show the last run status, imported count, and current deal count.
