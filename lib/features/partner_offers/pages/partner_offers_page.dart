import 'dart:async';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../app/app_theme.dart';
import '../../settings/app_strings.dart';
import '../api/partner_offers_api_client.dart';
import '../data/partner_offers_repository.dart';
import '../models/partner_offer.dart';

class PartnerOffersPage extends StatefulWidget {
  const PartnerOffersPage({super.key});

  @override
  State<PartnerOffersPage> createState() => _PartnerOffersPageState();
}

class _PartnerOffersPageState extends State<PartnerOffersPage> {
  final PartnerOffersRepository _repository = PartnerOffersRepository.instance;
  final TextEditingController _searchController = TextEditingController();

  Future<PartnerOffersLoadResult>? _future;
  String? _selectedCategory;
  List<PartnerOfferCategoryFacet> _knownCategories = const <PartnerOfferCategoryFacet>[];
  Timer? _searchDebounce;

  @override
  void initState() {
    super.initState();
    _future = _loadOffers();
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  Future<PartnerOffersLoadResult> _loadOffers() async {
    final result = await _repository.loadOffers(
      query: _searchController.text,
      category: _selectedCategory,
    );
    _rememberCategories(result.categories);
    return result;
  }

  void _rememberCategories(List<PartnerOfferCategoryFacet> categories) {
    final merged = List<PartnerOfferCategoryFacet>.of(_knownCategories);
    for (final category in categories) {
      final id = category.id.trim();
      if (id.isEmpty) continue;
      final index = merged.indexWhere((value) => value.id.toLowerCase() == id.toLowerCase());
      if (index >= 0) {
        merged[index] = category;
      } else {
        merged.add(category);
      }
    }

    merged.sort((a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()));
    var unchanged = merged.length == _knownCategories.length;
    if (unchanged) {
      for (var index = 0; index < merged.length; index += 1) {
        if (merged[index].id != _knownCategories[index].id ||
            merged[index].count != _knownCategories[index].count) {
          unchanged = false;
          break;
        }
      }
    }
    if (unchanged || !mounted) return;
    setState(() => _knownCategories = List.unmodifiable(merged));
  }

  Future<void> _refresh() async {
    final future = _loadOffers();
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
      setState(() => _future = _loadOffers());
    });
  }

  void _setCategory(String? category) {
    if (_selectedCategory == category) return;
    setState(() {
      _selectedCategory = category;
      _future = _loadOffers();
    });
  }

  Future<void> _openOffer(PartnerOffersLoadResult result, PartnerOffer offer) async {
    final url = _repository.clickUri(
      offerId: offer.id,
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

  Future<void> _copyCode(PartnerOffer offer) async {
    final code = offer.code?.trim();
    if (code == null || code.isEmpty) return;
    await Clipboard.setData(ClipboardData(text: code));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          AppStrings.select(
            en: 'Partner code copied',
            ru: 'Код партнёра скопирован',
            uz: 'Hamkor kodi nusxalandi',
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
            en: 'Partners',
            ru: 'Партнёры',
            uz: 'Hamkorlar',
          ),
        ),
      ),
      body: FutureBuilder<PartnerOffersLoadResult>(
        future: _future,
        builder: (context, snapshot) {
          final result = snapshot.data;
          final offers = result?.offers ?? const <PartnerOffer>[];
          final isLoading = snapshot.connectionState != ConnectionState.done;

          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 28),
              children: [
                _PartnerOffersHero(totalCount: result?.totalCount),
                const SizedBox(height: 14),
                _PartnerSearchField(
                  controller: _searchController,
                  onChanged: _onSearchChanged,
                  onClear: () {
                    _searchController.clear();
                    setState(() => _future = _loadOffers());
                  },
                ),
                if (_knownCategories.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  _PartnerCategoryFilters(
                    categories: _knownCategories,
                    selectedCategory: _selectedCategory,
                    onSelected: _setCategory,
                  ),
                ],
                if (isLoading) ...[
                  const SizedBox(height: 16),
                  const LinearProgressIndicator(minHeight: 3),
                ],
                if (snapshot.hasError && !isLoading) ...[
                  const SizedBox(height: 18),
                  _PartnerStatusCard(
                    icon: Icons.cloud_off_rounded,
                    title: AppStrings.select(
                      en: 'Partner offers are not available yet',
                      ru: 'Партнёрские предложения пока недоступны',
                      uz: 'Hamkor takliflari hozircha mavjud emas',
                    ),
                    message: AppStrings.select(
                      en: 'The page is ready for curated partner deals. Add offers from the admin API to fill this tab.',
                      ru: 'Страница уже готова для ручных партнёрских офферов. Добавьте предложения через admin API.',
                      uz: 'Sahifa hamkor takliflari uchun tayyor. Takliflarni admin API orqali qo‘shing.',
                    ),
                    onRetry: () => setState(() => _future = _loadOffers()),
                  ),
                ] else if (!isLoading && offers.isEmpty) ...[
                  const SizedBox(height: 18),
                  _PartnerStatusCard(
                    icon: Icons.handshake_outlined,
                    title: AppStrings.select(
                      en: 'No partner offers right now',
                      ru: 'Сейчас нет партнёрских предложений',
                      uz: 'Hozir hamkor takliflari yo‘q',
                    ),
                    message: AppStrings.select(
                      en: 'Curated software, SaaS and startup deals will appear here.',
                      ru: 'Здесь появятся отобранные предложения от SaaS, DevTools и стартапов.',
                      uz: 'Bu yerda SaaS, DevTools va startap takliflari ko‘rinadi.',
                    ),
                    onRetry: () => setState(() => _future = _loadOffers()),
                  ),
                ] else ...[
                  const SizedBox(height: 18),
                  for (final offer in offers) ...[
                    _PartnerOfferCard(
                      offer: offer,
                      onOpen: result == null ? null : () => _openOffer(result, offer),
                      onCopyCode: offer.hasCode ? () => _copyCode(offer) : null,
                    ),
                    const SizedBox(height: 16),
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

class _PartnerOffersHero extends StatelessWidget {
  const _PartnerOffersHero({this.totalCount});

  final int? totalCount;

  @override
  Widget build(BuildContext context) {
    final countText = totalCount == null || totalCount == 0
        ? AppStrings.select(en: 'Curated partner deals', ru: 'Предложения партнёров', uz: 'Hamkor takliflari')
        : AppStrings.select(en: '$totalCount partner offers', ru: '$totalCount предложений партнёров', uz: '$totalCount ta hamkor taklifi');

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF101828), Color(0xFF2563FF), Color(0xFF7C3AED)],
        ),
        borderRadius: BorderRadius.circular(30),
        boxShadow: AppTheme.softShadow,
      ),
      child: Stack(
        children: [
          Positioned(
            right: -28,
            top: -28,
            child: Container(
              width: 112,
              height: 112,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withValues(alpha: 0.10),
              ),
            ),
          ),
          Row(
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.16),
                  borderRadius: BorderRadius.circular(22),
                  border: Border.all(color: Colors.white.withValues(alpha: 0.24)),
                ),
                child: const Icon(
                  Icons.handshake_rounded,
                  color: Colors.white,
                  size: 29,
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
                        en: 'Manual limited-time deals from SaaS, AI tools, DevTools and startup partners.',
                        ru: 'Ручные лимитированные офферы от SaaS, AI, DevTools и стартап-партнёров.',
                        uz: 'SaaS, AI, DevTools va startap hamkorlardan maxsus takliflar.',
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
        ],
      ),
    );
  }
}

