import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:prava_uz/screens/auth.dart';
import 'package:prava_uz/screens/quiz.dart';
import 'package:prava_uz/screens/result.dart';

Map<String, dynamic> _item(int n, {bool answered = false, bool correct = false}) => {
      'question_id': n,
      'order': n,
      'text': 'Savol $n',
      'image': null,
      'answers': [
        {'id': n * 10 + 1, 'text': 'Javob A$n'},
        {'id': n * 10 + 2, 'text': 'Javob B$n'},
      ],
      'answered': answered,
      if (answered) ...{
        'is_correct': correct,
        'selected_answer_id': n * 10 + 2,
        'correct_answer_id': n * 10 + 1,
        'explanation': 'Izoh $n',
      },
    };

Widget _app(Widget home) => MaterialApp(home: home);

void main() {
  setUpAll(() => GoogleFonts.config.allowRuntimeFetching = false);

  testWidgets('Login ekrani bo\'sh formada xato ko\'rsatadi', (tester) async {
    await tester.pumpWidget(_app(const LoginScreen()));
    await tester.tap(find.text('Kirish'));
    await tester.pump();
    expect(find.text('Login va parolni kiriting.'), findsOneWidget);
  });

  testWidgets('Mashq: birinchi javobsiz savoldan boshlanadi, javob berilganida izoh ko\'rinadi', (tester) async {
    final session = {
      'id': 1,
      'mode': 'practice',
      'time_left': null,
      'items': [_item(1, answered: true, correct: false), _item(2)],
    };
    await tester.pumpWidget(_app(QuizScreen(session: session)));
    expect(find.text('2 / 2'), findsOneWidget);
    expect(find.text('Savol 2'), findsOneWidget);

    await tester.tap(find.text('‹ Oldingi'));
    await tester.pump();
    expect(find.text('Savol 1'), findsOneWidget);
    expect(find.text('Notoʻgʻri'), findsOneWidget);
    expect(find.text('Izoh 1'), findsOneWidget);
  });

  testWidgets('Imtihon: taymer serverdagi qiymatdan boshlanadi', (tester) async {
    final session = {
      'id': 2,
      'mode': 'exam',
      'time_left': 299,
      'items': [_item(1), _item(2)],
    };
    await tester.pumpWidget(_app(QuizScreen(session: session)));
    expect(find.text('04:59'), findsOneWidget);
    await tester.pump(const Duration(seconds: 1));
    expect(find.text('04:58'), findsOneWidget);
  });

  testWidgets('Natija: o\'tdi va xatolar tahlili', (tester) async {
    await tester.pumpWidget(_app(const ResultScreen(result: {
      'mode': 'exam',
      'status': 'finished',
      'is_passed': true,
      'score': 18,
      'total_questions': 20,
      'percent': 90,
      'elapsed_seconds': 600,
      'topic': null,
      'mistakes': [
        {'order': 3, 'text': 'Savol 3', 'image': null, 'selected_answer': null, 'correct_answer': 'A', 'explanation': ''},
      ],
    })));
    expect(find.text('Imtihondan oʻtdingiz!'), findsOneWidget);
    expect(find.text('18 / 20'), findsOneWidget);
    expect(find.textContaining('Javob berilmagan', findRichText: true), findsOneWidget);
  });
}
