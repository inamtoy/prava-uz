import 'package:flutter/material.dart';

import 'exam_start.dart';
import 'profile.dart';
import 'topics.dart';

/// Asosiy ekran: pastki menyu — Biletlar, Imtihon, Profil.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;
  // Har tab qayta ochilganda yangilanishi uchun kalit
  final _keys = [GlobalKey(), GlobalKey(), GlobalKey()];

  @override
  Widget build(BuildContext context) {
    final pages = [
      TopicsScreen(key: _keys[0]),
      ExamStartScreen(key: _keys[1]),
      ProfileScreen(key: _keys[2]),
    ];
    return Scaffold(
      body: IndexedStack(index: _index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() {
          if (i == _index) return;
          _index = i;
          _keys[i] = GlobalKey(); // tab ochilganda ma'lumot qayta yuklanadi
        }),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.grid_view_rounded), label: 'Biletlar'),
          NavigationDestination(icon: Icon(Icons.timer_outlined), label: 'Imtihon'),
          NavigationDestination(icon: Icon(Icons.person_outline_rounded), label: 'Profil'),
        ],
      ),
    );
  }
}
