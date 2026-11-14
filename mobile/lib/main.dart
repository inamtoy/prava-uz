import 'package:flutter/material.dart';

import 'api.dart';
import 'screens/auth.dart';
import 'screens/home_shell.dart';
import 'theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Api.instance.load();
  runApp(const PravaApp());
}

class PravaApp extends StatelessWidget {
  const PravaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Prava.uz',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(),
      home: Api.instance.isLoggedIn ? const HomeShell() : const LoginScreen(),
    );
  }
}
