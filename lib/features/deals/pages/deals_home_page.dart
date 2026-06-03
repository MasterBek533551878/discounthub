import 'dart:async';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../app/app_theme.dart';
import '../../../shared/widgets/discount_hub_logo.dart';
import '../../settings/app_strings.dart';
import '../data/deals_repository.dart';
import '../models/deal.dart';
import '../models/deal_filters.dart';
import '../models/deal_query.dart';
import '../widgets/deal_card.dart';
import '../widgets/deal_filter_sheet.dart';

class DealsHomePage extends StatefulWidget {
  const DealsHomePage({super.key});

  @override
  State<DealsHomePage> createState() => _DealsHomePageState();
}

class _DealsHomePageState extends State<DealsHomePage> {
  // Keep the first request small so the home page becomes interactive fast.
  // More deals are loaded lazily as the user scrolls.
  static const int _serverPageSize = 36;

  final DealsRepository _repository = DealsRepository.instance;
  final TextEditingController _searchController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  DealFilters _filters = const DealFilters();
  String _searchText = '';
  Timer? _searchDebounce;

  List<Deal> _visibleDeals = const <Deal>[];
  int _visibleTotalCount = 0;
  int _serverPage = 1;
  bool _serverSearchStarted = false;
  bool _isServerLoading = false;
  bool _isLoadingMore = false;
  bool _hasMoreServerDeals = true;
  String? _serverError;
  int _requestSerial = 0;

  List<String> get _platforms => _repository.getPlatforms(includeAll: true);
  List<String> get _categories => _repository.getCategories(includeAll: true);
  List<String> get _countries => _repository.getShippingCountries(includeAll: true);
  List<String> get _monetizationModes => _repository.getMonetizationModes(includeAll: true);

  List<String> get _quickCategories {
    return _categories.where((item) => item != 'All').take(5).toList();
  }

  DealQuery get _currentQuery {
    return DealQuery(
      searchText: _searchText,
      filters: _filters,
      sort: DealSort.discountHighToLow,
    );
  }

  List<Deal> get _localFilteredDeals {
    return _repository.searchDeals(_currentQuery).deals;
  }

  List<Deal> get _featuredDeals {
    return _repository
        .searchDeals(
          const DealQuery(
            searchText: '',
            filters: DealFilters(),
            sort: DealSort.discountHighToLow,
          ),
        )
        .deals;
  }

