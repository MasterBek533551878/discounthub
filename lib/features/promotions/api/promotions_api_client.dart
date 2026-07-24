import 'dart:convert';

import 'package:http/http.dart' as http;

import 'promotion_api_response.dart';

class PromotionCountryFacet {
  const PromotionCountryFacet({required this.id, required this.name});
  final String id;
  final String name;
}

class PromotionsApiClient {
  PromotionsApiClient({
    required this.baseUrl,
    http.Client? httpClient,
    this.timeout = const Duration(seconds: 10),
  }) : _httpClient = httpClient ?? http.Client();

  final Uri baseUrl;
  final http.Client _httpClient;
  final Duration timeout;

  Future<PromotionApiPage> getPromotions({
    String? query,
    String? type,
    String? store,
    List<String> stores = const <String>[],
    String? country,
    int page = 1,
    int pageSize = 50,
  }) async {
    final params = <String, String>{
      'page': page.toString(),
      'page_size': pageSize.toString(),
      'sort': 'featured',
      if (query != null && query.trim().isNotEmpty) 'q': query.trim(),
      if (type != null && type.trim().isNotEmpty) 'type': type.trim(),
      if (country != null && country.trim().isNotEmpty)
        'country': country.trim().toUpperCase(),
      if (stores.isNotEmpty)
        'store': stores
            .map((value) => value.trim())
            .where((value) => value.isNotEmpty)
            .join(',')
      else if (store != null && store.trim().isNotEmpty)
        'store': store.trim(),
    };

    final response = await _httpClient
        .get(_buildUri('/promotions', params))
        .timeout(timeout);
    final json = _decodeObject(response);
    return PromotionApiPage.fromJson(json);
  }

  Future<List<String>> getPromotionStores({String? query, String? type}) async {
    final params = <String, String>{
      if (query != null && query.trim().isNotEmpty) 'q': query.trim(),
      if (type != null && type.trim().isNotEmpty) 'type': type.trim(),
    };

    final response = await _httpClient
        .get(_buildUri('/promotions/stores', params))
        .timeout(timeout);
    final json = _decodeObject(response);
    final items = json['items'];
    if (items is! List) return const <String>[];

    final stores = <String>[];
    for (final item in items) {
      final value = item is Map<String, dynamic>
          ? item['name'] ?? item['id']
          : item;
      final store = value?.toString().trim() ?? '';
      if (store.isEmpty) continue;
      final exists = stores.any(
        (existing) => existing.toLowerCase() == store.toLowerCase(),
      );
      if (!exists) stores.add(store);
    }
    return List.unmodifiable(stores);
  }

  Future<List<PromotionCountryFacet>> getPromotionCountries({
    String? query,
    String? type,
    String? store,
  }) async {
    final params = <String, String>{
      if (query != null && query.trim().isNotEmpty) 'q': query.trim(),
      if (type != null && type.trim().isNotEmpty) 'type': type.trim(),
      if (store != null && store.trim().isNotEmpty) 'store': store.trim(),
    };
    final response = await _httpClient
        .get(_buildUri('/promotions/countries', params))
        .timeout(timeout);
    final json = _decodeObject(response);
    final items = json['items'];
    if (items is! List) return const <PromotionCountryFacet>[];
    final countries = <PromotionCountryFacet>[];
    for (final raw in items) {
      if (raw is! Map) continue;
      final mapped = raw.map((key, value) => MapEntry(key.toString(), value));
      final id = (mapped['id'] ?? mapped['name'] ?? '')
          .toString()
          .trim()
          .toUpperCase();
      if (id.isEmpty) continue;
      final name = (mapped['name'] ?? id).toString().trim();
      if (countries.any((item) => item.id == id)) continue;
      countries.add(
        PromotionCountryFacet(id: id, name: name.isEmpty ? id : name),
      );
    }
    return List<PromotionCountryFacet>.unmodifiable(countries);
  }

  Uri clickUri(String promotionId) {
    return _buildUri('/promotions/${Uri.encodeComponent(promotionId)}/click');
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
      throw PromotionsApiException(
        statusCode: response.statusCode,
        message: response.body,
      );
    }

    final decoded = jsonDecode(response.body);
    if (decoded is Map<String, dynamic>) return decoded;

    throw const PromotionsApiException(
      statusCode: 0,
      message: 'Unexpected API response format.',
    );
  }
}

class PromotionsApiException implements Exception {
  const PromotionsApiException({
    required this.statusCode,
    required this.message,
  });

  final int statusCode;
  final String message;

  @override
  String toString() {
    return 'PromotionsApiException(statusCode: $statusCode, message: $message)';
  }
}