class _PartnerSearchField extends StatelessWidget {
  const _PartnerSearchField({
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
          en: 'Search partners or tools',
          ru: 'Поиск партнёров или инструментов',
          uz: 'Hamkor yoki vosita qidirish',
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

class _PartnerCategoryFilters extends StatelessWidget {
  const _PartnerCategoryFilters({
    required this.categories,
    required this.selectedCategory,
    required this.onSelected,
  });

  final List<PartnerOfferCategoryFacet> categories;
  final String? selectedCategory;
  final ValueChanged<String?> onSelected;

  @override
  Widget build(BuildContext context) {
    return _HorizontalWheelScrollView(
      child: Row(
        children: [
          ChoiceChip(
            selected: selectedCategory == null,
            label: Text(AppStrings.select(en: 'All', ru: 'Все', uz: 'Hammasi')),
            onSelected: (_) => onSelected(null),
          ),
          const SizedBox(width: 8),
          for (final category in categories) ...[
            ChoiceChip(
              selected: selectedCategory == category.id,
              label: Text('${category.name} ${category.count > 0 ? category.count : ''}'.trim()),
              onSelected: (_) => onSelected(category.id),
            ),
            const SizedBox(width: 8),
          ],
        ],
      ),
    );
  }
}

class _PartnerOfferCard extends StatelessWidget {
  const _PartnerOfferCard({
    required this.offer,
    required this.onOpen,
    required this.onCopyCode,
  });

  final PartnerOffer offer;
  final VoidCallback? onOpen;
  final VoidCallback? onCopyCode;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: AppTheme.line),
        boxShadow: AppTheme.cardShadow,
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _PartnerOfferVisual(offer: offer),
          Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 6,
                  children: [
                    _PartnerBadge(label: _categoryLabel(offer.category)),
                    if (offer.featured)
                      _PartnerBadge(
                        label: AppStrings.select(en: 'Featured', ru: 'Лучшее', uz: 'Tanlangan'),
                        isAccent: true,
                      ),
                    if (offer.verified)
                      _PartnerBadge(
                        label: AppStrings.select(en: 'Verified', ru: 'Проверено', uz: 'Tekshirildi'),
                        isSuccess: true,
                      ),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    _PartnerLogo(offer: offer),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            offer.partnerName,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: AppTheme.primary,
                              fontSize: 13,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          if (offer.countries.trim().isNotEmpty)
                            Text(
                              offer.countries,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: AppTheme.mutedText,
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Text(
                  offer.title,
                  style: const TextStyle(
                    color: AppTheme.text,
                    fontSize: 21,
                    fontWeight: FontWeight.w900,
                    height: 1.12,
                    letterSpacing: -0.35,
                  ),
                ),
                if (offer.subtitle.trim().isNotEmpty) ...[
                  const SizedBox(height: 7),
                  Text(
                    offer.subtitle,
                    style: const TextStyle(
                      color: AppTheme.mutedText,
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      height: 1.35,
                    ),
                  ),
                ],
                if (offer.offerText.trim().isNotEmpty || offer.currentPriceText.trim().isNotEmpty) ...[
                  const SizedBox(height: 14),
                  _PartnerPriceStrip(offer: offer),
                ],
                if (offer.description.trim().isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text(
                    offer.description,
                    style: const TextStyle(
                      color: AppTheme.mutedText,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w600,
                      height: 1.38,
                    ),
                  ),
                ],
                if (offer.tags.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final tag in offer.tags.take(8)) _PartnerTag(label: tag),
                    ],
                  ),
                ],
                if (offer.hasCode) ...[
                  const SizedBox(height: 14),
                  _PartnerCodeBox(code: offer.code!.trim(), onCopy: onCopyCode),
                ],
                if (offer.validUntil != null) ...[
                  const SizedBox(height: 12),
                  _DeadlineLine(validUntil: offer.validUntil!),
                ],
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: onOpen,
                  icon: const Icon(Icons.open_in_new_rounded),
                  label: Text(
                    AppStrings.select(
                      en: 'Open partner offer',
                      ru: 'Открыть предложение',
                      uz: 'Taklifni ochish',
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _categoryLabel(String value) {
    final normalized = value.toLowerCase().replaceAll('_', '-');
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
        return value.replaceAll('_', ' ').trim().isEmpty
            ? AppStrings.select(en: 'Partner', ru: 'Партнёр', uz: 'Hamkor')
            : value.replaceAll('_', ' ');
    }
  }
}

class _PartnerOfferVisual extends StatelessWidget {
  const _PartnerOfferVisual({required this.offer});

  final PartnerOffer offer;

  @override
  Widget build(BuildContext context) {
    final imageUrl = offer.imageUrl?.trim();
    if (imageUrl != null && imageUrl.isNotEmpty) {
      return AspectRatio(
        aspectRatio: 16 / 8.5,
        child: CachedNetworkImage(
          imageUrl: imageUrl,
          fit: BoxFit.cover,
          errorWidget: (context, url, error) => _FallbackPartnerVisual(offer: offer),
          placeholder: (context, url) => _FallbackPartnerVisual(offer: offer, isLoading: true),
        ),
      );
    }

    return _FallbackPartnerVisual(offer: offer);
  }
}

class _FallbackPartnerVisual extends StatelessWidget {
  const _FallbackPartnerVisual({required this.offer, this.isLoading = false});

  final PartnerOffer offer;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 16 / 8.5,
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF0B1020), Color(0xFF1D4ED8), Color(0xFF16A34A)],
          ),
        ),
        child: Stack(
          children: [
            Positioned(
              right: -30,
              top: -36,
              child: Container(
                width: 122,
                height: 122,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.white.withValues(alpha: 0.10),
                ),
              ),
            ),
            Positioned(
              left: -26,
              bottom: -30,
              child: Container(
                width: 100,
                height: 100,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.white.withValues(alpha: 0.08),
                ),
              ),
            ),
            if (isLoading)
              const Center(child: CircularProgressIndicator(color: Colors.white))
            else
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.16),
                      borderRadius: BorderRadius.circular(999),
                      border: Border.all(color: Colors.white.withValues(alpha: 0.22)),
                    ),
                    child: Text(
                      offer.partnerName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    offer.currentPriceText.trim().isNotEmpty ? offer.currentPriceText : offer.offerText,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 26,
                      fontWeight: FontWeight.w900,
                      height: 1.04,
                      letterSpacing: -0.65,
                    ),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class _PartnerLogo extends StatelessWidget {
  const _PartnerLogo({required this.offer});

  final PartnerOffer offer;

  @override
  Widget build(BuildContext context) {
    final logoUrl = offer.logoUrl?.trim();
    if (logoUrl != null && logoUrl.isNotEmpty) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: CachedNetworkImage(
          imageUrl: logoUrl,
          width: 42,
          height: 42,
          fit: BoxFit.cover,
          errorWidget: (context, url, error) => _InitialsLogo(offer: offer),
          placeholder: (context, url) => _InitialsLogo(offer: offer),
        ),
      );
    }
    return _InitialsLogo(offer: offer);
  }
}

