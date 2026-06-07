import 'deal_filters.dart';

enum DealSort {
  bestMatch,
  discountHighToLow,
  newest,
  priceLowToHigh,
  priceHighToLow,
  ratingHighToLow,
}

class DealQuery {
  const DealQuery({
    this.searchText = '',
    this.filters = const DealFilters(),
    this.sort = DealSort.discountHighToLow,
  });

  final String searchText;
  final DealFilters filters;
  final DealSort sort;

  DealQuery copyWith({
    String? searchText,
    DealFilters? filters,
    DealSort? sort,
  }) {
    return DealQuery(
      searchText: searchText ?? this.searchText,
      filters: filters ?? this.filters,
      sort: sort ?? this.sort,
    );
  }
}
