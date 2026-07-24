import 'dart:async';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../app/app_theme.dart';
import '../../settings/app_strings.dart';
import '../../settings/settings_store.dart';
import '../api/promotions_api_client.dart';
import '../data/promotions_repository.dart';
import '../models/promotion.dart';

class PromotionsPage extends StatefulWidget {
  const PromotionsPage({super.key});

  @override
  State<PromotionsPage> createState() => _PromotionsPageState();
}

class _PromotionsPageState extends State<PromotionsPage> {
  final PromotionsRepository _repository = PromotionsRepository.instance;
  final TextEditingController _searchController = TextEditingController();

  Future<PromotionsLoadResult>? _future;
  String? _selectedType;
  final Set<String> _selectedStores = <String>{};
  String? _selectedCountry;
  List<PromotionCountryFacet> _knownCountries = const <PromotionCountryFacet>[];
  List<String> _knownStores = const <String>[];
  Timer? _searchDebounce;

  @override
  void initState() {
    super.initState();
    final savedCountry = UserSettingsStore.marketCountryCode.value;
    _selectedCountry = savedCountry.isEmpty ? null : savedCountry;
    UserSettingsStore.marketCountryCode.addListener(
      _handleMarketCountryChanged,
    );
    _future = _loadPromotions();
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    UserSettingsStore.marketCountryCode.removeListener(
      _handleMarketCountryChanged,
    );
    _searchController.dispose();
    super.dispose();
  }

  Future<PromotionsLoadResult> _loadPromotions() async {
    final result = await _repository.loadPromotions(
      query: _searchController.text,
      type: _selectedType,
      stores: _selectedStores.toList(growable: false),
      country: _selectedCountry,
    );
    _rememberStores(result.stores);
    _rememberCountries(result.countries);
    return result;
  }

  void _rememberStores(List<String> storeNames) {
    final stores = List<String>.of(_knownStores);
    for (final rawStore in storeNames) {
      final store = rawStore.trim();
      if (store.isEmpty) continue;
      final exists = stores.any(
        (value) => value.toLowerCase() == store.toLowerCase(),
      );
      if (!exists) stores.add(store);
    }

    stores.sort((a, b) => a.toLowerCase().compareTo(b.toLowerCase()));
    var unchanged = stores.length == _knownStores.length;
    if (unchanged) {
      for (var index = 0; index < stores.length; index += 1) {
        if (stores[index] != _knownStores[index]) {
          unchanged = false;
          break;
        }
      }
    }
    if (unchanged || !mounted) return;
    setState(() => _knownStores = List.unmodifiable(stores));
  }

  void _rememberCountries(List<PromotionCountryFacet> options) {
    final values = <PromotionCountryFacet>[];
    for (final option in options) {
      final id = option.id.trim().toUpperCase();
      if (id.isEmpty || values.any((item) => item.id == id)) continue;
      values.add(PromotionCountryFacet(id: id, name: option.name));
    }
    final selected = _selectedCountry;
    if (selected != null && values.every((item) => item.id != selected)) {
      values.insert(0, PromotionCountryFacet(id: selected, name: selected));
    }
    var unchanged = values.length == _knownCountries.length;
    if (unchanged) {
      for (var index = 0; index < values.length; index += 1) {
        if (values[index].id != _knownCountries[index].id ||
            values[index].name != _knownCountries[index].name) {
          unchanged = false;
          break;
        }
      }
    }
    if (unchanged || !mounted) return;
    setState(() => _knownCountries = List.unmodifiable(values));
  }

  void _handleMarketCountryChanged() {
    if (!mounted) return;
    final code = UserSettingsStore.marketCountryCode.value;
    final next = code.isEmpty ? null : code;
    if (_selectedCountry == next) return;
    setState(() {
      _selectedCountry = next;
      _future = _loadPromotions();
    });
  }

  Future<void> _setCountry(String? country) async {
    final normalized = country?.trim().toUpperCase();
    final next = normalized == null || normalized.isEmpty ? null : normalized;
    if (_selectedCountry == next) return;
    setState(() {
      _selectedCountry = next;
      _future = _loadPromotions();
    });
    await UserSettingsStore.setMarketCountryCode(next ?? '');
  }

