import 'package:flutter/material.dart';

import '../../../app/app_theme.dart';
import '../../../shared/widgets/discount_hub_logo.dart';
import '../../settings/app_strings.dart';

class AboutLegalPage extends StatelessWidget {
  const AboutLegalPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(AppStrings.legalTitle),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
        children: [
          _HeroCard(
            title: AppStrings.legalIntroTitle,
            body: AppStrings.legalIntroBody,
          ),
          const SizedBox(height: 14),
          _LegalSection(
            icon: Icons.storefront_rounded,
            title: AppStrings.legalNoSalesTitle,
            body: AppStrings.legalNoSalesBody,
          ),
          const SizedBox(height: 12),
          _LegalSection(
            icon: Icons.link_rounded,
            title: AppStrings.legalAffiliateTitle,
            body: AppStrings.legalAffiliateBody,
          ),
          const SizedBox(height: 12),
          _LegalSection(
            icon: Icons.price_check_rounded,
            title: AppStrings.legalPricesTitle,
            body: AppStrings.legalPricesBody,
          ),
          const SizedBox(height: 12),
          _LegalSection(
            icon: Icons.verified_user_rounded,
            title: AppStrings.legalResponsibilityTitle,
            body: AppStrings.legalResponsibilityBody,
          ),
        ],
      ),
    );
  }
}

class _HeroCard extends StatelessWidget {
  const _HeroCard({
    required this.title,
    required this.body,
  });

  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFFEEF4FF), Colors.white],
        ),
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: const Color(0xFFD9E6FF)),
        boxShadow: AppTheme.cardShadow,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const DiscountHubAppIcon(size: 58),
          const SizedBox(height: 18),
          Text(
            title,
            style: const TextStyle(
              color: AppTheme.text,
              fontSize: 23,
              fontWeight: FontWeight.w900,
              height: 1.12,
              letterSpacing: -0.4,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            body,
            style: const TextStyle(
              color: AppTheme.mutedText,
              fontSize: 15,
              fontWeight: FontWeight.w700,
              height: 1.45,
            ),
          ),
        ],
      ),
    );
  }
}

class _LegalSection extends StatelessWidget {
  const _LegalSection({
    required this.icon,
    required this.title,
    required this.body,
  });

  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(26),
        border: Border.all(color: AppTheme.line),
        boxShadow: AppTheme.cardShadow,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: AppTheme.softBlue,
              borderRadius: BorderRadius.circular(18),
            ),
            child: Icon(icon, color: AppTheme.primary),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: AppTheme.text,
                    fontSize: 16,
                    fontWeight: FontWeight.w900,
                    height: 1.25,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  body,
                  style: const TextStyle(
                    color: AppTheme.mutedText,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    height: 1.45,
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
