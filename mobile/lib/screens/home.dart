import 'package:flutter/material.dart';

import '../api.dart';
import '../settings.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/motion.dart';
import 'quiz.dart';

/// Bosh ekran: davom ettirish, kunlik maqsad, seriya, "Xatolarim" va bo'limlar.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.onOpenTab});

  /// HomeShell'dagi tabni ochish: 1 — Biletlar, 2 — Imtihon, 3 — Reyting, 4 — Profil.
  final ValueChanged<int> onOpenTab;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<dynamic> _future = Api.instance.get('/home/');
  bool _busy = false;

  void _reload() => setState(() => _future = Api.instance.get('/home/'));

  Future<void> _openSession(Future<dynamic> Function() request) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final session = await request();
      if (!mounted) return;
      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => QuizScreen(session: session)));
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) {
        setState(() => _busy = false);
        _reload();
      }
    }
  }

  Future<void> _resume(Map current) => _openSession(
    () => current['mode'] == 'exam'
        ? Api.instance.post('/exams/') // ochiq imtihonni davom ettiradi
        : Api.instance.get('/sessions/${current['id']}/'),
  );

  Future<void> _pickGoal(int goal, List<int> choices) async {
    final picked = await showModalBottomSheet<int>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Kunlik maqsad', style: barlow(size: 22, weight: FontWeight.w700)),
              const SizedBox(height: 4),
              Text('Har kuni nechta savol yechmoqchisiz?', style: TextStyle(color: AppColors.ink2)),
              const SizedBox(height: 16),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  for (final c in choices)
                    ChoiceChip(
                      label: Text('$c ta', style: barlow(size: 17, weight: FontWeight.w600)),
                      selected: c == goal,
                      onSelected: (_) => Navigator.pop(ctx, c),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
    if (picked == null || picked == goal) return;
    try {
      await Api.instance.post('/me/goal/', {'daily_goal': picked});
      _reload();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Row(children: [Logo(size: 30), SizedBox(width: 10), Text('Prava.uz')])),
      body: FutureBuilder<dynamic>(
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
          final data = Map<String, dynamic>.from(snap.data as Map);
          return RefreshIndicator(
            onRefresh: () async => _reload(),
            child: HomeDashboard(
              data: data,
              userName: _userName(),
              busy: _busy,
              onResume: _resume,
              onMistakes: () => _openSession(() => Api.instance.post('/mistakes/')),
              onGoal: () => _pickGoal(data['daily']['goal'] as int, List<int>.from(data['goal_choices'] as List)),
              onOpenTab: widget.onOpenTab,
            ),
          );
        },
      ),
    );
  }

  String _userName() {
    final u = Api.instance.user ?? const {};
    final first = u['first_name'] as String?;
    return (first != null && first.isNotEmpty) ? first : (u['username'] as String? ?? '');
  }
}

/// Bosh ekran tarkibi — faqat ma'lumotdan chiziladi (testlash uchun alohida).
class HomeDashboard extends StatelessWidget {
  const HomeDashboard({
    super.key,
    required this.data,
    required this.userName,
    required this.onResume,
    required this.onMistakes,
    required this.onGoal,
    required this.onOpenTab,
    this.busy = false,
  });

  final Map<String, dynamic> data;
  final String userName;
  final bool busy;
  final ValueChanged<Map> onResume;
  final VoidCallback onMistakes;
  final VoidCallback onGoal;
  final ValueChanged<int> onOpenTab;

  @override
  Widget build(BuildContext context) {
    final daily = Map<String, dynamic>.from(data['daily'] as Map);
    final current = data['current'] as Map?;
    final mistakes = data['mistakes_count'] as int;
    final overall = Map<String, dynamic>.from(data['overall'] as Map);
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
      children: [
        Text(userName.isEmpty ? 'Salom!' : 'Salom, $userName!', style: barlow(size: 26, weight: FontWeight.w700)),
        const SizedBox(height: 14),
        if (current != null) ...[
          _ResumeCard(current: current, onTap: busy ? null : () => onResume(current)),
          const SizedBox(height: 12),
        ],
        _GoalCard(daily: daily, onGoal: onGoal),
        const SizedBox(height: 12),
        _StreakCard(daily: daily),
        const SizedBox(height: 12),
        _MistakesCard(count: mistakes, busy: busy, onStart: onMistakes),
        const SizedBox(height: 20),
        Text('Boʻlimlar', style: barlow(size: 20, weight: FontWeight.w700)),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: _Tile(icon: Icons.grid_view_rounded, label: 'Biletlar', onTap: () => onOpenTab(1)),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _Tile(icon: Icons.timer_outlined, label: 'Imtihon', onTap: () => onOpenTab(2)),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _Tile(icon: Icons.emoji_events_rounded, label: 'Reyting', onTap: () => onOpenTab(3)),
            ),
          ],
        ),
        const SizedBox(height: 20),
        _Overall(percent: overall['percent'] as int, solved: overall['solved'] as int, total: overall['total'] as int),
      ],
    );
  }
}

