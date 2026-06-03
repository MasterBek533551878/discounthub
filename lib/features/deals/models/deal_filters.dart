import '../../settings/settings_store.dart';
import 'deal.dart';

class DealFilters {
  const DealFilters({
    this.platform = 'All',
    this.category = 'All',
    this.shipToCountry = 'All',
    this.monetizationMode = 'All',
    this.minDiscount = 0,
    this.maxPrice,
    this.minRating = 0,
    this.freeShippingOnly = false,
    this.verifiedOnly = false,
  });

  final String platform;
  final String category;
  final String shipToCountry;
  final String monetizationMode;
  final int minDiscount;
  final double? maxPrice;
  final double minRating;
  final bool freeShippingOnly;
  final bool verifiedOnly;

  bool get hasActiveFilters {
    return platform != 'All' ||
        category != 'All' ||
        shipToCountry != 'All' ||
        monetizationMode != 'All' ||
        minDiscount > 0 ||
        maxPrice != null ||
        minRating > 0 ||
        freeShippingOnly ||
        verifiedOnly;
  }

  int get activeCount {
    var count = 0;

    if (platform != 'All') count++;
    if (category != 'All') count++;
    if (shipToCountry != 'All') count++;
    if (monetizationMode != 'All') count++;
    if (minDiscount > 0) count++;
    if (maxPrice != null) count++;
    if (minRating > 0) count++;
    if (freeShippingOnly) count++;
    if (verifiedOnly) count++;

    return count;
  }

  // Kept for backward compatibility with older widgets.
  // New screens use DealsRepository so filtering stays centralized.
  List<Deal> apply(List<Deal> deals) {
    return deals.where((deal) {
      final matchesPlatform = platform == 'All' ||
          _publicMarketplaceLabel(deal.platform) == _publicMarketplaceLabel(platform);
      final matchesCategory = category == 'All' || deal.category == category;
      final matchesCountry = shipToCountry == 'All' || deal.shipsTo.contains(shipToCountry);
      final matchesMonetizationMode = monetizationMode == 'All' || deal.monetizationMode == monetizationMode;
      final matchesDiscount = deal.discountPercent >= minDiscount;
      final matchesPrice = maxPrice == null || deal.currentPrice <= maxPrice!;
      final matchesRating = deal.rating >= minRating;
      final matchesFreeShipping = !freeShippingOnly || _hasFreeShippingToSelectedCountry(deal);
      final matchesVerified = !verifiedOnly || deal.verified;

      return matchesPlatform &&
          matchesCategory &&
          matchesCountry &&
          matchesMonetizationMode &&
          matchesDiscount &&
          matchesPrice &&
          matchesRating &&
          matchesFreeShipping &&
          matchesVerified;
    }).toList();
  }


  static String _publicMarketplaceLabel(String value) {
    final normalized = value.trim().toLowerCase();
    if (normalized.startsWith('ebay')) return 'eBay';
    if (normalized.startsWith('aliexpress')) return 'AliExpress';
    if (normalized.startsWith('alibaba')) return 'Alibaba';
    if (normalized.startsWith('amazon')) return 'Amazon';
    return value.trim();
  }

  static bool _hasFreeShippingToSelectedCountry(Deal deal) {
    return deal.freeShipping &&
        deal.shipsTo.contains(UserSettingsStore.selectedCountryCode);
  }

  DealFilters copyWith({
    String? platform,
    String? category,
    String? shipToCountry,
    String? monetizationMode,
    int? minDiscount,
    double? maxPrice,
    bool clearMaxPrice = false,
    double? minRating,
    bool? freeShippingOnly,
    bool? verifiedOnly,
  }) {
    return DealFilters(
      platform: platform ?? this.platform,
      category: category ?? this.category,
      shipToCountry: shipToCountry ?? this.shipToCountry,
      monetizationMode: monetizationMode ?? this.monetizationMode,
      minDiscount: minDiscount ?? this.minDiscount,
      maxPrice: clearMaxPrice ? null : maxPrice ?? this.maxPrice,
      minRating: minRating ?? this.minRating,
      freeShippingOnly: freeShippingOnly ?? this.freeShippingOnly,
      verifiedOnly: verifiedOnly ?? this.verifiedOnly,
    );
  }
}
