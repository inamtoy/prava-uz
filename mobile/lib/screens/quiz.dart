import 'dart:async';

import 'package:flutter/material.dart';

import '../api.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'result.dart';

/// Mashq va imtihon uchun umumiy test ekrani.
/// Imtihonda: taymer (serverdagi time_left dan), "Yakunlash" tasdiqlash oynasi, 0 da avtomatik yakunlash.
/// Javob bosilganda darrov to'g'ri/xato ko'rsatiladi; birinchi javob yakuniy (server ham qayta yozmaydi).
class QuizScreen extends StatefulWidget {
  const QuizScreen({super.key, required this.session});
  final Map session;

  @override
  State<QuizScreen> createState() => _QuizScreenState();
}

class _QuizScreenState extends State<QuizScreen> {
  late final int _id = widget.session['id'] as int;
  late final bool _isExam = widget.session['mode'] == 'exam';
  late final List<Map<String, dynamic>> _items =
      (widget.session['items'] as List).map((e) => Map<String, dynamic>.from(e)).toList();
  late int _index = _items.indexWhere((i) => i['answered'] != true).clamp(0, _items.length - 1);
  int? _sending; // javobi yuborilayotgan savol
  int _timeLeft = 0;
  Timer? _timer;
  bool _finishing = false;
  final _navScroll = ScrollController();

  @override
  void initState() {
    super.initState();
    if (_isExam) {
      _timeLeft = (widget.session['time_left'] as int?) ?? 0;
      _timer = Timer.periodic(const Duration(seconds: 1), (_) {
        if (!mounted) return;
        setState(() => _timeLeft = (_timeLeft - 1).clamp(0, 1 << 30));
        if (_timeLeft == 0) _finish(auto: true);
      });
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _navScroll.dispose();
    super.dispose();
  }

  int get _answered => _items.where((i) => i['answered'] == true).length;
  int get _correct => _items.where((i) => i['is_correct'] == true).length;

  void _go(int i) {
    if (i < 0 || i >= _items.length) return;
    setState(() => _index = i);
    if (_navScroll.hasClients) {
      _navScroll.animateTo(
        (i * 46.0 - 120).clamp(0, _navScroll.position.maxScrollExtent),
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOut,
      );
    }
  }

  Future<void> _answer(Map<String, dynamic> item, int answerId) async {
    if (item['answered'] == true || _sending != null || _finishing) return;
    setState(() => _sending = item['question_id'] as int);
    try {
      final r = await Api.instance.post('/sessions/$_id/answer/', {
        'question_id': item['question_id'],
        'answer_id': answerId,
      });
      setState(() {
        item
          ..['answered'] = true
          ..['is_correct'] = r['is_correct']
          ..['selected_answer_id'] = r['selected_answer_id']
          ..['correct_answer_id'] = r['correct_answer_id']
          ..['explanation'] = r['explanation'];
        if (r['time_left'] is int) _timeLeft = r['time_left'] as int;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.expired) {
        await _openResult();
        return;
      }
      showError(context, e);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _sending = null);
    }
  }

  Future<void> _finish({bool auto = false}) async {
    if (_finishing) return;
    if (!auto) {
      final unanswered = _items.length - _answered;
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(_isExam ? 'Imtihonni yakunlaysizmi?' : 'Mashqni yakunlaysizmi?'),
          content: Text(unanswered > 0
              ? 'Javob berilmagan savollar: $unanswered ta.${_isExam ? ' Ular xato hisoblanadi.' : ''}'
              : 'Barcha savollarga javob berdingiz.'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Davom etish')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Yakunlash')),
          ],
        ),
      );
      if (ok != true) return;
    }
    _finishing = true;
    _timer?.cancel();
    try {
      final result = await Api.instance.post('/sessions/$_id/finish/');
      if (!mounted) return;
      Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => ResultScreen(result: result)));
    } catch (e) {
      _finishing = false;
      if (mounted) showError(context, e);
    }
  }

  Future<void> _openResult() async {
    _finishing = true;
    _timer?.cancel();
    try {
      final result = await Api.instance.get('/sessions/$_id/result/');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Imtihon vaqti tugadi.')));
      Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => ResultScreen(result: result)));
    } catch (e) {
      _finishing = false;
      if (mounted) showError(context, e);
    }
  }

  Future<bool> _confirmLeave() async {
    if (!_isExam) return true;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Imtihondan chiqasizmi?'),
        content: const Text('Vaqt toʻxtamaydi. Imtihonni keyin “Imtihon” boʻlimidan davom ettirishingiz mumkin.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Qolish')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Chiqish')),
        ],
      ),
    );
    return ok == true;
  }

  @override
  Widget build(BuildContext context) {
    final item = _items[_index];
    final timerColor = _timeLeft <= 60
        ? AppColors.danger
        : (_timeLeft <= 300 ? AppColors.warning : AppColors.ink);
    return PopScope(
      canPop: !_isExam,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        if (await _confirmLeave() && context.mounted) Navigator.of(context).pop();
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text('${_index + 1} / ${_items.length}'),
          actions: [
            if (_isExam)
              Padding(
                padding: const EdgeInsets.only(right: 4),
                child: Row(children: [
                  Icon(Icons.timer_outlined, color: timerColor, size: 20),
                  const SizedBox(width: 4),
                  Text(formatSeconds(_timeLeft), style: barlow(size: 20, weight: FontWeight.w700, color: timerColor)),
                ]),
              )
            else
              Center(
                child: Text('$_correct / $_answered toʻgʻri',
                    style: const TextStyle(color: AppColors.ink2, fontSize: 14)),
              ),
            TextButton(onPressed: _finishing ? null : () => _finish(), child: const Text('Yakunlash')),
          ],
        ),
        body: Column(children: [
          _NavMap(items: _items, current: _index, controller: _navScroll, onTap: _go),
          const Divider(height: 1),
          Expanded(
            child: ListView(
              key: ValueKey(_index),
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
              children: [
                _QuestionCard(
                  item: item,
                  sending: _sending == item['question_id'],
                  onAnswer: (id) => _answer(item, id),
                ),
              ],
            ),
          ),
          _BottomBar(
            canPrev: _index > 0,
            isLast: _index == _items.length - 1,
            answered: item['answered'] == true,
            isExam: _isExam,
            onPrev: () => _go(_index - 1),
            onNext: () => _go(_index + 1),
            onFinish: () => _finish(),
          ),
        ]),
      ),
    );
  }
}

