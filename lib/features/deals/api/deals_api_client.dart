import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/deal.dart';
import 'deal_api_dto.dart';
import 'deal_api_query.dart';
import 'deal_api_response.dart';

class DealsApiClient {
  DealsApiClient({
    required this.baseUrl,
    http.Client? httpClient,
    this.timeout = const Duration(seconds: 4),
  }) : _httpClient = httpClient ?? http.Client();

  final Uri baseUrl;
  final http.Client _httpClient;
  final Duration timeout;

  Future<DealApiPage> getDeals(DealApiQuery query) async {
    final uri = _buildUri('/deals', query.toQueryParameters());
    final response = await _httpClient.get(uri).timeout(timeout);
    final json = _decodeObject(response);

    return DealApiPage.fromJson(json);
  }

  Future<Deal> getDealById(String id) async {
    final safeId = Uri.encodeComponent(id);
    final uri = _buildUri('/deals/$safeId');
    final response = await _httpClient.get(uri).timeout(timeout);
    final json = _decodeObject(response);

    return DealApiDto.fromJson(json).toDomain();
  }

  Future<bool> health() async {
    try {
      final response = await _httpClient.get(_buildUri('/health')).timeout(timeout);
      return response.statusCode >= 200 && response.statusCode < 300;
    } catch (_) {
      return false;
    }
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
      throw DealsApiException(
        statusCode: response.statusCode,
        message: response.body,
      );
    }

    final decoded = jsonDecode(response.body);
    if (decoded is Map<String, dynamic>) return decoded;

    throw const DealsApiException(
      statusCode: 0,
      message: 'Unexpected API response format.',
    );
  }
}

class DealsApiException implements Exception {
  const DealsApiException({
    required this.statusCode,
    required this.message,
  });

  final int statusCode;
  final String message;

  @override
  String toString() {
    return 'DealsApiException(statusCode: $statusCode, message: $message)';
  }
}
