import 'deal.dart';

class DealFilters {
  const DealFilters({
    this.platform = 'All',
    this.category = 'All',
    this.platformSelections = const <String>[],
    this.categorySelections = const <String>[],
    this.shipToCountry = 'All',
    this.deliveryRegion = 'All',
    this.monetizationMode = 'All',
    this.minDiscount = 0,
    this.maxPrice,
    this.minRating = 0,
    this.freeShippingOnly = false,
    this.verifiedOnly = false,
  });

  // Kept for backward compatibility with older widgets/routes.
  // Use selectedPlatforms/selectedCategories for new multi-select filters.
  final String platform;
  final String category;
  final List<String> platformSelections;
  final List<String> categorySelections;
  final String shipToCountry;
  final String deliveryRegion;
  final String monetizationMode;
  final int minDiscount;
  final double? maxPrice;
  final double minRating;
  final bool freeShippingOnly;
  final bool verifiedOnly;

  List<String> get selectedPlatforms => _normalizedSelections(
        platformSelections,
        fallback: platform,
        publicMarketplace: true,
      );

  List<String> get selectedCategories => _normalizedSelections(
        categorySelections,
        fallback: category,
      );

  bool get hasPlatformFilters => selectedPlatforms.isNotEmpty;

  bool get hasCategoryFilters => selectedCategories.isNotEmpty;

  bool get hasActiveFilters {
    return hasPlatformFilters ||
        hasCategoryFilters ||
        minDiscount > 0 ||
        maxPrice != null;
  }

  int get activeCount {
    var count = 0;

    if (hasPlatformFilters) count++;
    if (hasCategoryFilters) count++;
    if (minDiscount > 0) count++;
    if (maxPrice != null) count++;

    return count;
  }

  // Kept for backward compatibility with older widgets.
  // New screens use DealsRepository so filtering stays centralized.
  List<Deal> apply(List<Deal> deals) {
    final selectedPlatformLabels = selectedPlatforms
        .map(_publicMarketplaceLabel)
        .toSet();
    final selectedCategoryLabels = selectedCategories.toSet();

    return deals.where((deal) {
      final matchesPlatform = selectedPlatformLabels.isEmpty ||
          selectedPlatformLabels.contains(_publicMarketplaceLabel(deal.platform));
      final matchesCategory = selectedCategoryLabels.isEmpty ||
          selectedCategoryLabels.contains(deal.category);
      final matchesDiscount = deal.discountPercent >= minDiscount;
      final matchesPrice = maxPrice == null || deal.currentPrice <= maxPrice!;

      return matchesPlatform &&
          matchesCategory &&
          matchesDiscount &&
          matchesPrice;
    }).toList();
  }

  static List<String> _normalizedSelections(
    List<String> rawValues, {
    required String fallback,
    bool publicMarketplace = false,
  }) {
    final values = rawValues.isNotEmpty ? rawValues : <String>[fallback];
    final normalized = <String>[];

    for (final rawValue in values) {
      final value = rawValue.trim();
      if (value.isEmpty || value == 'All') continue;
      final mapped = publicMarketplace ? _publicMarketplaceLabel(value) : value;
      if (!normalized.contains(mapped)) {
        normalized.add(mapped);
      }
    }

    return List<String>.unmodifiable(normalized);
  }

  static String _publicMarketplaceLabel(String value) {
    final normalized = value.trim().toLowerCase();
    if (normalized.startsWith('ebay')) return 'eBay';
    if (normalized.startsWith('aliexpress')) return 'AliExpress';
    if (normalized.startsWith('alibaba')) return 'Alibaba';
    if (normalized.startsWith('amazon')) return 'Amazon';
    return value.trim();
  }

  DealFilters copyWith({
    String? platform,
    String? category,
    List<String>? platformSelections,
    List<String>? categorySelections,
    bool clearPlatforms = false,
    bool clearCategories = false,
    String? shipToCountry,
    String? deliveryRegion,
    String? monetizationMode,
    int? minDiscount,
    double? maxPrice,
    bool clearMaxPrice = false,
    double? minRating,
    bool? freeShippingOnly,
    bool? verifiedOnly,
  }) {
    return DealFilters(
      platform: clearPlatforms ? 'All' : platform ?? this.platform,
      category: clearCategories ? 'All' : category ?? this.category,
      platformSelections: clearPlatforms
          ? const <String>[]
          : platformSelections ?? this.platformSelections,
      categorySelections: clearCategories
          ? const <String>[]
          : categorySelections ?? this.categorySelections,
      shipToCountry: shipToCountry ?? this.shipToCountry,
      deliveryRegion: deliveryRegion ?? this.deliveryRegion,
      monetizationMode: monetizationMode ?? this.monetizationMode,
      minDiscount: minDiscount ?? this.minDiscount,
      maxPrice: clearMaxPrice ? null : maxPrice ?? this.maxPrice,
      minRating: minRating ?? this.minRating,
      freeShippingOnly: freeShippingOnly ?? this.freeShippingOnly,
      verifiedOnly: verifiedOnly ?? this.verifiedOnly,
    );
  }
}
