import '../models/deal.dart';
import 'deals_data_source.dart';

class EmptyDealsDataSource implements DealsDataSource {
  const EmptyDealsDataSource();

  @override
  List<Deal> getDeals() => const <Deal>[];
}
