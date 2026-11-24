import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Qurilmadagi sozlamalar (serverga yuborilmaydi): vibratsiya, ovoz, animatsiya, mavzu.
class AppSettings extends ChangeNotifier {
  AppSettings._();
  static final AppSettings instance = AppSettings._();

  static const _kVibration = 'set_vibration';
  static const _kSound = 'set_sound';
  static const _kAnimations = 'set_animations';
  static const _kTheme = 'set_theme';

  SharedPreferences? _prefs;
  bool vibration = true;
  bool sound = false; // sukut bo'yicha o'chiq — dars/navbatda jim bo'lsin
  bool animations = true;
  ThemeMode themeMode = ThemeMode.system;

  Future<void> load() async {
    final p = _prefs = await SharedPreferences.getInstance();
    vibration = p.getBool(_kVibration) ?? true;
    sound = p.getBool(_kSound) ?? false;
    animations = p.getBool(_kAnimations) ?? true;
    themeMode = ThemeMode.values.firstWhere(
      (m) => m.name == p.getString(_kTheme),
      orElse: () => ThemeMode.system,
    );
  }

  Future<void> setVibration(bool v) async {
    vibration = v;
    notifyListeners();
    await _prefs?.setBool(_kVibration, v);
  }

  Future<void> setSound(bool v) async {
    sound = v;
    notifyListeners();
    await _prefs?.setBool(_kSound, v);
  }

  Future<void> setAnimations(bool v) async {
    animations = v;
    notifyListeners();
    await _prefs?.setBool(_kAnimations, v);
  }

  Future<void> setThemeMode(ThemeMode m) async {
    themeMode = m;
    notifyListeners();
    await _prefs?.setString(_kTheme, m.name);
  }

  /// Animatsiya ko'rsatilsinmi: ilova sozlamasi va telefonning "animatsiyalarni kamaytirish" holati.
  static bool motionOn(BuildContext context) => instance.animations && !MediaQuery.of(context).disableAnimations;
}
