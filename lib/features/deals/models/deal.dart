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
    };
  }

  int get discountPercent {
    if (oldPrice <= 0) return 0;
    return (((oldPrice - currentPrice) / oldPrice) * 100).round();
  }

  double get savedAmount => oldPrice - currentPrice;

  String get formattedCurrentPrice => '$currency ${currentPrice.toStringAsFixed(2)}';

  String get formattedOldPrice => '$currency ${oldPrice.toStringAsFixed(2)}';

  String get formattedSavedAmount => '$currency ${savedAmount.toStringAsFixed(2)}';

  static String _string(dynamic value, {String fallback = ''}) {
    if (value is String && value.trim().isNotEmpty) return value.trim();
    if (value is num) return value.toString();
    return fallback;
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
