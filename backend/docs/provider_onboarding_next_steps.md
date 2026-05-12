# Provider onboarding next steps

`provider.example.com` is only a placeholder URL. It is not expected to work.

The production flow is:

1. Register in an official affiliate network or marketplace partner program.
2. Get an official product feed/API URL.
3. Choose the closest adapter:
   - `discounthub_json`
   - `generic_products`
   - `google_merchant`
   - `awin_products`
   - `auto`
4. Test the URL:
   ```powershell
   .\scripts\provider_test_url.ps1 -FeedUrl "https://real-provider.example/products.json"
   ```
5. Add it to config:
   ```powershell
   .\scripts\provider_add_to_config.ps1 `
     -Id "provider_id" `
     -Name "Provider name" `
     -Url "https://real-provider.example/products.json" `
     -Adapter "generic_products"
   ```
6. Start backend.
7. Sync config:
   ```powershell
   .\scripts\provider_sync_from_config.ps1
   ```

## Remove a test provider from config

If you added the placeholder provider by mistake:

```powershell
.\scripts\provider_remove_from_config.ps1 -Id "real_provider_1"
```

This removes it from `backend/config/feed_providers.json`, so automatic sync will not try to fetch the fake URL.
