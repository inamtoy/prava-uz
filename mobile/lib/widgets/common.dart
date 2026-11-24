import 'package:flutter/material.dart';

import '../api.dart';
import '../screens/auth.dart';
import '../screens/quiz.dart';
import '../theme.dart';

/// Ko'k kvadrat ichida oq "P" — saytdagi static/img/logo.svg bilan bir xil.
class Logo extends StatelessWidget {
  const Logo({super.key, this.size = 40});
  final double size;

  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        alignment: Alignment.center,
        decoration: BoxDecoration(color: AppColors.primary, borderRadius: BorderRadius.circular(size * .2)),
        child: Text('P', style: barlow(size: size * .62, weight: FontWeight.w700, color: Colors.white)),
      );
}

/// Cheklov belgisi: oq doira, qalin qizil halqa, ichida raqam (20 savol, 25 daqiqa, 2 xato).
class LimitSign extends StatelessWidget {
  const LimitSign({super.key, required this.value, required this.label});
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Container(
            width: 72,
            height: 72,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: Colors.white,
              shape: BoxShape.circle,
              border: Border.all(color: AppColors.danger, width: 8),
            ),
            child: Text(value, style: barlow(size: 24, weight: FontWeight.w700, color: AppColors.signInk)),
          ),
          const SizedBox(height: 6),
          Text(label, style: TextStyle(color: AppColors.ink2, fontSize: 14)),
        ],
      );
}

void showError(BuildContext context, Object error) {
  if (error is ApiException && error.unauthorized) {
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (_) => false,
    );
    return;
  }
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(error.toString())));
}

/// Xato yoki bo'sh holat uchun markazdagi blok + "Qayta urinish".
class ErrorView extends StatelessWidget {
  const ErrorView({super.key, required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(Icons.wifi_off_rounded, size: 48, color: AppColors.ink2),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            OutlinedButton(onPressed: onRetry, child: const Text('Qayta urinish')),
          ]),
        ),
      );
}

Future<void> startPractice(BuildContext context, String slug) async {
  try {
    final session = await Api.instance.post('/topics/$slug/practice/');
    if (!context.mounted) return;
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => QuizScreen(session: session)));
  } catch (e) {
    if (context.mounted) showError(context, e);
  }
}

String formatSeconds(int s) {
  final m = (s ~/ 60).toString().padLeft(2, '0');
  final sec = (s % 60).toString().padLeft(2, '0');
  return '$m:$sec';
}
