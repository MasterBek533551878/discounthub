# Feed sync history

Stage 22 adds a persistent sync history table for feed providers.

## Why it exists

Provider sync can run manually, by script, from the admin panel, or by scheduler. The history table keeps a small audit trail so you can see:

- which provider was synced;
- whether sync succeeded or failed;
- how many deals were imported or updated;
- the total deal count after sync;
- duration in milliseconds;
- the exact error message when a feed URL is unavailable.

## API

All endpoints require the admin token header:

```http
X-Admin-Token: dev-local-admin-token
```

### List recent sync runs

```http
GET /admin/feed-providers/sync-runs?limit=50
```

Optional filters:

```http
GET /admin/feed-providers/sync-runs?provider_id=demo_feed
GET /admin/feed-providers/sync-runs?status=ok
GET /admin/feed-providers/sync-runs?status=error
```

### Clear sync history

```http
DELETE /admin/feed-providers/sync-runs
```

## PowerShell

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\scripts\feed_sync_runs.ps1
.\scripts\feed_sync_runs.ps1 -ProviderId demo_feed
.\scripts\feed_sync_runs.ps1 -Status error
.\scripts\feed_sync_runs_clear.ps1
```

## Notes

This is a local MVP audit log. In production, keep this table, but protect the admin endpoints with real authentication and add user/action metadata.
