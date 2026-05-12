import '../../core/localization/app_translation_keys.dart';
import '../../core/localization/app_translations.dart';
import 'settings_store.dart';

class AppStrings {
  const AppStrings._();

  static String get _languageCode => UserSettingsStore.languageCode;

  static String tr(
    String key, {
    Map<String, Object?> args = const <String, Object?>{},
  }) {
    final languageMap = AppTranslations.all[_languageCode] ?? AppTranslations.all['en']!;
    var value = languageMap[key] ?? AppTranslations.all['en']![key] ?? key;

    for (final entry in args.entries) {
      value = value.replaceAll('{${entry.key}}', entry.value.toString());
    }

    return value;
  }

  static String select({
    required String en,
    required String ru,
    required String uz,
  }) {
    switch (_languageCode) {
      case 'ru':
        return ru;
      case 'uz':
        return uz;
      default:
        return en;
    }
  }

  static String foundCount(int count) {
    return tr(
      AppTranslationKeys.commonFoundCount,
      args: {'count': count},
    );
  }

  static String dealsAvailable(int count) {
    return tr(
      AppTranslationKeys.commonDealsAvailable,
      args: {'count': count},
    );
  }

  static String filtersActive(int count) {
    return tr(
      AppTranslationKeys.filterActiveCount,
      args: {'count': count},
    );
  }

  static String openOn(String platform) {
    return tr(
      AppTranslationKeys.dealOpenOn,
      args: {'platform': platform},
    );
  }

  static String saveAmount(String amount) {
    return tr(
      AppTranslationKeys.dealSaveAmount,
      args: {'amount': amount},
    );
  }

  static String showDealsUpTo(String amount) {
    return tr(
      AppTranslationKeys.filterShowDealsUpTo,
      args: {'amount': amount},
    );
  }

  static String categoryName(String category) {
    switch (category) {
      case 'Auto':
        return tr(AppTranslationKeys.categoryAuto);
      case 'Electronics':
        return tr(AppTranslationKeys.categoryElectronics);
      case 'Computers':
        return tr(AppTranslationKeys.categoryComputers);
      case 'Fashion':
        return tr(AppTranslationKeys.categoryFashion);
      case 'Gaming':
        return tr(AppTranslationKeys.categoryGaming);
      case 'Home':
        return tr(AppTranslationKeys.categoryHome);
      case 'Office':
        return tr(AppTranslationKeys.categoryOffice);
      case 'Beauty':
        return tr(AppTranslationKeys.categoryBeauty);
      case 'Toys':
        return tr(AppTranslationKeys.categoryToys);
      case 'Sports':
        return tr(AppTranslationKeys.categorySports);
      case 'Other':
        return tr(AppTranslationKeys.categoryOther);
      case 'Air Fresheners':
        return select(en: 'Air Fresheners', ru: 'Освежители воздуха', uz: 'Havo tozalagichlar');
      case 'Athletic Shoes':
      case 'Sneakers':
        return select(en: 'Athletic Shoes', ru: 'Кроссовки', uz: 'Krossovkalar');
      case 'Cell Phones & Smartphones':
        return select(en: 'Smartphones', ru: 'Смартфоны', uz: 'Smartfonlar');
      case 'Headphones':
        return select(en: 'Headphones', ru: 'Наушники', uz: 'Quloqchinlar');
      case 'PC Laptops & Netbooks':
      case 'Laptops & Netbooks':
        return select(en: 'Laptops', ru: 'Ноутбуки', uz: 'Noutbuklar');
      case 'Smart Watches':
      case 'Watches':
        return select(en: 'Smart Watches', ru: 'Смарт-часы', uz: 'Aqlli soatlar');
      case 'Video Game Accessories':
        return select(en: 'Gaming Accessories', ru: 'Игровые аксессуары', uz: 'O‘yin aksessuarlari');
      case 'Home Gadgets':
        return select(en: 'Home Gadgets', ru: 'Гаджеты для дома', uz: 'Uy uchun gadjetlar');
      case 'Tablets & eBook Readers':
      case 'Digital Cameras':
      case 'Cameras & Photo':
        return tr(AppTranslationKeys.categoryElectronics);
      case 'Monitors':
      case 'Computer Components & Parts':
      case 'Computer Drives, Storage & Blank Media':
        return tr(AppTranslationKeys.categoryComputers);
      case 'Health & Beauty':
      case 'Makeup':
      case 'Skin Care':
      case 'Fragrances':
        return tr(AppTranslationKeys.categoryBeauty);
      case 'Toys & Hobbies':
        return tr(AppTranslationKeys.categoryToys);
      case 'Sporting Goods':
      case 'Fitness, Running & Yoga':
        return tr(AppTranslationKeys.categorySports);
      case 'Auto Parts & Accessories':
      case 'Vehicle Parts & Accessories':
        return tr(AppTranslationKeys.categoryAuto);
      default:
        return category;
    }
  }


