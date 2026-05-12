import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../app/app_theme.dart';
import '../../../shared/widgets/discount_hub_logo.dart';
import '../../deals/data/deals_repository.dart';
import '../../deals/widgets/deal_card.dart';
import '../../settings/app_strings.dart';
import '../favorites_store.dart';

class FavoritesPage extends StatelessWidget {
  const FavoritesPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(AppStrings.savedDeals),
      ),
      body: ValueListenableBuilder<Set<String>>(
        valueListenable: FavoritesStore.ids,
        builder: (context, ids, _) {
          return ValueListenableBuilder<int>(
            valueListenable: DealsRepository.instance.version,
            builder: (context, _, child) {
              final deals = DealsRepository.instance.getFavoriteDeals(ids);

              if (deals.isEmpty) {
                return const _EmptyFavorites();
              }

              return ListView.separated(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
                itemCount: deals.length,
                separatorBuilder: (context, index) => const SizedBox(height: 14),
                itemBuilder: (context, index) {
                  final deal = deals[index];

                  return DealCard(
                    deal: deal,
                    onTap: () => context.push('/deal/${deal.id}'),
                  );
                },
              );
            },
          );
        },
      ),
    );
  }
}

class _EmptyFavorites extends StatelessWidget {
  const _EmptyFavorites();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(30),
            border: Border.all(color: AppTheme.line),
            boxShadow: AppTheme.cardShadow,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const DiscountHubAppIcon(size: 72),
              const SizedBox(height: 18),
              Text(
                AppStrings.noSavedDealsYet,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: AppTheme.text,
                  fontSize: 22,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -0.3,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                AppStrings.savedDealsHint,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: AppTheme.mutedText,
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  height: 1.4,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