/// Ko'k axborot belgisi uslubidagi panel: oq ichki hoshiya.
class _SignPanel extends StatelessWidget {
  const _SignPanel({required this.child, this.onTap});
  final Widget child;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Material(
    color: AppColors.primary,
    borderRadius: BorderRadius.circular(10),
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        margin: const EdgeInsets.all(5),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.white, width: 2),
          borderRadius: BorderRadius.circular(6),
        ),
        child: child,
      ),
    ),
  );
}

class _ResumeCard extends StatelessWidget {
  const _ResumeCard({required this.current, required this.onTap});
  final Map current;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final isExam = current['mode'] == 'exam';
    final what = isExam
        ? 'Imtihon · ${((current['time_left'] as int? ?? 0) ~/ 60)} daqiqa qoldi'
        : (current['topic'] as String? ?? 'Xatolar ustida ishlash');
    return _SignPanel(
      onTap: onTap,
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(4)),
            child: Icon(Icons.play_arrow_rounded, color: AppColors.primary, size: 30),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Davom ettirish',
                  style: barlow(size: 20, weight: FontWeight.w700, color: Colors.white),
                ),
                Text(
                  '$what · ${current['answered_count']} / ${current['total_questions']} javob',
                  style: const TextStyle(color: Colors.white, fontSize: 14),
                ),
              ],
            ),
          ),
          const Icon(Icons.arrow_forward_rounded, color: Colors.white),
        ],
      ),
    );
  }
}

class _GoalCard extends StatelessWidget {
  const _GoalCard({required this.daily, required this.onGoal});
  final Map<String, dynamic> daily;
  final VoidCallback onGoal;

