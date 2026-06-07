import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../app/app_theme.dart';
import '../../settings/app_strings.dart';
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
  List<String> _knownStores = const <String>[];
  Timer? _searchDebounce;

  @override
  void initState() {
    super.initState();
    _future = _loadPromotions();
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  Future<PromotionsLoadResult> _loadPromotions() async {
    final result = await _repository.loadPromotions(
      query: _searchController.text,
      type: _selectedType,
      stores: _selectedStores.toList(growable: false),
    );
    _rememberStores(result.promotions);
    return result;
  }

  void _rememberStores(List<Promotion> promotions) {
    final stores = List<String>.of(_knownStores);
    for (final promotion in promotions) {
      final store = promotion.store.trim();
      if (store.isEmpty) continue;
      final exists = stores.any((value) => value.toLowerCase() == store.toLowerCase());
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

  Future<void> _refresh() async {
    final future = _loadPromotions();
    setState(() => _future = future);
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
      setState(() => _future = _loadPromotions());
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

  Future<void> _openPromotion(PromotionsLoadResult result, Promotion promotion) async {
    final url = _repository.clickUri(
      promotionId: promotion.id,
      baseUrl: result.baseUrl,
    );
    final opened = await launchUrl(url, mode: LaunchMode.externalApplication);
    if (!mounted) return;
    if (!opened) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppStrings.couldNotOpenLink)),
      );
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
            ru: 'Промокод скопирован',
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
          AppStrings.select(
            en: 'Promos',
            ru: 'Акции',
            uz: 'Aksiyalar',
          ),
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
                    setState(() => _future = _loadPromotions());
                  },
                ),
                const SizedBox(height: 12),
                _PromotionTypeFilters(
                  selectedType: _selectedType,
                  onSelected: _setType,
                ),
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
                      ru: 'Акции пока недоступны',
                      uz: 'Aksiyalar hozircha mavjud emas',
                    ),
                    message: AppStrings.select(
                      en: 'The app is ready for promo codes and store sales. Connect the backend promotions source to fill this tab.',
                      ru: 'Раздел уже готов для промокодов и распродаж. Подключите backend-источник акций, чтобы заполнить эту вкладку.',
                      uz: 'Ilova promokodlar va do‘kon aksiyalari uchun tayyor. Bu bo‘limni to‘ldirish uchun backend manbasini ulang.',
                    ),
                    onRetry: () => setState(() => _future = _loadPromotions()),
                  ),
                ] else if (!isLoading && promotions.isEmpty) ...[
                  const SizedBox(height: 18),
                  _PromotionStatusCard(
                    icon: Icons.local_offer_outlined,
                    title: AppStrings.select(
                      en: 'No live promos right now',
                      ru: 'Сейчас нет активных акций',
                      uz: 'Hozir faol aksiyalar yo‘q',
                    ),
                    message: AppStrings.select(
                      en: 'When promo codes, sales or short-time campaigns are imported, they will appear here.',
                      ru: 'Когда импортируются промокоды, распродажи или срочные акции, они появятся здесь.',
                      uz: 'Promokodlar, chegirmali savdolar yoki qisqa muddatli aksiyalar import qilinganda shu yerda ko‘rinadi.',
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
        ? AppStrings.select(en: 'Promo codes and sales', ru: 'Промокоды и распродажи', uz: 'Promokodlar va aksiyalar')
        : AppStrings.select(en: '$totalCount live promos', ru: '$totalCount активных акций', uz: '$totalCount ta faol aksiya');

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
                    ru: 'Общие акции магазинов, промокоды и срочные распродажи в одном месте.',
                    uz: 'Do‘kon aksiyalari, promokodlar va qisqa muddatli chegirmalar bir joyda.',
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
          ru: 'Поиск акций или магазинов',
          uz: 'Aksiya yoki do‘kon qidirish',
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
          AppStrings.select(en: 'Store', ru: 'Магазин', uz: 'Do‘kon'),
          style: const TextStyle(
            color: AppTheme.mutedText,
            fontSize: 12,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 8),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              ChoiceChip(
                selected: selectedStores.isEmpty,
                label: Text(
                  AppStrings.select(
                    en: 'All stores',
                    ru: 'Все магазины',
                    uz: 'Barcha do‘konlar',
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
      _PromoFilterOption(null, AppStrings.select(en: 'All', ru: 'Все', uz: 'Hammasi')),
      _PromoFilterOption('coupon', AppStrings.select(en: 'Codes', ru: 'Промокоды', uz: 'Promokodlar')),
      _PromoFilterOption('sale', AppStrings.select(en: 'Sales', ru: 'Распродажи', uz: 'Aksiyalar')),
      _PromoFilterOption('flash_sale', AppStrings.select(en: 'Urgent', ru: 'Срочно', uz: 'Shoshilinch')),
    ];

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
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
        color: Colors.white,
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
              _PromotionIcon(type: promotion.type),
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
                            label: AppStrings.select(en: 'Featured', ru: 'Лучшее', uz: 'Tanlangan'),
                            isAccent: true,
                          ),
                        if (promotion.isFlashSale)
                          _PromotionBadge(
                            label: AppStrings.select(en: 'Ends soon', ru: 'Скоро закончится', uz: 'Tez tugaydi'),
                            isWarning: true,
                          ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      promotion.store,
                      style: const TextStyle(
                        color: AppTheme.primary,
                        fontSize: 13,
                        fontWeight: FontWeight.w900,
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
                ru: 'Открыть акцию',
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
        return AppStrings.select(en: 'Promo code', ru: 'Промокод', uz: 'Promokod');
      case 'flash_sale':
        return AppStrings.select(en: 'Urgent sale', ru: 'Срочная акция', uz: 'Shoshilinch aksiya');
      default:
        return AppStrings.select(en: 'Sale', ru: 'Распродажа', uz: 'Aksiya');
    }
  }
}

class _PromotionIcon extends StatelessWidget {
  const _PromotionIcon({required this.type});

  final String type;

  @override
  Widget build(BuildContext context) {
    final icon = switch (type) {
      'coupon' => Icons.confirmation_number_rounded,
      'flash_sale' => Icons.bolt_rounded,
      _ => Icons.local_mall_rounded,
    };

    return Container(
      width: 50,
      height: 50,
      decoration: BoxDecoration(
        color: AppTheme.softBlue,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppTheme.line),
      ),
      child: Icon(icon, color: AppTheme.primary),
    );
  }
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
              AppStrings.select(en: 'Copy', ru: 'Копировать', uz: 'Nusxalash'),
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
    final date = '${local.day.toString().padLeft(2, '0')}.${local.month.toString().padLeft(2, '0')}.${local.year}';

    return Row(
      children: [
        const Icon(Icons.schedule_rounded, size: 18, color: AppTheme.mutedText),
        const SizedBox(width: 7),
        Expanded(
          child: Text(
            AppStrings.select(
              en: 'Valid until $date',
              ru: 'Действует до $date',
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
              AppStrings.select(en: 'Refresh', ru: 'Обновить', uz: 'Yangilash'),
            ),
          ),
        ],
      ),
    );
  }
}
