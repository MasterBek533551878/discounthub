# Stage 57b Admitad scope fix

Fixes Admitad API calls that received HTTP 403 on `/advcampaigns/website/{website_id}/` despite successful OAuth token generation.

The endpoint requires the `advcampaigns_for_website` access scope. The scripts now request:

```text
advcampaigns advcampaigns_for_website websites
```

Keep credentials only in `backend/.env`.
