import '../models/deal.dart';

class DealFacets {
  const DealFacets({
    required this.totalCount,
    required this.marketplaces,
    required this.categories,
    required this.countries,
    required this.deliveryRegions,
    required this.currencies,
    required this.monetizationModes,
    required this.priceRange,
    required this.discountRange,
  });

  final int totalCount;
  final List<DealFacetItem> marketplaces;
  final List<DealFacetItem> categories;
  final List<DealFacetItem> countries;
  final List<DealFacetItem> deliveryRegions;
  final List<DealFacetItem> currencies;
  final List<DealFacetItem> monetizationModes;
  final DealNumberRange priceRange;
  final DealNumberRange discountRange;

  bool get hasRemoteData {
    return totalCount > 0 ||
        marketplaces.isNotEmpty ||
        categories.isNotEmpty ||
        countries.isNotEmpty ||
        deliveryRegions.isNotEmpty ||
        currencies.isNotEmpty ||
        monetizationModes.isNotEmpty ||
        priceRange.max > 0 ||
        discountRange.max > 0;
  }

  factory DealFacets.empty() {
    return const DealFacets(
      totalCount: 0,
      marketplaces: <DealFacetItem>[],
      categories: <DealFacetItem>[],
      countries: <DealFacetItem>[],
      deliveryRegions: <DealFacetItem>[],
      currencies: <DealFacetItem>[],
      monetizationModes: <DealFacetItem>[],
      priceRange: DealNumberRange(min: 0, max: 0, unit: 'USD'),
      discountRange: DealNumberRange(min: 0, max: 0, unit: '%'),
    );
  }

  factory DealFacets.fromJson(Map<String, dynamic> json) {
    return DealFacets(
      totalCount: _int(
        json['total'] ?? json['totalCount'] ?? json['total_count'],
      ),
      marketplaces: _facetItems(json['marketplaces']),
      categories: _facetItems(json['categories']),
      countries: _facetItems(json['countries'] ?? json['shippingCountries'] ?? json['shipping_countries']),
      deliveryRegions: _facetItems(json['deliveryRegions'] ?? json['delivery_regions']),
      currencies: _facetItems(json['currencies']),
      monetizationModes: _facetItems(
        json['monetizationModes'] ?? json['monetization_modes'],
      ),
      priceRange: DealNumberRange.fromJson(
        json['priceRange'] ?? json['price_range'],
        defaultUnit: _string(json['currency'], fallback: 'USD'),
      ),
      discountRange: DealNumberRange.fromJson(
        json['discountRange'] ?? json['discount_range'],
        defaultUnit: '%',
      ),
    );
  }

  factory DealFacets.fromDeals(List<Deal> deals) {
    if (deals.isEmpty) return DealFacets.empty();

    return DealFacets(
      totalCount: deals.length,
      marketplaces: _itemsFromValues(deals.map((deal) => _publicMarketplaceLabel(deal.platform))),
      categories: _itemsFromValues(deals.map((deal) => deal.category)),
      countries: _itemsFromValues(deals.expand((deal) => deal.shipsTo)),
      deliveryRegions: _itemsFromValues(deals.expand((deal) => deal.deliveryRegions)),
      currencies: _itemsFromValues(deals.map((deal) => deal.currency)),
      monetizationModes: _itemsFromValues(
        deals.map((deal) => deal.monetizationMode),
      ),
      priceRange: DealNumberRange(
        min: deals.map((deal) => deal.currentPrice).reduce(_min),
        max: deals.map((deal) => deal.currentPrice).reduce(_max),
        unit: deals.first.currency,
      ),
      discountRange: DealNumberRange(
        min: deals.map((deal) => deal.discountPercent.toDouble()).reduce(_min),
        max: deals.map((deal) => deal.discountPercent.toDouble()).reduce(_max),
        unit: '%',
      ),
    );
  }

  int countForMarketplace(String id) => _countFor(marketplaces, id);

  int countForCategory(String id) => _countFor(categories, id);

  int countForCountry(String id) => _countFor(countries, id);

  int countForDeliveryRegion(String id) => _countFor(deliveryRegions, id);

  int countForMonetizationMode(String id) => _countFor(monetizationModes, id);

  static int _countFor(List<DealFacetItem> items, String id) {
    for (final item in items) {
      if (item.id == id) return item.count;
    }
    return 0;
  }

