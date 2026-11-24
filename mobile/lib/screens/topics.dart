import 'package:flutter/material.dart';

import '../api.dart';
import '../theme.dart';
import '../widgets/common.dart';

/// Biletlar: ixcham katakchalar (raqam + progress), bosilganda mashq boshlanadi.
class TopicsScreen extends StatefulWidget {
  const TopicsScreen({super.key});

  @override
  State<TopicsScreen> createState() => _TopicsScreenState();
}

class _TopicsScreenState extends State<TopicsScreen> {
  late Future<List<dynamic>> _future = _load();

  Future<List<dynamic>> _load() async => List<dynamic>.from(await Api.instance.get('/topics/'));

  void _reload() => setState(() => _future = _load());

  Future<void> _open(Map topic) async {
    await startPractice(context, topic['slug'] as String);
    if (mounted) _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Row(children: [Logo(size: 30), SizedBox(width: 10), Text('Biletlar')]),
      ),
      body: FutureBuilder<List<dynamic>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            final e = snap.error;
            if (e is ApiException && e.unauthorized) {
              WidgetsBinding.instance.addPostFrameCallback((_) => showError(context, e));
            }
            return ErrorView(message: e.toString(), onRetry: _reload);
          }
          final topics = snap.data!;
          if (topics.isEmpty) {
            return ErrorView(message: 'Hozircha biletlar yoʻq.', onRetry: _reload);
          }
          final total = topics.fold<int>(0, (s, t) => s + (t['question_count'] as int? ?? 0));
          final solved = topics.fold<double>(
              0, (s, t) => s + (t['question_count'] as int? ?? 0) * (t['progress'] as int) / 100);
          final overall = total == 0 ? 0 : (solved * 100 / total).round();
          return RefreshIndicator(
            onRefresh: () async => _reload(),
            child: CustomScrollView(
              slivers: [
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                  sliver: SliverToBoxAdapter(child: _Overview(percent: overall, total: total, solved: solved.round())),
                ),
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                  sliver: SliverGrid(
                    gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                      maxCrossAxisExtent: 96,
                      mainAxisSpacing: 10,
                      crossAxisSpacing: 10,
                      childAspectRatio: .9,
                    ),
                    delegate: SliverChildBuilderDelegate(
                      (context, i) => _TicketTile(topic: topics[i], onTap: () => _open(topics[i])),
                      childCount: topics.length,
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _Overview extends StatelessWidget {
  const _Overview({required this.percent, required this.total, required this.solved});
  final int percent;
  final int total;
  final int solved;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(color: AppColors.primary, borderRadius: BorderRadius.circular(10)),
        foregroundDecoration: BoxDecoration(
          // "Yo'l belgisi" paneli: oq ichki hoshiya
          border: Border.all(color: Colors.white, width: 2),
          borderRadius: BorderRadius.circular(6),
        ),
        margin: EdgeInsets.zero,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Umumiy tayyorgarlik', style: barlow(size: 15, weight: FontWeight.w500, color: Colors.white70)),
          const SizedBox(height: 4),
          Text('$percent%', style: barlow(size: 36, weight: FontWeight.w700, color: Colors.white)),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: percent / 100,
              minHeight: 8,
              backgroundColor: Colors.white24,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 8),
          Text('$solved / $total savol mashqda toʻgʻri yechilgan',
              style: const TextStyle(color: Colors.white, fontSize: 14)),
        ]),
      );
}

class _TicketTile extends StatelessWidget {
  const _TicketTile({required this.topic, required this.onTap});
  final Map topic;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final p = topic['progress'] as int;
    final color = p >= 90 ? AppColors.success : (p > 0 ? AppColors.primary : AppColors.line);
    return Material(
      color: AppColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(color: p >= 90 ? AppColors.success : AppColors.line, width: 1.5),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(8),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Text('${topic['order']}', style: barlow(size: 24, weight: FontWeight.w700)),
            Text('bilet', style: TextStyle(fontSize: 12, color: AppColors.ink2)),
            const SizedBox(height: 6),
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(
                value: p / 100,
                minHeight: 4,
                backgroundColor: AppColors.bg,
                color: color,
              ),
            ),
          ]),
        ),
      ),
    );
  }
}
