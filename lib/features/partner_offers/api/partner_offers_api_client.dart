import 'dart:convert';

import 'package:http/http.dart' as http;

import 'partner_offer_api_response.dart';

class PartnerOffersApiClient {
  PartnerOffersApiClient({
    required this.baseUrl,
    http.Client? httpClient,
    this.timeout = const Duration(seconds: 10),
  }) : _httpClient = httpClient ?? http.Client();

  final Uri baseUrl;
  final http.Client _httpClient;
  final Duration timeout;

  Future<PartnerOfferApiPage> getPartnerOffers({
    String? query,
    String? category,
    int page = 1,
    int pageSize = 50,
  }) async {
    final params = <String, String>{
      'page': page.toString(),
      'page_size': pageSize.toString(),
      'sort': 'featured',
      if (query != null && query.trim().isNotEmpty) 'q': query.trim(),
      if (category != null && category.trim().isNotEmpty) 'category': category.trim(),
    };

    final response = await _httpClient
        .get(_buildUri('/partner-offers', params))
        .timeout(timeout);
    final json = _decodeObject(response);
    return PartnerOfferApiPage.fromJson(json);
  }

  Future<List<PartnerOfferCategoryFacet>> getCategories({String? query}) async {
    final params = <String, String>{
      if (query != null && query.trim().isNotEmpty) 'q': query.trim(),
    };

    final response = await _httpClient
        .get(_buildUri('/partner-offers/categories', params))
        .timeout(timeout);
    final json = _decodeObject(response);
    final items = json['items'];
    if (items is! List) return const <PartnerOfferCategoryFacet>[];

    final categories = <PartnerOfferCategoryFacet>[];
    for (final item in items.whereType<Map<String, dynamic>>()) {
      final id = item['id']?.toString().trim() ?? '';
      if (id.isEmpty) continue;
      final name = item['name']?.toString().trim() ?? id;
      final count = _int(item['count']);
      categories.add(PartnerOfferCategoryFacet(id: id, name: name, count: count));
    }
    return List.unmodifiable(categories);
  }

  Uri clickUri(String offerId) {
    return _buildUri('/partner-offers/${Uri.encodeComponent(offerId)}/click');
  }

  Uri _buildUri(String path, [Map<String, String>? queryParameters]) {
    final normalizedBasePath = baseUrl.path.endsWith('/')
        ? baseUrl.path.substring(0, baseUrl.path.length - 1)
        : baseUrl.path;

    final normalizedPath = path.startsWith('/') ? path : '/$path';

    return baseUrl.replace(
      path: '$normalizedBasePath$normalizedPath',
      queryParameters: queryParameters == null || queryParameters.isEmpty
          ? null
          : queryParameters,
    );
  }

  Map<String, dynamic> _decodeObject(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw PartnerOffersApiException(
        statusCode: response.statusCode,
        message: response.body,
      );
    }

    final decoded = jsonDecode(response.body);
    if (decoded is Map<String, dynamic>) return decoded;

    throw const PartnerOffersApiException(
      statusCode: 0,
      message: 'Unexpected API response format.',
    );
  }

  static int _int(dynamic value, {int fallback = 0}) {
    if (value is int) return value;
    if (value is double) return value.round();
    if (value is String) return int.tryParse(value) ?? fallback;
    return fallback;
  }
}

class PartnerOfferCategoryFacet {
  const PartnerOfferCategoryFacet({
    required this.id,
    required this.name,
    required this.count,
  });

  final String id;
  final String name;
  final int count;
}

class PartnerOffersApiException implements Exception {
  const PartnerOffersApiException({
    required this.statusCode,
    required this.message,
  });

  final int statusCode;
  final String message;

  @override
  String toString() {
    return 'PartnerOffersApiException(statusCode: $statusCode, message: $message)';
  }
}
