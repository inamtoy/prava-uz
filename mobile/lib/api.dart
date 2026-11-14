import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'config.dart';

class ApiException implements Exception {
  ApiException(this.message, {this.status = 0, this.expired = false, this.errors = const {}});
  final String message;
  /// Maydon bo'yicha xatolar (ro'yxatdan o'tish formasi): {'email': '...'}
  final Map<String, String> errors;
  final int status;
  final bool expired;
  bool get unauthorized => status == 401;
  @override
  String toString() => message;
}

/// Django /api/v1/ uchun yupqa klient. Token shared_preferences'da saqlanadi.
class Api {
  Api._();
  static final Api instance = Api._();

  static const _tokenKey = 'auth_token';
  String? _token;
  Map<String, dynamic>? user;

  bool get isLoggedIn => _token != null;

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString(_tokenKey);
    if (_token != null) {
      try {
        user = Map<String, dynamic>.from(await get('/me/'));
      } on ApiException catch (e) {
        if (e.unauthorized) await _clear();
      } catch (_) {
        // tarmoq yo'q — token saqlanadi, keyingi so'rovda tekshiriladi
      }
    }
  }

  Future<void> _save(Map<String, dynamic> data) async {
    _token = data['token'] as String;
    user = Map<String, dynamic>.from(data['user']);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, _token!);
  }

  Future<void> _clear() async {
    _token = null;
    user = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
  }

  Future<void> login(String login, String password) async =>
      _save(await post('/auth/login/', {'login': login, 'password': password}));

  Future<void> register(Map<String, String> data) async => _save(await post('/auth/register/', data));

  Future<void> logout() async {
    try {
      await post('/auth/logout/');
    } catch (_) {}
    await _clear();
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        if (_token != null) 'Authorization': 'Token $_token',
      };

  Future<dynamic> get(String path) => _send(() => http.get(Uri.parse('$apiBase$path'), headers: _headers));

  Future<dynamic> post(String path, [Map<String, dynamic>? body]) => _send(
        () => http.post(Uri.parse('$apiBase$path'), headers: _headers, body: jsonEncode(body ?? {})),
      );

  Future<dynamic> _send(Future<http.Response> Function() request) async {
    http.Response r;
    try {
      r = await request().timeout(const Duration(seconds: 20));
    } catch (_) {
      throw ApiException('Server bilan aloqa yoʻq. Internetni tekshiring.');
    }
    dynamic data;
    try {
      data = r.body.isEmpty ? null : jsonDecode(utf8.decode(r.bodyBytes));
    } catch (_) {
      data = null;
    }
    if (r.statusCode >= 200 && r.statusCode < 300) return data;

    if (r.statusCode == 401) await _clear();
    final map = data is Map ? data : const {};
    final message = (map['error'] ?? map['detail'] ?? 'Xatolik yuz berdi (${r.statusCode}).').toString();
    final errors = <String, String>{};
    if (map['errors'] is Map) {
      (map['errors'] as Map).forEach((k, v) {
        if (v is List && v.isNotEmpty) errors[k.toString()] = v.first.toString();
      });
    }
    throw ApiException(message, status: r.statusCode, expired: map['expired'] == true, errors: errors);
  }
}
