import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// "Yo'l belgisi" dizayn tizimi — saytdagi static/css/main.css tokenlari bilan bir xil.
class AppColors {
  static const primary = Color(0xFF0055A4);
  static const primaryHover = Color(0xFF004588);
  static const primarySoft = Color(0xFFE7EFF8);
  static const success = Color(0xFF00843D);
  static const successSoft = Color(0xFFE5F3EB);
  static const danger = Color(0xFFC8102E);
  static const dangerSoft = Color(0xFFFBE8EB);
  static const warning = Color(0xFFF2A900);
  static const ink = Color(0xFF14171A);
  static const ink2 = Color(0xFF5E656D);
  static const line = Color(0xFFE2E4E7);
  static const bg = Color(0xFFF3F4F5);
  static const surface = Color(0xFFFFFFFF);
}

TextStyle barlow({double size = 16, FontWeight weight = FontWeight.w600, Color color = AppColors.ink}) =>
    GoogleFonts.barlow(fontSize: size, fontWeight: weight, color: color);

ThemeData buildTheme() {
  final base = ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: AppColors.primary,
      primary: AppColors.primary,
      error: AppColors.danger,
      surface: AppColors.surface,
    ),
    scaffoldBackgroundColor: AppColors.bg,
  );
  final shape = RoundedRectangleBorder(borderRadius: BorderRadius.circular(8));
  return base.copyWith(
    textTheme: GoogleFonts.interTextTheme(base.textTheme).apply(
      bodyColor: AppColors.ink,
      displayColor: AppColors.ink,
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: AppColors.surface,
      foregroundColor: AppColors.ink,
      elevation: 0,
      scrolledUnderElevation: 0.5,
      titleTextStyle: barlow(size: 20, weight: FontWeight.w700),
    ),
    cardTheme: CardThemeData(
      color: AppColors.surface,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: AppColors.line),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: AppColors.primary,
        minimumSize: const Size(48, 52),
        shape: shape,
        textStyle: barlow(size: 17, weight: FontWeight.w600, color: Colors.white),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.primary,
        minimumSize: const Size(48, 52),
        shape: shape,
        side: const BorderSide(color: AppColors.line, width: 1.5),
        textStyle: barlow(size: 17, weight: FontWeight.w600),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surface,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: AppColors.line, width: 1.5),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: AppColors.surface,
      indicatorColor: AppColors.primarySoft,
      labelTextStyle: WidgetStatePropertyAll(barlow(size: 13, weight: FontWeight.w600)),
    ),
  );
}
