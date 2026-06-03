import '../models/deal_filters.dart';
import '../models/deal_query.dart';

class DealApiQuery {
  const DealApiQuery({
    this.searchText = '',
    this.platform,
    this.category,
    this.shipToCountry,
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
  final String? category;
  final String? shipToCountry;
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
      platform: _publicMarketplaceFilter(_emptyAllToNull(filters.platform)),
      category: _emptyAllToNull(filters.category),
      shipToCountry: _emptyAllToNull(filters.shipToCountry),
      monetizationMode: _emptyAllToNull(filters.monetizationMode),
      currency: currency,
      minDiscount: filters.minDiscount,
      maxPrice: filters.maxPrice,
      minRating: filters.minRating,
      freeShippingOnly: filters.freeShippingOnly,
      verifiedOnly: filters.verifiedOnly,
      sort: query.sort,
    );
  }

  factory DealApiQuery.fromFilters(
    DealFilters filters, {
    String currency = '',
  }) {
    return DealApiQuery(
      platform: _publicMarketplaceFilter(_emptyAllToNull(filters.platform)),
      category: _emptyAllToNull(filters.category),
      shipToCountry: _emptyAllToNull(filters.shipToCountry),
      monetizationMode: _emptyAllToNull(filters.monetizationMode),
      currency: currency,
      minDiscount: filters.minDiscount,
      maxPrice: filters.maxPrice,
      minRating: filters.minRating,
      freeShippingOnly: filters.freeShippingOnly,
      verifiedOnly: filters.verifiedOnly,
    );
  }


  DealApiQuery copyWith({
    String? searchText,
    String? platform,
    String? category,
    String? shipToCountry,
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
      category: category ?? this.category,
      shipToCountry: shipToCountry ?? this.shipToCountry,
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

    addTextParameter('q', searchText);
    addTextParameter('platform', platform);
    addTextParameter('category', category);
    addTextParameter('ships_to', shipToCountry);
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

  static String? _publicMarketplaceFilter(String? value) {
    final normalized = value?.trim();
    if (normalized == null || normalized.isEmpty) return null;

    final lower = normalized.toLowerCase();
    if (lower.startsWith('ebay')) return 'eBay';
    if (lower.startsWith('aliexpress')) return 'AliExpress';
    if (lower.startsWith('alibaba')) return 'Alibaba';
    if (lower.startsWith('amazon')) return 'Amazon';

    return normalized;
  }

  static String? _emptyAllToNull(String value) {
    final normalized = value.trim();
    if (normalized.isEmpty || normalized == 'All') return null;
    return normalized;
  }

  static String _sortValue(DealSort sort) {
    switch (sort) {
      case DealSort.discountHighToLow:
        return 'discount_desc';
      case DealSort.priceLowToHigh:
        return 'price_asc';
      case DealSort.ratingHighToLow:
        return 'rating_desc';
    }
  }
}
