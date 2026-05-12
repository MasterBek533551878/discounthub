import '../models/deal.dart';
import 'deal_api_dto.dart';

class DealApiPage {
  const DealApiPage({
    required this.deals,
    required this.totalCount,
    required this.page,
    required this.pageSize,
    required this.hasNextPage,
  });

  final List<Deal> deals;
  final int totalCount;
  final int page;
  final int pageSize;
  final bool hasNextPage;

  bool get hasMore {
    if (hasNextPage) return true;
    if (totalCount <= 0) return false;
    return page * pageSize < totalCount;
  }

  factory DealApiPage.fromJson(Map<String, dynamic> json) {
    final items = json['items'];
    final rawDeals = items is List ? items : const <dynamic>[];
    final page = _int(json['page'], fallback: 1);
    final pageSize = _int(json['pageSize'] ?? json['page_size'], fallback: rawDeals.length);
    final totalCount = _int(json['totalCount'] ?? json['total'], fallback: rawDeals.length);

    return DealApiPage(
      deals: rawDeals
          .whereType<Map<String, dynamic>>()
          .map((item) => DealApiDto.fromJson(item).toDomain())
          .toList(growable: false),
      totalCount: totalCount,
      page: page,
      pageSize: pageSize,
      hasNextPage: _bool(json['hasNextPage'] ?? json['has_next_page']),
    );
  }

  static int _int(dynamic value, {int fallback = 0}) {
    if (value is int) return value;
    if (value is double) return value.round();
    if (value is String) return int.tryParse(value) ?? fallback;
    return fallback;
  }

  static bool _bool(dynamic value) {
    if (value is bool) return value;
    if (value is String) return value.toLowerCase() == 'true';
    return false;
  }
}
