import 'package:flutter/material.dart';

import '../../../app/app_theme.dart';
import '../../settings/app_strings.dart';
import '../../settings/settings_store.dart';
import '../api/deal_facets.dart';
import '../models/deal_filters.dart';
import '../models/deal_query.dart';


class DealFilterSheetResult {
  const DealFilterSheetResult({
    required this.filters,
    required this.sort,
  });

  final DealFilters filters;
  final DealSort sort;
}

class DealFilterSheet extends StatefulWidget {
  const DealFilterSheet({
    super.key,
    required this.initialFilters,
    required this.platforms,
    required this.categories,
    required this.initialSort,
    required this.maxAvailablePrice,
    this.facets,
  });

  final DealFilters initialFilters;
  final List<String> platforms;
  final List<String> categories;
  final DealSort initialSort;
  final double maxAvailablePrice;
  final DealFacets? facets;

  @override
  State<DealFilterSheet> createState() => _DealFilterSheetState();
}

class _DealFilterSheetState extends State<DealFilterSheet> {
  late Set<String> _selectedPlatforms;
  late Set<String> _selectedCategories;
  late int _minDiscount;
  late double _maxPrice;
  late bool _usePriceLimit;
  late DealSort _sort;

  final TextEditingController _marketplaceSearchController = TextEditingController();
  String _marketplaceSearchText = '';

  double get _safeMaxPrice => widget.maxAvailablePrice < 1 ? 1 : widget.maxAvailablePrice;

  List<String> get _visiblePlatforms {
    final query = _marketplaceSearchText.trim().toLowerCase();
    if (query.isEmpty) return widget.platforms;

    return widget.platforms.where((platform) {
      if (platform == 'All') return true;
      return platform.toLowerCase().contains(query);
    }).toList(growable: false);
  }

  @override
  void initState() {
    super.initState();

    final filters = widget.initialFilters;
    _selectedPlatforms = filters.selectedPlatforms.toSet();
    _selectedCategories = filters.selectedCategories.toSet();
    _minDiscount = filters.minDiscount;
    _maxPrice = filters.maxPrice ?? _safeMaxPrice;
    _usePriceLimit = filters.maxPrice != null;
    _sort = widget.initialSort;
  }

  @override
  void dispose() {
    _marketplaceSearchController.dispose();
    super.dispose();
  }

  DealFilters get _currentFilters {
    return DealFilters(
      platformSelections: _selectedPlatforms.toList(growable: false),
      categorySelections: _selectedCategories.toList(growable: false),
      minDiscount: _minDiscount,
      maxPrice: _usePriceLimit ? _maxPrice : null,
    );
  }

  void _clear() {
    setState(() {
      _selectedPlatforms = <String>{};
      _selectedCategories = <String>{};
      _minDiscount = 0;
      _maxPrice = _safeMaxPrice;
      _usePriceLimit = false;
      _sort = DealSort.discountHighToLow;
      _marketplaceSearchText = '';
      _marketplaceSearchController.clear();
    });
  }

  void _apply() {
    Navigator.of(context).pop(
      DealFilterSheetResult(
        filters: _currentFilters,
        sort: _sort,
      ),
    );
  }


  void _togglePlatform(String value) {
    setState(() {
      if (value == 'All') {
        _selectedPlatforms.clear();
        return;
      }

      if (_selectedPlatforms.contains(value)) {
        _selectedPlatforms.remove(value);
      } else {
        _selectedPlatforms.add(value);
      }
    });
  }

