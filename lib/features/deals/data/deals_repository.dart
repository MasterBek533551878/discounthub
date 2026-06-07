import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../settings/app_strings.dart';
import '../../settings/settings_store.dart';
import '../api/deal_api_query.dart';
import '../api/deal_facets.dart';
import '../api/deals_api_client.dart';
import '../models/deal.dart';
import '../models/deal_filters.dart';
import '../models/deal_query.dart';
import '../models/deal_search_result.dart';
import 'api_deals_data_source.dart';
import 'deals_data_source.dart';
import 'fake_deals_data_source.dart';
import 'memory_deals_data_source.dart';

class DealsRepository {
  DealsRepository._();

  static final DealsRepository instance = DealsRepository._();

  static const String _cacheKey = 'discounthub_cached_api_discount_deals_v2';
  static const String _legacyCacheKey = 'discounthub_cached_api_deals_v1';
  static const Duration _autoRefreshInterval = Duration(minutes: 5);
  static const Duration _apiRequestTimeout = Duration(seconds: 20);
  static const Duration _facetsRefreshInterval = Duration(minutes: 2);
  static const int _initialApiPageSize = 36;

  final ValueNotifier<int> version = ValueNotifier<int>(0);
  final ValueNotifier<bool> isLoading = ValueNotifier<bool>(false);
  final ValueNotifier<String> statusMessage = ValueNotifier<String>('');

  DealsDataSource _dataSource = const MemoryDealsDataSource(<Deal>[]);
  DealFacets _facets = DealFacets.empty();
  DateTime? _facetsLoadedAt;
  final Map<String, Deal> _recentApiDealsById = <String, Deal>{};
  String _activeSourceLabel = 'API';
  Timer? _autoRefreshTimer;
  bool _refreshInProgress = false;

  String get activeSourceLabel => _activeSourceLabel;

  DealFacets get facets => _facets;

  int get totalAvailableCount {
    if (_facets.totalCount > 0) return _facets.totalCount;
    return _dataSource.getDeals().length;
  }

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

      _rememberApiDeals(apiDeals);
      _dataSource = MemoryDealsDataSource(apiDeals);
      if (!_facets.hasRemoteData) {
        _facets = DealFacets.fromDeals(apiDeals);
      }
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
        final apiClient = DealsApiClient(
          baseUrl: Uri.parse(baseUrl),
          timeout: _apiRequestTimeout,
        );
        final apiDataSource = ApiDealsDataSource(apiClient: apiClient);

        await apiDataSource.refresh(
          const DealApiQuery(
            currency: '',
            pageSize: _initialApiPageSize,
          ),
        );

        final deals = apiDataSource.getDeals();
        if (deals.where(_isRealApiDeal).isNotEmpty) {
          try {
            _facets = await apiClient.getFacets(
              const DealApiQuery(),
            );
            _facetsLoadedAt = DateTime.now();
          } catch (error) {
            debugPrint('DiscountHub facets failed: $baseUrl -> $error');
            // Do not turn the initial 36-item page into "global" facets.
            // The home page will retry /deals/facets during the live search.
            if (!_facets.hasRemoteData) {
              _facets = DealFacets.empty();
            }
          }
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
    // Ignore and remove the old cache because it may contain ordinary Awin
    // catalogue products that were imported during diagnostics with 0% discount.
    await prefs.remove(_legacyCacheKey);
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

      _rememberApiDeals(deals);
      _dataSource = MemoryDealsDataSource(deals);
      _facets = DealFacets.fromDeals(deals);
      _facetsLoadedAt = null;
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
    await prefs.remove(_legacyCacheKey);
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
        deal.currentPrice > 0 &&
        deal.discountPercent >= 1;
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
    _facets = DealFacets.fromDeals(_dataSource.getDeals());
    _facetsLoadedAt = null;
    _activeSourceLabel = 'Demo';
    statusMessage.value = message;
    isLoading.value = false;
    _bump();
  }

