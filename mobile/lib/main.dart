import 'package:flutter/material.dart';

import 'api.dart';
import 'screens/auth.dart';
import 'screens/home_shell.dart';
import 'settings.dart';
import 'theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await AppSettings.instance.load();
  await Api.instance.load();
  runApp(const PravaApp());
}

class PravaApp extends StatefulWidget {
  const PravaApp({super.key});

  @override
  State<PravaApp> createState() => _PravaAppState();
}

class _PravaAppState extends State<PravaApp> with WidgetsBindingObserver {
  final _settings = AppSettings.instance;
  bool? _dark;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _settings.addListener(_onChanged);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _settings.removeListener(_onChanged);
    super.dispose();
  }

  // Telefonning yorug'/qorong'i rejimi o'zgarganda ("Tizim bo'yicha" tanlangan bo'lsa)
  @override
  void didChangePlatformBrightness() => _onChanged();

  bool get _isDark => switch (_settings.themeMode) {
        ThemeMode.dark => true,
        ThemeMode.light => false,
        ThemeMode.system => WidgetsBinding.instance.platformDispatcher.platformBrightness == Brightness.dark,
      };

  void _onChanged() {
    if (_isDark == _dark) return;
    setState(() {});
    // AppColors Theme'ga bog'lanmagan, shuning uchun ochiq ekranlar (holati saqlangan holda) qayta chiziladi
    WidgetsBinding.instance.addPostFrameCallback((_) {
      void rebuild(Element e) {
        e.markNeedsBuild();
        e.visitChildren(rebuild);
      }

      if (mounted) (context as Element).visitChildren(rebuild);
    });
  }

  @override
  Widget build(BuildContext context) {
    _dark = _isDark;
    return MaterialApp(
      title: 'Prava.uz',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(dark: _dark!),
      home: Api.instance.isLoggedIn ? const HomeShell() : const LoginScreen(),
    );
  }
}