  void _toggleCategory(String value) {
    setState(() {
      if (value == 'All') {
        _selectedCategories.clear();
        return;
      }

      if (_selectedCategories.contains(value)) {
        _selectedCategories.remove(value);
      } else {
        _selectedCategories.add(value);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.9,
        minChildSize: 0.55,
        maxChildSize: 0.95,
        builder: (context, scrollController) {
          return Column(
            children: [
              Expanded(
                child: ListView(
                  controller: scrollController,
                  padding: const EdgeInsets.fromLTRB(20, 4, 20, 20),
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            AppStrings.advancedFilters,
                            style: const TextStyle(
                              color: AppTheme.text,
                              fontSize: 26,
                              fontWeight: FontWeight.w900,
                              letterSpacing: -0.6,
                            ),
                          ),
                        ),
                        TextButton.icon(
                          onPressed: _clear,
                          icon: const Icon(Icons.refresh_rounded, size: 18),
                          label: Text(AppStrings.clear),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      AppStrings.select(
                        en: 'Choose a store, category, discount level, price limit or sorting for the main feed.',
                        ru: 'Выберите магазин, категорию, уровень скидки, лимит цены или сортировку для главной ленты.',
                        uz: 'Asosiy lenta uchun do‘kon, kategoriya, chegirma darajasi, narx limiti yoki tartibni tanlang.',
                      ),
                      style: const TextStyle(
                        color: AppTheme.mutedText,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        height: 1.35,
                      ),
                    ),
                    const SizedBox(height: 18),
                    _Section(
                      icon: Icons.storefront_rounded,
                      title: AppStrings.marketplace,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          TextField(
                            controller: _marketplaceSearchController,
                            onChanged: (value) => setState(() => _marketplaceSearchText = value),
                            decoration: InputDecoration(
                              hintText: AppStrings.select(
                                en: 'Search stores',
                                ru: 'Поиск магазинов',
                                uz: 'Do‘konlarni qidirish',
                              ),
                              prefixIcon: const Icon(Icons.search_rounded),
                              isDense: true,
                            ),
                          ),
                          const SizedBox(height: 12),
                          _MultiChoiceWrap(
                            values: _visiblePlatforms,
                            selectedValues: _selectedPlatforms,
                            labelBuilder: (value) => _labelWithCount(
                              value: value,
                              allLabel: AppStrings.all,
                              name: _marketplaceLabel(value),
                              count: value == 'All'
                                  ? widget.facets?.totalCount ?? 0
                                  : widget.facets?.countForMarketplace(value) ?? 0,
                            ),
                            onSelected: _togglePlatform,
                          ),
                        ],
                      ),
                    ),
                    _Section(
                      icon: Icons.category_rounded,
                      title: AppStrings.category,
                      child: _MultiChoiceWrap(
                        values: widget.categories,
                        selectedValues: _selectedCategories,
                        labelBuilder: (value) => _labelWithCount(
                          value: value,
                          allLabel: AppStrings.all,
                          name: value == 'All' ? null : AppStrings.categoryName(value),
                          count: value == 'All'
                              ? widget.facets?.totalCount ?? 0
                              : widget.facets?.countForCategory(value) ?? 0,
                        ),
                        onSelected: _toggleCategory,
                      ),
                    ),
                    _Section(
                      icon: Icons.percent_rounded,
                      title: AppStrings.minimumDiscount,
                      child: _ChoiceWrap<int>(
                        values: const [0, 10, 20, 30, 40, 50, 70],
                        selectedValue: _minDiscount,
                        labelBuilder: (value) => value == 0 ? AppStrings.any : '$value%+',
                        onSelected: (value) => setState(() => _minDiscount = value),
                      ),
                    ),
                    _Section(
                      icon: Icons.sort_rounded,
                      title: AppStrings.select(
                        en: 'Sort by',
                        ru: 'Сортировка',
                        uz: 'Saralash',
                      ),
                      child: _ChoiceWrap<DealSort>(
                        values: const [
                          DealSort.discountHighToLow,
                          DealSort.bestMatch,
                          DealSort.newest,
                          DealSort.priceLowToHigh,
                          DealSort.priceHighToLow,
                        ],
                        selectedValue: _sort,
                        labelBuilder: _sortLabel,
                        onSelected: (value) => setState(() => _sort = value),
                      ),
                    ),
                    _Section(
                      icon: Icons.payments_rounded,
                      title: AppStrings.priceLimit,
                      child: _PriceLimitCard(
                        usePriceLimit: _usePriceLimit,
                        maxPrice: _maxPrice,
                        safeMaxPrice: _safeMaxPrice,
                        onToggle: (value) => setState(() => _usePriceLimit = value),
                        onPriceChanged: (value) => setState(() => _maxPrice = value),
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  border: const Border(top: BorderSide(color: AppTheme.line)),
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.navy.withValues(alpha: 0.05),
                      blurRadius: 20,
                      offset: const Offset(0, -8),
                    ),
                  ],
                ),
                child: FilledButton.icon(
                  onPressed: _apply,
                  icon: const Icon(Icons.tune_rounded),
                  label: Text(AppStrings.applyFilters),
                ),
              ),
            ],
          );
        },
      ),
    );
  }


  String? _marketplaceLabel(String value) {
    final normalized = value.trim().toLowerCase();
    if (normalized.startsWith('ebay')) return 'eBay';
    if (normalized.startsWith('aliexpress')) return 'AliExpress';
    if (normalized.startsWith('alibaba')) return 'Alibaba';
    if (normalized.startsWith('amazon')) return 'Amazon';
    return null;
  }

  String _labelWithCount({
    required String value,
    required String allLabel,
    String? name,
    int count = 0,
  }) {
    // Counts are intentionally hidden in the UI. The backend still provides
    // them for sorting/ordering facets, but customers should only see filter
    // names, not catalog totals per store/category/link type.
    return value == 'All' ? allLabel : name ?? value;
  }



  String _sortLabel(DealSort value) {
    switch (value) {
      case DealSort.discountHighToLow:
        return AppStrings.select(en: 'Biggest discount', ru: 'Самая большая скидка', uz: 'Eng katta chegirma');
      case DealSort.bestMatch:
        return AppStrings.select(en: 'Best match', ru: 'Лучшие сначала', uz: 'Eng yaxshilari');
      case DealSort.newest:
        return AppStrings.select(en: 'Newest', ru: 'Новые', uz: 'Yangi');
      case DealSort.priceLowToHigh:
        return AppStrings.select(en: 'Lowest price', ru: 'Сначала дешёвые', uz: 'Arzonlari oldin');
      case DealSort.priceHighToLow:
        return AppStrings.select(en: 'Highest price', ru: 'Сначала дорогие', uz: 'Qimmatlari oldin');
      case DealSort.ratingHighToLow:
        return AppStrings.select(en: 'Highest rating', ru: 'Высокий рейтинг', uz: 'Yuqori reyting');
    }
  }

}

