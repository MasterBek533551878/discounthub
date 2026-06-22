import 'package:flutter/foundation.dart';

import '../../settings/settings_store.dart';
import '../api/promotions_api_client.dart';
import '../models/promotion.dart';

class PromotionsLoadResult {
  const PromotionsLoadResult({
    required this.promotions,
    required this.totalCount,
    required this.baseUrl,
    this.stores = const <String>[],
  });

  final List<Promotion> promotions;
  final int totalCount;
  final String baseUrl;
  final List<String> stores;
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
        var storeNames = const <String>[];
        try {
          storeNames = await apiClient.getPromotionStores(
            query: query,
            type: type,
          );
        } catch (error) {
          // Older backends may not expose /promotions/stores yet. Keep the page
          // usable and fall back to stores from the loaded promotion cards.
          debugPrint('DiscountHub promotion stores API failed: $baseUrl -> $error');
        }
        if (storeNames.isEmpty) {
          final fallbackStores = <String>[];
          for (final promotion in page.promotions) {
            final promotionStore = promotion.store.trim();
            if (promotionStore.isEmpty) continue;
            final exists = fallbackStores.any(
              (value) => value.toLowerCase() == promotionStore.toLowerCase(),
            );
            if (!exists) fallbackStores.add(promotionStore);
          }
          storeNames = List.unmodifiable(fallbackStores);
        }
        return PromotionsLoadResult(
          promotions: page.promotions,
          totalCount: page.totalCount,
          baseUrl: baseUrl,
          stores: storeNames,
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
