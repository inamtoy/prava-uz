import 'package:flutter/material.dart';

import '../api.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'settings.dart';

/// Haftalik TOP-10: dushanbadan beri to'g'ri javoblar soni.
class LeaderboardScreen extends StatefulWidget {
  const LeaderboardScreen({super.key});

  @override
  State<LeaderboardScreen> createState() => _LeaderboardScreenState();
}

class _LeaderboardScreenState extends State<LeaderboardScreen> {
  late Future<dynamic> _future = Api.instance.get('/leaderboard/');

  void _reload() => setState(() => _future = Api.instance.get('/leaderboard/'));

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Reyting')),
        body: FutureBuilder<dynamic>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) return ErrorView(message: snap.error.toString(), onRetry: _reload);
            return RefreshIndicator(
              onRefresh: () async => _reload(),
              child: LeaderboardView(
                data: Map<String, dynamic>.from(snap.data as Map),
                onSettings: () async {
                  await Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SettingsScreen()));
                  _reload();
                },
              ),
            );
          },
        ),
      );
}

/// Reyting tarkibi — faqat ma'lumotdan chiziladi (testlash uchun alohida).
class LeaderboardView extends StatelessWidget {
  const LeaderboardView({super.key, required this.data, required this.onSettings});
  final Map<String, dynamic> data;
  final VoidCallback onSettings;

  String _date(String iso) {
    final p = iso.split('-');
    return '${p[2]}.${p[1]}';
  }

  @override
  Widget build(BuildContext context) {
    final top = List<Map>.from(data['top'] as List);
    final me = data['me'] as Map?;
    final hidden = data['hidden'] == true;
    final toTop = data['to_top'] as int? ?? 0;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('${_date(data['week_start'] as String)} – ${_date(data['week_end'] as String)}',
            style: barlow(size: 14, weight: FontWeight.w600, color: AppColors.ink2)),
        Text('Haftalik TOP-10', style: barlow(size: 28, weight: FontWeight.w700)),
        const SizedBox(height: 4),
        Text('Shu hafta eng koʻp toʻgʻri javob berganlar. Har dushanba yangidan boshlanadi.',
            style: TextStyle(color: AppColors.ink2, height: 1.35)),
        const SizedBox(height: 16),
        _MyCard(
          correct: data['my_correct'] as int,
          rank: me?['rank'] as int?,
          participants: data['participants'] as int,
          hidden: hidden,
        ),
        const SizedBox(height: 16),
        if (top.isEmpty)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(children: [
                Icon(Icons.emoji_events_outlined, size: 48, color: AppColors.primary),
                const SizedBox(height: 8),
                const Text('Shu hafta hali hech kim savol yechmadi. Birinchi boʻling!', textAlign: TextAlign.center),
              ]),
            ),
          )
        else
          Card(
            clipBehavior: Clip.antiAlias,
            child: Column(children: [
              for (var i = 0; i < top.length; i++) ...[
                if (i > 0) Divider(height: 1, color: AppColors.line),
                _Row(r: top[i]),
              ],
            ]),
          ),
        if (toTop > 0) ...[
          const SizedBox(height: 12),
          Text('TOP-10 ga kirish uchun yana $toTop ta toʻgʻri javob kerak.',
              style: const TextStyle(fontSize: 15), textAlign: TextAlign.center),
        ],
        const SizedBox(height: 8),
        TextButton.icon(
          onPressed: onSettings,
          icon: Icon(hidden ? Icons.visibility_off_outlined : Icons.visibility_outlined, size: 18),
          label: Text(hidden ? 'Siz reytingda yashiringansiz — sozlash' : 'Reytingda koʻrinishni sozlash'),
        ),
      ],
    );
  }
}

class _MyCard extends StatelessWidget {
  const _MyCard({required this.correct, required this.rank, required this.participants, required this.hidden});
  final int correct;
  final int? rank;
  final int participants;
  final bool hidden;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(5),
        decoration: BoxDecoration(color: AppColors.primary, borderRadius: BorderRadius.circular(10)),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            border: Border.all(color: Colors.white, width: 2),
            borderRadius: BorderRadius.circular(6),
          ),
          child: Row(children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('Sizning natijangiz', style: TextStyle(color: Colors.white70, fontSize: 14)),
                Text.rich(TextSpan(children: [
                  TextSpan(text: '$correct', style: barlow(size: 36, weight: FontWeight.w700, color: Colors.white)),
                  const TextSpan(text: '  toʻgʻri javob', style: TextStyle(color: Colors.white, fontSize: 15)),
                ])),
              ]),
            ),
            if (rank != null)
              Column(children: [
                Text('$rank', style: barlow(size: 32, weight: FontWeight.w700, color: Colors.white)),
                Text('oʻrin / $participants', style: const TextStyle(color: Colors.white70, fontSize: 13)),
              ])
            else if (hidden)
              const Icon(Icons.visibility_off_outlined, color: Colors.white70),
          ]),
        ),
      );
}

class _Row extends StatelessWidget {
  const _Row({required this.r});
  final Map r;

  @override
  Widget build(BuildContext context) {
    final rank = r['rank'] as int;
    final isMe = r['is_me'] == true;
    final name = r['name'] as String;
    // 1–3 o'rin: ko'k, yashil, qizil doira (palitradan — sariq faqat ogohlantirish uchun)
    final podium = switch (rank) { 1 => AppColors.primary, 2 => AppColors.success, 3 => AppColors.danger, _ => null };
    return Container(
      color: isMe ? AppColors.primarySoft : null,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      child: Row(children: [
        Container(
          width: 36,
          height: 36,
          alignment: Alignment.center,
          decoration: podium != null ? BoxDecoration(color: podium, shape: BoxShape.circle) : null,
          child: Text('$rank',
              style: barlow(size: 18, weight: FontWeight.w700, color: podium != null ? Colors.white : AppColors.ink2)),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Row(children: [
            Flexible(
              child: Text(name,
                  overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            ),
            if (isMe) ...[
              const SizedBox(width: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(color: AppColors.primary, borderRadius: BorderRadius.circular(4)),
                child: const Text('Siz', style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w700)),
              ),
            ],
          ]),
        ),
        Text('${r['correct']}', style: barlow(size: 22, weight: FontWeight.w700)),
        const SizedBox(width: 4),
        Text('toʻgʻri', style: TextStyle(color: AppColors.ink2, fontSize: 13)),
      ]),
    );
  }
}
