import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../settings/app_strings.dart';
import '../../settings/settings_store.dart';
import '../api/deal_api_query.dart';
import '../api/deals_api_client.dart';
import '../models/deal.dart';
import '../models/deal_filters.dart';
import '../models/deal_query.dart';
import '../models/deal_search_result.dart';
import '../utils/deal_insights.dart';
import 'api_deals_data_source.dart';
import 'deals_data_source.dart';
import 'fake_deals_data_source.dart';
import 'memory_deals_data_source.dart';

class DealsRepository {
  DealsRepository._();

  static final DealsRepository instance = DealsRepository._();

  static const String _cacheKey = 'discounthub_cached_api_deals_v1';
  static const Duration _autoRefreshInterval = Duration(minutes: 1);

  final ValueNotifier<int> version = ValueNotifier<int>(0);
  final ValueNotifier<bool> isLoading = ValueNotifier<bool>(false);
  final ValueNotifier<String> statusMessage = ValueNotifier<String>('');

  DealsDataSource _dataSource = const MemoryDealsDataSource(<Deal>[]);
  String _activeSourceLabel = 'API';
  Timer? _autoRefreshTimer;
  bool _refreshInProgress = false;

  String get activeSourceLabel => _activeSourceLabel;

  bool get isApiActive => _activeSourceLabel.startsWith('API');

  Future<void> init() async {
    await _loadCachedApiDeals(notify: false);
    _startAutoRefresh();
    await configureFromSettings();
  }

  Future<void> configureFromSettings() async {
    if (!UserSettingsStore.useApiDataSource) {
      await _loadCachedApiDeals();
      if (_dataSource.getDeals().isEmpty) {
        _useDemo(AppStrings.dataSourceDemoReady);
      }
      return;
    }

    await _loadApiData();
  }

  Future<void> refresh() async {
    if (UserSettingsStore.useApiDataSource) {
      await _loadApiData();
      return;
    }

    await _loadCachedApiDeals();
    if (_dataSource.getDeals().isEmpty) {
      _useDemo(AppStrings.dataSourceDemoReady);
    }
  }

  Future<void> _loadApiData({bool silent = false}) async {
    if (_refreshInProgress) return;
    _refreshInProgress = true;

    if (!silent) {
      isLoading.value = true;
      _bump();
    }

    try {
      final apiDataSource = await _loadFromFirstAvailableApi();
      final apiDeals = apiDataSource.getDeals().where(_isRealApiDeal).toList();

      if (apiDeals.isEmpty) {
        throw StateError('API returned an empty real deal list.');
      }

      _dataSource = MemoryDealsDataSource(apiDeals);
      _activeSourceLabel = 'API';
      statusMessage.value = AppStrings.dataSourceApiConnected(apiDeals.length);
      await _saveCachedApiDeals(apiDeals);
    } catch (error) {
      // Never replace real products with an empty/demo list just because local
      // backend, adb reverse or Wi-Fi is temporarily unavailable.
      if (_dataSource.getDeals().where(_isRealApiDeal).isNotEmpty) {
        _activeSourceLabel = 'API cache';
        statusMessage.value = AppStrings.select(
          en: 'Showing saved deals. Connect backend to refresh.',
          ru: 'Показываем сохранённые товары. Подключите backend для обновления.',
          uz: 'Saqlangan takliflar ko‘rsatilmoqda. Yangilash uchun backendni ulang.',
        );
        return;
      }

      final loadedCache = await _loadCachedApiDeals(notify: false);
      if (loadedCache) {
        _activeSourceLabel = 'API cache';
        statusMessage.value = AppStrings.select(
          en: 'Showing saved deals. Connect backend to refresh.',
          ru: 'Показываем сохранённые товары. Подключите backend для обновления.',
          uz: 'Saqlangan takliflar ko‘rsatilmoqda. Yangilash uchun backendni ulang.',
        );
        return;
      }

      _dataSource = const MemoryDealsDataSource(<Deal>[]);
      _activeSourceLabel = 'API unavailable';
      statusMessage.value = AppStrings.select(
        en: 'Backend is unavailable. Check your internet connection or server status.',
        ru: 'Backend недоступен. Проверьте интернет или состояние сервера.',
        uz: 'Backend mavjud emas. Internet ulanishi yoki server holatini tekshiring.',
      );
    } finally {
      _refreshInProgress = false;
      if (!silent) {
        isLoading.value = false;
      }
      _bump();
    }
  }

