import 'translations_de.dart';
import 'translations_en.dart';
import 'translations_es.dart';
import 'translations_fr.dart';
import 'translations_ko.dart';
import 'translations_pt.dart';
import 'translations_ru.dart';
import 'translations_uz.dart';
import 'translations_zh.dart';

class AppTranslations {
  const AppTranslations._();

  static const Map<String, Map<String, String>> all = {
    'en': translationsEn,
    'ru': translationsRu,
    'uz': translationsUz,
    'es': translationsEs,
    'fr': translationsFr,
    'de': translationsDe,
    'pt': translationsPt,
    'ko': translationsKo,
    'zh': translationsZh,
  };
}
