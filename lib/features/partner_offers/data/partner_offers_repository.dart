import 'package:flutter/foundation.dart';

import '../../settings/settings_store.dart';
import '../api/partner_offers_api_client.dart';
import '../models/partner_offer.dart';

class PartnerOffersLoadResult {
  const PartnerOffersLoadResult({
    required this.offers,
    required this.totalCount,
    required this.baseUrl,
    this.categories = const <PartnerOfferCategoryFacet>[],
  });

  final List<PartnerOffer> offers;
  final int totalCount;
  final String baseUrl;
  final List<PartnerOfferCategoryFacet> categories;
}

class PartnerOffersRepository {
  PartnerOffersRepository._();

  static final PartnerOffersRepository instance = PartnerOffersRepository._();

  static const Duration _apiRequestTimeout = Duration(seconds: 12);

  Future<PartnerOffersLoadResult> loadOffers({
    String? query,
    String? category,
  }) async {
    Object? lastError;

    for (final baseUrl in _apiBaseUrlCandidates()) {
      try {
        final apiClient = PartnerOffersApiClient(
          baseUrl: Uri.parse(baseUrl),
          timeout: _apiRequestTimeout,
        );
        final page = await apiClient.getPartnerOffers(
          query: query,
          category: category,
          pageSize: 50,
        );
        var categories = const <PartnerOfferCategoryFacet>[];
        try {
          categories = await apiClient.getCategories(query: query);
        } catch (error) {
          debugPrint('DiscountHub partner offer categories API failed: $baseUrl -> $error');
        }
        if (categories.isEmpty) {
          categories = _fallbackCategories(page.offers);
        }
        return PartnerOffersLoadResult(
          offers: page.offers,
          totalCount: page.totalCount,
          baseUrl: baseUrl,
          categories: categories,
        );
      } catch (error) {
        lastError = error;
        debugPrint('DiscountHub partner offers API failed: $baseUrl -> $error');
      }
    }

    throw lastError ?? StateError('No partner offers API URL candidates are available.');
  }

  Uri clickUri({required String offerId, required String baseUrl}) {
    return PartnerOffersApiClient(
      baseUrl: Uri.parse(baseUrl),
      timeout: _apiRequestTimeout,
    ).clickUri(offerId);
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

  List<PartnerOfferCategoryFacet> _fallbackCategories(List<PartnerOffer> offers) {
    final counts = <String, int>{};
    final labels = <String, String>{};
    for (final offer in offers) {
      final id = offer.category.trim();
      if (id.isEmpty) continue;
      counts[id] = (counts[id] ?? 0) + 1;
      labels[id] = _categoryLabel(id);
    }
    return counts.entries
        .map((entry) => PartnerOfferCategoryFacet(
              id: entry.key,
              name: labels[entry.key] ?? entry.key,
              count: entry.value,
            ))
        .toList(growable: false);
  }

  String _categoryLabel(String id) {
    final normalized = id.toLowerCase().replaceAll('_', '-');
    switch (normalized) {
      case 'devtools':
      case 'dev-tools':
        return 'DevTools';
      case 'saas':
        return 'SaaS';
      case 'ai-tools':
        return 'AI Tools';
      case 'startup-tools':
        return 'Startup Tools';
      default:
        return id.replaceAll('_', ' ');
    }
  }
}