  static String demoDealTitle(String dealId, String fallback) {
    return tr(_demoDealTitleKey(dealId), args: const <String, Object?>{}) ==
            _demoDealTitleKey(dealId)
        ? fallback
        : tr(_demoDealTitleKey(dealId));
  }

  static String demoDealDescription(String dealId, String fallback) {
    return tr(_demoDealDescriptionKey(dealId), args: const <String, Object?>{}) ==
            _demoDealDescriptionKey(dealId)
        ? fallback
        : tr(_demoDealDescriptionKey(dealId));
  }

  static String _demoDealTitleKey(String dealId) {
    switch (dealId) {
      case 'deal_001':
        return AppTranslationKeys.mockDeal001Title;
      case 'deal_002':
        return AppTranslationKeys.mockDeal002Title;
      case 'deal_003':
        return AppTranslationKeys.mockDeal003Title;
      case 'deal_004':
        return AppTranslationKeys.mockDeal004Title;
      case 'deal_005':
        return AppTranslationKeys.mockDeal005Title;
      case 'deal_006':
        return AppTranslationKeys.mockDeal006Title;
      case 'deal_007':
        return AppTranslationKeys.mockDeal007Title;
      case 'deal_008':
        return AppTranslationKeys.mockDeal008Title;
      default:
        return 'mock.$dealId.title';
    }
  }

  static String _demoDealDescriptionKey(String dealId) {
    switch (dealId) {
      case 'deal_001':
        return AppTranslationKeys.mockDeal001Description;
      case 'deal_002':
        return AppTranslationKeys.mockDeal002Description;
      case 'deal_003':
        return AppTranslationKeys.mockDeal003Description;
      case 'deal_004':
        return AppTranslationKeys.mockDeal004Description;
      case 'deal_005':
        return AppTranslationKeys.mockDeal005Description;
      case 'deal_006':
        return AppTranslationKeys.mockDeal006Description;
      case 'deal_007':
        return AppTranslationKeys.mockDeal007Description;
      case 'deal_008':
        return AppTranslationKeys.mockDeal008Description;
      default:
        return 'mock.$dealId.description';
    }
  }

  static String get appName => tr(AppTranslationKeys.appName);

  static String get tabDeals => tr(AppTranslationKeys.tabDeals);
  static String get tabSearch => tr(AppTranslationKeys.tabSearch);
  static String get tabCategories => tr(AppTranslationKeys.tabCategories);
  static String get tabSaved => tr(AppTranslationKeys.tabSaved);
  static String get tabSettings => tr(AppTranslationKeys.tabSettings);

  static String get homeSubtitle => tr(AppTranslationKeys.homeSubtitle);
  static String get liveDeals => tr(AppTranslationKeys.homeLiveDeals);
  static String get globalMarketplaces => tr(AppTranslationKeys.homeGlobalMarketplaces);

  static String get all => tr(AppTranslationKeys.commonAll);
  static String get any => tr(AppTranslationKeys.commonAny);
  static String get clear => tr(AppTranslationKeys.commonClear);

  static String get freeShipping => tr(AppTranslationKeys.dealFreeShipping);
  static String get freeShippingOnly => tr(AppTranslationKeys.dealFreeShippingOnly);
  static String get verified => tr(AppTranslationKeys.dealVerified);
  static String get verifiedDeal => tr(AppTranslationKeys.dealVerifiedDeal);
  static String get verifiedDealsOnly => tr(AppTranslationKeys.dealVerifiedDealsOnly);

  static String get bestDealsToday => tr(AppTranslationKeys.homeBestDealsToday);
  static String get noDealsMatch => tr(AppTranslationKeys.homeNoDealsMatch);