  Future<DealSearchResult> searchDealsFromApi(
    DealQuery query, {
    int page = 1,
    int pageSize = 60,
  }) async {
    if (!UserSettingsStore.useApiDataSource) {
      return searchDeals(query);
    }

    Object? lastError;
    final normalizedPage = page < 1 ? 1 : page;
    final normalizedPageSize = pageSize.clamp(1, 100).toInt();

    for (final baseUrl in _apiBaseUrlCandidates()) {
      try {
        final apiClient = DealsApiClient(
          baseUrl: Uri.parse(baseUrl),
          timeout: _apiRequestTimeout,
        );
        final apiPage = await apiClient.getDeals(
          DealApiQuery.fromDealQuery(
            query,
            currency: '',
          ).copyWith(
            page: normalizedPage,
            pageSize: normalizedPageSize,
          ),
        );

        final realDeals = apiPage.deals.where(_isRealApiDeal).toList(growable: false);
        _rememberApiDeals(realDeals);
        _activeSourceLabel = 'API';

        // Keep filters tied to the live backend catalogue, not to the
        // currently loaded page. This is important after large Awin imports:
        // the first page may contain 36 AliExpress products, while the full
        // catalogue still contains thousands of AliExpress and eBay deals.
        final shouldRefreshFacets = normalizedPage == 1 && _shouldRefreshFacets(
          minimumTotal: apiPage.totalCount,
        );
        if (shouldRefreshFacets) {
          final latestFacets = await _loadFacetsFromClient(apiClient);
          if (_shouldUseFacets(latestFacets, minimumTotal: apiPage.totalCount)) {
            _facets = latestFacets;
            _facetsLoadedAt = DateTime.now();
            _bump();
          }
        }

        final safeTotalCount = realDeals.isEmpty ? 0 : apiPage.totalCount;
        return DealSearchResult(
          deals: List<Deal>.unmodifiable(realDeals),
          totalCount: safeTotalCount,
        );
      } catch (error) {
        lastError = error;
        debugPrint('DiscountHub API search failed: $baseUrl -> $error');
      }
    }

    if (_dataSource.getDeals().where(_isRealApiDeal).isNotEmpty) {
      _activeSourceLabel = 'API cache';
      return searchDeals(query);
    }

    throw lastError ?? StateError('No API URL candidates are available.');
  }

  Future<DealFacets> _loadFacetsFromClient(DealsApiClient apiClient) async {
    try {
      final loadedFacets = await apiClient.getFacets(
        const DealApiQuery(),
      );
      if (loadedFacets.hasRemoteData) return loadedFacets;
    } catch (error) {
      debugPrint('DiscountHub facets refresh failed: $error');
    }

    // Do not synthesize facets from the first loaded page here. If the remote
    // /deals/facets request times out, using the current page would make the
    // filter sheet show misleading values such as "All · 36" and hide older
    // marketplaces like eBay from the filter list. Keep the previous facets and
    // let the next refresh try the backend again.
    return DealFacets.empty();
  }

  bool _shouldRefreshFacets({required int minimumTotal}) {
    if (!_facets.hasRemoteData) return true;
    if (minimumTotal > 0 && _facets.totalCount < minimumTotal) return true;

    final loadedAt = _facetsLoadedAt;
    if (loadedAt == null) return false;

    return DateTime.now().difference(loadedAt) > _facetsRefreshInterval;
  }

  bool _shouldUseFacets(DealFacets facets, {required int minimumTotal}) {
    if (!facets.hasRemoteData) return false;
    if (minimumTotal <= 0) return true;

    // The backend total from /deals is authoritative for the current catalogue.
    // Reject tiny page-derived facets when the catalogue is clearly larger.
    return facets.totalCount >= minimumTotal;
  }

  List<Deal> getAllDeals() {
    return _sorted(_dataSource.getDeals(), DealSort.discountHighToLow);
  }

