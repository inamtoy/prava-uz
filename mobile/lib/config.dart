/// Server manzili. Ishga tushirishda o'zgartirish mumkin:
///   flutter run --dart-define=API_BASE=https://prava.uz/api/v1
/// Sukut bo'yicha — Android emulyatoridan kompyuterdagi `manage.py runserver` (10.0.2.2 = host).
const String apiBase = String.fromEnvironment(
  'API_BASE',
  defaultValue: 'http://10.0.2.2:8000/api/v1',
);
