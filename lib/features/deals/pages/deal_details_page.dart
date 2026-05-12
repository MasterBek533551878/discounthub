import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../app/app_theme.dart';
import '../../favorites/favorites_store.dart';
import '../../settings/app_strings.dart';
import '../../settings/settings_store.dart';
import '../models/deal.dart';
import '../utils/deal_insights.dart';

class DealDetailsPage extends StatelessWidget {
  const DealDetailsPage({
    super.key,
    required this.deal,
  });

  final Deal deal;

  Uri _clickUrl() {
    final baseUrl = Uri.parse(UserSettingsStore.apiBaseUrl.value);
    final normalizedBasePath = baseUrl.path.endsWith('/')
        ? baseUrl.path.substring(0, baseUrl.path.length - 1)
        : baseUrl.path;

    return baseUrl.replace(
      path:
          '$normalizedBasePath/deals/${Uri.encodeComponent(deal.id)}/click',
      queryParameters: null,
    );
  }

  Future<void> _openDeal(BuildContext context) async {
    final opened = await launchUrl(
      _clickUrl(),
      mode: LaunchMode.externalApplication,
    );

    if (!opened && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppStrings.couldNotOpenLink)),
      );
    }
  }

  Future<void> _shareDeal(BuildContext context) async {
    await Clipboard.setData(ClipboardData(text: _clickUrl().toString()));

    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(AppStrings.linkCopied)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final title = AppStrings.demoDealTitle(deal.id, deal.title);
    final score = DealInsights.score(deal);
    final isHotDeal = DealInsights.isHotDeal(deal);
    final isLowestPrice = DealInsights.isLowestPriceCandidate(deal);
    final shipsToCountry = DealInsights.shipsToSelectedCountry(deal);

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            pinned: true,
            backgroundColor: AppTheme.background,
            surfaceTintColor: AppTheme.background,
            actions: [
              IconButton.filledTonal(
                tooltip: AppStrings.share,
                onPressed: () => _shareDeal(context),
                icon: const Icon(Icons.share_rounded),
              ),
              const SizedBox(width: 8),
              ValueListenableBuilder<Set<String>>(
                valueListenable: FavoritesStore.ids,
                builder: (context, ids, _) {
                  final isFavorite = ids.contains(deal.id);

                  return IconButton.filledTonal(
                    onPressed: () => FavoritesStore.toggle(deal.id),
                    icon: Icon(
                      isFavorite
                          ? Icons.favorite_rounded
                          : Icons.favorite_border_rounded,
                      color: isFavorite ? AppTheme.dealRed : AppTheme.text,
                    ),
                  );
                },
              ),
              const SizedBox(width: 8),
            ],
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 14, 20, 32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _ProductImageCard(deal: deal),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _InfoBadge(
                        icon: Icons.storefront_rounded,
                        label: deal.platform,
                      ),
                      _InfoBadge(
                        icon: Icons.category_rounded,
                        label: AppStrings.categoryName(deal.category),
                      ),
                      if (isHotDeal)
                        _InfoBadge(
                          icon: Icons.local_fire_department_rounded,
                          label: AppStrings.hotDeal,
                        ),
                      if (isLowestPrice)
                        _InfoBadge(
                          icon: Icons.trending_down_rounded,
                          label: AppStrings.lowestPrice,
                        ),
                      if (deal.verified)
                        _InfoBadge(
                          icon: Icons.verified_rounded,
                          label: AppStrings.verifiedDeal,
                        ),
                      if (deal.freeShipping)
                        _InfoBadge(
                          icon: Icons.local_shipping_rounded,
                          label: AppStrings.freeShipping,
                        ),
                      if (shipsToCountry)
                        _InfoBadge(
                          icon: Icons.public_rounded,
                          label: AppStrings.shipsToYourCountry,
                        ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  Text(
                    title,
                    style: const TextStyle(
                      color: AppTheme.text,
                      fontSize: 26,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -0.6,
                      height: 1.08,
                    ),
                  ),
                  const SizedBox(height: 18),
                  _PriceCard(deal: deal),
                  const SizedBox(height: 16),
                  _ScoreCard(score: score),
                  const SizedBox(height: 16),
                  _DetailsSection(deal: deal),
                ],
              ),
            ),
          ),
        ],
      ),
      bottomNavigationBar: _DealBottomBar(
        platform: deal.platform,
        onPressed: () => _openDeal(context),
      ),
    );
  }
}