class _InitialsLogo extends StatelessWidget {
  const _InitialsLogo({required this.offer});

  final PartnerOffer offer;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 42,
      height: 42,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        gradient: AppTheme.brandGradient,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Text(
        _initials(offer.partnerName),
        maxLines: 1,
        overflow: TextOverflow.fade,
        softWrap: false,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 14,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }

  String _initials(String value) {
    final words = value
        .trim()
        .split(RegExp(r'\s+'))
        .where((word) => word.isNotEmpty)
        .toList(growable: false);
    if (words.isEmpty) return 'DH';
    if (words.length == 1) return String.fromCharCodes(words.first.runes.take(2)).toUpperCase();
    return words.take(2).map((word) => String.fromCharCode(word.runes.first)).join().toUpperCase();
  }
}

class _PartnerPriceStrip extends StatelessWidget {
  const _PartnerPriceStrip({required this.offer});

  final PartnerOffer offer;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.softBlue,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: AppTheme.primary.withValues(alpha: 0.10)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (offer.offerText.trim().isNotEmpty)
                  Text(
                    offer.offerText,
                    style: const TextStyle(
                      color: AppTheme.primary,
                      fontSize: 13,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                if (offer.currentPriceText.trim().isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    offer.currentPriceText,
                    style: const TextStyle(
                      color: AppTheme.text,
                      fontSize: 20,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -0.35,
                    ),
                  ),
                ],
              ],
            ),
          ),
          if (offer.originalPriceText.trim().isNotEmpty)
            Text(
              offer.originalPriceText,
              style: const TextStyle(
                color: AppTheme.mutedText,
                fontSize: 13,
                fontWeight: FontWeight.w800,
                decoration: TextDecoration.lineThrough,
              ),
            ),
        ],
      ),
    );
  }
}

