import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../theme.dart';

/// Javobdan keyingi "his": to'g'ri — yengil titrash, xato — ikki marta kuchliroq.
Future<void> answerHaptic(bool correct) async {
  if (correct) {
    await HapticFeedback.lightImpact();
  } else {
    await HapticFeedback.heavyImpact();
    await Future<void>.delayed(const Duration(milliseconds: 90));
    await HapticFeedback.mediumImpact();
  }
}

/// `trigger` o'zgarganda bolasini gorizontal silkitadi (xato javob).
class Shake extends StatefulWidget {
  const Shake({super.key, required this.trigger, required this.child});
  final int trigger;
  final Widget child;

  @override
  State<Shake> createState() => _ShakeState();
}

class _ShakeState extends State<Shake> with SingleTickerProviderStateMixin {
  late final _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 420));

  @override
  void didUpdateWidget(Shake old) {
    super.didUpdateWidget(old);
    if (widget.trigger != old.trigger && !MediaQuery.of(context).disableAnimations) _c.forward(from: 0);
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: _c,
    child: widget.child,
    builder: (context, child) {
      final t = _c.value;
      final dx = math.sin(t * math.pi * 6) * 9 * (1 - t); // so'nib boruvchi tebranish
      return Transform.translate(offset: Offset(dx, 0), child: child);
    },
  );
}

/// Bir martalik konfetti (imtihondan o'tganda). Bosishlarni o'tkazib yuboradi.
class Confetti extends StatefulWidget {
  const Confetti({super.key, this.count = 90});
  final int count;

  @override
  State<Confetti> createState() => _ConfettiState();
}

class _Piece {
  _Piece(math.Random r)
    : x = r.nextDouble(),
      delay = r.nextDouble() * .25,
      speed = .55 + r.nextDouble() * .6,
      drift = (r.nextDouble() - .5) * .35,
      spin = (r.nextDouble() - .5) * 14,
      size = 6 + r.nextDouble() * 7,
      color = _colors[r.nextInt(_colors.length)];
  final double x, delay, speed, drift, spin, size;
  final Color color;
  // "Yo'l belgisi" palitrasi: ko'k, yashil, qizil, och ko'k (sariq — faqat ogohlantirish uchun)
  static const _colors = [AppColors.primary, AppColors.success, AppColors.danger, Color(0xFF6FA2D6)];
}

class _ConfettiState extends State<Confetti> with SingleTickerProviderStateMixin {
  late final _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 2600));
  late final _pieces = List.generate(widget.count, (_) => _Piece(math.Random()));

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && !MediaQuery.of(context).disableAnimations) _c.forward();
    });
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => IgnorePointer(
    child: AnimatedBuilder(
      animation: _c,
      builder: (context, _) => _c.isAnimating
          ? CustomPaint(painter: _ConfettiPainter(_pieces, _c.value), size: Size.infinite)
          : const SizedBox.expand(),
    ),
  );
}

class _ConfettiPainter extends CustomPainter {
  _ConfettiPainter(this.pieces, this.t);
  final List<_Piece> pieces;
  final double t;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint();
    for (final p in pieces) {
      final local = ((t - p.delay) / (1 - p.delay)).clamp(0.0, 1.0);
      if (local <= 0) continue;
      final y = -20 + local * p.speed * (size.height + 40) * 1.2;
      final x = (p.x + p.drift * local) * size.width + math.sin(local * 9 + p.x * 10) * 12;
      paint.color = p.color.withValues(alpha: local > .8 ? (1 - local) * 5 : 1);
      canvas
        ..save()
        ..translate(x, y)
        ..rotate(p.spin * local);
      canvas.drawRect(Rect.fromCenter(center: Offset.zero, width: p.size, height: p.size * .55), paint);
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(_ConfettiPainter old) => old.t != t;
}

/// Halqa ko'rinishidagi progress (0..1), qiymat o'zgarganda silliq to'ladi.
class GoalRing extends StatelessWidget {
  const GoalRing({super.key, required this.value, required this.color, this.size = 112, this.stroke = 10, this.child});
  final double value;
  final Color color;
  final double size;
  final double stroke;
  final Widget? child;

  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
    tween: Tween(begin: 0, end: value.clamp(0, 1)),
    duration: const Duration(milliseconds: 900),
    curve: Curves.easeOutCubic,
    builder: (context, v, _) => SizedBox(
      width: size,
      height: size,
      child: CustomPaint(
        painter: _RingPainter(v, color, stroke),
        child: Center(child: child),
      ),
    ),
  );
}

class _RingPainter extends CustomPainter {
  _RingPainter(this.value, this.color, this.stroke);
  final double value;
  final Color color;
  final double stroke;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset(stroke / 2, stroke / 2) & Size(size.width - stroke, size.height - stroke);
    final track = Paint()
      ..color = AppColors.line
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke;
    canvas.drawArc(rect, 0, math.pi * 2, false, track);
    if (value <= 0) return;
    final fill = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeWidth = stroke;
    canvas.drawArc(rect, -math.pi / 2, math.pi * 2 * value, false, fill);
  }

  @override
  bool shouldRepaint(_RingPainter old) => old.value != value || old.color != color;
}
