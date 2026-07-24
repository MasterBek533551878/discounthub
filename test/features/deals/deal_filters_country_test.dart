import 'package:discounthub/features/deals/models/deal.dart';
import 'package:discounthub/features/deals/models/deal_filters.dart';
import 'package:flutter_test/flutter_test.dart';

Deal _deal({
  required String id,
  List<String> countries = const <String>[],
  bool isGlobal = false,
}) {
  return Deal(
    id: id,
    title: id,
    description: '',
    imageUrl: 'https://example.com/$id.jpg',
    platform: 'Store',
    category: 'Other',
    oldPrice: 10,
    currentPrice: 5,
    currency: 'USD',
    productUrl: 'https://example.com/$id',
    rating: 0,
    reviewCount: 0,
    freeShipping: false,
    verified: false,
    shipsTo: const <String>[],
    availabilityCountries: countries,
    isGlobal: isGlobal,
  );
}

void main() {
  test('country filter includes matching and global deals', () {
    final deals = <Deal>[
      _deal(id: 'gb', countries: const <String>['GB']),
      _deal(id: 'us', countries: const <String>['US']),
      _deal(id: 'global', isGlobal: true),
    ];

    const filters = DealFilters(shipToCountry: 'GB');
    final result = filters.apply(deals);

    expect(result.map((deal) => deal.id), <String>['gb', 'global']);
    expect(filters.hasCountryFilter, isTrue);
    expect(filters.activeCount, 1);
  });
}
