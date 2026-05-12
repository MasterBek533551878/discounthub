import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class OnboardingStore {
  static const String _completedKey = 'onboarding_completed';

  static SharedPreferences? _prefs;

  static final ValueNotifier<bool> completed = ValueNotifier<bool>(false);

  static Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
    completed.value = _prefs?.getBool(_completedKey) ?? false;
  }

  static bool get isCompleted => completed.value;

  static Future<void> complete() async {
    completed.value = true;
    await _prefs?.setBool(_completedKey, true);
  }

  static Future<void> reset() async {
    completed.value = false;
    await _prefs?.setBool(_completedKey, false);
  }
}
