import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class FavoritesStore {
  static const String _key = 'favorite_deal_ids';

  static SharedPreferences? _prefs;

  static final ValueNotifier<Set<String>> ids = ValueNotifier<Set<String>>(
    <String>{},
  );

  static Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
    final savedIds = _prefs?.getStringList(_key) ?? <String>[];
    ids.value = savedIds.toSet();
  }

  static bool isFavorite(String dealId) {
    return ids.value.contains(dealId);
  }

  static Future<void> toggle(String dealId) async {
    final nextIds = <String>{...ids.value};

    if (nextIds.contains(dealId)) {
      nextIds.remove(dealId);
    } else {
      nextIds.add(dealId);
    }

    ids.value = nextIds;
    await _prefs?.setStringList(_key, nextIds.toList());
  }
}