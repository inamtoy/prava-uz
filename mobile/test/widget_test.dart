import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:prava_uz/screens/auth.dart';
import 'package:prava_uz/screens/home.dart';
import 'package:prava_uz/screens/quiz.dart';
import 'package:prava_uz/screens/result.dart';
import 'package:prava_uz/updater.dart';
import 'package:prava_uz/widgets/update_dialog.dart';

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

  testWidgets('Bosh ekran: kunlik maqsad, seriya, xatolar va davom ettirish', (tester) async {
    var mistakesTapped = 0;
    var openedTab = -1;
    Map? resumed;
    final data = {
      'daily': {
        'goal': 20,
        'today': 12,
        'percent': 60,
        'reached': false,
        'left': 8,
        'streak': 3,
        'week': [
          for (var i = 0; i < 7; i++)
            {'date': '2026-11-${19 + i}', 'label': ['Ch', 'Pa', 'Ju', 'Sh', 'Ya', 'Du', 'Se'][i], 'count': i == 6 ? 12 : 20, 'reached': i != 6, 'is_today': i == 6},
        ],
      },
      'goal_choices': [10, 20, 30, 50],
      'mistakes_count': 5,
      'current': {'id': 9, 'mode': 'practice', 'topic': '7-bilet', 'answered_count': 4, 'total_questions': 15, 'time_left': null},
      'overall': {'percent': 40, 'solved': 540, 'total': 1350},
    };
    await tester.pumpWidget(_app(Scaffold(
      body: HomeDashboard(
        data: data,
        userName: 'Ali',
        onResume: (c) => resumed = c,
        onMistakes: () => mistakesTapped++,
        onGoal: () {},
        onOpenTab: (i) => openedTab = i,
      ),
    )));
    await tester.pump(const Duration(seconds: 1)); // olov animatsiyasi takrorlanadi — pumpAndSettle tugamaydi
    expect(find.text('Salom, Ali!'), findsOneWidget);
    expect(find.text('Yana 8 ta savol qoldi'), findsOneWidget);
    expect(find.text('5 ta savol'), findsOneWidget);
    expect(find.textContaining('7-bilet · 4 / 15 javob'), findsOneWidget);
    expect(find.text('3 kun ketma-ket', findRichText: true), findsOneWidget); // seriya

    await tester.tap(find.text('Davom ettirish'));
    expect(resumed?['id'], 9);
    await tester.ensureVisible(find.text('Xatolar ustida ishlash'));
    await tester.pump();
    await tester.tap(find.text('Xatolar ustida ishlash'));
    expect(mistakesTapped, 1);
    await tester.ensureVisible(find.text('Imtihon'));
    await tester.pump();
    await tester.tap(find.text('Imtihon'));
    expect(openedTab, 2);
  });

  testWidgets('Xatolar mashqi natijasi: hammasi togri — konfetti va tabrik', (tester) async {
    await tester.pumpWidget(_app(const ResultScreen(result: {
      'mode': 'mistakes',
      'status': 'finished',
      'is_passed': null,
      'score': 3,
      'total_questions': 3,
      'percent': 100,
      'elapsed_seconds': 40,
      'topic': null,
      'mistakes': [],
    })));
    expect(find.text('Xatolar ustida ishlash'), findsNWidgets(2)); // AppBar + sarlavha
    expect(find.text('Hammasi toʻgʻri — barakalla!'), findsOneWidget);
    await tester.pumpAndSettle();
  });

  testWidgets('Yangilash oynasi: versiya, nima yangi, tugmalar', (tester) async {
    AppUpdate upd({bool required = false}) => AppUpdate({
          'version_code': 3,
          'version_name': '0.2.1',
          'notes': 'Xatolarim va kunlik maqsad',
          'apk_url': 'http://x/media/app/p.apk',
          'size': 5 * 1024 * 1024,
          'required': required,
        }, 2);

    await tester.pumpWidget(_app(Scaffold(body: UpdateDialog(update: upd()))));
    expect(find.text('Yangi versiya: 0.2.1'), findsOneWidget);
    expect(find.text('Xatolarim va kunlik maqsad'), findsOneWidget);
    expect(find.text('Hajmi: 5.0 MB'), findsOneWidget);
    expect(find.text('Keyinroq'), findsOneWidget);
    expect(find.text('Yangilash'), findsOneWidget);

    await tester.pumpWidget(_app(Scaffold(body: UpdateDialog(update: upd(required: true)))));
    expect(find.text('Keyinroq'), findsNothing); // majburiy — yopib bo'lmaydi
    expect(find.textContaining('majburiy'), findsOneWidget);
  });
}
