import '../models/deal.dart';
import 'deals_data_source.dart';

class MemoryDealsDataSource implements DealsDataSource {
  const MemoryDealsDataSource(this.deals);

  final List<Deal> deals;

  @override
  List<Deal> getDeals() {
    return List<Deal>.unmodifiable(deals);
  }
}
