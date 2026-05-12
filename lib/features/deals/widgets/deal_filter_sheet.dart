import 'package:flutter/material.dart';

import '../../../app/app_theme.dart';
import '../../settings/app_strings.dart';
import '../../settings/settings_store.dart';
import '../models/deal_filters.dart';

class DealFilterSheet extends StatefulWidget {
  const DealFilterSheet({
    super.key,
    required this.initialFilters,
    required this.platforms,
    required this.categories,
    required this.countries,
    required this.maxAvailablePrice,
  });

  final DealFilters initialFilters;
  final List<String> platforms;
  final List<String> categories;
  final List<String> countries;
  final double maxAvailablePrice;

  @override
  State<DealFilterSheet> createState() => _DealFilterSheetState();
}

class _DealFilterSheetState extends State<DealFilterSheet> {
  late String _platform;
  late String _category;
  late String _shipToCountry;
  late int _minDiscount;
  late double _maxPrice;
  late bool _usePriceLimit;
  late double _minRating;
  late bool _freeShippingOnly;
  late bool _verifiedOnly;

  double get _safeMaxPrice => widget.maxAvailablePrice < 1 ? 1 : widget.maxAvailablePrice;

  @override
  void initState() {
    super.initState();

    final filters = widget.initialFilters;
    _platform = filters.platform;
    _category = filters.category;
    _shipToCountry = filters.shipToCountry;
    _minDiscount = filters.minDiscount;
    _maxPrice = filters.maxPrice ?? _safeMaxPrice;
    _usePriceLimit = filters.maxPrice != null;
    _minRating = filters.minRating;
    _freeShippingOnly = filters.freeShippingOnly;
    _verifiedOnly = filters.verifiedOnly;
  }

  DealFilters get _currentFilters {
    return DealFilters(
      platform: _platform,
      category: _category,
      shipToCountry: _shipToCountry,
      minDiscount: _minDiscount,
      maxPrice: _usePriceLimit ? _maxPrice : null,
      minRating: _minRating,
      freeShippingOnly: _freeShippingOnly,
      verifiedOnly: _verifiedOnly,
    );
  }

  void _clear() {
    setState(() {
      _platform = 'All';
      _category = 'All';
      _shipToCountry = 'All';
      _minDiscount = 0;
      _maxPrice = _safeMaxPrice;
      _usePriceLimit = false;
      _minRating = 0;
      _freeShippingOnly = false;
      _verifiedOnly = false;
    });
  }

  void _apply() {
    Navigator.of(context).pop(_currentFilters);
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.88,
        minChildSize: 0.55,
        maxChildSize: 0.94,
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
                      AppStrings.filterDescription,
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
                      child: _ChoiceWrap(
                        values: widget.platforms,
                        selectedValue: _platform,
                        labelBuilder: (value) => value == 'All' ? AppStrings.all : value,
                        onSelected: (value) => setState(() => _platform = value),
                      ),
                    ),
                    _Section(
                      icon: Icons.category_rounded,
                      title: AppStrings.category,
                      child: _ChoiceWrap(
                        values: widget.categories,
                        selectedValue: _category,
                        labelBuilder: (value) => value == 'All' ? AppStrings.all : AppStrings.categoryName(value),
                        onSelected: (value) => setState(() => _category = value),
                      ),
                    ),
                    _Section(
                      icon: Icons.public_rounded,
                      title: AppStrings.shipsTo,
                      child: _ChoiceWrap(
                        values: widget.countries,
                        selectedValue: _shipToCountry,
                        labelBuilder: (value) => value == 'All' ? AppStrings.all : value,
                        onSelected: (value) => setState(() => _shipToCountry = value),
                      ),
                    ),
                    _Section(
                      icon: Icons.percent_rounded,
                      title: AppStrings.minimumDiscount,
                      child: _ChoiceWrap<int>(
                        values: const [0, 20, 30, 40, 50],
                        selectedValue: _minDiscount,
                        labelBuilder: (value) => value == 0 ? AppStrings.any : '$value%+',
                        onSelected: (value) => setState(() => _minDiscount = value),
                      ),
                    ),
                    _Section(
                      icon: Icons.star_rounded,
                      title: AppStrings.minimumRating,
                      child: _ChoiceWrap<double>(
                        values: const [0, 4.0, 4.5],
                        selectedValue: _minRating,
                        labelBuilder: (value) => value == 0 ? AppStrings.any : '${value.toStringAsFixed(1)}+',
                        onSelected: (value) => setState(() => _minRating = value),
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
                    _Section(
                      icon: Icons.verified_rounded,
                      title: AppStrings.dealQuality,
                      child: Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          FilterChip(
                            label: Text(AppStrings.freeShippingOnly),
                            selected: _freeShippingOnly,
                            onSelected: (value) => setState(() => _freeShippingOnly = value),
                          ),
                          FilterChip(
                            label: Text(AppStrings.verifiedDealsOnly),
                            selected: _verifiedOnly,
                            onSelected: (value) => setState(() => _verifiedOnly = value),
                          ),
                        ],
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
