import '../models/deal.dart';

class DealApiDto {
  const DealApiDto({required this.json});

  final Map<String, dynamic> json;

  factory DealApiDto.fromJson(Map<String, dynamic> json) {
    return DealApiDto(json: json);
  }

  Deal toDomain() {
    return Deal(
      id: _string(json['id']),
      title: _localizedText(json['title']),
      description: _localizedText(json['description']),
      imageUrl: _string(json['imageUrl']),
      platform: _string(json['platform']),
      category: _string(json['category']),
      oldPrice: _double(json['oldPrice']),
      currentPrice: _double(json['currentPrice']),
      currency: _string(json['currency'], fallback: 'USD'),
      productUrl: _string(
        json['affiliateUrl'],
        fallback: _string(json['productUrl']),
      ),
      rating: _double(json['rating']),
      reviewCount: _int(json['reviewCount']),
      freeShipping: _bool(json['freeShipping']),
      verified: _bool(json['verified']),
      shipsTo: _stringList(json['shipsTo']),
      availabilityCountries: _stringList(
        json['availabilityCountries'] ?? json['availability_countries'],
      ),
      isGlobal: _bool(json['isGlobal'] ?? json['is_global']),
      deliveryRegions: _stringList(
        json['deliveryRegions'] ?? json['delivery_regions'],
      ),
      providerId: _nullableString(json['providerId'] ?? json['provider_id']),
      monetizationMode: _string(
        json['monetizationMode'] ?? json['monetization_mode'],
        fallback: 'direct',
      ),
      hotDeal: _bool(json['hotDeal'] ?? json['hot_deal']),
      lowestPrice: _bool(json['lowestPrice'] ?? json['lowest_price']),
      dealScore: _int(json['dealScore'] ?? json['deal_score']),
    );
  }

  static String _localizedText(dynamic value) {
    if (value is String) return value;

    if (value is Map) {
      for (final key in const ['en', 'ru', 'uz']) {
        final text = value[key];
        if (text is String && text.trim().isNotEmpty) return text;
      }

      for (final entry in value.entries) {
        final text = entry.value;
        if (text is String && text.trim().isNotEmpty) return text;
      }
    }

    return '';
  }

  static String _string(dynamic value, {String fallback = ''}) {
    if (value is String && value.trim().isNotEmpty) return value.trim();
    if (value is num) return value.toString();
    return fallback;
  }

  static String? _nullableString(dynamic value) {
    if (value is String && value.trim().isNotEmpty) return value.trim();
    if (value is num) return value.toString();
    return null;
  }

  static double _double(dynamic value) {
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) return double.tryParse(value) ?? 0;
    return 0;
  }

  static int _int(dynamic value) {
    if (value is int) return value;
    if (value is double) return value.round();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }

  static bool _bool(dynamic value) {
    if (value is bool) return value;
    if (value is String) return value.toLowerCase() == 'true';
    if (value is num) return value != 0;
    return false;
  }

  static List<String> _stringList(dynamic value) {
    if (value is! List) return const <String>[];

    return value
        .whereType<Object>()
        .map((item) => item.toString().trim())
        .where((item) => item.isNotEmpty)
        .toList(growable: false);
  }
}
