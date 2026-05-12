import '../../settings/settings_store.dart';
import '../models/deal.dart';

class DealInsights {
  const DealInsights._();

  static int score(Deal deal) {
    final rawScore =
        (deal.discountPercent * 1.15) +
        (deal.rating * 7.5) +
        (deal.reviewCount >= 1000 ? 6 : 0) +
        (hasFreeShippingToSelectedCountry(deal) ? 9 : 0) +
        (deal.verified ? 12 : 0) +
        (shipsToSelectedCountry(deal) ? 8 : 0);

    return rawScore.clamp(0, 100).round();
  }

  static bool isHotDeal(Deal deal) {
    return deal.discountPercent >= 40 && (deal.verified || deal.rating >= 4.4);
  }

  static bool isLowestPriceCandidate(Deal deal) {
    return deal.discountPercent >= 50 && deal.verified;
  }

  static bool shipsToSelectedCountry(Deal deal) {
    return deal.shipsTo.contains(UserSettingsStore.selectedCountryCode);
  }

  static bool hasFreeShippingToSelectedCountry(Deal deal) {
    return deal.freeShipping && shipsToSelectedCountry(deal);
  }

  static List<String> reasonTypes(Deal deal) {
    final reasons = <String>[];

    if (deal.discountPercent >= 30) reasons.add('highDiscount');
    if (hasFreeShippingToSelectedCountry(deal)) reasons.add('freeShipping');
    if (deal.verified) reasons.add('verified');
    if (shipsToSelectedCountry(deal)) reasons.add('shipsToCountry');
    if (deal.rating >= 4.5) reasons.add('strongRating');

    if (reasons.isEmpty) {
      reasons.add('marketplaceExternal');
    }

    return reasons;
  }
}