class _ProductImageCard extends StatelessWidget {
  const _ProductImageCard({required this.deal});

  final Deal deal;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: AppTheme.line),
        boxShadow: AppTheme.cardShadow,
      ),
      child: Stack(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(26),
            child: AspectRatio(
              aspectRatio: 1.18,
              child: Container(
                color: Colors.white,
                padding: const EdgeInsets.all(10),
                child: CachedNetworkImage(
                  imageUrl: deal.imageUrl,
                  fit: BoxFit.contain,
                  placeholder: (context, url) => Container(
                    color: const Color(0xFFF2F5FA),
                    child: const Center(
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  ),
                  errorWidget: (context, url, error) => Container(
                    color: const Color(0xFFF2F5FA),
                    child: const Icon(
                      Icons.image_not_supported_outlined,
                      size: 48,
                      color: AppTheme.mutedText,
                    ),
                  ),
                ),
              ),
            ),
          ),
          Positioned(
            left: 12,
            bottom: 12,
            child: _DiscountPill(percent: deal.discountPercent),
          ),
        ],
      ),
    );
  }
}

class _DiscountPill extends StatelessWidget {
  const _DiscountPill({required this.percent});

  final int percent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
      decoration: BoxDecoration(
        color: AppTheme.secondary,
        borderRadius: BorderRadius.circular(999),
        boxShadow: [
          BoxShadow(
            color: AppTheme.navy.withValues(alpha: 0.16),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Text(
        '-$percent%',
        style: const TextStyle(
          color: Colors.white,
          fontSize: 16,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

class _DealBottomBar extends StatelessWidget {
  const _DealBottomBar({
    required this.platform,
    required this.onPressed,
  });

  final String platform;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 14, 20, 20),
      decoration: BoxDecoration(
        color: Colors.white,
        border: const Border(top: BorderSide(color: AppTheme.line)),
        boxShadow: [
          BoxShadow(
            color: AppTheme.navy.withValues(alpha: 0.05),
            blurRadius: 22,
            offset: const Offset(0, -8),
          ),
        ],
      ),
      child: SafeArea(
        child: FilledButton.icon(
          onPressed: onPressed,
          icon: const Icon(Icons.open_in_new_rounded),
          label: Text(AppStrings.openOn(platform)),
        ),
      ),
    );
  }
}

class _PriceCard extends StatelessWidget {
  const _PriceCard({required this.deal});

  final Deal deal;

  @override
  Widget build(BuildContext context) {
    return _SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            AppStrings.dealPrice,
            style: const TextStyle(
              color: AppTheme.mutedText,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 10),
          Wrap(
            crossAxisAlignment: WrapCrossAlignment.end,
            spacing: 10,
            runSpacing: 6,
            children: [
              Text(
                UserSettingsStore.formatUsd(deal.currentPrice),
                style: const TextStyle(
                  color: AppTheme.primary,
                  fontSize: 34,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -0.9,
                ),
              ),
              if (deal.oldPrice > 0)
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(
                    UserSettingsStore.formatUsd(deal.oldPrice),
                    style: const TextStyle(
                      color: AppTheme.mutedText,
                      fontSize: 16,
                      decoration: TextDecoration.lineThrough,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              if (deal.savedAmount > 0)
                _SoftBadge(
                  label: AppStrings.saveAmount(
                    UserSettingsStore.formatUsd(deal.savedAmount),
                  ),
                  color: AppTheme.secondary,
                  backgroundColor: AppTheme.softGreen,
                ),
              _SoftBadge(
                label: '-${deal.discountPercent}%',
                color: AppTheme.dealRed,
                backgroundColor: AppTheme.softRed,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ScoreCard extends StatelessWidget {
  const _ScoreCard({required this.score});

  final int score;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFFEEF4FF), Colors.white],
        ),
        borderRadius: BorderRadius.circular(26),
        border: Border.all(color: const Color(0xFFD9E6FF)),
        boxShadow: AppTheme.cardShadow,
      ),
      child: Row(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(20),
            ),
            child: const Icon(Icons.speed_rounded, color: AppTheme.primary),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  AppStrings.dealScoreTitle,
                  style: const TextStyle(
                    color: AppTheme.text,
                    fontSize: 16,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  AppStrings.dealScore(score),
                  style: const TextStyle(
                    color: AppTheme.mutedText,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          Text(
            '$score',
            style: const TextStyle(
              color: AppTheme.primary,
              fontSize: 36,
              fontWeight: FontWeight.w900,
              height: 1,
            ),
          ),
        ],
      ),
    );
  }
}

class _DetailsSection extends StatelessWidget {
  const _DetailsSection({required this.deal});

  final Deal deal;

  @override
  Widget build(BuildContext context) {
    final rows = <Widget>[];

    if (deal.rating > 0 && deal.reviewCount > 0) {
      rows.add(
        _DetailRow(
          icon: Icons.star_rounded,
          title: AppStrings.rating,
          value: '${deal.rating.toStringAsFixed(1)} / 5 (${deal.reviewCount})',
        ),
      );
    }

    final shippingCountries = deal.shipsTo
        .where((item) => item.trim().isNotEmpty)
        .toList();
    if (shippingCountries.isNotEmpty) {
      if (rows.isNotEmpty) rows.add(const Divider(height: 24));
      rows.add(
        _DetailRow(
          icon: Icons.public_rounded,
          title: AppStrings.shipsTo,
          value: shippingCountries.join(', '),
        ),
      );
    }

    if (rows.isNotEmpty) rows.add(const Divider(height: 24));
    rows.add(
      _DetailRow(
        icon: Icons.local_shipping_rounded,
        title: AppStrings.shipping,
        value: deal.freeShipping
            ? AppStrings.freeShippingAvailable
            : AppStrings.shippingFeeMayApply,
      ),
    );

    return _SurfaceCard(
      child: Column(children: rows),
    );
  }
}

class _SurfaceCard extends StatelessWidget {
  const _SurfaceCard({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(26),
        border: Border.all(color: AppTheme.line),
        boxShadow: AppTheme.cardShadow,
      ),
      child: child,
    );
  }
}

class _InfoBadge extends StatelessWidget {
  const _InfoBadge({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: AppTheme.line),
        boxShadow: AppTheme.cardShadow,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: AppTheme.primary),
          const SizedBox(width: 6),
          Text(
            label,
            style: const TextStyle(
              color: AppTheme.text,
              fontSize: 13,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _SoftBadge extends StatelessWidget {
  const _SoftBadge({
    required this.label,
    required this.color,
    required this.backgroundColor,
  });

  final String label;
  final Color color;
  final Color backgroundColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontWeight: FontWeight.w900),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.icon,
    required this.title,
    required this.value,
  });

  final IconData icon;
  final String title;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
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
        const SizedBox(width: 12),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              title,
              style: const TextStyle(
                color: AppTheme.mutedText,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ),
        const SizedBox(width: 12),
        Flexible(
          child: Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              value,
              textAlign: TextAlign.end,
              style: const TextStyle(
                color: AppTheme.text,
                fontWeight: FontWeight.w900,
                height: 1.25,
              ),
            ),
          ),
        ),
      ],
    );
  }
}
