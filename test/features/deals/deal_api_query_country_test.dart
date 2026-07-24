import 'package:discounthub/features/deals/api/deal_api_query.dart';
import 'package:discounthub/features/deals/models/deal_filters.dart';
import 'package:discounthub/features/deals/models/deal_query.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('country filter uses the backend country parameter', () {
    const query = DealQuery(filters: DealFilters(shipToCountry: 'gb'));
    final parameters = DealApiQuery.fromDealQuery(query).toQueryParameters();
    expect(parameters['country'], 'GB');
    expect(parameters.containsKey('ships_to'), isFalse);
  });

  test('All countries does not send a country parameter', () {
    const query = DealQuery(filters: DealFilters(shipToCountry: 'All'));
    final parameters = DealApiQuery.fromDealQuery(query).toQueryParameters();
    expect(parameters.containsKey('country'), isFalse);
  });
}
