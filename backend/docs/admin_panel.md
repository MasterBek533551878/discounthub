# DiscountHub Admin Panel

Stage 17 adds a small local admin dashboard for MVP testing.

## URL

Start the backend and open:

```text
http://127.0.0.1:8000/admin-panel
```

For local development, the default admin token is:

```text
dev-local-admin-token
```

Paste this token into the **Admin token** field before saving, deleting or resetting deals.

## What the panel can do

- show API/storage status;
- list current deals from SQLite;
- search and filter deals by platform;
- add a new deal;
- edit an existing deal;
- delete a deal;
- reset the database back to demo deals.

## Important

This admin panel is for local MVP development only. Production admin must use real authentication, role checks, HTTPS, audit logs and safer permissions.
