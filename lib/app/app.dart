import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../features/deals/data/deals_repository.dart';
import '../features/favorites/favorites_store.dart';
import '../features/onboarding/onboarding_store.dart';
import '../features/settings/settings_store.dart';
import '../features/splash/pages/animated_splash_page.dart';
import 'app_router.dart';
import 'app_theme.dart';

class DiscountHubApp extends StatefulWidget {
  const DiscountHubApp({super.key});

  @override
  State<DiscountHubApp> createState() => _DiscountHubAppState();
}

class _DiscountHubAppState extends State<DiscountHubApp> {
  late Future<void> _bootstrapFuture;
  GoRouter? _router;

  @override
  void initState() {
    super.initState();
    _bootstrapFuture = _bootstrap();
  }

  Future<void> _bootstrap() async {
    final startedAt = DateTime.now();

    await FavoritesStore.init();
    await UserSettingsStore.init();
    await OnboardingStore.init();
    await DealsRepository.instance.init();

    final elapsed = DateTime.now().difference(startedAt);
    const minimumSplashDuration = Duration(milliseconds: 1450);
    if (elapsed < minimumSplashDuration) {
      await Future<void>.delayed(minimumSplashDuration - elapsed);
    }

    _router = createAppRouter();
  }

  void _retryBootstrap() {
    setState(() {
      _bootstrapFuture = _bootstrap();
    });
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<void>(
      future: _bootstrapFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const MaterialApp(
            title: 'DiscountHub',
            debugShowCheckedModeBanner: false,
            home: AnimatedSplashPage(),
          );
        }

        if (snapshot.hasError || _router == null) {
          return MaterialApp(
            title: 'DiscountHub',
            debugShowCheckedModeBanner: false,
            theme: AppTheme.light,
            home: _StartupErrorPage(
              error: snapshot.error,
              onRetry: _retryBootstrap,
            ),
          );
        }

        return ValueListenableBuilder<int>(
          valueListenable: UserSettingsStore.version,
          builder: (context, _, child) {
            return MaterialApp.router(
              title: 'DiscountHub',
              debugShowCheckedModeBanner: false,
              theme: AppTheme.light,
              routerConfig: _router!,
            );
          },
        );
      },
    );
  }
}

class _StartupErrorPage extends StatelessWidget {
  const _StartupErrorPage({required this.error, required this.onRetry});

  final Object? error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.background,
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.wifi_off_rounded,
                    color: AppTheme.primary,
                    size: 48,
                  ),
                  const SizedBox(height: 18),
                  const Text(
                    'DiscountHub could not start',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: AppTheme.text,
                      fontSize: 22,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'Please check your connection and try again.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: AppTheme.mutedText,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      height: 1.45,
                    ),
                  ),
                  const SizedBox(height: 22),
                  FilledButton.icon(
                    onPressed: onRetry,
                    icon: const Icon(Icons.refresh_rounded),
                    label: const Text('Try again'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
