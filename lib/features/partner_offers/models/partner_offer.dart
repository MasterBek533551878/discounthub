class PartnerOffer {
  const PartnerOffer({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.description,
    required this.partnerName,
    required this.category,
    required this.tags,
    required this.offerText,
    required this.originalPriceText,
    required this.currentPriceText,
    required this.landingUrl,
    required this.countries,
    required this.monetizationMode,
    required this.featured,
    required this.verified,
    required this.updatedAt,
    this.code,
    this.checkoutUrl,
    this.imageUrl,
    this.logoUrl,
    this.validFrom,
    this.validUntil,
  });

  final String id;
  final String title;
  final String subtitle;
  final String description;
  final String partnerName;
  final String category;
  final List<String> tags;
  final String offerText;
  final String originalPriceText;
  final String currentPriceText;
  final String? code;
  final String landingUrl;
  final String? checkoutUrl;
  final String? imageUrl;
  final String? logoUrl;
  final String countries;
  final String monetizationMode;
  final DateTime? validFrom;
  final DateTime? validUntil;
  final bool featured;
  final bool verified;
  final DateTime updatedAt;

  bool get hasCode => code != null && code!.trim().isNotEmpty;

  bool get hasVisual => imageUrl != null && imageUrl!.trim().isNotEmpty;

  bool get hasDeadline => validUntil != null;

  factory PartnerOffer.fromJson(Map<String, dynamic> json) {
    return PartnerOffer(
      id: _string(json['id']),
      title: _string(json['title']),
      subtitle: _string(json['subtitle']),
      description: _string(json['description']),
      partnerName: _string(json['partnerName'] ?? json['partner_name']),
      category: _string(json['category'], fallback: 'other'),
      tags: _stringList(json['tags']),
      offerText: _string(json['offerText'] ?? json['offer_text']),
      originalPriceText: _string(json['originalPriceText'] ?? json['original_price_text']),
      currentPriceText: _string(json['currentPriceText'] ?? json['current_price_text']),
      code: _nullableString(json['code']),
      landingUrl: _string(json['landingUrl'] ?? json['landing_url']),
      checkoutUrl: _nullableString(json['checkoutUrl'] ?? json['checkout_url']),
      imageUrl: _nullableString(json['imageUrl'] ?? json['image_url']),
      logoUrl: _nullableString(json['logoUrl'] ?? json['logo_url']),
      countries: _string(json['countries'], fallback: 'Global'),
      monetizationMode: _string(
        json['monetizationMode'] ?? json['monetization_mode'],
        fallback: 'direct',
      ),
      validFrom: _dateTime(json['validFrom'] ?? json['valid_from']),
      validUntil: _dateTime(json['validUntil'] ?? json['valid_until']),
      featured: _bool(json['featured']),
      verified: _bool(json['verified']),
      updatedAt: _dateTime(json['updatedAt'] ?? json['updated_at']) ?? DateTime.now(),
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
    final result = <String>[];
    for (final item in value) {
      final text = item?.toString().trim() ?? '';
      if (text.isEmpty) continue;
      final exists = result.any((existing) => existing.toLowerCase() == text.toLowerCase());
      if (!exists) result.add(text);
    }
    return List.unmodifiable(result);
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