class _PartnerBadge extends StatelessWidget {
  const _PartnerBadge({
    required this.label,
    this.isAccent = false,
    this.isSuccess = false,
  });

  final String label;
  final bool isAccent;
  final bool isSuccess;

  @override
  Widget build(BuildContext context) {
    final color = isSuccess
        ? AppTheme.secondary
        : isAccent
            ? const Color(0xFF7C3AED)
            : AppTheme.primary;
    final background = isSuccess
        ? AppTheme.softGreen
        : isAccent
            ? const Color(0xFFF3E8FF)
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

class _PartnerTag extends StatelessWidget {
  const _PartnerTag({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppTheme.surfaceSoft,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: AppTheme.line),
      ),
      child: Text(
        label,
        style: const TextStyle(
          color: AppTheme.mutedText,
          fontSize: 12,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _PartnerCodeBox extends StatelessWidget {
  const _PartnerCodeBox({required this.code, required this.onCopy});

  final String code;
  final VoidCallback? onCopy;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 10, 8, 10),
      decoration: BoxDecoration(
        color: const Color(0xFFFFFBEB),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFFDE68A)),
      ),
      child: Row(
        children: [
          const Icon(Icons.confirmation_number_rounded, color: AppTheme.amber, size: 19),
          const SizedBox(width: 9),
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
            label: Text(AppStrings.select(en: 'Copy', ru: 'Копировать', uz: 'Nusxalash')),
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

class _PartnerStatusCard extends StatelessWidget {
  const _PartnerStatusCard({
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
            label: Text(AppStrings.select(en: 'Refresh', ru: 'Обновить', uz: 'Yangilash')),
          ),
        ],
      ),
    );
  }
}

class _HorizontalWheelScrollView extends StatefulWidget {
  const _HorizontalWheelScrollView({required this.child});

  final Widget child;

  @override
  State<_HorizontalWheelScrollView> createState() => _HorizontalWheelScrollViewState();
}

class _HorizontalWheelScrollViewState extends State<_HorizontalWheelScrollView> {
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
        final delta = horizontalDelta.abs() > verticalDelta.abs() ? horizontalDelta : verticalDelta;
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
