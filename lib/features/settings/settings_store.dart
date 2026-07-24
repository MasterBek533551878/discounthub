import 'package:flutter/foundation.dart';
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

class UserSettingsStore {
  static const String _countryKey = 'user_country';
  static const String _marketCountryKey = 'market_country_code';
  static const String _currencyKey = 'user_currency';
  static const String _languageKey = 'user_language';
  static const String _dataSourceKey = 'user_data_source';
  static const String _apiBaseUrlKey = 'user_api_base_url';

  static SharedPreferences? _prefs;

  static final ValueNotifier<int> version = ValueNotifier<int>(0);

  static final ValueNotifier<String> country = ValueNotifier<String>(
    'Uzbekistan',
  );

  // Independent catalogue filter shared by Deals and Promos.
  // Empty string means all countries and does not change the profile country.
  static final ValueNotifier<String> marketCountryCode = ValueNotifier<String>(
    '',
  );

  static final ValueNotifier<String> currency = ValueNotifier<String>('USD');

  // UI still stores/display names, but localization internally uses stable codes.
  // This keeps old saved values compatible and lets us add new languages safely.
  static final ValueNotifier<String> language = ValueNotifier<String>(
    'English',
  );

  static final ValueNotifier<String> dataSource = ValueNotifier<String>('API');

  static const String productionApiBaseUrl = 'https://api.discounthub.uz';

  static const String defaultApiBaseUrl = String.fromEnvironment(
    'DISCOUNTHUB_API_BASE_URL',
    defaultValue: productionApiBaseUrl,
  );

  static final ValueNotifier<String> apiBaseUrl = ValueNotifier<String>(
    defaultApiBaseUrl,
  );

  static const String dataSourceDemo = 'Demo';
  static const String dataSourceApi = 'API';

  static const List<String> dataSources = [dataSourceApi];

  static const List<String> countries = [
    'Uzbekistan',
    'United States',
    'United Kingdom',
    'Germany',
    'Turkey',
    'UAE',
  ];

  static const List<String> currencies = [
    'USD',
    'EUR',
    'UZS',
    'GBP',
    'TRY',
    'AED',
  ];

  static const List<String> languages = [
    'English',
    'Русский',
    'O‘zbekcha',
    'Español',
    'Français',
    'Deutsch',
    'Português',
    '한국어',
    '简体中文',
  ];

  static const Map<String, String> countryCodes = {
    'Uzbekistan': 'UZ',
    'United States': 'US',
    'United Kingdom': 'UK',
    'Germany': 'DE',
    'Turkey': 'TR',
    'UAE': 'AE',
  };

  static const Map<String, String> languageCodes = {
    'English': 'en',
    'Русский': 'ru',
    'O‘zbekcha': 'uz',
    'Español': 'es',
    'Français': 'fr',
    'Deutsch': 'de',
    'Português': 'pt',
    '한국어': 'ko',
    '简体中文': 'zh',
    'en': 'en',
    'ru': 'ru',
    'uz': 'uz',
    'es': 'es',
    'fr': 'fr',
    'de': 'de',
    'pt': 'pt',
    'ko': 'ko',
    'zh': 'zh',
    'zh-Hans': 'zh',
  };

  // Temporary local rates until backend FX conversion is connected.
  static const Map<String, double> demoUsdRates = {
    'USD': 1,
    'EUR': 0.92,
    'UZS': 12800,
    'GBP': 0.79,
    'TRY': 32.20,
    'AED': 3.67,
  };

  static Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();

    country.value = _safeValue(
      saved: _prefs?.getString(_countryKey),
      allowed: countries,
      fallback: 'Uzbekistan',
    );

    final savedMarketCountry = (_prefs?.getString(_marketCountryKey) ?? '')
        .trim()
        .toUpperCase();
    marketCountryCode.value = RegExp(r'^[A-Z]{2}$').hasMatch(savedMarketCountry)
        ? savedMarketCountry
        : '';

    currency.value = _safeValue(
      saved: _prefs?.getString(_currencyKey),
      allowed: currencies,
      fallback: 'USD',
    );

    language.value = _safeLanguageValue(_prefs?.getString(_languageKey));

    dataSource.value = _safeValue(
      saved: _prefs?.getString(_dataSourceKey),
      allowed: dataSources,
      fallback: dataSourceApi,
    );

    final savedApiUrl = _prefs?.getString(_apiBaseUrlKey);
    final normalizedApiUrl = _safeApiBaseUrl(savedApiUrl);
    apiBaseUrl.value = normalizedApiUrl;
    await _prefs?.setString(_apiBaseUrlKey, normalizedApiUrl);

