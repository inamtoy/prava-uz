import 'package:flutter/material.dart';

import '../api.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'auth.dart';
import 'result.dart';
import 'settings.dart';

/// Profil: 4 ta ko'rsatkich, biletlar bo'yicha progress, kuchsiz biletlar, oxirgi 10 ta urinish.
class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late Future<dynamic> _future = Api.instance.get('/stats/');

  void _reload() => setState(() => _future = Api.instance.get('/stats/'));

  Future<void> _openSettings() async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SettingsScreen()));
    if (mounted) _reload(); // ism o'zgargan bo'lishi mumkin
  }

  Future<void> _logout() async {
    await Api.instance.logout();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const LoginScreen()), (_) => false);
  }

  Future<void> _openResult(Map exam) async {
    try {
      final r = await Api.instance.get('/sessions/${exam['id']}/result/');
      if (!mounted) return;
      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ResultScreen(result: r)));
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = Api.instance.user ?? const {};
    final name = (user['first_name'] as String?)?.isNotEmpty == true ? user['first_name'] : user['username'];
    return Scaffold(
      appBar: AppBar(
        title: const Text('Profil'),
        actions: [
          IconButton(onPressed: _openSettings, tooltip: 'Sozlamalar', icon: const Icon(Icons.settings_outlined)),
          IconButton(onPressed: _logout, tooltip: 'Chiqish', icon: const Icon(Icons.logout_rounded)),
        ],
      ),
      body: FutureBuilder<dynamic>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) return ErrorView(message: snap.error.toString(), onRetry: _reload);
          final st = snap.data as Map;
          final recent = List<Map>.from(st['recent_exams'] as List);
          final practiced = List<Map>.from(st['practiced_topics'] as List);
          final weakest = List<Map>.from(st['weakest_topics'] as List);
          return RefreshIndicator(
            onRefresh: () async => _reload(),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text('Salom, ${name ?? ''}!', style: barlow(size: 24, weight: FontWeight.w700)),
                const SizedBox(height: 14),
                GridView.count(
                  crossAxisCount: 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 10,
                  crossAxisSpacing: 10,
                  childAspectRatio: 1.7,
                  children: [
                    _Stat('Jami imtihonlar', '${st['total_exams']}'),
                    _Stat('Oʻtganlar', '${st['passed_exams']}'),
                    _Stat('Oʻrtacha ball', '${st['average_percent']}%'),
                    _Stat('Eng yaxshi natija', '${st['best_percent']}%'),
                  ],
                ),
                if (weakest.isNotEmpty) ...[
                  const SizedBox(height: 22),
                  Text('Kuchsiz biletlar', style: barlow(size: 20, weight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  for (final t in weakest)
                    Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        title: Text('${t['name']}'),
                        subtitle: Text('${t['percent']}% toʻgʻri'),
                        trailing: OutlinedButton(
                          style: OutlinedButton.styleFrom(minimumSize: const Size(0, 40)),
                          onPressed: () async {
                            await startPractice(context, t['slug'] as String);
                            _reload();
                          },
                          child: const Text('Mashq'),
                        ),
                      ),
                    ),
                ],
                if (practiced.isNotEmpty) ...[
                  const SizedBox(height: 22),
                  Text('Biletlar boʻyicha', style: barlow(size: 20, weight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  for (final t in practiced)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Row(children: [
                          Expanded(child: Text('${t['name']}')),
                          Text('${t['percent']}%', style: barlow(size: 15)),
                        ]),
                        const SizedBox(height: 4),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: LinearProgressIndicator(
                            value: (t['percent'] as int) / 100,
                            minHeight: 8,
                            backgroundColor: AppColors.line,
                            color: (t['percent'] as int) >= 90 ? AppColors.success : AppColors.primary,
                          ),
                        ),
                      ]),
                    ),
                ],
                const SizedBox(height: 22),
                Text('Oxirgi urinishlar', style: barlow(size: 20, weight: FontWeight.w700)),
                const SizedBox(height: 8),
                if (recent.isEmpty)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(16),
                      child: Text('Hali imtihon topshirmagansiz — “Imtihon” boʻlimidan boshlang.'),
                    ),
                  )
                else
                  for (final e in recent)
                    Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        onTap: () => _openResult(e),
                        leading: Icon(
                          e['mode'] == 'exam' ? Icons.timer_outlined : Icons.menu_book_outlined,
                          color: AppColors.primary,
                        ),
                        title: Text(e['mode'] == 'exam' ? 'Imtihon' : 'Mashq · ${e['topic'] ?? ''}'),
                        subtitle: Text(_date(e['started_at'] as String)),
                        trailing: _Badge(e),
                      ),
                    ),
              ],
            ),
          );
        },
      ),
    );
  }

  static String _date(String iso) {
    final d = DateTime.tryParse(iso);
    if (d == null) return '';
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(d.day)}.${two(d.month)}.${d.year} ${two(d.hour)}:${two(d.minute)}';
  }
}

class _Stat extends StatelessWidget {
  const _Stat(this.label, this.value);
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
            Text(value, style: barlow(size: 26, weight: FontWeight.w700, color: AppColors.primary)),
            Text(label, style: TextStyle(color: AppColors.ink2, fontSize: 13)),
          ]),
        ),
      );
}

class _Badge extends StatelessWidget {
  const _Badge(this.e);
  final Map e;

  @override
  Widget build(BuildContext context) {
    final isExam = e['mode'] == 'exam';
    final passed = e['is_passed'] == true;
    final color = !isExam ? AppColors.primary : (passed ? AppColors.success : AppColors.danger);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: color.withValues(alpha: .1), borderRadius: BorderRadius.circular(6)),
      child: Text('${e['score']}/${e['total_questions']}', style: barlow(size: 15, color: color)),
    );
  }
}