  static List<DealFacetItem> _facetItems(dynamic value) {
    if (value is! List) return const <DealFacetItem>[];

    final items = value
        .map(DealFacetItem.fromDynamic)
        .where((item) => item.id.trim().isNotEmpty)
        .toList(growable: false);

    items.sort((a, b) {
      final byCount = b.count.compareTo(a.count);
      if (byCount != 0) return byCount;
      return a.name.toLowerCase().compareTo(b.name.toLowerCase());
    });

    return List<DealFacetItem>.unmodifiable(items);
  }

  static List<DealFacetItem> _itemsFromValues(Iterable<String> rawValues) {
    final counts = <String, int>{};
    final names = <String, String>{};

    for (final rawValue in rawValues) {
      final value = rawValue.trim();
      if (value.isEmpty) continue;
      final key = value.toLowerCase();
      counts[key] = (counts[key] ?? 0) + 1;
      names.putIfAbsent(key, () => value);
    }

    final items = counts.entries
        .map(
          (entry) => DealFacetItem(
            id: names[entry.key] ?? entry.key,
            name: names[entry.key] ?? entry.key,
            count: entry.value,
          ),
        )
        .toList(growable: false);

    items.sort((a, b) {
      final byCount = b.count.compareTo(a.count);
      if (byCount != 0) return byCount;
      return a.name.toLowerCase().compareTo(b.name.toLowerCase());
    });

    return List<DealFacetItem>.unmodifiable(items);
  }


  static String _publicMarketplaceLabel(String value) {
    final normalized = value.trim().toLowerCase();
    if (normalized.startsWith('ebay')) return 'eBay';
    if (normalized.startsWith('aliexpress')) return 'AliExpress';
    if (normalized.startsWith('alibaba')) return 'Alibaba';
    if (normalized.startsWith('amazon')) return 'Amazon';
    return value.trim();
  }

  static double _min(double a, double b) => a < b ? a : b;

  static double _max(double a, double b) => a > b ? a : b;
}

class DealFacetItem {
  const DealFacetItem({
    required this.id,
    required this.name,
    required this.count,
  });

  final String id;
  final String name;
  final int count;

  factory DealFacetItem.fromDynamic(dynamic value) {
    if (value is String) {
      return DealFacetItem(id: value.trim(), name: value.trim(), count: 0);
    }

    if (value is Map<String, dynamic>) {
      final id = _string(value['id'] ?? value['value'] ?? value['key'] ?? value['name']);
      return DealFacetItem(
        id: id,
        name: _string(value['name'], fallback: id),
        count: _int(value['count'] ?? value['total']),
      );
    }

    if (value is Map) {
      final mapped = value.map(
        (key, mappedValue) => MapEntry(key.toString(), mappedValue),
      );
      return DealFacetItem.fromDynamic(mapped);
    }

    return const DealFacetItem(id: '', name: '', count: 0);
  }
}

class DealNumberRange {
  const DealNumberRange({
    required this.min,
    required this.max,
    required this.unit,
  });

  final double min;
  final double max;
  final String unit;

  factory DealNumberRange.fromJson(dynamic value, {required String defaultUnit}) {
    if (value is Map<String, dynamic>) {
      return DealNumberRange(
        min: _double(value['min']),
        max: _double(value['max']),
        unit: _string(value['currency'] ?? value['unit'], fallback: defaultUnit),
      );
    }

    if (value is Map) {
      final mapped = value.map(
        (key, mappedValue) => MapEntry(key.toString(), mappedValue),
      );
      return DealNumberRange.fromJson(mapped, defaultUnit: defaultUnit);
    }

    return DealNumberRange(min: 0, max: 0, unit: defaultUnit);
  }
}

String _string(dynamic value, {String fallback = ''}) {
  if (value is String && value.trim().isNotEmpty) return value.trim();
  if (value is num) return value.toString();
  return fallback;
}

int _int(dynamic value, {int fallback = 0}) {
  if (value is int) return value;
  if (value is double) return value.round();
  if (value is String) return int.tryParse(value) ?? fallback;
  return fallback;
}

double _double(dynamic value, {double fallback = 0}) {
  if (value is double) return value;
  if (value is int) return value.toDouble();
  if (value is String) return double.tryParse(value) ?? fallback;
  return fallback;
}
