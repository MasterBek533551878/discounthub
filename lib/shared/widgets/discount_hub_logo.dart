import 'package:flutter/material.dart';

import '../../app/app_theme.dart';

class BrandAssets {
  static const String logo = 'assets/brand/logo.png';
}

class DiscountHubLogo extends StatelessWidget {
  const DiscountHubLogo({
    super.key,
    this.markSize = 42,
    this.wordmarkSize = 24,
    this.showTagline = false,
    this.center = false,
    this.compact = false,
  });

  final double markSize;
  final double wordmarkSize;
  final bool showTagline;
  final bool center;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final logo = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        DiscountHubMark(size: markSize),
        SizedBox(width: compact ? markSize * 0.14 : markSize * 0.18),
        Flexible(
          child: RichText(
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            text: TextSpan(
              style: TextStyle(
                color: AppTheme.text,
                fontSize: compact ? wordmarkSize - 1 : wordmarkSize,
                fontWeight: FontWeight.w900,
                letterSpacing: -0.8,
                height: 1,
              ),
              children: const [
                TextSpan(text: 'Discount'),
                TextSpan(
                  text: 'Hub',
                  style: TextStyle(color: AppTheme.primary),
                ),
              ],
            ),
          ),
        ),
      ],
    );

    if (!showTagline) return logo;

    return Column(
      crossAxisAlignment:
          center ? CrossAxisAlignment.center : CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        logo,
        const SizedBox(height: 6),
        Text(
          'SMART SAVINGS. CLEAN DISCOVERY.',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            color: AppTheme.mutedText,
            fontSize: (wordmarkSize * 0.28).clamp(9, 12),
            fontWeight: FontWeight.w800,
            letterSpacing: 1.8,
          ),
        ),
      ],
    );
  }
}

class DiscountHubMark extends StatelessWidget {
  const DiscountHubMark({
    super.key,
    this.size = 48,
    this.darkBackground = false,
  });

  final double size;
  final bool darkBackground;

  @override
  Widget build(BuildContext context) {
    return SizedBox.square(
      dimension: size,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(size * 0.24),
        child: Image.asset(
          BrandAssets.logo,
          fit: BoxFit.cover,
          filterQuality: FilterQuality.high,
        ),
      ),
    );
  }
}

class DiscountHubAppIcon extends StatelessWidget {
  const DiscountHubAppIcon({
    super.key,
    this.size = 56,
    this.dark = false,
    this.flat = false,
  });

  final double size;
  final bool dark;
  final bool flat;

  @override
  Widget build(BuildContext context) {
    final image = ClipRRect(
      borderRadius: BorderRadius.circular(size * 0.24),
      child: Image.asset(
        BrandAssets.logo,
        fit: BoxFit.cover,
        filterQuality: FilterQuality.high,
      ),
    );

    if (flat) {
      return SizedBox.square(dimension: size, child: image);
    }

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: dark ? AppTheme.navy : Colors.white,
        borderRadius: BorderRadius.circular(size * 0.26),
        border: Border.all(
          color: dark ? Colors.white.withValues(alpha: 0.12) : AppTheme.line,
        ),
        boxShadow: AppTheme.softShadow,
      ),
      clipBehavior: Clip.antiAlias,
      child: image,
    );
  }
}