  Future<ApiDealsDataSource> _loadFromFirstAvailableApi() async {
    Object? lastError;

    for (final baseUrl in _apiBaseUrlCandidates()) {
      try {
        final apiDataSource = ApiDealsDataSource(
          apiClient: DealsApiClient(
            baseUrl: Uri.parse(baseUrl),
            timeout: const Duration(seconds: 4),
          ),
        );

        await apiDataSource.refresh(
          const DealApiQuery(
            currency: 'USD',
            pageSize: 100,
          ),
        );

        final deals = apiDataSource.getDeals();
        if (deals.where(_isRealApiDeal).isNotEmpty) {
          return apiDataSource;
        }

        lastError = StateError('API $baseUrl returned no real deals.');
      } catch (error) {
        lastError = error;
        debugPrint('DiscountHub API failed: $baseUrl -> $error');
      }
    }

    throw lastError ?? StateError('No API URL candidates are available.');
  }

  List<String> _apiBaseUrlCandidates() {
    final values = <String>[
      // The saved/default URL comes first. Production builds can still override
      // it with --dart-define=DISCOUNTHUB_API_BASE_URL=...
      UserSettingsStore.apiBaseUrl.value.trim(),
      // Always keep production as a fallback so products do not disappear.
      UserSettingsStore.productionApiBaseUrl,
    ];

    final unique = <String>[];
    for (final value in values) {
      final normalized = value.trim();
      if (normalized.isEmpty) continue;
      if (unique.contains(normalized)) continue;
      unique.add(normalized);
    }

    return unique;
  }

