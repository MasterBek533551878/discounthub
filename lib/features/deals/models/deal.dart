class Deal {
  const Deal({
    required this.id,
    required this.title,
    required this.description,
    required this.imageUrl,
    required this.platform,
    required this.category,
    required this.oldPrice,
    required this.currentPrice,
    required this.currency,
    required this.productUrl,
    required this.rating,
    required this.reviewCount,
    required this.freeShipping,
    required this.verified,
    required this.shipsTo,
    this.availabilityCountries = const <String>[],
    this.isGlobal = false,
    this.deliveryRegions = const <String>[],
    this.providerId,
    this.monetizationMode = 'direct',
    this.hotDeal = false,
    this.lowestPrice = false,
    this.dealScore = 0,
    this.updatedAt,
  });

  final String id;
  final String title;
  final String description;
  final String imageUrl;
  final String platform;
  final String category;
  final double oldPrice;
  final double currentPrice;
  final String currency;
  final String productUrl;
  final double rating;
  final int reviewCount;
  final bool freeShipping;
  final bool verified;
  final List<String> shipsTo;
  final List<String> availabilityCountries;
  final bool isGlobal;
  final List<String> deliveryRegions;
  final String? providerId;
  final String monetizationMode;
  final bool hotDeal;
  final bool lowestPrice;
  final int dealScore;
  final DateTime? updatedAt;

  factory Deal.fromJson(Map<String, dynamic> json) {
    return Deal(
      id: _string(json['id']),
      title: _string(json['title']),
      description: _string(json['description']),
      imageUrl: _string(json['imageUrl']),
      platform: _string(json['platform']),
      category: _string(json['category']),
      oldPrice: _double(json['oldPrice']),
      currentPrice: _double(json['currentPrice']),
      currency: _string(json['currency'], fallback: 'USD'),
      productUrl: _string(json['productUrl']),
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
      updatedAt: _dateTime(json['updatedAt'] ?? json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'id': id,
      'title': title,
      'description': description,
      'imageUrl': imageUrl,
      'platform': platform,
      'category': category,
      'oldPrice': oldPrice,
      'currentPrice': currentPrice,
      'currency': currency,
      'productUrl': productUrl,
      'rating': rating,
      'reviewCount': reviewCount,
      'freeShipping': freeShipping,
      'verified': verified,
      'shipsTo': shipsTo,
      'availabilityCountries': availabilityCountries,
      'isGlobal': isGlobal,
      'deliveryRegions': deliveryRegions,
      'providerId': providerId,
      'monetizationMode': monetizationMode,
      'hotDeal': hotDeal,
      'lowestPrice': lowestPrice,
      'dealScore': dealScore,
      'updatedAt': updatedAt?.toIso8601String(),
    };
  }

  double get rawDiscountPercent {
    if (oldPrice <= 0 || currentPrice <= 0 || oldPrice <= currentPrice) {
      return 0;
    }
    return ((oldPrice - currentPrice) / oldPrice) * 100;
  }

  bool get hasRealDiscount => rawDiscountPercent >= 1;

  int get discountPercent {
    if (!hasRealDiscount) {
      return 0;
    }
    final percent = rawDiscountPercent.round();
    if (percent < 1) return 0;
    if (percent > 100) return 100;
    return percent;
  }

  double get savedAmount {
    if (!hasRealDiscount) {
      return 0;
    }
    return oldPrice - currentPrice;
  }

  String get formattedCurrentPrice =>
      '$currency ${currentPrice.toStringAsFixed(2)}';

  String get formattedOldPrice => '$currency ${oldPrice.toStringAsFixed(2)}';

  String get formattedSavedAmount =>
      '$currency ${savedAmount.toStringAsFixed(2)}';

  static DateTime? _dateTime(dynamic value) {
    if (value is DateTime) return value;
    if (value is String && value.trim().isNotEmpty) {
      return DateTime.tryParse(value.trim());
    }
    return null;
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
