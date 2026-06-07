import 'package:flutter/foundation.dart';

import '../../settings/settings_store.dart';
import '../api/promotions_api_client.dart';
import '../models/promotion.dart';

class PromotionsLoadResult {
  const PromotionsLoadResult({
    required this.promotions,
    required this.totalCount,
    required this.baseUrl,
  });

  final List<Promotion> promotions;
  final int totalCount;
  final String baseUrl;
}

class PromotionsRepository {
  PromotionsRepository._();

  static final PromotionsRepository instance = PromotionsRepository._();

  static const Duration _apiRequestTimeout = Duration(seconds: 12);

  Future<PromotionsLoadResult> loadPromotions({
    String? query,
    String? type,
    String? store,
    List<String> stores = const <String>[],
  }) async {
    Object? lastError;

    for (final baseUrl in _apiBaseUrlCandidates()) {
      try {
        final apiClient = PromotionsApiClient(
          baseUrl: Uri.parse(baseUrl),
          timeout: _apiRequestTimeout,
        );
        final page = await apiClient.getPromotions(
          query: query,
          type: type,
          store: store,
          stores: stores,
          pageSize: 50,
        );
        return PromotionsLoadResult(
          promotions: page.promotions,
          totalCount: page.totalCount,
          baseUrl: baseUrl,
        );
      } catch (error) {
        lastError = error;
        debugPrint('DiscountHub promotions API failed: $baseUrl -> $error');
      }
    }

    throw lastError ?? StateError('No promotions API URL candidates are available.');
  }

  Uri clickUri({required String promotionId, required String baseUrl}) {
    return PromotionsApiClient(
      baseUrl: Uri.parse(baseUrl),
      timeout: _apiRequestTimeout,
    ).clickUri(promotionId);
  }

  List<String> _apiBaseUrlCandidates() {
    final values = <String>[
      UserSettingsStore.apiBaseUrl.value.trim(),
      UserSettingsStore.productionApiBaseUrl,
    ];

    final unique = <String>[];
    for (final value in values) {
      if (value.isEmpty) continue;
      if (unique.contains(value)) continue;
      unique.add(value);
    }
    return unique;
  }
}
