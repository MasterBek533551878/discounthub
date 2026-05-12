import '../models/deal.dart';
import 'deals_data_source.dart';
import 'mock_deals.dart';

class FakeDealsDataSource implements DealsDataSource {
  const FakeDealsDataSource();

  @override
  List<Deal> getDeals() {
    return List<Deal>.unmodifiable(mockDeals);
  }
}