  @override
  void initState() {
    super.initState();
    _repository.version.addListener(_handleRepositoryChanged);
    _scrollController.addListener(_handleScroll);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadServerDeals();
    });
  }

  @override
  void dispose() {
    _repository.version.removeListener(_handleRepositoryChanged);
    _scrollController.removeListener(_handleScroll);
    _searchDebounce?.cancel();
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _handleRepositoryChanged() {
    if (!mounted) return;

    // Repository version changes are usually caused by cache/facet refreshes.
    // Do not restart the live list request from here: the home page already
    // owns pagination and a restart can turn the UI back into a cached first
    // page of 80 items while a server request is still in flight.
    setState(() {});
  }

  void _handleScroll() {
    if (!_scrollController.hasClients) return;
    if (_isServerLoading || _isLoadingMore || !_hasMoreServerDeals) return;

    final position = _scrollController.position;
    final shouldLoadMore = position.pixels >= position.maxScrollExtent - 700;
    if (shouldLoadMore) {
      _loadServerDeals(silent: true, reset: false);
    }
  }

  Future<void> _openAdvancedFilters() async {
    final result = await showModalBottomSheet<DealFilters>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.background,
      builder: (context) {
        return DealFilterSheet(
          initialFilters: _filters,
          platforms: _platforms,
          categories: _categories,
          countries: _countries,
          monetizationModes: _monetizationModes,
          maxAvailablePrice: _repository.maxAvailablePrice,
          facets: _repository.facets,
        );
      },
    );

    if (result == null) return;
    setState(() => _filters = result);
    _loadServerDeals();
  }

  void _onSearchChanged(String value) {
    setState(() => _searchText = value);
    _scheduleServerSearch();
  }

  void _scheduleServerSearch() {
    _searchDebounce?.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 350), () {
      if (!mounted) return;
      _loadServerDeals(silent: true);
    });
  }

  Future<void> _loadServerDeals({bool silent = false, bool reset = true}) async {
    if (!reset && (_isLoadingMore || _isServerLoading || !_hasMoreServerDeals)) {
      return;
    }

    final requestId = reset ? ++_requestSerial : _requestSerial;
    final nextPage = reset ? 1 : _serverPage + 1;

    setState(() {
      _serverSearchStarted = true;
      _serverError = null;
      if (reset) {
        _isServerLoading = true;
        _isLoadingMore = false;
        _serverPage = 1;
        _hasMoreServerDeals = true;
        if (!silent) {
          _visibleDeals = const <Deal>[];
          _visibleTotalCount = 0;
        }
      } else {
        _isLoadingMore = true;
      }
    });

    try {
      final query = _currentQuery;
      final result = await _repository.searchDealsFromApi(
        query,
        page: nextPage,
        pageSize: _serverPageSize,
      );
      if (!mounted || requestId != _requestSerial) return;

      final mergedDeals = reset
          ? result.deals
          : _appendUniqueDeals(_visibleDeals, result.deals);

      final estimatedTotal = _repository.estimateTotalForQuery(
        query,
        fallback: result.totalCount,
      );
      final safeTotal = estimatedTotal > mergedDeals.length
          ? estimatedTotal
          : mergedDeals.length;

      setState(() {
        _visibleDeals = mergedDeals;
        _visibleTotalCount = safeTotal;
        _serverPage = nextPage;
        _serverError = null;
        _isServerLoading = false;
        _isLoadingMore = false;
        _serverSearchStarted = true;
        _hasMoreServerDeals =
            result.deals.isNotEmpty && mergedDeals.length < safeTotal;
      });
    } catch (error) {
      if (!mounted || requestId != _requestSerial) return;

      if (!reset) {
        setState(() {
          _serverError = AppStrings.select(
            en: 'Could not load more deals. Try again in a moment.',
            ru: 'Не удалось загрузить ещё предложения. Попробуйте чуть позже.',
            uz: 'Yana takliflarni yuklab bo‘lmadi. Birozdan keyin urinib ko‘ring.',
          );
          _isLoadingMore = false;
          _hasMoreServerDeals = false;
        });
        return;
      }

      final fallback = _repository.searchDeals(_currentQuery);

      setState(() {
        _visibleDeals = fallback.deals;
        _visibleTotalCount = fallback.foundCount;
        _serverError = AppStrings.select(
          en: 'Live filters are unavailable. Showing cached results.',
          ru: 'Live-фильтры недоступны. Показываем сохранённые результаты.',
          uz: 'Live filtrlar mavjud emas. Saqlangan natijalar ko‘rsatilmoqda.',
        );
        _isServerLoading = false;
        _isLoadingMore = false;
        _hasMoreServerDeals = false;
        _serverSearchStarted = true;
      });
    }
  }

  List<Deal> _appendUniqueDeals(List<Deal> current, List<Deal> next) {
    if (next.isEmpty) return current;

    final seenIds = current.map((deal) => deal.id).toSet();
    final merged = <Deal>[...current];
    for (final deal in next) {
      if (seenIds.add(deal.id)) {
        merged.add(deal);
      }
    }
    return List<Deal>.unmodifiable(merged);
  }

  void _clearSearch() {
    _searchController.clear();
    setState(() => _searchText = '');
    _loadServerDeals();
  }

  void _clearFilters() {
    setState(() => _filters = const DealFilters());
    _loadServerDeals();
  }

  void _selectCategory(String category) {
    setState(() {
      _filters = _filters.copyWith(
        category: _filters.category == category ? 'All' : category,
      );
    });
    _loadServerDeals();
  }

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<int>(
      valueListenable: _repository.version,
      builder: (context, _, child) {
        final localFallback = _localFilteredDeals;
        final deals = _serverSearchStarted ? _visibleDeals : localFallback;
        final resultCount = _serverSearchStarted
            ? (deals.isEmpty ? 0 : _visibleTotalCount)
            : _repository.totalAvailableCount;
        final featured = _featuredDeals;
        final heroDeal = featured.isNotEmpty ? featured.first : null;

        return CustomScrollView(
          controller: _scrollController,
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          slivers: [
            SliverToBoxAdapter(child: _HomeHeader(onRefresh: _repository.refresh)),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 6, 20, 8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _SearchAndActionsBar(
                      controller: _searchController,
                      query: _searchText,
                      activeFilterCount: _filters.activeCount,
                      onChanged: _onSearchChanged,
                      onClearSearch: _clearSearch,
                      onOpenFilters: _openAdvancedFilters,
                      onOpenFavorites: () => context.push('/favorites'),
                    ),
                    if (_isServerLoading) ...[
                      const SizedBox(height: 10),
                      const LinearProgressIndicator(minHeight: 3),
                    ],
                    if (_serverError != null) ...[
                      const SizedBox(height: 10),
                      _InlineStatusBanner(message: _serverError!),
                    ],
                    const SizedBox(height: 16),
                    _HeroBanner(featuredDeal: heroDeal),
                    const SizedBox(height: 18),
                    _CategorySection(
                      categories: ['All', ..._quickCategories],
                      selectedCategory: _filters.category,
                      onSelected: _selectCategory,
                    ),
                    if (_filters.hasActiveFilters || _searchText.trim().isNotEmpty) ...[
                      const SizedBox(height: 14),
                      _ClearBar(
                        onClearFilters:
                            _filters.hasActiveFilters ? _clearFilters : null,
                        onClearSearch:
                            _searchText.trim().isNotEmpty ? _clearSearch : null,
                      ),
                    ],
                    const SizedBox(height: 18),
                    _SectionTitle(
                      title: _searchText.trim().isEmpty
                          ? AppStrings.bestDealsToday
                          : AppStrings.searchResults,
                      count: resultCount,
                    ),
                  ],
                ),
              ),
            ),
            if (deals.isEmpty && !_isServerLoading)
              SliverFillRemaining(
                hasScrollBody: false,
                child: Center(
                  child: Padding(
                    padding: const EdgeInsets.all(28),
                    child: Text(
                      _searchText.trim().isEmpty
                          ? AppStrings.noDealsMatch
                          : AppStrings.noDealsFound,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: AppTheme.mutedText,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        height: 1.35,
                      ),
                    ),
                  ),
                ),
              )
            else
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 14),
                sliver: SliverList.separated(
                  itemCount: deals.length,
                  separatorBuilder: (context, index) => const SizedBox(height: 14),
                  itemBuilder: (context, index) {
                    final deal = deals[index];
                    return DealCard(
                      deal: deal,
                      onTap: () => context.push(
                        '/deal/${Uri.encodeComponent(deal.id)}',
                        extra: deal,
                      ),
                    );
                  },
                ),
              ),
            SliverToBoxAdapter(
              child: _PagingFooter(
                loadedCount: deals.length,
                totalCount: resultCount,
                isLoadingMore: _isLoadingMore,
                hasMore: _hasMoreServerDeals,
                onLoadMore: () => _loadServerDeals(silent: true, reset: false),
              ),
            ),
          ],
        );
      },
    );
  }
}


