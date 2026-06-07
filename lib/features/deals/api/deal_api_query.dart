import '../models/deal_filters.dart';
import '../models/deal_query.dart';

class DealApiQuery {
  const DealApiQuery({
    this.searchText = '',
    this.platform,
    this.platforms = const <String>[],
    this.category,
    this.categories = const <String>[],
    this.shipToCountry,
    this.deliveryRegion,
    this.monetizationMode,
    this.currency = '',
    this.minDiscount = 0,
    this.maxPrice,
    this.minRating = 0,
    this.freeShippingOnly = false,
    this.verifiedOnly = false,
    this.sort = DealSort.discountHighToLow,
    this.page = 1,
    this.pageSize = 100,
  });

  final String searchText;
  final String? platform;
  final List<String> platforms;
  final String? category;
  final List<String> categories;
  final String? shipToCountry;
  final String? deliveryRegion;
  final String? monetizationMode;
  final String currency;
  final int minDiscount;
  final double? maxPrice;
  final double minRating;
  final bool freeShippingOnly;
  final bool verifiedOnly;
  final DealSort sort;
  final int page;
  final int pageSize;

  factory DealApiQuery.fromDealQuery(
    DealQuery query, {
    String currency = '',
  }) {
    final filters = query.filters;

    return DealApiQuery(
      searchText: query.searchText,
      platforms: _publicMarketplaceFilters(filters.selectedPlatforms),
      categories: _nonEmptyAllValues(filters.selectedCategories),
      monetizationMode: null,
      currency: currency,
      minDiscount: filters.minDiscount,
      maxPrice: filters.maxPrice,
      sort: query.sort,
    );
  }

  factory DealApiQuery.fromFilters(
    DealFilters filters, {
    String currency = '',
  }) {
    return DealApiQuery(
      platforms: _publicMarketplaceFilters(filters.selectedPlatforms),
      categories: _nonEmptyAllValues(filters.selectedCategories),
      monetizationMode: null,
      currency: currency,
      minDiscount: filters.minDiscount,
      maxPrice: filters.maxPrice,
    );
  }

  DealApiQuery copyWith({
    String? searchText,
    String? platform,
    List<String>? platforms,
    String? category,
    List<String>? categories,
    String? shipToCountry,
    String? deliveryRegion,
    String? monetizationMode,
    String? currency,
    int? minDiscount,
    double? maxPrice,
    double? minRating,
    bool? freeShippingOnly,
    bool? verifiedOnly,
    DealSort? sort,
    int? page,
    int? pageSize,
  }) {
    return DealApiQuery(
      searchText: searchText ?? this.searchText,
      platform: platform ?? this.platform,
      platforms: platforms ?? this.platforms,
      category: category ?? this.category,
      categories: categories ?? this.categories,
      shipToCountry: shipToCountry ?? this.shipToCountry,
      deliveryRegion: deliveryRegion ?? this.deliveryRegion,
      monetizationMode: monetizationMode ?? this.monetizationMode,
      currency: currency ?? this.currency,
      minDiscount: minDiscount ?? this.minDiscount,
      maxPrice: maxPrice ?? this.maxPrice,
      minRating: minRating ?? this.minRating,
      freeShippingOnly: freeShippingOnly ?? this.freeShippingOnly,
      verifiedOnly: verifiedOnly ?? this.verifiedOnly,
      sort: sort ?? this.sort,
      page: page ?? this.page,
      pageSize: pageSize ?? this.pageSize,
    );
  }

  Map<String, String> toQueryParameters() {
    final parameters = <String, String>{
      'sort': _sortValue(sort),
      'page': page.toString(),
      'page_size': pageSize.toString(),
    };

    void addTextParameter(String key, String? value) {
      final normalized = value?.trim();
      if (normalized == null || normalized.isEmpty) return;
      parameters[key] = normalized;
    }

    void addMultiTextParameter(
      String key,
      List<String> values, {
      String? fallback,
    }) {
      final normalized = _nonEmptyAllValues(values);
      if (normalized.isNotEmpty) {
        parameters[key] = normalized.join(',');
        return;
      }
      addTextParameter(key, fallback);
    }

    addTextParameter('q', searchText);
    addMultiTextParameter('platform', platforms, fallback: platform);
    addMultiTextParameter('category', categories, fallback: category);
    addTextParameter('ships_to', shipToCountry);
    addTextParameter('delivery_region', deliveryRegion);
    addTextParameter('monetization_mode', monetizationMode);

    final normalizedCurrency = currency.trim().toUpperCase();
    if (normalizedCurrency.isNotEmpty) {
      parameters['currency'] = normalizedCurrency;
    }

    if (minDiscount > 0) {
      parameters['min_discount'] = minDiscount.toString();
    }
    if (maxPrice != null) {
      parameters['max_price'] = maxPrice!.toStringAsFixed(2);
    }
    if (minRating > 0) {
      parameters['min_rating'] = minRating.toStringAsFixed(1);
    }
    if (freeShippingOnly) {
      parameters['free_shipping'] = 'true';
    }
    if (verifiedOnly) {
      parameters['verified'] = 'true';
    }

    return parameters;
  }

  static List<String> _publicMarketplaceFilters(List<String> values) {
    final normalizedValues = <String>[];
    for (final value in values) {
      final mapped = _publicMarketplaceFilter(value);
      if (mapped == null || normalizedValues.contains(mapped)) continue;
      normalizedValues.add(mapped);
    }
    return List<String>.unmodifiable(normalizedValues);
  }

  static String? _publicMarketplaceFilter(String? value) {
    final normalized = value?.trim();
    if (normalized == null || normalized.isEmpty || normalized == 'All') return null;

    final lower = normalized.toLowerCase();
    if (lower.startsWith('ebay')) return 'eBay';
    if (lower.startsWith('aliexpress')) return 'AliExpress';
    if (lower.startsWith('alibaba')) return 'Alibaba';
    if (lower.startsWith('amazon')) return 'Amazon';

    return normalized;
  }

  static List<String> _nonEmptyAllValues(List<String> values) {
    final normalizedValues = <String>[];
    for (final rawValue in values) {
      final value = rawValue.trim();
      if (value.isEmpty || value == 'All') continue;
      if (!normalizedValues.contains(value)) {
        normalizedValues.add(value);
      }
    }
    return List<String>.unmodifiable(normalizedValues);
  }

  static String _sortValue(DealSort sort) {
    switch (sort) {
      case DealSort.bestMatch:
        return 'score_desc';
      case DealSort.discountHighToLow:
        return 'discount_desc';
      case DealSort.newest:
        return 'newest';
      case DealSort.priceLowToHigh:
        return 'price_asc';
      case DealSort.priceHighToLow:
        return 'price_desc';
      case DealSort.ratingHighToLow:
        return 'rating_desc';
    }
  }
}