class _NavMap extends StatelessWidget {
  const _NavMap({required this.items, required this.current, required this.controller, required this.onTap});
  final List<Map<String, dynamic>> items;
  final int current;
  final ScrollController controller;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) => Container(
        color: AppColors.surface,
        height: 58,
        child: ListView.separated(
          controller: controller,
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          itemCount: items.length,
          separatorBuilder: (_, __) => const SizedBox(width: 6),
          itemBuilder: (context, i) {
            final it = items[i];
            final answered = it['answered'] == true;
            final bg = !answered ? AppColors.bg : (it['is_correct'] == true ? AppColors.success : AppColors.danger);
            return InkWell(
              onTap: () => onTap(i),
              borderRadius: BorderRadius.circular(6),
              child: Container(
                width: 40,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: bg,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: i == current ? AppColors.primary : (answered ? bg : AppColors.line),
                    width: i == current ? 2.5 : 1.5,
                  ),
                ),
                child: Text('${i + 1}',
                    style: barlow(size: 16, weight: FontWeight.w600, color: answered ? Colors.white : AppColors.ink)),
              ),
            );
          },
        ),
      );
}

class _QuestionCard extends StatelessWidget {
  const _QuestionCard({required this.item, required this.sending, required this.onAnswer});
  final Map<String, dynamic> item;
  final bool sending;
  final ValueChanged<int> onAnswer;

