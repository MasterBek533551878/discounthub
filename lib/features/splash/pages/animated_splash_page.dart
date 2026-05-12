import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../shared/widgets/discount_hub_logo.dart';

class AnimatedSplashPage extends StatefulWidget {
  const AnimatedSplashPage({super.key});

  @override
  State<AnimatedSplashPage> createState() => _AnimatedSplashPageState();
}

class _AnimatedSplashPageState extends State<AnimatedSplashPage>
    with TickerProviderStateMixin {
  late final AnimationController _introController;
  late final AnimationController _ambientController;

  late final Animation<double> _logoScale;
  late final Animation<double> _logoOpacity;
  late final Animation<Offset> _contentOffset;
  late final Animation<double> _textOpacity;

  @override
  void initState() {
    super.initState();

    _introController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1150),
    )..forward();

    _ambientController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 5200),
    )..repeat();

    _logoScale = CurvedAnimation(
      parent: _introController,
      curve: const Interval(0.05, 0.78, curve: Curves.easeOutBack),
    ).drive(Tween<double>(begin: 0.78, end: 1));

    _logoOpacity = CurvedAnimation(
      parent: _introController,
      curve: const Interval(0, 0.48, curve: Curves.easeOut),
    );

    _contentOffset = CurvedAnimation(
      parent: _introController,
      curve: const Interval(0.18, 0.86, curve: Curves.easeOutCubic),
    ).drive(Tween<Offset>(begin: const Offset(0, 0.16), end: Offset.zero));

    _textOpacity = CurvedAnimation(
      parent: _introController,
      curve: const Interval(0.42, 1, curve: Curves.easeOut),
    );
  }

  @override
  void dispose() {
    _introController.dispose();
    _ambientController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: AnimatedBuilder(
        animation: Listenable.merge([_introController, _ambientController]),
        builder: (context, child) {
          final progress = _ambientController.value;

          return DecoratedBox(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Color(0xFF07153B),
                  Color(0xFF0B36A8),
                  Color(0xFF0EA5FF),
                ],
                stops: [0, 0.58, 1],
              ),
            ),
            child: CustomPaint(
              painter: _SplashBackgroundPainter(progress: progress),
              child: SafeArea(
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 430),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 28),
                      child: SlideTransition(
                        position: _contentOffset,
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            FadeTransition(
                              opacity: _logoOpacity,
                              child: Transform.scale(
                                scale: _logoScale.value,
                                child: _GlowCard(progress: progress),
                              ),
                            ),
                            const SizedBox(height: 28),
                            FadeTransition(
                              opacity: _textOpacity,
                              child: const _SplashWordmark(),
                            ),
                            const SizedBox(height: 10),
                            FadeTransition(
                              opacity: _textOpacity,
                              child: Text(
                                'Smart savings. Clean discovery.',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  color: Colors.white.withValues(alpha: 0.78),
                                  fontSize: 15,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 0.3,
                                  height: 1.35,
                                ),
                              ),
                            ),
                            const SizedBox(height: 34),
                            FadeTransition(
                              opacity: _textOpacity,
                              child: _LoadingDots(progress: progress),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _GlowCard extends StatelessWidget {
  const _GlowCard({required this.progress});

  final double progress;

  @override
  Widget build(BuildContext context) {
    final pulse = 0.5 + (math.sin(progress * math.pi * 2) * 0.5);

    return Stack(
      alignment: Alignment.center,
      children: [
        Container(
          width: 176 + (pulse * 12),
          height: 176 + (pulse * 12),
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: const Color(0xFF2DD4FF).withValues(alpha: 0.16),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF38BDF8).withValues(alpha: 0.35),
                blurRadius: 64 + (pulse * 18),
                spreadRadius: 6 + (pulse * 4),
              ),
            ],
          ),
        ),
        Container(
          width: 132,
          height: 132,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(34),
            border: Border.all(
              color: Colors.white.withValues(alpha: 0.2),
              width: 1.2,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.34),
                blurRadius: 34,
                offset: const Offset(0, 18),
              ),
            ],
          ),
          clipBehavior: Clip.antiAlias,
          child: const DiscountHubAppIcon(
            size: 132,
            dark: true,
            flat: true,
          ),
        ),
      ],
    );
  }
}