  Future<void> _refresh() async {
    final future = _loadPromotions();
    setState(() {
      _future = future;
    });
    try {
      await future;
    } catch (_) {
      // The FutureBuilder below renders the friendly unavailable state.
    }
  }

  void _onSearchChanged(String value) {
    _searchDebounce?.cancel();
    _searchDebounce = Timer(const Duration(milliseconds: 350), () {
      if (!mounted) return;
      setState(() {
        _future = _loadPromotions();
      });
    });
  }

  void _setType(String? type) {
    if (_selectedType == type) return;
    setState(() {
      _selectedType = type;
      _future = _loadPromotions();
    });
  }

  void _toggleStore(String? store) {
    setState(() {
      if (store == null || store.trim().isEmpty) {
        _selectedStores.clear();
      } else if (_selectedStores.contains(store)) {
        _selectedStores.remove(store);
      } else {
        _selectedStores.add(store);
      }
      _future = _loadPromotions();
    });
  }

  Future<void> _openPromotion(
    PromotionsLoadResult result,
    Promotion promotion,
  ) async {
    final url = _repository.clickUri(
      promotionId: promotion.id,
      baseUrl: result.baseUrl,
    );
    final opened = await launchUrl(url, mode: LaunchMode.externalApplication);
    if (!mounted) return;
    if (!opened) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(AppStrings.couldNotOpenLink)));
    }
  }

  Future<void> _copyCode(Promotion promotion) async {
    final code = promotion.code?.trim();
    if (code == null || code.isEmpty) return;
    await Clipboard.setData(ClipboardData(text: code));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          AppStrings.select(
            en: 'Promo code copied',
            ru: 'РџСЂРѕРјРѕРєРѕРґ СЃРєРѕРїРёСЂРѕРІР°РЅ',
            uz: 'Promokod nusxalandi',
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          AppStrings.select(en: 'Promos', ru: 'РђРєС†РёРё', uz: 'Aksiyalar'),
        ),
      ),
      body: FutureBuilder<PromotionsLoadResult>(
        future: _future,
        builder: (context, snapshot) {
          final result = snapshot.data;
          final promotions = result?.promotions ?? const <Promotion>[];
          final isLoading = snapshot.connectionState != ConnectionState.done;

          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 28),
              children: [
                _PromotionsHero(totalCount: result?.totalCount),
                const SizedBox(height: 14),
                _PromotionSearchField(
                  controller: _searchController,
                  onChanged: _onSearchChanged,
                  onClear: () {
                    _searchController.clear();
                    setState(() {
                      _future = _loadPromotions();
                    });
                  },
                ),
                const SizedBox(height: 12),
                _PromotionTypeFilters(
                  selectedType: _selectedType,
                  onSelected: _setType,
                ),
                if (_knownCountries.isNotEmpty || _selectedCountry != null) ...[
                  const SizedBox(height: 12),
                  _PromotionCountryFilters(
                    countries: _knownCountries,
                    selectedCountry: _selectedCountry,
                    onSelected: _setCountry,
                  ),
                ],
                if (_knownStores.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  _PromotionStoreFilters(
                    stores: _knownStores,
                    selectedStores: _selectedStores,
                    onSelected: _toggleStore,
                  ),
                ],
                if (isLoading) ...[
                  const SizedBox(height: 16),
                  const LinearProgressIndicator(minHeight: 3),
                ],
                if (snapshot.hasError && !isLoading) ...[
                  const SizedBox(height: 18),
                  _PromotionStatusCard(
                    icon: Icons.cloud_off_rounded,
                    title: AppStrings.select(
                      en: 'Promotions are not available yet',
                      ru: 'РђРєС†РёРё РїРѕРєР° РЅРµРґРѕСЃС‚СѓРїРЅС‹',
                      uz: 'Aksiyalar hozircha mavjud emas',
                    ),
                    message: AppStrings.select(
                      en: 'The app is ready for promo codes and store sales. Connect the backend promotions source to fill this tab.',
                      ru: 'Р Р°Р·РґРµР» СѓР¶Рµ РіРѕС‚РѕРІ РґР»СЏ РїСЂРѕРјРѕРєРѕРґРѕРІ Рё СЂР°СЃРїСЂРѕРґР°Р¶. РџРѕРґРєР»СЋС‡РёС‚Рµ backend-РёСЃС‚РѕС‡РЅРёРє Р°РєС†РёР№, С‡С‚РѕР±С‹ Р·Р°РїРѕР»РЅРёС‚СЊ СЌС‚Сѓ РІРєР»Р°РґРєСѓ.',
                      uz: 'Ilova promokodlar va doвЂkon aksiyalari uchun tayyor. Bu boвЂlimni toвЂldirish uchun backend manbasini ulang.',
                    ),
                    onRetry: () => setState(() => _future = _loadPromotions()),
                  ),
                ] else if (!isLoading && promotions.isEmpty) ...[
                  const SizedBox(height: 18),
                  _PromotionStatusCard(
                    icon: Icons.local_offer_outlined,
                    title: AppStrings.select(
                      en: 'No live promos right now',
                      ru: 'РЎРµР№С‡Р°СЃ РЅРµС‚ Р°РєС‚РёРІРЅС‹С… Р°РєС†РёР№',
                      uz: 'Hozir faol aksiyalar yoвЂq',
                    ),
                    message: AppStrings.select(
                      en: 'When promo codes, sales or short-time campaigns are imported, they will appear here.',
                      ru: 'РљРѕРіРґР° РёРјРїРѕСЂС‚РёСЂСѓСЋС‚СЃСЏ РїСЂРѕРјРѕРєРѕРґС‹, СЂР°СЃРїСЂРѕРґР°Р¶Рё РёР»Рё СЃСЂРѕС‡РЅС‹Рµ Р°РєС†РёРё, РѕРЅРё РїРѕСЏРІСЏС‚СЃСЏ Р·РґРµСЃСЊ.',
                      uz: 'Promokodlar, chegirmali savdolar yoki qisqa muddatli aksiyalar import qilinganda shu yerda koвЂrinadi.',
                    ),
                    onRetry: () => setState(() => _future = _loadPromotions()),
                  ),
                ] else ...[
                  const SizedBox(height: 18),
                  for (final promotion in promotions) ...[
                    _PromotionCard(
                      promotion: promotion,
                      onOpen: result == null
                          ? null
                          : () => _openPromotion(result, promotion),
                      onCopyCode: promotion.hasCode
                          ? () => _copyCode(promotion)
                          : null,
                    ),
                    const SizedBox(height: 14),
                  ],
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}

class _PromotionsHero extends StatelessWidget {
  const _PromotionsHero({this.totalCount});

  final int? totalCount;

  @override
  Widget build(BuildContext context) {
    final countText = totalCount == null || totalCount == 0
        ? AppStrings.select(
            en: 'Promo codes and sales',
            ru: 'РџСЂРѕРјРѕРєРѕРґС‹ Рё СЂР°СЃРїСЂРѕРґР°Р¶Рё',
            uz: 'Promokodlar va aksiyalar',
          )
        : AppStrings.select(
            en: '$totalCount live promos',
            ru: '$totalCount Р°РєС‚РёРІРЅС‹С… Р°РєС†РёР№',
            uz: '$totalCount ta faol aksiya',
          );

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: AppTheme.brandGradient,
        borderRadius: BorderRadius.circular(28),
        boxShadow: AppTheme.softShadow,
      ),
      child: Row(
        children: [
          Container(
            width: 54,
            height: 54,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: Colors.white.withValues(alpha: 0.25)),
            ),
            child: const Icon(
              Icons.local_offer_rounded,
              color: Colors.white,
              size: 28,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  countText,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w900,
                    height: 1.08,
                    letterSpacing: -0.35,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  AppStrings.select(
                    en: 'Store-wide offers, promo codes and limited-time sales in one place.',
                    ru: 'РћР±С‰РёРµ Р°РєС†РёРё РјР°РіР°Р·РёРЅРѕРІ, РїСЂРѕРјРѕРєРѕРґС‹ Рё СЃСЂРѕС‡РЅС‹Рµ СЂР°СЃРїСЂРѕРґР°Р¶Рё РІ РѕРґРЅРѕРј РјРµСЃС‚Рµ.',
                    uz: 'DoвЂkon aksiyalari, promokodlar va qisqa muddatli chegirmalar bir joyda.',
                  ),
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.86),
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    height: 1.3,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PromotionSearchField extends StatelessWidget {
  const _PromotionSearchField({
    required this.controller,
    required this.onChanged,
    required this.onClear,
  });

  final TextEditingController controller;
  final ValueChanged<String> onChanged;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      onChanged: onChanged,
      textInputAction: TextInputAction.search,
      decoration: InputDecoration(
        prefixIcon: const Icon(Icons.search_rounded),
        hintText: AppStrings.select(
          en: 'Search promos or stores',
          ru: 'РџРѕРёСЃРє Р°РєС†РёР№ РёР»Рё РјР°РіР°Р·РёРЅРѕРІ',
          uz: 'Aksiya yoki doвЂkon qidirish',
        ),
        suffixIcon: controller.text.trim().isEmpty
            ? null
            : IconButton(
                onPressed: onClear,
                icon: const Icon(Icons.close_rounded),
              ),
      ),
    );
  }
}

class _PromotionCountryFilters extends StatelessWidget {
  const _PromotionCountryFilters({
    required this.countries,
    required this.selectedCountry,
    required this.onSelected,
  });

  final List<PromotionCountryFacet> countries;
  final String? selectedCountry;
  final ValueChanged<String?> onSelected;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          AppStrings.country,
          style: const TextStyle(
            color: AppTheme.mutedText,
            fontSize: 12,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 8),
        _HorizontalWheelScrollView(
          child: Row(
            children: [
              ChoiceChip(
                selected: selectedCountry == null,
                label: Text(
                  AppStrings.select(
                    en: 'All countries',
                    ru: 'Р’СЃРµ СЃС‚СЂР°РЅС‹',
                    uz: 'Barcha mamlakatlar',
                  ),
                ),
                onSelected: (_) => onSelected(null),
              ),
              const SizedBox(width: 8),
              for (final country in countries) ...[
                ChoiceChip(
                  selected: selectedCountry == country.id,
                  label: Text(country.name),
                  onSelected: (_) => onSelected(country.id),
                ),
                const SizedBox(width: 8),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _PromotionStoreFilters extends StatelessWidget {
  const _PromotionStoreFilters({
    required this.stores,
    required this.selectedStores,
    required this.onSelected,
  });

  final List<String> stores;
  final Set<String> selectedStores;
  final ValueChanged<String?> onSelected;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          AppStrings.select(en: 'Store', ru: 'РњР°РіР°Р·РёРЅ', uz: 'DoвЂkon'),
          style: const TextStyle(
            color: AppTheme.mutedText,
            fontSize: 12,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 8),
        _HorizontalWheelScrollView(
          child: Row(
            children: [
              ChoiceChip(
                selected: selectedStores.isEmpty,
                label: Text(
                  AppStrings.select(
                    en: 'All stores',
                    ru: 'Р’СЃРµ РјР°РіР°Р·РёРЅС‹',
                    uz: 'Barcha doвЂkonlar',
                  ),
                ),
                onSelected: (_) => onSelected(null),
              ),
              const SizedBox(width: 8),
              for (final store in stores) ...[
                ChoiceChip(
                  selected: selectedStores.contains(store),
                  label: Text(store),
                  onSelected: (_) => onSelected(store),
                ),
                const SizedBox(width: 8),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _PromotionTypeFilters extends StatelessWidget {
  const _PromotionTypeFilters({
    required this.selectedType,
    required this.onSelected,
  });

  final String? selectedType;
  final ValueChanged<String?> onSelected;

  @override
  Widget build(BuildContext context) {
    final options = <_PromoFilterOption>[
      _PromoFilterOption(
        null,
        AppStrings.select(en: 'All', ru: 'Р’СЃРµ', uz: 'Hammasi'),
      ),
      _PromoFilterOption(
        'coupon',
        AppStrings.select(
          en: 'Codes',
          ru: 'РџСЂРѕРјРѕРєРѕРґС‹',
          uz: 'Promokodlar',
        ),
      ),
      _PromoFilterOption(
        'sale',
        AppStrings.select(
          en: 'Sales',
          ru: 'Р Р°СЃРїСЂРѕРґР°Р¶Рё',
          uz: 'Aksiyalar',
        ),
      ),
      _PromoFilterOption(
        'flash_sale',
        AppStrings.select(en: 'Urgent', ru: 'РЎСЂРѕС‡РЅРѕ', uz: 'Shoshilinch'),
      ),
    ];

    return _HorizontalWheelScrollView(
      child: Row(
        children: [
          for (final option in options) ...[
            ChoiceChip(
              selected: selectedType == option.type,
              label: Text(option.label),
              onSelected: (_) => onSelected(option.type),
            ),
            const SizedBox(width: 8),
          ],
        ],
      ),
    );
  }
}

class _PromoFilterOption {
  const _PromoFilterOption(this.type, this.label);

  final String? type;
  final String label;
}

class _PromotionCard extends StatelessWidget {
  const _PromotionCard({
    required this.promotion,
    required this.onOpen,
    required this.onCopyCode,
  });

  final Promotion promotion;
  final VoidCallback? onOpen;
  final VoidCallback? onCopyCode;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Colors.white, AppTheme.softBlue.withValues(alpha: 0.32)],
        ),
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: AppTheme.line),
        boxShadow: AppTheme.cardShadow,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _PromotionVisual(promotion: promotion),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: 8,
                      runSpacing: 6,
                      children: [
                        _PromotionBadge(label: _typeLabel(promotion.type)),
                        if (promotion.featured)
                          _PromotionBadge(
                            label: AppStrings.select(
                              en: 'Featured',
                              ru: 'Р›СѓС‡С€РµРµ',
                              uz: 'Tanlangan',
                            ),
                            isAccent: true,
                          ),
                        if (promotion.isFlashSale)
                          _PromotionBadge(
                            label: AppStrings.select(
                              en: 'Ends soon',
                              ru: 'РЎРєРѕСЂРѕ Р·Р°РєРѕРЅС‡РёС‚СЃСЏ',
                              uz: 'Tez tugaydi',
                            ),
                            isWarning: true,
                          ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.72),
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(color: AppTheme.line),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.storefront_rounded,
                            size: 14,
                            color: AppTheme.primary,
                          ),
                          const SizedBox(width: 6),
                          Flexible(
                            child: Text(
                              promotion.store,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: AppTheme.primary,
                                fontSize: 13,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            promotion.title,
            style: const TextStyle(
              color: AppTheme.text,
              fontSize: 19,
              fontWeight: FontWeight.w900,
              height: 1.15,
              letterSpacing: -0.25,
            ),
          ),
          if (promotion.discountText.trim().isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              promotion.discountText,
              style: const TextStyle(
                color: AppTheme.secondary,
                fontSize: 15,
                fontWeight: FontWeight.w900,
              ),
            ),
          ],
          if (promotion.description.trim().isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              promotion.description,
              style: const TextStyle(
                color: AppTheme.mutedText,
                fontSize: 13.5,
                fontWeight: FontWeight.w600,
                height: 1.35,
              ),
            ),
          ],
          if (promotion.hasCode) ...[
            const SizedBox(height: 14),
            _PromoCodeBox(code: promotion.code!.trim(), onCopy: onCopyCode),
          ],
          if (promotion.validUntil != null) ...[
            const SizedBox(height: 12),
            _DeadlineLine(validUntil: promotion.validUntil!),
          ],
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: onOpen,
            icon: const Icon(Icons.open_in_new_rounded),
            label: Text(
              AppStrings.select(
                en: 'Open promo',
                ru: 'РћС‚РєСЂС‹С‚СЊ Р°РєС†РёСЋ',
                uz: 'Aksiyani ochish',
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _typeLabel(String type) {
    switch (type) {
      case 'coupon':
        return AppStrings.select(
          en: 'Promo code',
          ru: 'РџСЂРѕРјРѕРєРѕРґ',
          uz: 'Promokod',
        );
      case 'flash_sale':
        return AppStrings.select(
          en: 'Urgent sale',
          ru: 'РЎСЂРѕС‡РЅР°СЏ Р°РєС†РёСЏ',
          uz: 'Shoshilinch aksiya',
        );
      default:
        return AppStrings.select(
          en: 'Sale',
          ru: 'Р Р°СЃРїСЂРѕРґР°Р¶Р°',
          uz: 'Aksiya',
        );
    }
  }
}

class _PromotionVisual extends StatelessWidget {
  const _PromotionVisual({required this.promotion});

  final Promotion promotion;

  @override
  Widget build(BuildContext context) {
    final initials = _storeInitials(promotion.store);
    final icon = _promotionIcon(promotion.type);

    return Container(
      width: 66,
      height: 66,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            AppTheme.primaryLight.withValues(alpha: 0.24),
            AppTheme.primary.withValues(alpha: 0.10),
          ],
        ),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.12)),
        borderRadius: BorderRadius.circular(22),
      ),
      child: Stack(
        children: [
          Positioned(
            right: -12,
            top: -14,
            child: Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withValues(alpha: 0.30),
              ),
            ),
          ),
          Center(
            child: Text(
              initials,
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.fade,
              softWrap: false,
              style: const TextStyle(
                color: AppTheme.primary,
                fontSize: 17,
                fontWeight: FontWeight.w900,
                letterSpacing: -0.2,
              ),
            ),
          ),
          Positioned(
            right: 6,
            bottom: 6,
            child: Container(
              width: 24,
              height: 24,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.94),
                borderRadius: BorderRadius.circular(9),
                border: Border.all(color: AppTheme.line),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.06),
                    blurRadius: 8,
                    offset: const Offset(0, 3),
                  ),
                ],
              ),
              child: Icon(icon, color: AppTheme.primary, size: 15),
            ),
          ),
        ],
      ),
    );
  }

  String _storeInitials(String store) {
    final words = store
        .trim()
        .split(RegExp(r'\s+'))
        .where((word) => word.isNotEmpty)
        .toList(growable: false);
    if (words.isEmpty) return 'DH';
    if (words.length == 1) {
      final word = words.first;
      return String.fromCharCodes(word.runes.take(2)).toUpperCase();
    }
    return words
        .take(2)
        .map((word) => String.fromCharCode(word.runes.first))
        .join()
        .toUpperCase();
  }
}

