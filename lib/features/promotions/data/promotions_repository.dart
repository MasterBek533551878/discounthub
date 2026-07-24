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
    this.countries = const <PromotionCountryFacet>[],
  });

  final List<Promotion> promotions;
  final int totalCount;
  final String baseUrl;
  final List<String> stores;
  final List<PromotionCountryFacet> countries;
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
    String? country,
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
          country: country,
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
          debugPrint(
            'DiscountHub promotion stores API failed: $baseUrl -> $error',
          );
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
        var countryOptions = const <PromotionCountryFacet>[];
        try {
          countryOptions = await apiClient.getPromotionCountries(
            query: query,
            type: type,
            store: stores.length == 1 ? stores.first : store,
          );
        } catch (error) {
          debugPrint(
            'DiscountHub promotion countries API failed: $baseUrl -> $error',
          );
        }
        if (countryOptions.isEmpty) {
          countryOptions = _fallbackCountryOptions(page.promotions);
        }
        return PromotionsLoadResult(
          promotions: page.promotions,
          totalCount: page.totalCount,
          baseUrl: baseUrl,
          stores: storeNames,
          countries: countryOptions,
        );
      } catch (error) {
        lastError = error;
        debugPrint('DiscountHub promotions API failed: $baseUrl -> $error');
      }
    }

    throw lastError ??
        StateError('No promotions API URL candidates are available.');
  }

  List<PromotionCountryFacet> _fallbackCountryOptions(
    List<Promotion> promotions,
  ) {
    final codes = <String>[];
    for (final promotion in promotions) {
      for (final raw in promotion.availabilityCountries) {
        final code = raw.trim().toUpperCase();
        if (code.isEmpty || codes.contains(code)) continue;
        codes.add(code);
      }
    }
    codes.sort();
    return List<PromotionCountryFacet>.unmodifiable(
      codes.map(
        (code) => PromotionCountryFacet(id: code, name: _countryName(code)),
      ),
    );
  }

  String _countryName(String code) {
    const names = <String, String>{
      'US': 'United States',
      'GB': 'United Kingdom',
      'FR': 'France',
      'DE': 'Germany',
      'ES': 'Spain',
      'IT': 'Italy',
      'PL': 'Poland',
      'AU': 'Australia',
      'CA': 'Canada',
      'BR': 'Brazil',
      'MX': 'Mexico',
      'UZ': 'Uzbekistan',
    };
    return names[code] ?? code;
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
