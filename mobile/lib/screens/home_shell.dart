import 'package:flutter/material.dart';

import '../updater.dart';
import '../widgets/update_dialog.dart';

import 'exam_start.dart';
import 'home.dart';
import 'profile.dart';
import 'topics.dart';

/// Asosiy ekran: pastki menyu — Bosh, Biletlar, Imtihon, Profil.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;
  // Har tab qayta ochilganda yangilanishi uchun kalit
  final _keys = [GlobalKey(), GlobalKey(), GlobalKey(), GlobalKey()];
  AppUpdate? _update; // "Keyinroq" bosilsa ham ekran pastida eslatma qoladi

  @override
  void initState() {
    super.initState();
    _checkUpdate();
  }

  Future<void> _checkUpdate() async {
    final update = await Updater.check();
    if (update == null || !mounted) return;
    setState(() => _update = update);
    await showUpdateDialog(context, update);
  }

  void _open(int i) => setState(() {
    if (i == _index) return;
    _index = i;
    _keys[i] = GlobalKey(); // tab ochilganda ma'lumot qayta yuklanadi
  });

  @override
  Widget build(BuildContext context) {
    final pages = [
      HomeScreen(key: _keys[0], onOpenTab: _open),
      TopicsScreen(key: _keys[1]),
      ExamStartScreen(key: _keys[2]),
      ProfileScreen(key: _keys[3]),
    ];
    return Scaffold(
      body: IndexedStack(index: _index, children: pages),
      bottomNavigationBar: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (_update != null) UpdateBar(update: _update!, onTap: () => showUpdateDialog(context, _update!)),
          NavigationBar(
            selectedIndex: _index,
            onDestinationSelected: _open,
            destinations: const [
              NavigationDestination(
                icon: Icon(Icons.home_outlined),
                selectedIcon: Icon(Icons.home_rounded),
                label: 'Bosh',
              ),
              NavigationDestination(icon: Icon(Icons.grid_view_rounded), label: 'Biletlar'),
              NavigationDestination(icon: Icon(Icons.timer_outlined), label: 'Imtihon'),
              NavigationDestination(icon: Icon(Icons.person_outline_rounded), label: 'Profil'),
            ],
          ),
        ],
      ),
    );
  }
}