IconData _promotionIcon(String type) {
  return switch (type) {
    'coupon' => Icons.confirmation_number_rounded,
    'flash_sale' => Icons.bolt_rounded,
    _ => Icons.local_mall_rounded,
  };
}

class _HorizontalWheelScrollView extends StatefulWidget {
  const _HorizontalWheelScrollView({required this.child});

  final Widget child;

  @override
  State<_HorizontalWheelScrollView> createState() =>
      _HorizontalWheelScrollViewState();
}

class _HorizontalWheelScrollViewState
    extends State<_HorizontalWheelScrollView> {
  final ScrollController _controller = ScrollController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Listener(
      onPointerSignal: (signal) {
        if (signal is! PointerScrollEvent || !_controller.hasClients) return;
        final horizontalDelta = signal.scrollDelta.dx;
        final verticalDelta = signal.scrollDelta.dy;
        final delta = horizontalDelta.abs() > verticalDelta.abs()
            ? horizontalDelta
            : verticalDelta;
        if (delta == 0) return;

        final position = _controller.position;
        final target = (_controller.offset + delta)
            .clamp(position.minScrollExtent, position.maxScrollExtent)
            .toDouble();
        if (target == _controller.offset) return;
        _controller.jumpTo(target);
      },
      child: ScrollConfiguration(
        behavior: const _HorizontalDragScrollBehavior(),
        child: SingleChildScrollView(
          controller: _controller,
          scrollDirection: Axis.horizontal,
          physics: const ClampingScrollPhysics(),
          child: widget.child,
        ),
      ),
    );
  }
}

