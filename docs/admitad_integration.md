# DiscountHub Admitad integration

Admitad credentials are backend-only secrets. Do not put them into Flutter, Android, iOS, web builds, screenshots, GitHub, ZIPs shared externally, or public docs.

Required backend `.env` values:

```env
ADMITAD_CLIENT_ID=
ADMITAD_CLIENT_SECRET=
ADMITAD_WEBSITE_ID=2946975
ADMITAD_API_BASE_URL=https://api.admitad.com
```

Stage 57 workflow:

1. Add credentials to `backend/.env`.
2. Start backend locally.
3. Run `scripts/stage57_check_admitad_api.ps1`.
4. Wait until joined programs move from `pending` to `active`.
5. Run `scripts/stage57_register_active_admitad_product_feeds.ps1`.
6. Sync the registered `admitad_products` providers through the normal feed-provider flow.

The API check script obtains an Admitad OAuth token with client credentials and lists active/pending/declined programs for the configured ad space. It never prints the access token, client secret, or base64 header.