  @override
  Widget build(BuildContext context) {
    final goal = daily['goal'] as int;
    final today = daily['today'] as int;
    final reached = daily['reached'] == true;
    final left = daily['left'] as int;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            GoalRing(
              value: goal == 0 ? 0 : today / goal,
              color: reached ? AppColors.success : AppColors.primary,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('$today', style: barlow(size: 30, weight: FontWeight.w700)),
                  Text(
                    '/ $goal',
                    style: barlow(size: 14, weight: FontWeight.w600, color: AppColors.ink2),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'KUNLIK MAQSAD',
                    style: barlow(size: 13, weight: FontWeight.w600, color: AppColors.ink2),
                  ),
                  const SizedBox(height: 4),
                  if (reached)
                    Row(
                      children: [
                        Icon(Icons.check_circle, color: AppColors.success, size: 20),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            'Bajarildi!',
                            style: barlow(size: 20, weight: FontWeight.w700, color: AppColors.success),
                          ),
                        ),
                      ],
                    )
                  else
                    Text(
                      today == 0 ? 'Bugun hali savol yechilmadi' : 'Yana $left ta savol qoldi',
                      style: const TextStyle(fontSize: 16, height: 1.3),
                    ),
                  const SizedBox(height: 8),
                  TextButton.icon(
                    onPressed: onGoal,
                    style: TextButton.styleFrom(padding: EdgeInsets.zero, minimumSize: const Size(0, 36)),
                    icon: const Icon(Icons.tune_rounded, size: 18),
                    label: Text('Maqsad: $goal ta'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StreakCard extends StatelessWidget {
  const _StreakCard({required this.daily});
  final Map<String, dynamic> daily;

  @override
  Widget build(BuildContext context) {
    final streak = daily['streak'] as int;
    final week = List<Map>.from(daily['week'] as List);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Row(
              children: [
                _Flame(on: streak > 0),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'SERIYA',
                        style: barlow(size: 13, weight: FontWeight.w600, color: AppColors.ink2),
                      ),
                      Text.rich(
                        TextSpan(
                          children: [
                            TextSpan(
                              text: '$streak',
                              style: barlow(size: 28, weight: FontWeight.w700),
                            ),
                            TextSpan(
                              text: ' kun ketma-ket',
                              style: TextStyle(fontSize: 16, color: AppColors.ink2),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                for (final w in week)
                  Expanded(
                    child: Column(
                      children: [
                        _DayDot(day: w),
                        const SizedBox(height: 4),
                        Text(
                          w['label'] as String,
                          style: TextStyle(
                            fontSize: 12,
                            color: w['is_today'] == true ? AppColors.primary : AppColors.ink2,
                            fontWeight: w['is_today'] == true ? FontWeight.w700 : FontWeight.w400,
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _DayDot extends StatelessWidget {
  const _DayDot({required this.day});
  final Map day;

  @override
  Widget build(BuildContext context) {
    final done = day['reached'] == true;
    final part = !done && (day['count'] as int) > 0;
    final isToday = day['is_today'] == true;
    return Container(
      width: 34,
      height: 34,
      decoration: BoxDecoration(
        color: done ? AppColors.success : (part ? AppColors.primarySoft : AppColors.bg),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: isToday ? AppColors.primary : (done ? AppColors.success : AppColors.line),
          width: isToday ? 2 : 1.5,
        ),
      ),
      child: done ? const Icon(Icons.check_rounded, color: Colors.white, size: 20) : null,
    );
  }
}

/// Seriya belgisi: faol bo'lsa qizil doirada "yonib turgan" olov.
class _Flame extends StatefulWidget {
  const _Flame({required this.on});
  final bool on;

  @override
  State<_Flame> createState() => _FlameState();
}

class _FlameState extends State<_Flame> with SingleTickerProviderStateMixin {
  late final _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 1600));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (widget.on && AppSettings.motionOn(context) && !_c.isAnimating) _c.repeat(reverse: true);
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Container(
    width: 52,
    height: 52,
    decoration: BoxDecoration(color: widget.on ? AppColors.danger : AppColors.bg, shape: BoxShape.circle),
    child: ScaleTransition(
      scale: Tween(begin: 1.0, end: 1.12).animate(CurvedAnimation(parent: _c, curve: Curves.easeInOut)),
      child: Icon(
        Icons.local_fire_department_rounded,
        size: 30,
        color: widget.on ? Colors.white : AppColors.ink2.withValues(alpha: .5),
      ),
    ),
  );
}

class _MistakesCard extends StatelessWidget {
  const _MistakesCard({required this.count, required this.busy, required this.onStart});
  final int count;
  final bool busy;
  final VoidCallback onStart;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: count > 0 ? AppColors.danger : AppColors.successSoft,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  count > 0 ? Icons.gps_fixed_rounded : Icons.done_all_rounded,
                  color: count > 0 ? Colors.white : AppColors.success,
                  size: 28,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'XATOLARIM',
                      style: barlow(size: 13, weight: FontWeight.w600, color: AppColors.ink2),
                    ),
                    Text(count > 0 ? '$count ta savol' : 'Xato yoʻq', style: barlow(size: 22, weight: FontWeight.w700)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            count > 0
                ? 'Har birini 2 marta ketma-ket toʻgʻri yeching — roʻyxatdan chiqadi.'
                : 'Biletlarni yechganingizda xato qilingan savollar shu yerga yigʻiladi.',
            style: TextStyle(color: AppColors.ink2, height: 1.35),
          ),
          if (count > 0) ...[
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: busy ? null : onStart,
              icon: const Icon(Icons.bolt_rounded),
              label: const Text('Xatolar ustida ishlash'),
            ),
          ],
        ],
      ),
    ),
  );
}

class _Tile extends StatelessWidget {
  const _Tile({required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
    color: AppColors.surface,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(10),
      side: BorderSide(color: AppColors.line),
    ),
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 6),
        child: Column(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(color: AppColors.primary, borderRadius: BorderRadius.circular(6)),
              child: Icon(icon, color: Colors.white),
            ),
            const SizedBox(height: 8),
            Text(
              label,
              style: barlow(size: 15, weight: FontWeight.w600),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    ),
  );
}

class _Overall extends StatelessWidget {
  const _Overall({required this.percent, required this.solved, required this.total});
  final int percent, solved, total;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Row(
        children: [
          const Expanded(child: Text('Umumiy tayyorgarlik', style: TextStyle(fontSize: 15))),
          Text('$percent%', style: barlow(size: 18, weight: FontWeight.w700)),
        ],
      ),
      const SizedBox(height: 6),
      ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: TweenAnimationBuilder<double>(
          tween: Tween(begin: 0, end: percent / 100),
          duration: const Duration(milliseconds: 900),
          curve: Curves.easeOutCubic,
          builder: (context, v, _) => LinearProgressIndicator(
            value: v,
            minHeight: 8,
            backgroundColor: AppColors.line,
            color: AppColors.primary,
          ),
        ),
      ),
      const SizedBox(height: 6),
      Text(
        '$solved / $total savol mashqda toʻgʻri yechilgan',
        style: TextStyle(color: AppColors.ink2, fontSize: 13),
      ),
    ],
  );
}
