import '../models/promotion.dart';

class PromotionApiPage {
  const PromotionApiPage({
    required this.promotions,
    required this.totalCount,
    required this.page,
    required this.pageSize,
    required this.hasNextPage,
  });

  final List<Promotion> promotions;
  final int totalCount;
  final int page;
  final int pageSize;
  final bool hasNextPage;

  factory PromotionApiPage.fromJson(Map<String, dynamic> json) {
    final items = json['items'];
    final rawItems = items is List ? items : const <dynamic>[];
    final page = _int(json['page'], fallback: 1);
    final pageSize = _int(json['pageSize'] ?? json['page_size'], fallback: rawItems.length);
    final totalCount = _int(json['totalCount'] ?? json['total'], fallback: rawItems.length);

    return PromotionApiPage(
      promotions: rawItems
          .whereType<Map<String, dynamic>>()
          .map(Promotion.fromJson)
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
