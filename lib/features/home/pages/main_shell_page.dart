import 'package:flutter/material.dart';

import '../../../app/app_theme.dart';
import '../../deals/pages/deals_home_page.dart';
import '../../partner_offers/pages/partner_offers_page.dart';
import '../../promotions/pages/promotions_page.dart';
import '../../settings/app_strings.dart';
import '../../settings/pages/settings_page.dart';
import '../../settings/settings_store.dart';

class MainShellPage extends StatefulWidget {
  const MainShellPage({super.key});

  @override
  State<MainShellPage> createState() => _MainShellPageState();
}

class _MainShellPageState extends State<MainShellPage> {
  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<int>(
      valueListenable: UserSettingsStore.version,
      builder: (context, version, _) {
        final pages = [
          DealsHomePage(key: ValueKey('deals_$version')),
          PromotionsPage(key: ValueKey('promotions_$version')),
          PartnerOffersPage(key: ValueKey('partners_$version')),
          SettingsPage(key: ValueKey('settings_$version')),
        ];

        return Scaffold(
          body: IndexedStack(
            index: _selectedIndex,
            children: pages,
          ),
          bottomNavigationBar: Container(
            decoration: BoxDecoration(
              color: Colors.white,
              border: const Border(top: BorderSide(color: AppTheme.line)),
              boxShadow: [
                BoxShadow(
                  color: AppTheme.navy.withValues(alpha: 0.055),
                  blurRadius: 24,
                  offset: const Offset(0, -10),
                ),
              ],
            ),
            child: SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(8, 6, 8, 4),
                child: NavigationBar(
                  selectedIndex: _selectedIndex,
                  onDestinationSelected: (index) {
                    setState(() => _selectedIndex = index);
                  },
                  destinations: [
                    NavigationDestination(
                      icon: const Icon(Icons.home_outlined),
                      selectedIcon: const Icon(Icons.home_rounded),
                      label: AppStrings.tabDeals,
                    ),
                    NavigationDestination(
                      icon: const Icon(Icons.local_offer_outlined),
                      selectedIcon: const Icon(Icons.local_offer_rounded),
                      label: AppStrings.select(
                        en: 'Promos',
                        ru: 'Акции',
                        uz: 'Aksiyalar',
                      ),
                    ),
                    NavigationDestination(
                      icon: const Icon(Icons.handshake_outlined),
                      selectedIcon: const Icon(Icons.handshake_rounded),
                      label: AppStrings.select(
                        en: 'Partners',
                        ru: 'Партнёры',
                        uz: 'Hamkorlar',
                      ),
                    ),
                    NavigationDestination(
                      icon: const Icon(Icons.settings_outlined),
                      selectedIcon: const Icon(Icons.settings_rounded),
                      label: AppStrings.tabSettings,
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