class _Section extends StatelessWidget {
  const _Section({
    required this.icon,
    required this.title,
    required this.child,
  });

  final IconData icon;
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(26),
        border: Border.all(color: AppTheme.line),
        boxShadow: AppTheme.cardShadow,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: AppTheme.softBlue,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(icon, color: AppTheme.primary, size: 20),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    color: AppTheme.text,
                    fontSize: 16,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}

class _PriceLimitCard extends StatelessWidget {
  const _PriceLimitCard({
    required this.usePriceLimit,
    required this.maxPrice,
    required this.safeMaxPrice,
    required this.onToggle,
    required this.onPriceChanged,
  });

  final bool usePriceLimit;
  final double maxPrice;
  final double safeMaxPrice;
  final ValueChanged<bool> onToggle;
  final ValueChanged<double> onPriceChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SwitchListTile(
          value: usePriceLimit,
          onChanged: onToggle,
          contentPadding: EdgeInsets.zero,
          title: Text(
            AppStrings.useMaximumPrice,
            style: const TextStyle(
              color: AppTheme.text,
              fontWeight: FontWeight.w900,
            ),
          ),
          subtitle: Text(
            usePriceLimit
                ? AppStrings.showDealsUpTo(UserSettingsStore.formatUsd(maxPrice))
                : AppStrings.noPriceLimit,
            style: const TextStyle(
              color: AppTheme.mutedText,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        Slider(
          value: maxPrice.clamp(1, safeMaxPrice).toDouble(),
          min: 1,
          max: safeMaxPrice,
          divisions: safeMaxPrice.round().clamp(1, 500).toInt(),
          label: UserSettingsStore.formatUsd(maxPrice),
          onChanged: usePriceLimit ? onPriceChanged : null,
        ),
      ],
    );
  }
}


class _ChoiceWrap<T> extends StatelessWidget {
  const _ChoiceWrap({
    required this.values,
    required this.selectedValue,
    required this.onSelected,
    this.labelBuilder,
  });

  final List<T> values;
  final T selectedValue;
  final ValueChanged<T> onSelected;
  final String Function(T value)? labelBuilder;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: values.map((value) {
        final selected = value == selectedValue;
        final label = labelBuilder?.call(value) ?? value.toString();

        return ChoiceChip(
          label: Text(label),
          selected: selected,
          onSelected: (_) => onSelected(value),
          selectedColor: AppTheme.primary,
          labelStyle: TextStyle(
            color: selected ? Colors.white : AppTheme.text,
            fontWeight: FontWeight.w900,
          ),
          side: BorderSide(color: selected ? AppTheme.primary : AppTheme.line),
          backgroundColor: Colors.white,
        );
      }).toList(),
    );
  }
}

class _MultiChoiceWrap<T> extends StatelessWidget {
  const _MultiChoiceWrap({
    required this.values,
    required this.selectedValues,
    required this.onSelected,
    this.labelBuilder,
  });

  final List<T> values;
  final Set<T> selectedValues;
  final ValueChanged<T> onSelected;
  final String Function(T value)? labelBuilder;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: values.map((value) {
        final isAll = value == 'All';
        final selected = isAll ? selectedValues.isEmpty : selectedValues.contains(value);
        final label = labelBuilder?.call(value) ?? value.toString();

        return ChoiceChip(
          label: Text(label),
          selected: selected,
          onSelected: (_) => onSelected(value),
          selectedColor: AppTheme.primary,
          labelStyle: TextStyle(
            color: selected ? Colors.white : AppTheme.text,
            fontWeight: FontWeight.w900,
          ),
          side: BorderSide(color: selected ? AppTheme.primary : AppTheme.line),
          backgroundColor: Colors.white,
        );
      }).toList(),
    );
  }
}
