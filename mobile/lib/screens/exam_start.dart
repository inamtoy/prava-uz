import 'package:flutter/material.dart';

import '../api.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'quiz.dart';

/// Imtihon haqida ma'lumot (20 savol, 25 daqiqa, 2 xato) va "Boshlash" / "Davom ettirish".
class ExamStartScreen extends StatefulWidget {
  const ExamStartScreen({super.key});

  @override
  State<ExamStartScreen> createState() => _ExamStartScreenState();
}

class _ExamStartScreenState extends State<ExamStartScreen> {
  late Future<List<dynamic>> _future = _load();
  bool _busy = false;

  Future<List<dynamic>> _load() =>
      Future.wait([Api.instance.get('/config/'), Api.instance.get('/exams/')]);

  void _reload() => setState(() => _future = _load());

  Future<void> _start() async {
    setState(() => _busy = true);
    try {
      final session = await Api.instance.post('/exams/');
      if (!mounted) return;
      if (session['resumed'] == true) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Sizda tugallanmagan imtihon bor — davom ettiryapsiz.')),
        );
      }
      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => QuizScreen(session: session)));
      if (mounted) _reload();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Imtihon')),
      body: FutureBuilder<List<dynamic>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) return ErrorView(message: snap.error.toString(), onRetry: _reload);
          final cfg = snap.data![0] as Map;
          final current = (snap.data![1] as Map)['current'];
          final count = cfg['exam_question_count'];
          final minutes = (cfg['exam_duration_seconds'] as int) ~/ 60;
          final mistakes = cfg['exam_max_mistakes'] as int;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(children: [
                    Text('Imtihon shartlari', style: barlow(size: 22, weight: FontWeight.w700)),
                    const SizedBox(height: 20),
                    Row(mainAxisAlignment: MainAxisAlignment.spaceAround, children: [
                      LimitSign(value: '$count', label: 'savol'),
                      LimitSign(value: '$minutes', label: 'daqiqa'),
                      LimitSign(value: '$mistakes', label: 'xato'),
                    ]),
                    const SizedBox(height: 20),
                    Text(
                      'Savollar barcha biletlardan tasodifiy tanlanadi. Oʻtish uchun kamida '
                      '${(count as int) - mistakes} ta toʻgʻri javob kerak. Javob berilmagan savol xato hisoblanadi. '
                      'Har bir savolga birinchi javobingiz yakuniy.',
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: AppColors.ink2, height: 1.4),
                    ),
                  ]),
                ),
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _busy ? null : _start,
                icon: Icon(current != null ? Icons.play_arrow_rounded : Icons.flag_rounded),
                label: Text(current != null ? 'Imtihonni davom ettirish' : 'Imtihonni boshlash'),
              ),
              if (current != null) ...[
                const SizedBox(height: 10),
                const Text(
                  'Sizda tugallanmagan imtihon bor. Vaqt hisoblanishda davom etmoqda.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: AppColors.ink2),
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}
