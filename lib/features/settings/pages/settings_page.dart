import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../app/app_theme.dart';
import '../../onboarding/onboarding_store.dart';
import '../app_strings.dart';
import '../settings_store.dart';

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(AppStrings.tabSettings),
      ),
      body: ValueListenableBuilder<int>(
        valueListenable: UserSettingsStore.version,
        builder: (context, _, child) {
          return ListView(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
            children: [
              _SectionHeader(
                title: AppStrings.select(
                  en: 'Preferences',
                  ru: 'Предпочтения',
                  uz: 'Sozlamalar',
                ),
                trailing: AppStrings.select(
                  en: 'For you',
                  ru: 'Под вас',
                  uz: 'Siz uchun',
                ),
              ),
              const SizedBox(height: 14),
              _DropdownCard(
                title: AppStrings.country,
                subtitle: AppStrings.countrySubtitle,
                icon: Icons.public_rounded,
                value: UserSettingsStore.country.value,
                values: UserSettingsStore.countries,
                onChanged: (value) async {
                  if (value == null) return;
                  await UserSettingsStore.setCountry(value);
                },
              ),
              const SizedBox(height: 14),
              _DropdownCard(
                title: AppStrings.currency,
                subtitle: AppStrings.currencySubtitle,
                icon: Icons.account_balance_wallet_rounded,
                value: UserSettingsStore.currency.value,
                values: UserSettingsStore.currencies,
                onChanged: (value) async {
                  if (value == null) return;
                  await UserSettingsStore.setCurrency(value);
                },
              ),
              const SizedBox(height: 14),
              _DropdownCard(
                title: AppStrings.language,
                subtitle: AppStrings.languageSubtitle,
                icon: Icons.translate_rounded,
                value: UserSettingsStore.language.value,
                values: UserSettingsStore.languages,
                onChanged: (value) {
                  if (value == null) return;
                  UserSettingsStore.setLanguage(value);
                },
              ),
              const SizedBox(height: 22),
              _SectionHeader(
                title: AppStrings.select(
                  en: 'More',
                  ru: 'Дополнительно',
                  uz: 'Qo‘shimcha',
                ),
              ),
              const SizedBox(height: 14),
              _ActionCard(
                title: AppStrings.showOnboardingAgain,
                subtitle: AppStrings.showOnboardingAgainSubtitle,
                icon: Icons.auto_stories_rounded,
                onTap: () async {
                  await OnboardingStore.reset();
                  if (!context.mounted) return;
                  context.go('/onboarding');
                },
              ),
              const SizedBox(height: 14),
              _ActionCard(
                title: AppStrings.aboutLegal,
                subtitle: AppStrings.aboutLegalSubtitle,
                icon: Icons.policy_rounded,
                onTap: () => context.push('/legal'),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.title,
    this.trailing,
  });

  final String title;
  final String? trailing;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            title,
            style: const TextStyle(
              color: AppTheme.text,
              fontSize: 18,
              fontWeight: FontWeight.w900,
              letterSpacing: -0.2,
            ),
          ),
        ),
        if (trailing != null)
          Text(
            trailing!,
            style: const TextStyle(
              color: AppTheme.primary,
              fontSize: 14,
              fontWeight: FontWeight.w900,
            ),
          ),
      ],
    );
  }
}

class _ActionCard extends StatelessWidget {
  const _ActionCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(24),
      child: InkWell(
        borderRadius: BorderRadius.circular(24),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: AppTheme.line),
            boxShadow: AppTheme.cardShadow,
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _LeadingIcon(icon: icon),
              const SizedBox(width: 16),
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
                        height: 1.2,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      subtitle,
                      style: const TextStyle(
                        color: AppTheme.mutedText,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              const Padding(
                padding: EdgeInsets.only(top: 12),
                child: Icon(
                  Icons.chevron_right_rounded,
                  color: AppTheme.mutedText,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DropdownCard extends StatelessWidget {
  const _DropdownCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.value,
    required this.values,
    required this.onChanged,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final String value;
  final List<String> values;
  final ValueChanged<String?> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppTheme.line),
        boxShadow: AppTheme.cardShadow,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _LeadingIcon(icon: icon),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        color: AppTheme.text,
                        fontSize: 17,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: const TextStyle(
                        color: AppTheme.mutedText,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            initialValue: value,
            isExpanded: true,
            decoration: InputDecoration(
              filled: true,
              fillColor: const Color(0xFFF6F7FB),
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 14,
              ),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(18),
                borderSide: BorderSide.none,
              ),
            ),
            items: values
                .map(
                  (item) => DropdownMenuItem<String>(
                    value: item,
                    child: Text(
                      item,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: AppTheme.text,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                )
                .toList(),
            onChanged: onChanged,
          ),
        ],
      ),
    );
  }
}

class _LeadingIcon extends StatelessWidget {
  const _LeadingIcon({required this.icon});

  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 54,
      height: 54,
      decoration: BoxDecoration(
        color: AppTheme.softBlue,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Icon(
        icon,
        color: AppTheme.primary,
        size: 28,
      ),
    );
  }
}
