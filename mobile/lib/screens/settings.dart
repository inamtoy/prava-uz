import 'package:flutter/material.dart';

import '../api.dart';
import '../settings.dart';
import '../theme.dart';
import '../updater.dart';
import '../widgets/common.dart';
import '../widgets/update_dialog.dart';
import 'auth.dart';

/// Sozlamalar: ko'rinish, javob berganda (vibratsiya/ovoz/animatsiya), profil, parol, ilova haqida.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _s = AppSettings.instance;
  String? _version;
  bool _checking = false;

  @override
  void initState() {
    super.initState();
    _s.addListener(_refresh);
    Updater.currentVersionName().then((v) {
      if (mounted) setState(() => _version = v);
    });
  }

  @override
  void dispose() {
    _s.removeListener(_refresh);
    super.dispose();
  }

  void _refresh() => setState(() {});

  Map get _user => Api.instance.user ?? const {};

  Future<void> _saveProfile(Map<String, dynamic> changes, String done) async {
    try {
      final u = await Api.instance.post('/me/', changes);
      Api.instance.user = Map<String, dynamic>.from(u as Map);
      if (!mounted) return;
      setState(() {});
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(done)));
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  Future<void> _editText({required String title, required String field, required String initial, TextInputType? type}) async {
    final c = TextEditingController(text: initial);
    final value = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: c,
          autofocus: true,
          keyboardType: type,
          textInputAction: TextInputAction.done,
          onSubmitted: (v) => Navigator.pop(ctx, v.trim()),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Bekor qilish')),
          FilledButton(onPressed: () => Navigator.pop(ctx, c.text.trim()), child: const Text('Saqlash')),
        ],
      ),
    );
    if (value == null || value.isEmpty || value == initial) return;
    await _saveProfile({field: value}, 'Saqlandi.');
  }

  Future<void> _changePassword() async {
    final ok = await showDialog<bool>(context: context, builder: (_) => const _PasswordDialog());
    if (ok == true && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Parol oʻzgartirildi.')));
    }
  }

  Future<void> _checkUpdate() async {
    setState(() => _checking = true);
    final update = await Updater.check();
    if (!mounted) return;
    setState(() => _checking = false);
    if (update != null) {
      await showUpdateDialog(context, update);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Sizda eng soʻnggi versiya.')));
    }
  }

  Future<void> _logout() async {
    await Api.instance.logout();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const LoginScreen()), (_) => false);
  }

  @override
  Widget build(BuildContext context) {
    final user = _user;
    return Scaffold(
      appBar: AppBar(title: const Text('Sozlamalar')),
      body: ListView(
        padding: const EdgeInsets.symmetric(vertical: 8),
        children: [
          const _Header('Koʻrinish'),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
            child: SegmentedButton<ThemeMode>(
              segments: const [
                ButtonSegment(value: ThemeMode.light, icon: Icon(Icons.light_mode_outlined), label: Text('Yorugʻ')),
                ButtonSegment(value: ThemeMode.dark, icon: Icon(Icons.dark_mode_outlined), label: Text('Qorongʻi')),
                ButtonSegment(value: ThemeMode.system, icon: Icon(Icons.phone_android_rounded), label: Text('Tizim')),
              ],
              selected: {_s.themeMode},
              showSelectedIcon: false,
              onSelectionChanged: (v) => _s.setThemeMode(v.first),
            ),
          ),
          const _Header('Javob berganda'),
          SwitchListTile(
            secondary: const Icon(Icons.vibration_rounded),
            title: const Text('Vibratsiya'),
            subtitle: const Text('Toʻgʻri va xato javobda telefon titraydi'),
            value: _s.vibration,
            onChanged: _s.setVibration,
          ),
          SwitchListTile(
            secondary: const Icon(Icons.volume_up_outlined),
            title: const Text('Ovoz'),
            subtitle: const Text('Toʻgʻri va xato javobda qisqa ovoz'),
            value: _s.sound,
            onChanged: _s.setSound,
          ),
          SwitchListTile(
            secondary: const Icon(Icons.animation_rounded),
            title: const Text('Animatsiyalar'),
            subtitle: const Text('Silkinish, chaqnash, konfetti'),
            value: _s.animations,
            onChanged: _s.setAnimations,
          ),
          const _Header('Profil'),
          ListTile(
            leading: const Icon(Icons.badge_outlined),
            title: const Text('Ism'),
            subtitle: Text((user['first_name'] as String?)?.isNotEmpty == true ? user['first_name'] : 'Kiritilmagan'),
            trailing: const Icon(Icons.chevron_right_rounded),
            onTap: () => _editText(title: 'Ismingiz', field: 'first_name', initial: user['first_name'] ?? ''),
          ),
          ListTile(
            leading: const Icon(Icons.alternate_email_rounded),
            title: const Text('Email'),
            subtitle: Text(user['email'] ?? ''),
            trailing: const Icon(Icons.chevron_right_rounded),
            onTap: () => _editText(
              title: 'Email',
              field: 'email',
              initial: user['email'] ?? '',
              type: TextInputType.emailAddress,
            ),
          ),
          ListTile(
            leading: const Icon(Icons.person_outline_rounded),
            title: const Text('Login'),
            subtitle: Text('${user['username'] ?? ''} (oʻzgartirilmaydi)'),
          ),
          ListTile(
            leading: const Icon(Icons.lock_outline_rounded),
            title: const Text('Parolni oʻzgartirish'),
            trailing: const Icon(Icons.chevron_right_rounded),
            onTap: _changePassword,
          ),
          SwitchListTile(
            secondary: const Icon(Icons.emoji_events_outlined),
            title: const Text('Reytingda koʻrinish'),
            subtitle: const Text('Oʻchirilsa, haftalik TOP-10 da ismingiz chiqmaydi'),
            value: user['show_in_leaderboard'] != false,
            onChanged: (v) => _saveProfile(
              {'show_in_leaderboard': v},
              v ? 'Endi reytingda koʻrinasiz.' : 'Reytingda yashirindingiz.',
            ),
          ),
          const _Header('Ilova haqida'),
          ListTile(
            leading: const Icon(Icons.info_outline_rounded),
            title: const Text('Versiya'),
            subtitle: Text(_version ?? '—'),
          ),
          ListTile(
            leading: const Icon(Icons.system_update_rounded),
            title: const Text('Yangilanishni tekshirish'),
            trailing: _checking
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.chevron_right_rounded),
            onTap: _checking ? null : _checkUpdate,
          ),
          const SizedBox(height: 8),
          Padding(
            padding: const EdgeInsets.all(16),
            child: OutlinedButton.icon(
              onPressed: _logout,
              style: OutlinedButton.styleFrom(foregroundColor: AppColors.danger),
              icon: const Icon(Icons.logout_rounded),
              label: const Text('Chiqish'),
            ),
          ),
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 6),
        child: Text(text.toUpperCase(), style: barlow(size: 13, weight: FontWeight.w700, color: AppColors.primary)),
      );
}

