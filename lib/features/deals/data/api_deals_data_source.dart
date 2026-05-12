import '../api/deal_api_query.dart';
import '../api/deals_api_client.dart';
import '../models/deal.dart';
import 'deals_data_source.dart';

class ApiDealsDataSource implements DealsDataSource {
  ApiDealsDataSource({required this.apiClient});

  static const int _maxPagesPerRefresh = 12;

  final DealsApiClient apiClient;

  List<Deal> _cachedDeals = const <Deal>[];

  Future<void> refresh([DealApiQuery query = const DealApiQuery()]) async {
    final dealsById = <String, Deal>{};
    var pageNumber = query.page < 1 ? 1 : query.page;
    final pageSize = query.pageSize < 1 ? 100 : query.pageSize;

    for (var requestIndex = 0; requestIndex < _maxPagesPerRefresh; requestIndex++) {
      final page = await apiClient.getDeals(
        query.copyWith(
          page: pageNumber,
          pageSize: pageSize,
        ),
      );

      for (final deal in page.deals) {
        if (_looksLikeDemoDeal(deal)) continue;
        dealsById[deal.id] = deal;
      }

      if (!page.hasMore || page.deals.isEmpty) break;
      pageNumber += 1;
    }

    _cachedDeals = List<Deal>.unmodifiable(dealsById.values);
  }

  @override
  List<Deal> getDeals() {
    return List<Deal>.unmodifiable(_cachedDeals);
  }

  bool _looksLikeDemoDeal(Deal deal) {
    final id = deal.id.toLowerCase();
    final platform = deal.platform.toLowerCase();
    final url = deal.productUrl.toLowerCase();

    return id.startsWith('mock_') ||
        id.startsWith('feed_demo_') ||
        platform == 'feedshop' ||
        platform == 'demo' ||
        url.contains('example.com');
  }
}
