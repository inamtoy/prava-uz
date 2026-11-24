import 'package:flutter/material.dart';

import '../theme.dart';
import '../updater.dart';

/// "Yangi versiya" oynasi: nima yangi, "Yangilash" → yuklab olish (progress) → o'rnatish oynasi.
/// Majburiy yangilanishda yopib bo'lmaydi.
Future<void> showUpdateDialog(BuildContext context, AppUpdate update) => showDialog<void>(
  context: context,
  barrierDismissible: !update.required,
  builder: (_) => PopScope(
    canPop: !update.required,
    child: UpdateDialog(update: update),
  ),
);

enum _Stage { idle, downloading, needPermission, installing, error }

class UpdateDialog extends StatefulWidget {
  const UpdateDialog({super.key, required this.update});
  final AppUpdate update;

  @override
  State<UpdateDialog> createState() => _UpdateDialogState();
}

class _UpdateDialogState extends State<UpdateDialog> with WidgetsBindingObserver {
  _Stage _stage = _Stage.idle;
  double? _progress;
  String? _path;
  String _error = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  // Sozlamalardan ruxsat berib qaytganda o'rnatishni avtomatik davom ettiramiz
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && _stage == _Stage.needPermission && _path != null) {
      _install();
    }
  }

  Future<void> _start() async {
    setState(() {
      _stage = _Stage.downloading;
      _progress = 0;
    });
    try {
      _path = await Updater.download(widget.update, (p) {
        if (mounted) setState(() => _progress = p);
      });
      await _install();
    } catch (e) {
      if (mounted) {
        setState(() {
          _stage = _Stage.error;
          _error = e.toString();
        });
      }
    }
  }

  Future<void> _install() async {
    if (!await Updater.canInstall()) {
      if (mounted) setState(() => _stage = _Stage.needPermission);
      return;
    }
    if (mounted) setState(() => _stage = _Stage.installing);
    await Updater.install(_path!);
  }

  String _mb(int bytes) => (bytes / 1024 / 1024).toStringAsFixed(bytes > 10 * 1024 * 1024 ? 0 : 1);

  @override
  Widget build(BuildContext context) {
    final u = widget.update;
    return AlertDialog(
      icon: Container(
        width: 56,
        height: 56,
        decoration: BoxDecoration(color: AppColors.primary, borderRadius: BorderRadius.circular(10)),
        child: const Icon(Icons.system_update_rounded, color: Colors.white, size: 32),
      ),
      title: Text('Yangi versiya: ${u.versionName}', textAlign: TextAlign.center),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (u.notes.isNotEmpty) ...[
            Text(u.notes, style: const TextStyle(fontSize: 15, height: 1.4)),
            const SizedBox(height: 12),
          ],
          if (u.required && _stage == _Stage.idle)
            Text(
              'Bu yangilanish majburiy — davom etish uchun ilovani yangilang.',
              style: TextStyle(color: AppColors.danger, fontSize: 14),
            ),
          if (_stage == _Stage.downloading) ...[
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(value: _progress, minHeight: 8),
            ),
            const SizedBox(height: 8),
            Text(
              _progress == null
                  ? 'Yuklab olinmoqda...'
                  : 'Yuklab olinmoqda: ${(_progress! * 100).round()}%'
                        '${u.size != null ? ' · ${_mb((u.size! * _progress!).round())} / ${_mb(u.size!)} MB' : ''}',
              textAlign: TextAlign.center,
              style: TextStyle(color: AppColors.ink2, fontSize: 14),
            ),
          ],
          if (_stage == _Stage.needPermission)
            const Text(
              'Telefon ilovaga yangilanishni oʻrnatishga ruxsat soʻraydi. “Sozlamalar”da '
              '“Ushbu manbadan ruxsat berish”ni yoqing va orqaga qayting.',
              style: TextStyle(fontSize: 14, height: 1.4),
            ),
          if (_stage == _Stage.installing)
            const Text(
              'Oʻrnatish oynasida “Yangilash” (yoki “Oʻrnatish”) tugmasini bosing.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14, height: 1.4),
            ),
          if (_stage == _Stage.error) Text(_error, style: TextStyle(color: AppColors.danger, fontSize: 14)),
          if (_stage == _Stage.idle && u.size != null) ...[
            const SizedBox(height: 4),
            Text('Hajmi: ${_mb(u.size!)} MB', style: TextStyle(color: AppColors.ink2, fontSize: 13)),
          ],
        ],
      ),
      actions: [
        if (!u.required && _stage != _Stage.downloading)
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Keyinroq')),
        switch (_stage) {
          _Stage.idle => FilledButton(onPressed: _start, child: const Text('Yangilash')),
          _Stage.downloading => const FilledButton(onPressed: null, child: Text('Yuklanmoqda...')),
          _Stage.needPermission => FilledButton(
            onPressed: Updater.openInstallSettings,
            child: const Text('Sozlamalar'),
          ),
          _Stage.installing => FilledButton(onPressed: _install, child: const Text('Qayta ochish')),
          _Stage.error => FilledButton(onPressed: _start, child: const Text('Qayta urinish')),
        },
      ],
    );
  }
}

/// Oyna yopilgandan keyin ekran pastida qoladigan eslatma ("Keyinroq" bosilganda).
class UpdateBar extends StatelessWidget {
  const UpdateBar({super.key, required this.update, required this.onTap});
  final AppUpdate update;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
    color: AppColors.primary,
    child: InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        child: Row(
          children: [
            const Icon(Icons.system_update_rounded, color: Colors.white),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Yangi versiya ${update.versionName} mavjud',
                style: const TextStyle(color: Colors.white, fontSize: 15),
              ),
            ),
            Text(
              'Yangilash',
              style: barlow(size: 16, weight: FontWeight.w700, color: Colors.white),
            ),
            const Icon(Icons.chevron_right_rounded, color: Colors.white),
          ],
        ),
      ),
    ),
  );
}
