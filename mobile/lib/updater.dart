import 'dart:io';

import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;

import 'api.dart';

/// Yangi versiya haqida ma'lumot (serverdagi /app/version/).
class AppUpdate {
  AppUpdate(Map data, this.currentCode)
    : versionCode = data['version_code'] as int,
      versionName = data['version_name'] as String,
      notes = (data['notes'] as String?) ?? '',
      apkUrl = data['apk_url'] as String,
      size = data['size'] as int?,
      required = data['required'] == true;

  final int versionCode;
  final String versionName;
  final String notes;
  final String apkUrl;
  final int? size;
  final bool required;
  final int currentCode;
}

/// Ilova ichidan yangilanish (faqat Android): tekshirish → yuklab olish → o'rnatish oynasi.
/// Native qismi: android/.../MainActivity.kt ("uz.prava/updater" kanali).
class Updater {
  Updater._();
  static const _channel = MethodChannel('uz.prava/updater');

  /// O'rnatilgan versiya nomi (masalan "0.2.1"); Android bo'lmasa yoki xatoda null.
  static Future<String?> currentVersionName() async {
    if (!Platform.isAndroid) return null;
    try {
      return await _channel.invokeMethod<String>('versionName');
    } catch (_) {
      return null;
    }
  }

  /// Yangi versiya bo'lsa — uni qaytaradi, aks holda (yoki xatoda) null.
  static Future<AppUpdate?> check() async {
    if (!Platform.isAndroid) return null;
    try {
      final current = await _channel.invokeMethod<int>('versionCode') ?? 0;
      final r = await Api.instance.get('/app/version/?current=$current');
      final latest = r is Map ? r['latest'] : null;
      if (latest is! Map) return null;
      final update = AppUpdate(latest, current);
      return update.versionCode > current ? update : null;
    } catch (_) {
      return null; // tekshiruv ishlamasa ilova odatdagidek ishlayveradi
    }
  }

  /// APK'ni yuklab oladi; `onProgress(0..1)` — hajm ma'lum bo'lsa. Fayl yo'lini qaytaradi.
  static Future<String> download(AppUpdate update, void Function(double? progress) onProgress) async {
    final dir = await _channel.invokeMethod<String>('updatesDir');
    final file = File('$dir/prava-${update.versionCode}.apk');
    // Oldin to'liq yuklangan bo'lsa — qayta yuklamaymiz
    if (update.size != null && await file.exists() && await file.length() == update.size) {
      onProgress(1);
      return file.path;
    }
    final client = http.Client();
    final part = File('${file.path}.part');
    try {
      final response = await client.send(http.Request('GET', Uri.parse(update.apkUrl)));
      if (response.statusCode != 200) {
        throw ApiException('Yangilanishni yuklab boʻlmadi (${response.statusCode}).');
      }
      final total = response.contentLength ?? update.size;
      var received = 0;
      final sink = part.openWrite();
      try {
        await for (final chunk in response.stream) {
          sink.add(chunk);
          received += chunk.length;
          onProgress(total != null && total > 0 ? received / total : null);
        }
      } finally {
        await sink.close();
      }
      if (await file.exists()) await file.delete();
      await part.rename(file.path);
      return file.path;
    } on ApiException {
      rethrow;
    } catch (_) {
      throw ApiException('Yuklab olishda xatolik. Internetni tekshirib, qayta urinib koʻring.');
    } finally {
      client.close();
    }
  }

  /// "Noma'lum manbalardan o'rnatish" ruxsati bormi (Android 8+ da har ilova uchun alohida).
  static Future<bool> canInstall() async => await _channel.invokeMethod<bool>('canInstall') ?? false;

  static Future<void> openInstallSettings() => _channel.invokeMethod('openInstallSettings');

  /// Android o'rnatish oynasini ochadi (foydalanuvchi "O'rnatish"ni bosadi).
  static Future<void> install(String path) => _channel.invokeMethod('install', {'path': path});
}