class _SplashWordmark extends StatelessWidget {
  const _SplashWordmark();

  @override
  Widget build(BuildContext context) {
    return FittedBox(
      fit: BoxFit.scaleDown,
      child: RichText(
        textAlign: TextAlign.center,
        text: const TextSpan(
          style: TextStyle(
            fontSize: 40,
            fontWeight: FontWeight.w900,
            letterSpacing: -1.2,
            height: 1,
          ),
          children: [
            TextSpan(
              text: 'Discount',
              style: TextStyle(color: Colors.white),
            ),
            TextSpan(
              text: 'Hub',
              style: TextStyle(color: Color(0xFF27D7FF)),
            ),
          ],
        ),
      ),
    );
  }
}

class _LoadingDots extends StatelessWidget {
  const _LoadingDots({required this.progress});

  final double progress;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(3, (index) {
        final phase = (progress + index * 0.18) % 1;
        final scale = 0.72 + math.sin(phase * math.pi) * 0.52;
        final opacity = 0.34 + math.sin(phase * math.pi) * 0.56;

        return Transform.scale(
          scale: scale,
          child: Container(
            width: 9,
            height: 9,
            margin: const EdgeInsets.symmetric(horizontal: 5),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.white.withValues(
                alpha: opacity.clamp(0.2, 0.9).toDouble(),
              ),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF38BDF8).withValues(alpha: 0.45),
                  blurRadius: 14 * scale,
                ),
              ],
            ),
          ),
        );
      }),
    );
  }
}