class _PagingFooter extends StatelessWidget {
  const _PagingFooter({
    required this.loadedCount,
    required this.totalCount,
    required this.isLoadingMore,
    required this.hasMore,
    required this.onLoadMore,
  });

  final int loadedCount;
  final int totalCount;
  final bool isLoadingMore;
  final bool hasMore;
  final VoidCallback onLoadMore;

  @override
  Widget build(BuildContext context) {
    if (loadedCount == 0 && !isLoadingMore) {
      return const SizedBox(height: 24);
    }

    final label = totalCount > loadedCount
        ? AppStrings.select(
            en: 'Showing $loadedCount of $totalCount live deals',
            ru: 'Показано $loadedCount из $totalCount предложений',
            uz: '$totalCount ta faol taklifdan $loadedCount tasi ko‘rsatildi',
          )
        : AppStrings.select(
            en: 'All $loadedCount deals loaded',
            ru: 'Все $loadedCount предложений загружены',
            uz: 'Barcha $loadedCount ta taklif yuklandi',
          );

    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 2, 20, 30),
      child: Column(
        children: [
          Text(
            label,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: AppTheme.mutedText,
              fontSize: 12.5,
              fontWeight: FontWeight.w800,
            ),
          ),
          if (isLoadingMore) ...[
            const SizedBox(height: 12),
            const SizedBox(
              width: 24,
              height: 24,
              child: CircularProgressIndicator(strokeWidth: 2.4),
            ),
          ] else if (hasMore) ...[
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: onLoadMore,
              icon: const Icon(Icons.expand_more_rounded),
              label: Text(
                AppStrings.select(
                  en: 'Load more deals',
                  ru: 'Загрузить ещё',
                  uz: 'Yana yuklash',
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _HomeHeader extends StatelessWidget {
  const _HomeHeader({required this.onRefresh});

  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      bottom: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 8),
        child: Row(
          children: [
            const Expanded(
              child: DiscountHubLogo(
                markSize: 40,
                wordmarkSize: 26,
                compact: true,
              ),
            ),
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.line),
                boxShadow: AppTheme.cardShadow,
              ),
              child: IconButton(
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints.tightFor(
                  width: 42,
                  height: 42,
                ),
                tooltip: AppStrings.select(
                  en: 'Refresh deals',
                  ru: 'Обновить скидки',
                  uz: 'Takliflarni yangilash',
                ),
                onPressed: () {
                  onRefresh();
                },
                icon: const Icon(
                  Icons.sync_rounded,
                  color: AppTheme.text,
                  size: 21,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HeroBanner extends StatelessWidget {
  const _HeroBanner({required this.featuredDeal});

  final Deal? featuredDeal;

  String get _title => AppStrings.select(
        en: 'Top brands.\nReal savings.',
        ru: 'Топ-бренды.\nБольше выгоды.',
        uz: 'Top brendlar.\nKo‘proq foyda.',
      );

  String get _subtitle => AppStrings.select(
        en: 'Verified marketplace deals collected in one clean feed',
        ru: 'Реальные скидки с маркетплейсов и онлайн-магазинов',
        uz: 'Turli bozorlardagi real takliflar bir lentada',
      );

  String get _caption => AppStrings.select(
        en: 'Browse deals',
        ru: 'Смотреть скидки',
        uz: 'Chegirmalarni ko‘rish',
      );

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isCompact = constraints.maxWidth < 370;
        final bannerHeight = isCompact ? 200.0 : 188.0;
        final imageWidth = isCompact ? 150.0 : 168.0;
        final titleSize = isCompact ? 20.0 : 23.0;
        final rightPadding = imageWidth + 30;

        return Container(
          height: bannerHeight,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color(0xFF2D6DFF), Color(0xFF134DE8)],
            ),
            borderRadius: BorderRadius.circular(28),
            boxShadow: AppTheme.softShadow,
          ),
          child: Stack(
            children: [
              Positioned(
                right: -18,
                top: -12,
                child: Container(
                  width: 118,
                  height: 118,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.08),
                    shape: BoxShape.circle,
                  ),
                ),
              ),
              if (featuredDeal != null)
                Positioned(
                  right: 14,
                  top: 20,
                  bottom: 20,
                  child: Container(
                    width: imageWidth,
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.96),
                      borderRadius: BorderRadius.circular(24),
                      boxShadow: [
                        BoxShadow(
                          color: AppTheme.navy.withValues(alpha: 0.08),
                          blurRadius: 18,
                          offset: const Offset(0, 8),
                        ),
                      ],
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(18),
                      child: CachedNetworkImage(
                        imageUrl: featuredDeal!.imageUrl,
                        fit: BoxFit.contain,
                        placeholder: (context, url) => Container(
                          color: Colors.white.withValues(alpha: 0.16),
                          child: const Center(
                            child: CircularProgressIndicator(
                              color: Colors.white,
                              strokeWidth: 2,
                            ),
                          ),
                        ),
                        errorWidget: (context, url, error) => Container(
                          color: Colors.white.withValues(alpha: 0.16),
                          child: const Icon(
                            Icons.image_outlined,
                            color: Colors.white,
                            size: 36,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              Padding(
                padding: EdgeInsets.fromLTRB(18, 18, rightPadding, 18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: titleSize,
                        fontWeight: FontWeight.w900,
                        height: 1.02,
                        letterSpacing: -0.35,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      _subtitle,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.92),
                        fontSize: isCompact ? 12.0 : 12.8,
                        fontWeight: FontWeight.w700,
                        height: 1.28,
                      ),
                    ),
                    const Spacer(),
                    Container(
                      height: 42,
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Flexible(
                            child: Text(
                              _caption,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: AppTheme.primary,
                                fontSize: 12.2,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          const Icon(
                            Icons.local_offer_rounded,
                            color: AppTheme.primary,
                            size: 17,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _InlineStatusBanner extends StatelessWidget {
  const _InlineStatusBanner({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppTheme.softBlue,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppTheme.line),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.info_outline_rounded,
            color: AppTheme.primary,
            size: 18,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(
                color: AppTheme.text,
                fontSize: 12.5,
                fontWeight: FontWeight.w800,
                height: 1.25,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _CategorySection extends StatelessWidget {
  const _CategorySection({
    required this.categories,
    required this.selectedCategory,
    required this.onSelected,
  });

  final List<String> categories;
  final String selectedCategory;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    if (categories.isEmpty) return const SizedBox.shrink();

    final title = AppStrings.select(
      en: 'Popular categories',
      ru: 'Популярные категории',
      uz: 'Mashhur kategoriyalar',
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(
            color: AppTheme.text,
            fontSize: 18,
            fontWeight: FontWeight.w900,
            letterSpacing: -0.2,
          ),
        ),
        const SizedBox(height: 10),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: categories.map((category) {
              final selected = selectedCategory == category;
              return Padding(
                padding: const EdgeInsets.only(right: 8),
                child: _CategoryChip(
                  label: category == 'All'
                      ? AppStrings.all
                      : AppStrings.categoryName(category),
                  selected: selected,
                  onTap: () => onSelected(category),
                ),
              );
            }).toList(),
          ),
        ),
      ],
    );
  }
}

class _CategoryChip extends StatelessWidget {
  const _CategoryChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: selected ? AppTheme.primary : Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: selected ? AppTheme.primary : AppTheme.line,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? Colors.white : AppTheme.text,
            fontSize: 13,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }
}

class _SearchAndActionsBar extends StatelessWidget {
  const _SearchAndActionsBar({
    required this.controller,
    required this.query,
    required this.activeFilterCount,
    required this.onChanged,
    required this.onClearSearch,
    required this.onOpenFilters,
    required this.onOpenFavorites,
  });

  final TextEditingController controller;
  final String query;
  final int activeFilterCount;
  final ValueChanged<String> onChanged;
  final VoidCallback onClearSearch;
  final VoidCallback onOpenFilters;
  final VoidCallback onOpenFavorites;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: DecoratedBox(
            decoration: BoxDecoration(
              boxShadow: AppTheme.cardShadow,
              borderRadius: BorderRadius.circular(18),
            ),
            child: TextField(
              controller: controller,
              onChanged: onChanged,
              textInputAction: TextInputAction.search,
              decoration: InputDecoration(
                hintText: AppStrings.searchHint,
                prefixIcon: const Icon(Icons.search_rounded),
                suffixIcon: query.trim().isEmpty
                    ? null
                    : IconButton(
                        onPressed: onClearSearch,
                        icon: const Icon(Icons.close_rounded),
                      ),
              ),
            ),
          ),
        ),
        const SizedBox(width: 10),
        _HeaderActionButton(
          onPressed: onOpenFilters,
          icon: Icons.tune_rounded,
          tooltip: activeFilterCount > 0
              ? AppStrings.filtersActive(activeFilterCount)
              : AppStrings.advancedFilters,
          badgeCount: activeFilterCount,
        ),
        const SizedBox(width: 8),
        _HeaderActionButton(
          onPressed: onOpenFavorites,
          icon: Icons.favorite_border_rounded,
          tooltip: AppStrings.savedDeals,
        ),
      ],
    );
  }
}

class _HeaderActionButton extends StatelessWidget {
  const _HeaderActionButton({
    required this.onPressed,
    required this.icon,
    required this.tooltip,
    this.badgeCount = 0,
  });

  final VoidCallback onPressed;
  final IconData icon;
  final String tooltip;
  final int badgeCount;

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.none,
      children: [
        Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: AppTheme.line),
            boxShadow: AppTheme.cardShadow,
          ),
          child: IconButton(
            onPressed: onPressed,
            icon: Icon(icon),
            tooltip: tooltip,
            color: AppTheme.text,
            style: IconButton.styleFrom(
              minimumSize: const Size(52, 52),
            ),
          ),
        ),
        if (badgeCount > 0)
          Positioned(
            right: -3,
            top: -3,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: AppTheme.primary,
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: Colors.white, width: 2),
              ),
              child: Text(
                '$badgeCount',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({
    required this.title,
    required this.count,
  });

  final String title;
  final int count;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(
          child: Text(
            title,
            style: const TextStyle(
              color: AppTheme.text,
              fontSize: 22,
              fontWeight: FontWeight.w900,
              letterSpacing: -0.4,
              height: 1.1,
            ),
          ),
        ),
        const SizedBox(width: 12),
        Text(
          AppStrings.foundCount(count),
          style: const TextStyle(
            color: AppTheme.mutedText,
            fontWeight: FontWeight.w800,
          ),
        ),
      ],
    );
  }
}

class _ClearBar extends StatelessWidget {
  const _ClearBar({
    required this.onClearFilters,
    required this.onClearSearch,
  });

  final VoidCallback? onClearFilters;
  final VoidCallback? onClearSearch;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        if (onClearSearch != null)
          ActionChip(
            avatar: const Icon(Icons.search_off_rounded, size: 18),
            label: Text(AppStrings.clear),
            onPressed: onClearSearch,
          ),
        if (onClearFilters != null)
          ActionChip(
            avatar: const Icon(Icons.filter_alt_off_rounded, size: 18),
            label: Text(AppStrings.clearFilters),
            onPressed: onClearFilters,
          ),
      ],
    );
  }
}
