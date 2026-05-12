import '../models/deal.dart';

abstract class DealsDataSource {
  List<Deal> getDeals();
}
