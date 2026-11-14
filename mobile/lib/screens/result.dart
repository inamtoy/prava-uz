import 'package:flutter/material.dart';

import '../theme.dart';
import '../widgets/common.dart';

/// Natija: ball, o'tdi/o'tmadi, vaqt va xatolar tahlili.
class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key, required this.result});
  final Map result;

  @override
  Widget build(BuildContext context) {
    final isExam = result['mode'] == 'exam';
    final passed = result['is_passed'] == true;
    final mistakes = List<Map>.from(result['mistakes'] as List);
    final headColor = !isExam ? AppColors.primary : (passed ? AppColors.success : AppColors.danger);
    return Scaffold(
      appBar: AppBar(title: Text(isExam ? 'Imtihon natijasi' : 'Mashq natijasi')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(color: headColor, borderRadius: BorderRadius.circular(10)),
            child: Column(children: [
              if (isExam)
                Text(passed ? 'Imtihondan oʻtdingiz!' : 'Imtihondan oʻtmadingiz',
                    style: barlow(size: 22, weight: FontWeight.w700, color: Colors.white))
              else if (result['topic'] != null)
                Text('${result['topic']}', style: barlow(size: 22, weight: FontWeight.w700, color: Colors.white)),
              const SizedBox(height: 8),
              Text('${result['score']} / ${result['total_questions']}',
                  style: barlow(size: 44, weight: FontWeight.w700, color: Colors.white)),
              Text('${result['percent']}% · vaqt ${formatSeconds(result['elapsed_seconds'] as int)}',
                  style: const TextStyle(color: Colors.white, fontSize: 15)),
              if (result['status'] == 'expired') ...[
                const SizedBox(height: 6),
                const Text('Vaqt tugagani uchun avtomatik yakunlandi',
                    style: TextStyle(color: Colors.white70, fontSize: 14)),
              ],
            ]),
          ),
          const SizedBox(height: 20),
          Text(
            mistakes.isEmpty ? 'Xatolar yoʻq — barakalla!' : 'Xatolar tahlili (${mistakes.length})',
            style: barlow(size: 20, weight: FontWeight.w700),
          ),
          const SizedBox(height: 10),
          for (final m in mistakes) ...[
            _MistakeCard(m: m),
            const SizedBox(height: 12),
          ],
          const SizedBox(height: 8),
          FilledButton(
            onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst),
            child: const Text('Bosh sahifaga'),
          ),
        ],
      ),
    );
  }
}

class _MistakeCard extends StatelessWidget {
  const _MistakeCard({required this.m});
  final Map m;

  Widget _line(String label, String? text, Color color, Color bg) => Container(
        width: double.infinity,
        margin: const EdgeInsets.only(top: 8),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(6),
          border: Border(left: BorderSide(color: color, width: 4)),
        ),
        child: RichText(
          text: TextSpan(style: const TextStyle(color: AppColors.ink, fontSize: 15, height: 1.35), children: [
            TextSpan(text: '$label: ', style: TextStyle(fontWeight: FontWeight.w700, color: color)),
            TextSpan(text: text ?? 'Javob berilmagan'),
          ]),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final explanation = (m['explanation'] as String?) ?? '';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${m['order']}-savol', style: const TextStyle(color: AppColors.ink2, fontSize: 13)),
          const SizedBox(height: 6),
          if (m['image'] != null) ...[
            ClipRRect(borderRadius: BorderRadius.circular(6), child: Image.network(m['image'] as String)),
            const SizedBox(height: 10),
          ],
          Text(m['text'] as String, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          _line('Siz tanlagan', m['selected_answer'] as String?, AppColors.danger, AppColors.dangerSoft),
          _line('Toʻgʻri javob', m['correct_answer'] as String?, AppColors.success, AppColors.successSoft),
          if (explanation.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(explanation, style: const TextStyle(color: AppColors.ink2, height: 1.4)),
          ],
        ]),
      ),
    );
  }
}
