# Local feed server

For local tests, backend feed providers can read `backend/examples/provider_feed.json` from a tiny local HTTP server.

Start it from the backend folder:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\scripts\start_provider_feed_server.ps1
```

Keep that PowerShell window open.

Then sync the provider from another PowerShell:

```powershell
cd C:\Users\Victus\Desktop\discounthub\backend
.\scripts\sync_feed_provider.ps1 -ProviderId demo_feed
```

If the server is not running, sync will fail because `http://127.0.0.1:9000/provider_feed.json` cannot be fetched.