  static String get advancedFilters => tr(AppTranslationKeys.filterAdvanced);
  static String get clearFilters => tr(AppTranslationKeys.filterClearFilters);
  static String get filterDescription => tr(AppTranslationKeys.filterDescription);
  static String get marketplace => tr(AppTranslationKeys.filterMarketplace);
  static String get category => tr(AppTranslationKeys.filterCategory);
  static String get shipsTo => tr(AppTranslationKeys.filterShipsTo);
  static String get minimumDiscount => tr(AppTranslationKeys.filterMinimumDiscount);
  static String get minimumRating => tr(AppTranslationKeys.filterMinimumRating);
  static String get priceLimit => tr(AppTranslationKeys.filterPriceLimit);
  static String get useMaximumPrice => tr(AppTranslationKeys.filterUseMaximumPrice);
  static String get noPriceLimit => tr(AppTranslationKeys.filterNoPriceLimit);
  static String get dealQuality => tr(AppTranslationKeys.filterDealQuality);
  static String get applyFilters => tr(AppTranslationKeys.filterApply);

  static String get searchDeals => tr(AppTranslationKeys.searchTitle);
  static String get searchHint => tr(AppTranslationKeys.searchHint);
  static String get popularDeals => tr(AppTranslationKeys.searchPopularDeals);
  static String get searchResults => tr(AppTranslationKeys.searchResults);
  static String get noDealsFound => tr(AppTranslationKeys.searchNoDealsFound);

  static String get savedDeals => tr(AppTranslationKeys.savedTitle);
  static String get noSavedDealsYet => tr(AppTranslationKeys.savedEmptyTitle);
  static String get savedDealsHint => tr(AppTranslationKeys.savedEmptyHint);

  static String get country => tr(AppTranslationKeys.settingsCountry);
  static String get countrySubtitle => tr(AppTranslationKeys.settingsCountrySubtitle);
  static String get currency => tr(AppTranslationKeys.settingsCurrency);
  static String get currencySubtitle => tr(AppTranslationKeys.settingsCurrencySubtitle);
  static String get language => tr(AppTranslationKeys.settingsLanguage);
  static String get languageSubtitle => tr(AppTranslationKeys.settingsLanguageSubtitle);
  static String get infoNotice => tr(AppTranslationKeys.settingsInfoNotice);
  static String get currencyNotice => tr(AppTranslationKeys.settingsCurrencyNotice);
  static String get localStorageNotice => tr(AppTranslationKeys.settingsLocalStorageNotice);

  static String activeSource(String source) {
    return tr(
      AppTranslationKeys.settingsActiveSource,
      args: {'source': source},
    );
  }

  static String dataSourceApiConnected(int count) {
    return tr(
      AppTranslationKeys.settingsDataSourceApiConnected,
      args: {'count': count},
    );
  }

  static String get dataSource => tr(AppTranslationKeys.settingsDataSource);
  static String get dataSourceSubtitle => tr(AppTranslationKeys.settingsDataSourceSubtitle);
  static String get apiBaseUrl => tr(AppTranslationKeys.settingsApiBaseUrl);
  static String get apiBaseUrlSubtitle => tr(AppTranslationKeys.settingsApiBaseUrlSubtitle);
  static String get refreshApiData => tr(AppTranslationKeys.settingsRefreshApiData);
  static String get dataSourceDemoReady => tr(AppTranslationKeys.settingsDataSourceDemoReady);
  static String get dataSourceApiFallback => tr(AppTranslationKeys.settingsDataSourceApiFallback);
  static String get aboutLegal => tr(AppTranslationKeys.settingsAboutLegal);
  static String get aboutLegalSubtitle => tr(AppTranslationKeys.settingsAboutLegalSubtitle);

