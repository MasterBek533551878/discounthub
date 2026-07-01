DiscountHub restricted offers patch

Purpose:
- Keep big mixed stores such as El Corte Ingles enabled.
- Block pork/ham products and alcoholic drinks at import/cleanup level.
- Remove already imported restricted deals/promotions via scripts/cleanup_restricted_offers.py.

Changed files:
- backend/app/services/restricted_offer_filter.py
- backend/app/services/awin_feed_list_service.py
- backend/app/services/awin_offers_service.py
- backend/app/services/feed_import_service.py
- backend/app/services/promotion_cleanup_service.py
- backend/scripts/cleanup_restricted_offers.py

Validation run:
- python -m py_compile app/services/restricted_offer_filter.py app/services/awin_feed_list_service.py app/services/awin_offers_service.py app/services/feed_import_service.py app/services/promotion_cleanup_service.py scripts/cleanup_restricted_offers.py
- python compileall for backend/app and backend/scripts
- small filter tests for jamon/wine/vodka and false positives like shampoo/serum/beginner
