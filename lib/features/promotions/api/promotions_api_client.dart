import 'dart:convert';

import 'package:http/http.dart' as http;

import 'promotion_api_response.dart';

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
    int page = 1,
    int pageSize = 50,
  }) async {
    final params = <String, String>{
      'page': page.toString(),
      'page_size': pageSize.toString(),
      'sort': 'featured',
      if (query != null && query.trim().isNotEmpty) 'q': query.trim(),
      if (type != null && type.trim().isNotEmpty) 'type': type.trim(),
    };

    final response = await _httpClient
        .get(_buildUri('/promotions', params))
        .timeout(timeout);
    final json = _decodeObject(response);
    return PromotionApiPage.fromJson(json);
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
