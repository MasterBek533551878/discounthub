class Promotion {
  const Promotion({
    required this.id,
    required this.type,
    required this.title,
    required this.description,
    required this.store,
    required this.discountText,
    required this.landingUrl,
    required this.featured,
    required this.updatedAt,
    this.code,
    this.affiliateUrl,
    this.imageUrl,
    this.providerId,
    this.monetizationMode = 'affiliate',
    this.availabilityCountries = const <String>[],
    this.isGlobal = false,
    this.validFrom,
    this.validUntil,
  });

  final String id;
  final String type;
  final String title;
  final String description;
  final String store;
  final String discountText;
  final String? code;
  final String landingUrl;
  final String? affiliateUrl;
  final String? imageUrl;
  final String? providerId;
  final String monetizationMode;
  final List<String> availabilityCountries;
  final bool isGlobal;
  final DateTime? validFrom;
  final DateTime? validUntil;
  final bool featured;
  final DateTime updatedAt;

  bool get hasCode => code != null && code!.trim().isNotEmpty;

  bool get isFlashSale => type == 'flash_sale';

  bool get hasDeadline => validUntil != null;

  factory Promotion.fromJson(Map<String, dynamic> json) {
    return Promotion(
      id: _string(json['id']),
      type: _string(json['type'], fallback: 'sale'),
      title: _string(json['title']),
      description: _string(json['description']),
      store: _string(json['store']),
      discountText: _string(json['discountText'] ?? json['discount_text']),
      code: _nullableString(json['code']),
      landingUrl: _string(json['landingUrl'] ?? json['landing_url']),
      affiliateUrl: _nullableString(
        json['affiliateUrl'] ?? json['affiliate_url'],
      ),
      imageUrl: _nullableString(json['imageUrl'] ?? json['image_url']),
      providerId: _nullableString(json['providerId'] ?? json['provider_id']),
      monetizationMode: _string(
        json['monetizationMode'] ?? json['monetization_mode'],
        fallback: 'affiliate',
      ),
      availabilityCountries: _stringList(
        json['availabilityCountries'] ?? json['availability_countries'],
      ),
      isGlobal: _bool(json['isGlobal'] ?? json['is_global']),
      validFrom: _dateTime(json['validFrom'] ?? json['valid_from']),
      validUntil: _dateTime(json['validUntil'] ?? json['valid_until']),
      featured: _bool(json['featured']),
      updatedAt:
          _dateTime(json['updatedAt'] ?? json['updated_at']) ?? DateTime.now(),
    );
  }

  static String _string(dynamic value, {String fallback = ''}) {
    if (value == null) return fallback;
    return value.toString();
  }

  static String? _nullableString(dynamic value) {
    if (value == null) return null;
    final text = value.toString().trim();
    return text.isEmpty ? null : text;
  }

  static List<String> _stringList(dynamic value) {
    if (value is! List) return const <String>[];
    return value
        .whereType<Object>()
        .map((item) => item.toString().trim())
        .where((item) => item.isNotEmpty)
        .toList(growable: false);
  }

  static bool _bool(dynamic value) {
    if (value is bool) return value;
    if (value is num) return value != 0;
    if (value is String) return value.toLowerCase() == 'true' || value == '1';
    return false;
  }

  static DateTime? _dateTime(dynamic value) {
    if (value == null) return null;
    if (value is DateTime) return value;
    final text = value.toString().trim();
    if (text.isEmpty) return null;
    return DateTime.tryParse(text);
  }
}
