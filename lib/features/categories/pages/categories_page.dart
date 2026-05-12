import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../app/app_theme.dart';
import '../../deals/data/deals_repository.dart';
import '../../deals/models/deal.dart';
import '../../deals/widgets/deal_card.dart';
import '../../settings/app_strings.dart';

class CategoriesPage extends StatelessWidget {
  const CategoriesPage({super.key});

  DealsRepository get _repository => DealsRepository.instance;

  IconData _iconForCategory(String category) {
    switch (category) {
      case 'Electronics':
        return Icons.devices_rounded;
      case 'Fashion':
        return Icons.checkroom_rounded;
      case 'Home':
        return Icons.home_rounded;
      case 'Office':
        return Icons.work_rounded;
      case 'Auto':
        return Icons.directions_car_rounded;
      case 'Gaming':
        return Icons.sports_esports_rounded;
      default:
        return Icons.category_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<int>(
      valueListenable: _repository.version,
      builder: (context, _, child) {
        final categories = _repository.getCategories();

        return Scaffold(
          appBar: AppBar(
            title: Text(AppStrings.tabCategories),
          ),
          body: ListView.separated(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
            itemCount: categories.length,
            separatorBuilder: (context, index) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final category = categories[index];

              return Material(
                color: Colors.transparent,
                child: InkWell(
                  borderRadius: BorderRadius.circular(26),
                  onTap: () => _showCategoryDeals(context, category),
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(26),
                      border: Border.all(color: AppTheme.line),
                      boxShadow: AppTheme.cardShadow,
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 54,
                          height: 54,
                          decoration: BoxDecoration(
                            color: AppTheme.softBlue,
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Icon(_iconForCategory(category), color: AppTheme.primary),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                AppStrings.categoryName(category),
                                style: const TextStyle(
                                  color: AppTheme.text,
                                  fontSize: 17,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                              const SizedBox(height: 3),
                              Text(
                                AppStrings.dealsAvailable(_repository.countByCategory(category)),
                                style: const TextStyle(
                                  color: AppTheme.mutedText,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const Icon(Icons.chevron_right_rounded, color: AppTheme.mutedText),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        );
      },
    );
  }

  void _showCategoryDeals(BuildContext context, String category) {
    final deals = _repository.getDealsByCategory(category);

    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      backgroundColor: AppTheme.background,
      builder: (context) {
        return DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.82,
          minChildSize: 0.45,
          maxChildSize: 0.92,
          builder: (context, scrollController) {
            return ListView(
              controller: scrollController,
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
              children: [
                Text(
                  AppStrings.categoryName(category),
                  style: const TextStyle(
                    color: AppTheme.text,
                    fontSize: 26,
                    fontWeight: FontWeight.w900,
                    letterSpacing: -0.6,
                  ),
                ),
                const SizedBox(height: 14),
                ...deals.map(
                  (Deal deal) => Padding(
                    padding: const EdgeInsets.only(bottom: 14),
                    child: DealCard(
                      deal: deal,
                      onTap: () {
                        Navigator.of(context).pop();
                        context.push('/deal/${deal.id}');
                      },
                    ),
                  ),
                ),
              ],
            );
          },
        );
      },
    );
  }
}