  @override
  Widget build(BuildContext context) {
    final answered = item['answered'] == true;
    final selected = item['selected_answer_id'];
    final correct = item['correct_answer_id'];
    final answers = item['answers'] as List;
    final explanation = (item['explanation'] as String?) ?? '';
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      if (item['image'] != null) ...[
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: Image.network(
            item['image'] as String,
            fit: BoxFit.contain,
            loadingBuilder: (c, child, p) =>
                p == null ? child : const AspectRatio(aspectRatio: 4 / 3, child: Center(child: CircularProgressIndicator())),
            errorBuilder: (c, e, s) => Container(
              height: 120,
              color: AppColors.line,
              alignment: Alignment.center,
              child: const Text('Rasm yuklanmadi', style: TextStyle(color: AppColors.ink2)),
            ),
          ),
        ),
        const SizedBox(height: 14),
      ],
      Text(item['text'] as String, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600, height: 1.35)),
      const SizedBox(height: 16),
      for (var n = 0; n < answers.length; n++) ...[
        _AnswerButton(
          number: n + 1,
          text: answers[n]['text'] as String,
          state: !answered
              ? _AnswerState.idle
              : answers[n]['id'] == correct
                  ? _AnswerState.correct
                  : (answers[n]['id'] == selected ? _AnswerState.wrong : _AnswerState.dim),
          onTap: answered || sending ? null : () => onAnswer(answers[n]['id'] as int),
        ),
        const SizedBox(height: 10),
      ],
      if (sending) const LinearProgressIndicator(),
      if (answered) ...[
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: item['is_correct'] == true ? AppColors.successSoft : AppColors.dangerSoft,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(
              item['is_correct'] == true ? 'Toʻgʻri!' : 'Notoʻgʻri',
              style: barlow(
                size: 18,
                weight: FontWeight.w700,
                color: item['is_correct'] == true ? AppColors.success : AppColors.danger,
              ),
            ),
            if (explanation.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(explanation, style: const TextStyle(fontSize: 16, height: 1.4)),
            ],
          ]),
        ),
      ],
    ]);
  }
}

enum _AnswerState { idle, correct, wrong, dim }

class _AnswerButton extends StatelessWidget {
  const _AnswerButton({required this.number, required this.text, required this.state, this.onTap});
  final int number;
  final String text;
  final _AnswerState state;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final (bg, border, badge) = switch (state) {
      _AnswerState.correct => (AppColors.successSoft, AppColors.success, AppColors.success),
      _AnswerState.wrong => (AppColors.dangerSoft, AppColors.danger, AppColors.danger),
      _AnswerState.dim => (AppColors.surface, AppColors.line, AppColors.ink2),
      _AnswerState.idle => (AppColors.surface, AppColors.line, AppColors.primary),
    };
    return Material(
      color: bg,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(color: border, width: state == _AnswerState.idle || state == _AnswerState.dim ? 1.5 : 2),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 56),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Row(children: [
              Container(
                width: 34,
                height: 34,
                alignment: Alignment.center,
                decoration: BoxDecoration(color: badge, borderRadius: BorderRadius.circular(6)),
                child: Text('F$number', style: barlow(size: 14, weight: FontWeight.w700, color: Colors.white)),
              ),
              const SizedBox(width: 12),
              Expanded(child: Text(text, style: const TextStyle(fontSize: 16, height: 1.3))),
              if (state == _AnswerState.correct) const Icon(Icons.check_circle, color: AppColors.success),
              if (state == _AnswerState.wrong) const Icon(Icons.cancel, color: AppColors.danger),
            ]),
          ),
        ),
      ),
    );
  }
}

class _BottomBar extends StatelessWidget {
  const _BottomBar({
    required this.canPrev,
    required this.isLast,
    required this.answered,
    required this.isExam,
    required this.onPrev,
    required this.onNext,
    required this.onFinish,
  });
  final bool canPrev, isLast, answered, isExam;
  final VoidCallback onPrev, onNext, onFinish;

  @override
  Widget build(BuildContext context) => Container(
        color: AppColors.surface,
        padding: EdgeInsets.fromLTRB(16, 10, 16, 10 + MediaQuery.of(context).padding.bottom),
        child: Row(children: [
          Expanded(
            child: OutlinedButton(onPressed: canPrev ? onPrev : null, child: const Text('‹ Oldingi')),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: isLast
                ? FilledButton(onPressed: onFinish, child: Text(isExam ? 'Yakunlash' : 'Natijani koʻrish'))
                : FilledButton(
                    onPressed: onNext,
                    child: Text(!isExam && answered ? 'Keyingi savol' : 'Keyingi ›'),
                  ),
          ),
        ]),
      );
}
