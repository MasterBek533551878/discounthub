# Stage 79 — Delivery region filter + release UI cleanup

This stage adds a user-selected delivery-region filter without collecting user
location data.

## Regions

The backend stores product/source delivery buckets in `deals.delivery_regions`:

- `global` — international/global delivery bucket
- `cis` — CIS / СНГ bucket
- `europe` — Europe bucket
- `usa` — USA bucket
- `latam` — Latin America bucket

Filtering semantics:

- `delivery_region=global` returns only global items.
- `delivery_region=cis` returns `cis` plus `global`.
- `delivery_region=europe` returns `europe` plus `global`.
- `delivery_region=usa` returns `usa` plus `global`.
- `delivery_region=latam` returns `latam` plus `global`.

This is not geolocation. The app never asks for GPS/IP location for this filter;
the user selects a catalog filter manually.

## UI cleanup

- Removed the customer-facing “Link type / Тип ссылки” filter.
- Removed release-inappropriate MVP blocks from About / Legal:
  - Privacy in MVP
  - Support placeholder
  - MVP status

## Backend notes

Existing rows are backfilled by a SQLite migration. New rows are inferred on
upsert from platform/provider/product URL and shipping countries.
