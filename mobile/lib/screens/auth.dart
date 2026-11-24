import 'package:flutter/material.dart';

import '../api.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'home_shell.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _login = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  String? _error;

  Future<void> _submit() async {
    if (_login.text.trim().isEmpty || _password.text.isEmpty) {
      setState(() => _error = 'Login va parolni kiriting.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await Api.instance.login(_login.text.trim(), _password.text);
      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const HomeShell()), (_) => false);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 40, 20, 24),
          children: [
            const Center(child: Logo(size: 64)),
            const SizedBox(height: 16),
            Center(child: Text('Prava.uz', style: barlow(size: 30, weight: FontWeight.w700))),
            const SizedBox(height: 4),
            Center(
              child: Text('Haydovchilik imtihoniga tayyorlaning', style: TextStyle(color: AppColors.ink2)),
            ),
            const SizedBox(height: 32),
            TextField(
              controller: _login,
              decoration: const InputDecoration(labelText: 'Login yoki email'),
              keyboardType: TextInputType.emailAddress,
              autocorrect: false,
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 14),
            TextField(
              controller: _password,
              decoration: const InputDecoration(labelText: 'Parol'),
              obscureText: true,
              onSubmitted: (_) => _submit(),
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: TextStyle(color: AppColors.danger)),
            ],
            const SizedBox(height: 20),
            FilledButton(
              onPressed: _busy ? null : _submit,
              child: _busy
                  ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5))
                  : const Text('Kirish'),
            ),
            const SizedBox(height: 12),
            OutlinedButton(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const RegisterScreen())),
              child: const Text('Roʻyxatdan oʻtish'),
            ),
          ],
        ),
      ),
    );
  }
}

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _c = {
    for (final k in ['first_name', 'username', 'email', 'password', 'password2']) k: TextEditingController(),
  };
  Map<String, String> _errors = {};
  String? _error;
  bool _busy = false;

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _errors = {};
      _error = null;
    });
    try {
      await Api.instance.register({for (final e in _c.entries) e.key: e.value.text.trim()});
      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const HomeShell()), (_) => false);
    } on ApiException catch (e) {
      setState(() {
        _errors = Map.of(e.errors);
        // Parol xatolari server tomonda 'password' ga yig'iladi
        _error = _errors.isEmpty || !_errors.keys.every(_c.containsKey) ? e.message : null;
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _field(String key, String label, {bool obscure = false, TextInputType? type}) => Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: TextField(
          controller: _c[key],
          obscureText: obscure,
          keyboardType: type,
          autocorrect: false,
          decoration: InputDecoration(labelText: label, errorText: _errors[key]),
        ),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Roʻyxatdan oʻtish')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            _field('first_name', 'Ismingiz'),
            _field('username', 'Foydalanuvchi nomi (login)'),
            _field('email', 'Email', type: TextInputType.emailAddress),
            _field('password', 'Parol', obscure: true),
            _field('password2', 'Parolni takrorlang', obscure: true),
            if (_error != null) ...[
              Text(_error!, style: TextStyle(color: AppColors.danger)),
              const SizedBox(height: 12),
            ],
            FilledButton(
              onPressed: _busy ? null : _submit,
              child: _busy
                  ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5))
                  : const Text('Roʻyxatdan oʻtish'),
            ),
          ],
        ),
      ),
    );
  }
}
