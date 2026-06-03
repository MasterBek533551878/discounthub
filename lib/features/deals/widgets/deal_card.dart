import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../../app/app_theme.dart';
import '../../favorites/favorites_store.dart';
import '../../settings/app_strings.dart';
import '../../settings/settings_store.dart';
import '../models/deal.dart';
import '../utils/deal_insights.dart';

class DealCard extends StatelessWidget {
  const DealCard({
    super.key,
    required this.deal,
    required this.onTap,
  });

  final Deal deal;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<int>(
      valueListenable: UserSettingsStore.version,
      builder: (context, _, child) {
        final title = AppStrings.demoDealTitle(deal.id, deal.title);
        final isHotDeal = DealInsights.isHotDeal(deal);
        final shipsToCountry = DealInsights.shipsToSelectedCountry(deal);
        final freeShippingToCountry =
            DealInsights.hasFreeShippingToSelectedCountry(deal);

        return Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(28),
            onTap: onTap,
            child: Ink(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(28),
                border: Border.all(color: AppTheme.line),
                boxShadow: AppTheme.cardShadow,
              ),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _DealImage(deal: deal),
                    const SizedBox(width: 14),
                    Expanded(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(minHeight: 132),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _TopLine(deal: deal),
                            const SizedBox(height: 8),
                            Text(
                              title,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: AppTheme.text,
                                fontSize: 17,
                                fontWeight: FontWeight.w900,
                                height: 1.18,
                                letterSpacing: -0.25,
                              ),
                            ),
                            const SizedBox(height: 8),
                            _PriceLine(deal: deal),
                            const SizedBox(height: 10),
                            Wrap(
                              spacing: 6,
                              runSpacing: 6,
                              children: [
                                if (isHotDeal)
                                  _MiniBadge(
                                    label: AppStrings.hotDeal,
                                    color: AppTheme.primary,
                                    backgroundColor: AppTheme.softBlue,
                                  ),
                                if (freeShippingToCountry)
                                  _MiniBadge(
                                    label: AppStrings.freeShipping,
                                    color: AppTheme.secondary,
                                    backgroundColor: AppTheme.softGreen,
                                  ),
                                if (shipsToCountry)
                                  _MiniBadge(
                                    label: AppStrings.shipsToYourCountry,
                                    color: AppTheme.secondary,
                                    backgroundColor: AppTheme.softGreen,
                                  ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _DealImage extends StatelessWidget {
  const _DealImage({required this.deal});

  final Deal deal;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 126,
      height: 138,
      child: Stack(
        children: [
          Positioned.fill(
            child: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(color: AppTheme.line),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(18),
                child: CachedNetworkImage(
                  imageUrl: deal.imageUrl,
                  fit: BoxFit.contain,
                  placeholder: (context, url) => Container(
                    color: const Color(0xFFF1F5F9),
                    child: const Center(
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  ),
                  errorWidget: (context, url, error) => Container(
                    color: const Color(0xFFF1F5F9),
                    child: const Icon(
                      Icons.image_not_supported_outlined,
                      color: AppTheme.mutedText,
                    ),
                  ),
                ),
              ),
            ),
          ),
          if (deal.hasRealDiscount)
            Positioned(
              top: 9,
              left: 9,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
                decoration: BoxDecoration(
                  color: AppTheme.secondary,
                  borderRadius: BorderRadius.circular(999),
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.navy.withValues(alpha: 0.12),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Text(
                  '-${deal.discountPercent}%',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ),
          Positioned(
            right: 8,
            bottom: 8,
            child: ValueListenableBuilder<Set<String>>(
              valueListenable: FavoritesStore.ids,
              builder: (context, ids, _) {
                final isFavorite = ids.contains(deal.id);

                return Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.96),
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: [
                      BoxShadow(
                        color: AppTheme.navy.withValues(alpha: 0.09),
                        blurRadius: 12,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: IconButton(
                    padding: EdgeInsets.zero,
                    onPressed: () => FavoritesStore.toggle(deal.id),
                    icon: Icon(
                      isFavorite
                          ? Icons.favorite_rounded
                          : Icons.favorite_border_rounded,
                      size: 20,
                      color: isFavorite ? AppTheme.dealRed : AppTheme.text,
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _TopLine extends StatelessWidget {
  const _TopLine({required this.deal});

  final Deal deal;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Flexible(
          child: Text(
            deal.platform,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: AppTheme.primary,
              fontSize: 12,
              fontWeight: FontWeight.w900,
            ),
          ),
        ),
        if (deal.verified) ...[
          const SizedBox(width: 6),
          const Icon(Icons.verified_rounded, color: AppTheme.secondary, size: 15),
        ],
        if (deal.rating > 0 && deal.reviewCount > 0) ...[
          const SizedBox(width: 8),
          const Icon(Icons.star_rounded, color: AppTheme.amber, size: 16),
          Text(
            deal.rating.toStringAsFixed(1),
            style: const TextStyle(
              color: AppTheme.text,
              fontSize: 12,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ],
    );
  }
}

class _PriceLine extends StatelessWidget {
  const _PriceLine({required this.deal});

  final Deal deal;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 3,
      crossAxisAlignment: WrapCrossAlignment.end,
      children: [
        Text(
          UserSettingsStore.formatDealPrice(deal.currentPrice, deal.currency),
          style: const TextStyle(
            color: AppTheme.primary,
            fontSize: 23,
            fontWeight: FontWeight.w900,
            letterSpacing: -0.6,
          ),
        ),
        if (deal.oldPrice > deal.currentPrice)
          Padding(
            padding: const EdgeInsets.only(bottom: 3),
            child: Text(
              UserSettingsStore.formatDealPrice(deal.oldPrice, deal.currency),
              style: const TextStyle(
                color: AppTheme.mutedText,
                fontSize: 13,
                fontWeight: FontWeight.w800,
                decoration: TextDecoration.lineThrough,
              ),
            ),
          ),
      ],
    );
  }
}

class _MiniBadge extends StatelessWidget {
  const _MiniBadge({
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
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}