  static String get legalTitle => tr(AppTranslationKeys.legalTitle);
  static String get legalIntroTitle => tr(AppTranslationKeys.legalIntroTitle);
  static String get legalIntroBody => tr(AppTranslationKeys.legalIntroBody);
  static String get legalNoSalesTitle => tr(AppTranslationKeys.legalNoSalesTitle);
  static String get legalNoSalesBody => tr(AppTranslationKeys.legalNoSalesBody);
  static String get legalAffiliateTitle => tr(AppTranslationKeys.legalAffiliateTitle);
  static String get legalAffiliateBody => tr(AppTranslationKeys.legalAffiliateBody);
  static String get legalPricesTitle => tr(AppTranslationKeys.legalPricesTitle);
  static String get legalPricesBody => tr(AppTranslationKeys.legalPricesBody);
  static String get legalResponsibilityTitle => tr(AppTranslationKeys.legalResponsibilityTitle);
  static String get legalResponsibilityBody => tr(AppTranslationKeys.legalResponsibilityBody);
  static String get legalPrivacyTitle => tr(AppTranslationKeys.legalPrivacyTitle);
  static String get legalPrivacyBody => tr(AppTranslationKeys.legalPrivacyBody);
  static String get legalContactTitle => tr(AppTranslationKeys.legalContactTitle);
  static String get legalContactBody => tr(AppTranslationKeys.legalContactBody);
  static String get legalAppStatusTitle => tr(AppTranslationKeys.legalAppStatusTitle);
  static String get legalAppStatusBody => tr(AppTranslationKeys.legalAppStatusBody);

  static String get dealPrice => tr(AppTranslationKeys.dealPrice);
  static String get rating => tr(AppTranslationKeys.dealRating);
  static String get shipping => tr(AppTranslationKeys.dealShipping);
  static String get freeShippingAvailable => tr(AppTranslationKeys.dealFreeShippingAvailable);
  static String get shippingFeeMayApply => tr(AppTranslationKeys.dealShippingFeeMayApply);
  static String get externalPriceNotice => tr(AppTranslationKeys.dealExternalNotice);
  static String get couldNotOpenLink => tr(AppTranslationKeys.dealCouldNotOpenLink);

  static String dealScore(int score) {
    return tr(
      AppTranslationKeys.dealScore,
      args: {'score': score},
    );
  }

  static String whyHighDiscount(int percent) {
    return tr(
      AppTranslationKeys.dealWhyHighDiscount,
      args: {'percent': percent},
    );
  }

  static String whyShipsToCountry(String countryCode) {
    return tr(
      AppTranslationKeys.dealWhyShipsToCountry,
      args: {'country': countryCode},
    );
  }

  static String whyStrongRating(double rating) {
    return tr(
      AppTranslationKeys.dealWhyStrongRating,
      args: {'rating': rating.toStringAsFixed(1)},
    );
  }

  static String get hotDeal => tr(AppTranslationKeys.dealHotDeal);
  static String get lowestPrice => tr(AppTranslationKeys.dealLowestPrice);
  static String get shipsToYourCountry => tr(AppTranslationKeys.dealShipsToYourCountry);
  static String get dealScoreTitle => tr(AppTranslationKeys.dealScoreTitle);
  static String get share => tr(AppTranslationKeys.dealShare);
  static String get linkCopied => tr(AppTranslationKeys.dealLinkCopied);
  static String get whyGoodTitle => tr(AppTranslationKeys.dealWhyGoodTitle);
  static String get whyGoodSubtitle => tr(AppTranslationKeys.dealWhyGoodSubtitle);
  static String get whyFreeShipping => tr(AppTranslationKeys.dealWhyFreeShipping);
  static String get whyVerified => tr(AppTranslationKeys.dealWhyVerified);
  static String get whyMarketplaceExternal => tr(AppTranslationKeys.dealWhyMarketplaceExternal);

  static String get onboardingFindTitle => tr(AppTranslationKeys.onboardingFindTitle);
  static String get onboardingFindSubtitle => tr(AppTranslationKeys.onboardingFindSubtitle);
  static String get onboardingFiltersTitle => tr(AppTranslationKeys.onboardingFiltersTitle);
  static String get onboardingFiltersSubtitle => tr(AppTranslationKeys.onboardingFiltersSubtitle);
  static String get onboardingNoRegistrationTitle => tr(AppTranslationKeys.onboardingNoRegistrationTitle);
  static String get onboardingNoRegistrationSubtitle => tr(AppTranslationKeys.onboardingNoRegistrationSubtitle);
  static String get onboardingSkip => tr(AppTranslationKeys.onboardingSkip);
  static String get onboardingNext => tr(AppTranslationKeys.onboardingNext);
  static String get onboardingStart => tr(AppTranslationKeys.onboardingStart);
  static String get showOnboardingAgain => tr(AppTranslationKeys.settingsShowOnboarding);
  static String get showOnboardingAgainSubtitle => tr(AppTranslationKeys.settingsShowOnboardingSubtitle);

}

