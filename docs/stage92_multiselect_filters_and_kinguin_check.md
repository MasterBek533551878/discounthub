# Stage 92 — Multi-select filters and Kinguin audit

## Goal

Improve filtering before the next mobile release:

- allow selecting more than one marketplace on the home feed, for example AliExpress + eBay;
- allow selecting more than one category;
- allow selecting more than one store in the Promotions tab;
- keep delivery filters removed;
- add quick local scripts to verify multi-select API behavior and audit the new Awin Kinguin partner.

## Notes

Backend `/deals` and `/deals/facets` now accept comma-separated values for `platform` and `category`.

Examples:

```text
/deals?platform=AliExpress,eBay
/deals?category=Electronics,Fashion
```

Backend `/promotions` now accepts comma-separated values for `store`.

Example:

```text
/promotions?store=AliExpress PL,Navimow FR
```

Kinguin UE from Awin should be checked before production import. If Product Feed is `No`, it cannot supply normal product discount cards yet, but it may still have Awin promotions/vouchers.
