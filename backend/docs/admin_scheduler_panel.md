# DiscountHub Admin Scheduler Panel

Stage 23 adds feed scheduler controls to the local admin panel.

Open:

```text
http://127.0.0.1:8000/admin-panel
```

Use the admin token:

```text
dev-local-admin-token
```

## What you can do from the panel

- Reload scheduler status.
- Run one immediate provider sync.
- Start the temporary in-process scheduler.
- Stop the scheduler.
- Configure interval seconds and timeout seconds for local testing.
- View the latest scheduler status and message.

## Important local testing note

If your provider URL is the demo feed URL:

```text
http://127.0.0.1:9000/provider_feed.json
```

then the demo feed server must stay running in a separate PowerShell window:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\.venv\Scripts\Activate.ps1
.\scripts\start_provider_feed_server.ps1
```

If the feed server is closed, scheduler sync will correctly create an error history record.

## Production note

The in-process scheduler is useful for local MVP testing. For production deployment, use a real external scheduler or worker process, such as Cloud Scheduler, cron, Celery beat, APScheduler in a separate worker, or a platform-native scheduled job.