class _HorizontalDragScrollBehavior extends MaterialScrollBehavior {
  const _HorizontalDragScrollBehavior();

  @override
  Set<PointerDeviceKind> get dragDevices => {
    ...super.dragDevices,
    PointerDeviceKind.mouse,
  };
}

class _PromotionBadge extends StatelessWidget {
  const _PromotionBadge({
    required this.label,
    this.isAccent = false,
    this.isWarning = false,
  });

  final String label;
  final bool isAccent;
  final bool isWarning;

  @override
  Widget build(BuildContext context) {
    final color = isWarning
        ? AppTheme.amber
        : isAccent
        ? AppTheme.secondary
        : AppTheme.primary;
    final background = isWarning
        ? const Color(0xFFFFF7E6)
        : isAccent
        ? AppTheme.softGreen
        : AppTheme.softBlue;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _PromoCodeBox extends StatelessWidget {
  const _PromoCodeBox({required this.code, required this.onCopy});

  final String code;
  final VoidCallback? onCopy;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 10, 8, 10),
      decoration: BoxDecoration(
        color: AppTheme.surfaceSoft,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppTheme.line),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              code,
              style: const TextStyle(
                color: AppTheme.text,
                fontSize: 16,
                fontWeight: FontWeight.w900,
                letterSpacing: 0.7,
              ),
            ),
          ),
          TextButton.icon(
            onPressed: onCopy,
            icon: const Icon(Icons.copy_rounded, size: 18),
            label: Text(
              AppStrings.select(
                en: 'Copy',
                ru: 'РљРѕРїРёСЂРѕРІР°С‚СЊ',
                uz: 'Nusxalash',
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DeadlineLine extends StatelessWidget {
  const _DeadlineLine({required this.validUntil});

  final DateTime validUntil;

  @override
  Widget build(BuildContext context) {
    final local = validUntil.toLocal();
    final date =
        '${local.day.toString().padLeft(2, '0')}.${local.month.toString().padLeft(2, '0')}.${local.year}';

    return Row(
      children: [
        const Icon(Icons.schedule_rounded, size: 18, color: AppTheme.mutedText),
        const SizedBox(width: 7),
        Expanded(
          child: Text(
            AppStrings.select(
              en: 'Valid until $date',
              ru: 'Р”РµР№СЃС‚РІСѓРµС‚ РґРѕ $date',
              uz: '$date gacha amal qiladi',
            ),
            style: const TextStyle(
              color: AppTheme.mutedText,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ],
    );
  }
}

class _PromotionStatusCard extends StatelessWidget {
  const _PromotionStatusCard({
    required this.icon,
    required this.title,
    required this.message,
    required this.onRetry,
  });

  final IconData icon;
  final String title;
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: AppTheme.line),
        boxShadow: AppTheme.cardShadow,
      ),
      child: Column(
        children: [
          Icon(icon, color: AppTheme.primary, size: 42),
          const SizedBox(height: 12),
          Text(
            title,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: AppTheme.text,
              fontSize: 18,
              fontWeight: FontWeight.w900,
              letterSpacing: -0.2,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            message,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: AppTheme.mutedText,
              fontSize: 13.5,
              fontWeight: FontWeight.w600,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh_rounded),
            label: Text(
              AppStrings.select(
                en: 'Refresh',
                ru: 'РћР±РЅРѕРІРёС‚СЊ',
                uz: 'Yangilash',
              ),
            ),
          ),
        ],
      ),
    );
  }
}