  Future<bool> _loadCachedApiDeals({bool notify = true}) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_cacheKey);
    if (raw == null || raw.trim().isEmpty) return false;

    try {
      final decoded = jsonDecode(raw);
      if (decoded is! List) return false;

      final deals = decoded
          .whereType<Map<String, dynamic>>()
          .map(Deal.fromJson)
          .where(_isRealApiDeal)
          .toList(growable: false);

      if (deals.isEmpty) return false;

      _dataSource = MemoryDealsDataSource(deals);
      _activeSourceLabel = 'API cache';
      statusMessage.value = AppStrings.select(
        en: 'Showing saved deals. Connect backend to refresh.',
        ru: 'Показываем сохранённые товары. Подключите backend для обновления.',
        uz: 'Saqlangan takliflar ko‘rsatilmoqda. Yangilash uchun backendni ulang.',
      );
      if (notify) _bump();
      return true;
    } catch (error) {
      debugPrint('DiscountHub cache failed: $error');
      return false;
    }
  }

  Future<void> _saveCachedApiDeals(List<Deal> deals) async {
    final realDeals = deals.where(_isRealApiDeal).toList(growable: false);
    if (realDeals.isEmpty) return;

    final prefs = await SharedPreferences.getInstance();
    final raw = jsonEncode(realDeals.map((deal) => deal.toJson()).toList());
    await prefs.setString(_cacheKey, raw);
  }

  bool _isRealApiDeal(Deal deal) {
    final id = deal.id.toLowerCase();
    final platform = deal.platform.toLowerCase();
    final url = deal.productUrl.toLowerCase();

    if (id.startsWith('deal_')) return false;
    if (id.startsWith('feed_demo_')) return false;
    if (platform == 'feedshop') return false;
    if (url.contains('example.com')) return false;

    return deal.id.trim().isNotEmpty &&
        deal.title.trim().isNotEmpty &&
        deal.imageUrl.trim().isNotEmpty &&
        deal.currentPrice > 0;
  }

  void _startAutoRefresh() {
    _autoRefreshTimer ??= Timer.periodic(_autoRefreshInterval, (_) {
      if (UserSettingsStore.useApiDataSource) {
        _loadApiData(silent: true);
      }
    });
  }

  void _useDemo(String message) {
    _dataSource = const FakeDealsDataSource();
    _activeSourceLabel = 'Demo';
    statusMessage.value = message;
    isLoading.value = false;
    _bump();
  }

  List<Deal> getAllDeals() {
    return _sorted(_dataSource.getDeals(), DealSort.discountHighToLow);
  }

  Deal? findById(String? id) {
    if (id == null) return null;

    for (final deal in _dataSource.getDeals()) {
      if (deal.id == id) return deal;
    }

    return null;
  }

  DealSearchResult searchDeals(DealQuery query) {
    final allDeals = _dataSource.getDeals();
    var deals = allDeals.where((deal) {
      return _matchesSearch(deal, query.searchText) &&
          _matchesFilters(deal, query.filters);
    }).toList();

    deals = _sorted(deals, query.sort);

    return DealSearchResult(
      deals: List<Deal>.unmodifiable(deals),
      totalCount: allDeals.length,
    );
  }

  List<Deal> getDealsByCategory(String category) {
    return searchDeals(
      DealQuery(
        filters: DealFilters(category: category),
      ),
    ).deals;
  }

  List<Deal> getFavoriteDeals(Set<String> ids) {
    final deals = _dataSource.getDeals().where((deal) => ids.contains(deal.id)).toList();
    return List<Deal>.unmodifiable(deals);
  }

  List<String> getPlatforms({bool includeAll = false}) {
    final values = _dataSource.getDeals().map((deal) => deal.platform).toSet().toList();
    values.sort();
    return includeAll ? ['All', ...values] : values;
  }

  List<String> getCategories({bool includeAll = false}) {
    final values = _dataSource.getDeals().map((deal) => deal.category).toSet().toList();
    values.sort();
    return includeAll ? ['All', ...values] : values;
  }

  List<String> getShippingCountries({bool includeAll = false}) {
    final values = _dataSource
        .getDeals()
        .expand((deal) => deal.shipsTo)
        .toSet()
        .toList();
    values.sort();
    return includeAll ? ['All', ...values] : values;
  }

  int countByCategory(String category) {
    return _dataSource.getDeals().where((deal) => deal.category == category).length;
  }

  double get maxAvailablePrice {
    final deals = _dataSource.getDeals();
    if (deals.isEmpty) return 1;

    final maxPrice = deals
        .map((deal) => deal.currentPrice)
        .reduce((value, element) => value > element ? value : element);

    return maxPrice.ceilToDouble();
  }

  bool _matchesSearch(Deal deal, String searchText) {
    final query = searchText.trim().toLowerCase();
    if (query.isEmpty) return true;

    final localizedTitle = AppStrings.demoDealTitle(deal.id, deal.title).toLowerCase();
    final localizedDescription = AppStrings.demoDealDescription(
      deal.id,
      deal.description,
    ).toLowerCase();
    final localizedCategory = AppStrings.categoryName(deal.category).toLowerCase();

    return localizedTitle.contains(query) ||
        localizedDescription.contains(query) ||
        localizedCategory.contains(query) ||
        deal.title.toLowerCase().contains(query) ||
        deal.description.toLowerCase().contains(query) ||
        deal.platform.toLowerCase().contains(query) ||
        deal.category.toLowerCase().contains(query) ||
        deal.shipsTo.any((country) => country.toLowerCase().contains(query));
  }

  bool _matchesFilters(Deal deal, DealFilters filters) {
    final matchesPlatform = filters.platform == 'All' || deal.platform == filters.platform;
    final matchesCategory = filters.category == 'All' || deal.category == filters.category;
    final matchesCountry = filters.shipToCountry == 'All' || deal.shipsTo.contains(filters.shipToCountry);
    final matchesDiscount = deal.discountPercent >= filters.minDiscount;
    final matchesPrice = filters.maxPrice == null || deal.currentPrice <= filters.maxPrice!;
    final matchesRating = deal.rating >= filters.minRating;
    final matchesFreeShipping = !filters.freeShippingOnly || DealInsights.hasFreeShippingToSelectedCountry(deal);
    final matchesVerified = !filters.verifiedOnly || deal.verified;

    return matchesPlatform &&
        matchesCategory &&
        matchesCountry &&
        matchesDiscount &&
        matchesPrice &&
        matchesRating &&
        matchesFreeShipping &&
        matchesVerified;
  }

  List<Deal> _sorted(List<Deal> deals, DealSort sort) {
    final sorted = [...deals];

    switch (sort) {
      case DealSort.discountHighToLow:
        sorted.sort((a, b) => b.discountPercent.compareTo(a.discountPercent));
        break;
      case DealSort.priceLowToHigh:
        sorted.sort((a, b) => a.currentPrice.compareTo(b.currentPrice));
        break;
      case DealSort.ratingHighToLow:
        sorted.sort((a, b) => b.rating.compareTo(a.rating));
        break;
    }

    return sorted;
  }

  void _bump() {
    version.value = version.value + 1;
  }
}
