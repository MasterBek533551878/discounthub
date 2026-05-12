import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../app/app_theme.dart';
import '../../deals/data/deals_repository.dart';
import '../../deals/models/deal_query.dart';
import '../../deals/widgets/deal_card.dart';
import '../../settings/app_strings.dart';

class SearchPage extends StatefulWidget {
  const SearchPage({super.key});

  @override
  State<SearchPage> createState() => _SearchPageState();
}

class _SearchPageState extends State<SearchPage> {
  final TextEditingController _controller = TextEditingController();
  final DealsRepository _repository = DealsRepository.instance;

  String _query = '';

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<int>(
      valueListenable: _repository.version,
      builder: (context, _, child) {
        final result = _repository.searchDeals(
          DealQuery(
            searchText: _query,
            sort: DealSort.discountHighToLow,
          ),
        );
        final results = result.deals;

        return Scaffold(
          appBar: AppBar(
            title: Text(AppStrings.searchDeals),
          ),
          body: ListView(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
            children: [
              DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  boxShadow: AppTheme.cardShadow,
                ),
                child: TextField(
                  controller: _controller,
                  onChanged: (value) => setState(() => _query = value),
                  textInputAction: TextInputAction.search,
                  decoration: InputDecoration(
                    hintText: AppStrings.searchHint,
                    prefixIcon: const Icon(Icons.search_rounded),
                    suffixIcon: _query.isEmpty
                        ? null
                        : IconButton(
                            onPressed: () {
                              _controller.clear();
                              setState(() => _query = '');
                            },
                            icon: const Icon(Icons.close_rounded),
                          ),
                  ),
                ),
              ),
              const SizedBox(height: 20),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      _query.isEmpty ? AppStrings.popularDeals : AppStrings.searchResults,
                      style: const TextStyle(
                        color: AppTheme.text,
                        fontSize: 22,
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.4,
                      ),
                    ),
                  ),
                  Text(
                    AppStrings.foundCount(results.length),
                    style: const TextStyle(
                      color: AppTheme.mutedText,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              if (results.isEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 80),
                  child: Center(
                    child: Text(
                      AppStrings.noDealsFound,
                      style: const TextStyle(
                        color: AppTheme.mutedText,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                )
              else
                ...results.map(
                  (deal) => Padding(
                    padding: const EdgeInsets.only(bottom: 14),
                    child: DealCard(
                      deal: deal,
                      onTap: () => context.push('/deal/${deal.id}'),
                    ),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }
}
