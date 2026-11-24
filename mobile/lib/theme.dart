import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// "Yo'l belgisi" dizayn tizimi — saytdagi static/css/main.css tokenlari bilan bir xil.
/// Qorong'i rejimda ranglar almashadi (`AppColors.dark`), shuning uchun ular `const` emas:
/// mavzu o'zgarganda butun daraxt qayta chiziladi (main.dart).
class AppColors {
  static bool dark = false;

  static Color get primary => dark ? const Color(0xFF3A7FC2) : const Color(0xFF0055A4);
  static Color get primaryHover => dark ? const Color(0xFF6FA2D6) : const Color(0xFF004588);
  static Color get primarySoft => dark ? const Color(0xFF1B2B3D) : const Color(0xFFE7EFF8);
  static Color get success => dark ? const Color(0xFF2EA866) : const Color(0xFF00843D);
  static Color get successSoft => dark ? const Color(0xFF15301F) : const Color(0xFFE5F3EB);
  static Color get danger => dark ? const Color(0xFFE5484D) : const Color(0xFFC8102E);
  static Color get dangerSoft => dark ? const Color(0xFF3A1A1F) : const Color(0xFFFBE8EB);
  static const warning = Color(0xFFF2A900);
  static Color get ink => dark ? const Color(0xFFE8EAED) : const Color(0xFF14171A);
  static Color get ink2 => dark ? const Color(0xFFA0A7AF) : const Color(0xFF5E656D);
  static Color get line => dark ? const Color(0xFF2E343B) : const Color(0xFFE2E4E7);
  static Color get bg => dark ? const Color(0xFF0F1215) : const Color(0xFFF3F4F5);
  static Color get surface => dark ? const Color(0xFF1A1E23) : const Color(0xFFFFFFFF);

  /// Yo'l belgisining oq foni va undagi qora yozuv — mavzudan qat'i nazar o'zgarmaydi.
  static const signWhite = Color(0xFFFFFFFF);
  static const signInk = Color(0xFF14171A);
}

TextStyle barlow({double size = 16, FontWeight weight = FontWeight.w600, Color? color}) =>
    GoogleFonts.barlow(fontSize: size, fontWeight: weight, color: color ?? AppColors.ink);

ThemeData buildTheme({bool dark = false}) {
  AppColors.dark = dark;
  final base = ThemeData(
    useMaterial3: true,
    brightness: dark ? Brightness.dark : Brightness.light,
    colorScheme: ColorScheme.fromSeed(
      seedColor: AppColors.primary,
      brightness: dark ? Brightness.dark : Brightness.light,
      primary: AppColors.primary,
      onPrimary: Colors.white,
      error: AppColors.danger,
      surface: AppColors.surface,
      onSurface: AppColors.ink,
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
        side: BorderSide(color: AppColors.line),
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
        side: BorderSide(color: AppColors.line, width: 1.5),
        textStyle: barlow(size: 17, weight: FontWeight.w600),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surface,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: BorderSide(color: AppColors.line, width: 1.5),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: AppColors.surface,
      indicatorColor: AppColors.primarySoft,
      labelTextStyle: WidgetStatePropertyAll(barlow(size: 13, weight: FontWeight.w600)),
    ),
  );
}