  Deal? findById(String? id) {
    if (id == null) return null;

    final recentDeal = _recentApiDealsById[id];
    if (recentDeal != null) return recentDeal;

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
        filters: DealFilters(categorySelections: <String>[category]),
      ),
    ).deals;
  }

  List<Deal> getFavoriteDeals(Set<String> ids) {
    final deals = _dataSource.getDeals().where((deal) => ids.contains(deal.id)).toList();
    return List<Deal>.unmodifiable(deals);
  }


  int estimateTotalForQuery(DealQuery query, {required int fallback}) {
    if (!_facets.hasRemoteData) return fallback;

    final filters = query.filters;
    final hasSearch = query.searchText.trim().isNotEmpty;
    if (hasSearch) return fallback;

    final hasRangeOrQualityFilters = filters.minDiscount > 0 ||
        filters.maxPrice != null;
    if (hasRangeOrQualityFilters) return fallback;

    final selectedDimensions = <int>[
      if (filters.selectedPlatforms.isNotEmpty)
        filters.selectedPlatforms
            .map(_facets.countForMarketplace)
            .fold<int>(0, (total, count) => total + count),
      if (filters.selectedCategories.isNotEmpty)
        filters.selectedCategories
            .map(_facets.countForCategory)
            .fold<int>(0, (total, count) => total + count),
    ].where((count) => count > 0).toList(growable: false);

    if (selectedDimensions.isEmpty) {
      return _facets.totalCount > fallback ? _facets.totalCount : fallback;
    }

    final conservativeEstimate = selectedDimensions.reduce(
      (value, element) => value < element ? value : element,
    );
    return conservativeEstimate > fallback ? conservativeEstimate : fallback;
  }

  List<String> getPlatforms({bool includeAll = false}) {
    final facetValues = _facets.marketplaces.map((item) => item.id).toList();
    if (facetValues.isNotEmpty) {
      return includeAll ? ['All', ...facetValues] : facetValues;
    }

    final values = _dataSource.getDeals().map((deal) => deal.platform).toSet().toList();
    values.sort();
    return includeAll ? ['All', ...values] : values;
  }

  List<String> getCategories({bool includeAll = false}) {
    final facetValues = _facets.categories.map((item) => item.id).toList();
    if (facetValues.isNotEmpty) {
      return includeAll ? ['All', ...facetValues] : facetValues;
    }

    final values = _dataSource.getDeals().map((deal) => deal.category).toSet().toList();
    values.sort();
    return includeAll ? ['All', ...values] : values;
  }

  List<String> getShippingCountries({bool includeAll = false}) {
    final facetValues = _facets.countries.map((item) => item.id).toList();
    if (facetValues.isNotEmpty) {
      return includeAll ? ['All', ...facetValues] : facetValues;
    }

    final values = _dataSource
        .getDeals()
        .expand((deal) => deal.shipsTo)
        .toSet()
        .toList();
    values.sort();
    return includeAll ? ['All', ...values] : values;
  }


  List<String> getDeliveryRegions({bool includeAll = false}) {
    final facetValues = _facets.deliveryRegions.map((item) => item.id).toList();
    final ordered = <String>[
      for (final value in const <String>['global', 'cis', 'europe', 'usa', 'latam'])
        if (facetValues.contains(value)) value,
    ];

    if (ordered.isNotEmpty) {
      return includeAll ? ['All', ...ordered] : ordered;
    }

    final values = _dataSource
        .getDeals()
        .expand((deal) => deal.deliveryRegions)
        .toSet()
        .toList();
    values.sort();
    if (values.isEmpty) {
      const defaults = <String>['global', 'cis', 'europe', 'usa', 'latam'];
      return includeAll ? ['All', ...defaults] : defaults;
    }
    return includeAll ? ['All', ...values] : values;
  }

  List<String> getMonetizationModes({bool includeAll = false}) {
    final facetValues = _facets.monetizationModes.map((item) => item.id).toList();
    if (facetValues.isNotEmpty) {
      return includeAll ? ['All', ...facetValues] : facetValues;
    }

    final values = _dataSource.getDeals().map((deal) => deal.monetizationMode).toSet().toList();
    values.sort();
    return includeAll ? ['All', ...values] : values;
  }

  int countByCategory(String category) {
    final facetCount = _facets.countForCategory(category);
    if (facetCount > 0) return facetCount;
    return _dataSource.getDeals().where((deal) => deal.category == category).length;
  }

  int countByPlatform(String platform) {
    final facetCount = _facets.countForMarketplace(platform);
    if (facetCount > 0) return facetCount;
    return _dataSource
        .getDeals()
        .where((deal) => _publicMarketplaceLabel(deal.platform) == _publicMarketplaceLabel(platform))
        .length;
  }

  int countByMonetizationMode(String mode) {
    final facetCount = _facets.countForMonetizationMode(mode);
    if (facetCount > 0) return facetCount;
    return _dataSource.getDeals().where((deal) => deal.monetizationMode == mode).length;
  }

  double get maxAvailablePrice {
    if (_facets.priceRange.max > 0) return _facets.priceRange.max.ceilToDouble();

    final deals = _dataSource.getDeals();
    if (deals.isEmpty) return 1;

    final maxPrice = deals
        .map((deal) => deal.currentPrice)
        .reduce((value, element) => value > element ? value : element);

    return maxPrice.ceilToDouble();
  }


  String _publicMarketplaceLabel(String value) {
    final normalized = value.trim().toLowerCase();
    if (normalized.startsWith('ebay')) return 'eBay';
    if (normalized.startsWith('aliexpress')) return 'AliExpress';
    if (normalized.startsWith('alibaba')) return 'Alibaba';
    if (normalized.startsWith('amazon')) return 'Amazon';
    return value.trim();
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
        deal.shipsTo.any((country) => country.toLowerCase().contains(query)) ||
        deal.deliveryRegions.any((region) => region.toLowerCase().contains(query));
  }

  bool _matchesFilters(Deal deal, DealFilters filters) {
    if (!deal.hasRealDiscount) return false;

    final selectedPlatforms = filters.selectedPlatforms
        .map(_publicMarketplaceLabel)
        .toSet();
    final selectedCategories = filters.selectedCategories.toSet();

    final matchesPlatform = selectedPlatforms.isEmpty ||
        selectedPlatforms.contains(_publicMarketplaceLabel(deal.platform));
    final matchesCategory = selectedCategories.isEmpty ||
        selectedCategories.contains(deal.category);
    final matchesDiscount = deal.discountPercent >= filters.minDiscount;
    final matchesPrice = filters.maxPrice == null || deal.currentPrice <= filters.maxPrice!;

    return matchesPlatform &&
        matchesCategory &&
        matchesDiscount &&
        matchesPrice;
  }

  List<Deal> _sorted(List<Deal> deals, DealSort sort) {
    final sorted = [...deals];

    switch (sort) {
      case DealSort.bestMatch:
        sorted.sort((a, b) => b.dealScore.compareTo(a.dealScore));
        break;
      case DealSort.discountHighToLow:
        sorted.sort((a, b) => b.discountPercent.compareTo(a.discountPercent));
        break;
      case DealSort.newest:
        sorted.sort((a, b) {
          final aUpdated = a.updatedAt ?? DateTime.fromMillisecondsSinceEpoch(0);
          final bUpdated = b.updatedAt ?? DateTime.fromMillisecondsSinceEpoch(0);
          return bUpdated.compareTo(aUpdated);
        });
        break;
      case DealSort.priceLowToHigh:
        sorted.sort((a, b) => a.currentPrice.compareTo(b.currentPrice));
        break;
      case DealSort.priceHighToLow:
        sorted.sort((a, b) => b.currentPrice.compareTo(a.currentPrice));
        break;
      case DealSort.ratingHighToLow:
        sorted.sort((a, b) => b.rating.compareTo(a.rating));
        break;
    }

    return sorted;
  }

  void _rememberApiDeals(List<Deal> deals) {
    for (final deal in deals.where(_isRealApiDeal)) {
      _recentApiDealsById[deal.id] = deal;
    }

    // Keep memory bounded while preserving the latest visible/server-loaded
    // deals for details navigation. Favorites still use the saved local ids.
    const maxRememberedDeals = 500;
    if (_recentApiDealsById.length <= maxRememberedDeals) return;

    final overflow = _recentApiDealsById.length - maxRememberedDeals;
    final keysToRemove = _recentApiDealsById.keys.take(overflow).toList();
    for (final key in keysToRemove) {
      _recentApiDealsById.remove(key);
    }
  }

  void _bump() {
    version.value = version.value + 1;
  }
}
