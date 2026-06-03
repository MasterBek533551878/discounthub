# DiscountHub Stage 56 — Direct marketplace expansion

Stage 56 adds a safe direct-provider pack for public marketplace data that does not require affiliate approval.

## Added

- `backend/config/stage56_direct_marketplace_providers.json`
  - Mercado Libre Mexico, Brazil, Argentina, and Chile.
  - Categories: electronics, computers, fashion, gaming.
  - `monetizationMode: direct`.
  - Discount-only, free-shipping-biased queries.

- `scripts/stage56_register_direct_marketplaces.ps1`
  - Registers the Stage 56 providers through the admin API.
  - Optional `-SyncAfterRegister` flag.

- `scripts/stage56_sync_direct_marketplaces.ps1`
  - Syncs the Stage 56 providers sequentially.
  - Prints imported counts and marketplace facets.

- `scripts/stage56_check_direct_marketplaces.ps1`
  - Checks provider registration, facets, currencies, monetization mode, and a sample Mercado Libre query.

## Recommended local flow

```powershell
cd C:\Users\Victus\Desktop\discounthub
.\scripts\stage56_register_direct_marketplaces.ps1
.\scripts\stage56_sync_direct_marketplaces.ps1
.\scripts\stage56_check_direct_marketplaces.ps1
```

If your admin token differs from the local default:

```powershell
.\scripts\stage56_register_direct_marketplaces.ps1 -AdminToken "YOUR_TOKEN"
.\scripts\stage56_sync_direct_marketplaces.ps1 -AdminToken "YOUR_TOKEN"
.\scripts\stage56_check_direct_marketplaces.ps1 -AdminToken "YOUR_TOKEN"
```

## Notes

These providers are direct links, not affiliate links. They are useful for growing the first public catalog and collecting click statistics before applying or re-applying to affiliate networks.
