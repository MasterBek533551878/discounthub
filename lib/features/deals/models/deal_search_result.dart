import 'deal.dart';

class DealSearchResult {
  const DealSearchResult({
    required this.deals,
    required this.totalCount,
  });

  final List<Deal> deals;
  final int totalCount;

  int get foundCount => deals.length;
  bool get isEmpty => deals.isEmpty;
}