class _SplashBackgroundPainter extends CustomPainter {
  const _SplashBackgroundPainter({required this.progress});

  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width * 0.5, size.height * 0.46);

    _paintSoftGlow(canvas, size, center);
    _paintOrbit(canvas, size, center);
    _paintFloatingSymbols(canvas, size);
    _paintBottomWave(canvas, size);
  }

  void _paintSoftGlow(Canvas canvas, Size size, Offset center) {
    final rect = Offset.zero & size;
    final glowPaint = Paint()
      ..shader = RadialGradient(
        center: Alignment(
          math.sin(progress * math.pi * 2) * 0.12,
          -0.12,
        ),
        radius: 0.72,
        colors: [
          const Color(0xFF38BDF8).withValues(alpha: 0.34),
          const Color(0xFF2563FF).withValues(alpha: 0.12),
          Colors.transparent,
        ],
        stops: const [0, 0.38, 1],
      ).createShader(rect);

    canvas.drawRect(rect, glowPaint);

    final logoGlow = Paint()
      ..shader = RadialGradient(
        colors: [
          const Color(0xFF7DD3FC).withValues(alpha: 0.34),
          Colors.transparent,
        ],
      ).createShader(Rect.fromCircle(center: center, radius: size.width * 0.52));
    canvas.drawCircle(center, size.width * 0.44, logoGlow);
  }

  void _paintOrbit(Canvas canvas, Size size, Offset center) {
    final orbitPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2
      ..color = Colors.white.withValues(alpha: 0.14);

    final orbitRect = Rect.fromCenter(
      center: center.translate(0, size.height * 0.02),
      width: size.width * 0.92,
      height: size.height * 0.18,
    );

    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(-0.16);
    canvas.translate(-center.dx, -center.dy);
    canvas.drawOval(orbitRect, orbitPaint);
    canvas.restore();

    final dotPhase = progress * math.pi * 2;
    final dot = Offset(
      center.dx + math.cos(dotPhase) * size.width * 0.44,
      center.dy + math.sin(dotPhase) * size.height * 0.085,
    );
    canvas.drawCircle(
      dot,
      4,
      Paint()..color = const Color(0xFF67E8F9).withValues(alpha: 0.92),
    );
    canvas.drawCircle(
      dot,
      14,
      Paint()..color = const Color(0xFF67E8F9).withValues(alpha: 0.14),
    );
  }

  void _paintFloatingSymbols(Canvas canvas, Size size) {
    final textPainter = TextPainter(textDirection: TextDirection.ltr);
    final symbolStyle = TextStyle(
      color: Colors.white.withValues(alpha: 0.13),
      fontSize: 34,
      fontWeight: FontWeight.w900,
    );

    final symbols = <_FloatingSymbol>[
      _FloatingSymbol('%', Offset(size.width * 0.82, size.height * 0.23), 0),
      _FloatingSymbol('%', Offset(size.width * 0.16, size.height * 0.72), 0.36),
      _FloatingSymbol('-25%', Offset(size.width * 0.18, size.height * 0.31), 0.72),
    ];

    for (final symbol in symbols) {
      final floatY = math.sin((progress + symbol.phase) * math.pi * 2) * 8;
      textPainter.text = TextSpan(text: symbol.text, style: symbolStyle);
      textPainter.layout();
      textPainter.paint(
        canvas,
        symbol.offset.translate(-textPainter.width / 2, floatY),
      );
    }

    _drawTagOutline(
      canvas,
      Offset(size.width * 0.16, size.height * 0.22),
      76,
      -0.14 + math.sin(progress * math.pi * 2) * 0.035,
    );
    _drawTagOutline(
      canvas,
      Offset(size.width * 0.79, size.height * 0.70),
      82,
      0.62 + math.cos(progress * math.pi * 2) * 0.035,
    );

    final particlePaint = Paint()..color = Colors.white.withValues(alpha: 0.28);
    for (var i = 0; i < 18; i++) {
      final x = (math.sin(i * 19.7) * 0.5 + 0.5) * size.width;
      final y = (math.cos(i * 13.3) * 0.5 + 0.5) * size.height;
      final alpha = 0.10 + (math.sin(progress * math.pi * 2 + i) + 1) * 0.09;
      particlePaint.color = Colors.white.withValues(alpha: alpha);
      canvas.drawCircle(Offset(x, y), 1.4 + (i % 3) * 0.6, particlePaint);
    }
  }

  void _drawTagOutline(Canvas canvas, Offset center, double size, double angle) {
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..color = const Color(0xFF67E8F9).withValues(alpha: 0.16);

    final w = size;
    final h = size * 0.64;
    final r = size * 0.13;
    final path = Path()
      ..moveTo(-w * 0.42 + r, -h * 0.5)
      ..lineTo(w * 0.18, -h * 0.5)
      ..quadraticBezierTo(w * 0.42, -h * 0.5, w * 0.42, -h * 0.25)
      ..lineTo(w * 0.42, h * 0.25)
      ..quadraticBezierTo(w * 0.42, h * 0.5, w * 0.18, h * 0.5)
      ..lineTo(-w * 0.42 + r, h * 0.5)
      ..quadraticBezierTo(-w * 0.42, h * 0.5, -w * 0.42, h * 0.5 - r)
      ..lineTo(-w * 0.42, -h * 0.5 + r)
      ..quadraticBezierTo(-w * 0.42, -h * 0.5, -w * 0.42 + r, -h * 0.5)
      ..close();

    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(angle);
    canvas.drawPath(path, paint);
    canvas.drawCircle(Offset(w * 0.25, -h * 0.22), 4.5, paint);
    canvas.restore();
  }

  void _paintBottomWave(Canvas canvas, Size size) {
    final wavePaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          Colors.white.withValues(alpha: 0.08),
          Colors.white.withValues(alpha: 0.0),
        ],
      ).createShader(Rect.fromLTWH(0, size.height * 0.77, size.width, size.height * 0.22));

    final wave = Path()
      ..moveTo(0, size.height * 0.84)
      ..cubicTo(
        size.width * 0.22,
        size.height * 0.78,
        size.width * 0.42,
        size.height * 0.92,
        size.width * 0.64,
        size.height * 0.84,
      )
      ..cubicTo(
        size.width * 0.78,
        size.height * 0.79,
        size.width * 0.92,
        size.height * 0.82,
        size.width,
        size.height * 0.76,
      )
      ..lineTo(size.width, size.height)
      ..lineTo(0, size.height)
      ..close();

    canvas.drawPath(wave, wavePaint);
  }

  @override
  bool shouldRepaint(covariant _SplashBackgroundPainter oldDelegate) {
    return oldDelegate.progress != progress;
  }
}

class _FloatingSymbol {
  const _FloatingSymbol(this.text, this.offset, this.phase);

  final String text;
  final Offset offset;
  final double phase;
}