class _PasswordDialog extends StatefulWidget {
  const _PasswordDialog();

  @override
  State<_PasswordDialog> createState() => _PasswordDialogState();
}

class _PasswordDialogState extends State<_PasswordDialog> {
  final _old = TextEditingController();
  final _new = TextEditingController();
  final _new2 = TextEditingController();
  Map<String, String> _errors = const {};
  String? _error;
  bool _busy = false;

  Future<void> _submit() async {
    if (_new.text != _new2.text) {
      setState(() => _errors = {'new_password': 'Yangi parollar bir xil emas.'});
      return;
    }
    setState(() {
      _busy = true;
      _errors = const {};
      _error = null;
    });
    try {
      await Api.instance.post('/me/password/', {'old_password': _old.text, 'new_password': _new.text});
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (e) {
      if (e.unauthorized) {
        if (mounted) showError(context, e);
        return;
      }
      setState(() {
        _errors = e.errors;
        _error = e.errors.isEmpty ? e.message : null;
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('Parolni oʻzgartirish'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(
              controller: _old,
              obscureText: true,
              decoration: InputDecoration(labelText: 'Joriy parol', errorText: _errors['old_password']),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _new,
              obscureText: true,
              decoration: InputDecoration(labelText: 'Yangi parol', errorText: _errors['new_password'], errorMaxLines: 3),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _new2,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Yangi parolni takrorlang'),
              onSubmitted: (_) => _submit(),
            ),
            if (_error != null) ...[
              const SizedBox(height: 10),
              Text(_error!, style: TextStyle(color: AppColors.danger)),
            ],
          ]),
        ),
        actions: [
          TextButton(onPressed: _busy ? null : () => Navigator.pop(context), child: const Text('Bekor qilish')),
          FilledButton(onPressed: _busy ? null : _submit, child: const Text('Saqlash')),
        ],
      );
}