    _bump();
  }

  static bool get useApiDataSource => dataSource.value == dataSourceApi;

  static String get selectedCountryCode {
    return countryCodes[country.value] ?? 'US';
  }

  static String get selectedMarketCountryCode => marketCountryCode.value;

  static String get languageCode {
    return languageCodes[language.value] ?? 'en';
  }

  static Future<void> setCountry(String value) async {
    if (!countries.contains(value)) return;
    country.value = value;
    await _prefs?.setString(_countryKey, value);
    _bump();
  }

  static Future<void> setMarketCountryCode(String value) async {
    final normalized = value.trim().toUpperCase();
    final safeValue = normalized.isEmpty || normalized == 'ALL'
        ? ''
        : (RegExp(r'^[A-Z]{2}$').hasMatch(normalized) ? normalized : '');
    if (marketCountryCode.value == safeValue) return;
    marketCountryCode.value = safeValue;
    if (safeValue.isEmpty) {
      await _prefs?.remove(_marketCountryKey);
    } else {
      await _prefs?.setString(_marketCountryKey, safeValue);
    }
  }

  static Future<void> setCurrency(String value) async {
    if (!currencies.contains(value)) return;
    currency.value = value;
    await _prefs?.setString(_currencyKey, value);
    _bump();
  }

  static Future<void> setLanguage(String value) async {
    final safeValue = _safeLanguageValue(value);
    language.value = safeValue;
    await _prefs?.setString(_languageKey, safeValue);
    _bump();
  }

  static Future<void> setDataSource(String value) async {
    if (!dataSources.contains(value)) return;
    dataSource.value = value;
    await _prefs?.setString(_dataSourceKey, value);
    _bump();
  }

  static Future<void> setApiBaseUrl(String value) async {
    final trimmed = value.trim();
    if (trimmed.isEmpty) return;
    apiBaseUrl.value = trimmed;
    await _prefs?.setString(_apiBaseUrlKey, trimmed);
    _bump();
  }

  static String formatUsd(double usdAmount) {
    final selectedCurrency = currency.value;
    final rate = demoUsdRates[selectedCurrency] ?? 1;
    final converted = usdAmount * rate;
    return formatNativeAmount(converted, selectedCurrency);
  }

  static String formatDealPrice(double amount, String currencyCode) {
    final normalizedCurrency = currencyCode.trim().toUpperCase();
    final displayCurrency = normalizedCurrency.isEmpty
        ? currency.value
        : normalizedCurrency;
    return formatNativeAmount(amount, displayCurrency);
  }

  static String formatNativeAmount(double amount, String currencyCode) {
    final normalizedCurrency = currencyCode.trim().toUpperCase();
    final displayCurrency = normalizedCurrency.isEmpty
        ? currency.value
        : normalizedCurrency;
    final decimalDigits = _zeroDecimalCurrencies.contains(displayCurrency)
        ? 0
        : 2;

    final formatter = NumberFormat.currency(
      locale: 'en_US',
      symbol: '',
      decimalDigits: decimalDigits,
    );

    return '$displayCurrency ${formatter.format(amount).trim()}';
  }

  static const Set<String> _zeroDecimalCurrencies = {
    'UZS',
    'JPY',
    'KRW',
    'CLP',
    'COP',
    'ARS',
  };

  static String _safeApiBaseUrl(String? saved) {
    final normalized = saved?.trim();
    if (normalized == null || normalized.isEmpty) {
      return defaultApiBaseUrl;
    }

    final uri = Uri.tryParse(normalized);
    if (uri == null || !uri.hasScheme || uri.host.isEmpty) {
      return defaultApiBaseUrl;
    }

    // Old local test values are easy to get stuck in SharedPreferences after
    // removing the developer API controls from settings. In normal app runs we
    // should fall back to the production API so deals do not disappear when the
    // local backend is not running.
    final host = uri.host.toLowerCase();
    final isLocalDevHost =
        host == 'localhost' ||
        host == '127.0.0.1' ||
        host == '10.0.2.2' ||
        host.startsWith('192.168.') ||
        host.startsWith('10.') ||
        host.startsWith('172.16.') ||
        host.startsWith('172.17.') ||
        host.startsWith('172.18.') ||
        host.startsWith('172.19.') ||
        host.startsWith('172.2') ||
        host.startsWith('172.30.') ||
        host.startsWith('172.31.');

    if (isLocalDevHost) {
      return defaultApiBaseUrl;
    }

    return normalized;
  }

  static String _safeValue({
    required String? saved,
    required List<String> allowed,
    required String fallback,
  }) {
    if (saved != null && allowed.contains(saved)) {
      return saved;
    }

    return fallback;
  }

  static String _safeLanguageValue(String? saved) {
    switch (saved) {
      case 'ru':
      case 'Русский':
        return 'Русский';
      case 'uz':
      case 'O‘zbekcha':
        return 'O‘zbekcha';
      case 'es':
      case 'Español':
        return 'Español';
      case 'fr':
      case 'Français':
        return 'Français';
      case 'de':
      case 'Deutsch':
        return 'Deutsch';
      case 'pt':
      case 'Português':
        return 'Português';
      case 'ko':
      case '한국어':
        return '한국어';
      case 'zh':
      case 'zh-Hans':
      case '简体中文':
        return '简体中文';
      case 'en':
      case 'English':
      default:
        return 'English';
    }
  }

  static void _bump() {
    version.value = version.value + 1;
  }
}
