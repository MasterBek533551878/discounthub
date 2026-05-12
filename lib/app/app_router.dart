import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../features/deals/data/deals_repository.dart';
import '../features/deals/models/deal.dart';
import '../features/deals/pages/deal_details_page.dart';
import '../features/favorites/pages/favorites_page.dart';
import '../features/home/pages/main_shell_page.dart';
import '../features/legal/pages/about_legal_page.dart';
import '../features/onboarding/onboarding_store.dart';
import '../features/onboarding/pages/onboarding_page.dart';

GoRouter createAppRouter() {
  return GoRouter(
    initialLocation: OnboardingStore.isCompleted ? '/' : '/onboarding',
    routes: [
      GoRoute(
        path: '/onboarding',
        builder: (context, state) => const OnboardingPage(),
      ),
      GoRoute(
        path: '/',
        builder: (context, state) => const MainShellPage(),
      ),
      GoRoute(
        path: '/legal',
        builder: (context, state) => const AboutLegalPage(),
      ),
      GoRoute(
        path: '/favorites',
        builder: (context, state) => const FavoritesPage(),
      ),
      GoRoute(
        path: '/deal/:id',
        builder: (context, state) {
          final id = state.pathParameters['id'];
          final deal = _findDealById(id);

          if (deal == null) {
            return const _NotFoundPage();
          }

          return DealDetailsPage(deal: deal);
        },
      ),
    ],
  );
}

Deal? _findDealById(String? id) {
  return DealsRepository.instance.findById(id);
}

class _NotFoundPage extends StatelessWidget {
  const _NotFoundPage();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Deal not found'),
      ),
      body: const Center(
        child: Text('This deal is no longer available.'),
      ),
    );
  }
}
