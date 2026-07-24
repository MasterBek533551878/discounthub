import 'dart:convert';
import 'dart:math';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';

import '../../../app/app_theme.dart';
import '../../settings/app_strings.dart';
import '../../settings/settings_store.dart';

class AiFinderPage extends StatefulWidget {
  const AiFinderPage({super.key});

  @override
  State<AiFinderPage> createState() => _AiFinderPageState();
}

class _AiFinderPageState extends State<AiFinderPage> {
  static const int _maxHistory = 8;

  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final http.Client _httpClient = http.Client();

  final List<_AiMessage> _messages = <_AiMessage>[];
  final List<Map<String, String>> _history = <Map<String, String>>[];

  late String _sessionId;
  bool _busy = false;
  int? _remainingRequests;
  List<String> _suggestions = const <String>[];

  @override
  void initState() {
    super.initState();
    _sessionId = _newSessionId();
    _startConversation();
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    _httpClient.close();
    super.dispose();
  }

  String _newSessionId() {
    final random = Random();
    final first = random.nextInt(1 << 30).toRadixString(36);
    final second = random.nextInt(1 << 30).toRadixString(36);

    return 'mobile-${DateTime.now().microsecondsSinceEpoch}-$first$second';
  }

  void _startConversation() {
    _messages
      ..clear()
      ..add(
        _AiMessage.assistant(
          AppStrings.select(
            en: 'Tell me what you want to buy, your budget, a store, or the discount you need.',
            ru: 'Напишите, что хотите купить, бюджет, магазин или нужную скидку.',
            uz: 'Nima sotib olmoqchi ekaningizni, budjetni, do‘konni yoki kerakli chegirmani yozing.',
          ),
        ),
      );
    _history.clear();
    _remainingRequests = null;
    _suggestions = <String>[
      AppStrings.select(
        en: 'Tech deals under \$50',
        ru: 'Техника до \$50',
        uz: '\$50 gacha texnika',
      ),
      AppStrings.select(
        en: 'Shopping promo codes',
        ru: 'Промокоды для покупок',
        uz: 'Xarid promokodlari',
      ),
      AppStrings.select(
        en: 'Lifetime partner offers',
        ru: 'Пожизненные предложения',
        uz: 'Umrbod takliflar',
      ),
    ];
  }

  Future<void> _reset() async {
    if (_busy) return;
    setState(() {
      _sessionId = _newSessionId();
      _startConversation();
    });
    _scrollToBottom();
  }

  Future<void> _submit([String? rawValue]) async {
    final message = (rawValue ?? _controller.text).trim();
    if (_busy || message.length < 2) return;

    final requestHistory = _history.length <= _maxHistory
        ? List<Map<String, String>>.from(_history)
        : _history.sublist(_history.length - _maxHistory);

    setState(() {
      _messages.add(_AiMessage.user(message));
      _history.add(<String, String>{'role': 'user', 'content': message});
      _controller.clear();
      _suggestions = const <String>[];
      _busy = true;
    });
    _scrollToBottom();

    try {
      final baseUrl = Uri.parse(UserSettingsStore.apiBaseUrl.value);
      final normalizedBasePath = baseUrl.path.endsWith('/')
          ? baseUrl.path.substring(0, baseUrl.path.length - 1)
          : baseUrl.path;
      final uri = baseUrl.replace(path: '$normalizedBasePath/ai/chat');

      final response = await _httpClient
          .post(
            uri,
            headers: const <String, String>{
              'Accept': 'application/json',
              'Content-Type': 'application/json',
            },
            body: jsonEncode(<String, Object>{
              'message': message,
              'history': requestHistory,
              'sessionId': _sessionId,
            }),
          )
          .timeout(const Duration(seconds: 30));

      Map<String, dynamic> json = const <String, dynamic>{};
      try {
        final decoded = jsonDecode(response.body);
        if (decoded is Map<String, dynamic>) json = decoded;
      } catch (_) {}

      if (response.statusCode < 200 || response.statusCode >= 300) {
        final detail = json['detail']?.toString().trim();
        throw _AiRequestException(
          detail == null || detail.isEmpty
              ? AppStrings.select(
                  en: 'The AI assistant is temporarily unavailable.',
                  ru: 'ИИ-помощник временно недоступен.',
                  uz: 'AI yordamchi vaqtincha mavjud emas.',
                )
              : detail,
        );
      }

      final reply = (json['reply'] ?? '').toString().trim();
      final items = _AiOfferItem.listFromJson(json['items']);
      final suggestions = _stringList(json['suggestions']).take(3).toList();
      final remaining = _int(
        json['remainingRequests'] ?? json['remaining_requests'],
      );

      if (!mounted) return;
      setState(() {
        final safeReply = reply.isEmpty
            ? AppStrings.select(
                en: 'Here are the closest current DiscountHub results.',
                ru: 'Вот самые подходящие актуальные предложения DiscountHub.',
                uz: 'DiscountHub’dagi eng yaqin joriy natijalar.',
              )
            : reply;
        _messages.add(_AiMessage.assistant(safeReply, items: items));
        _history.add(<String, String>{
          'role': 'assistant',
          'content': safeReply,
        });
        while (_history.length > _maxHistory) {
          _history.removeAt(0);
        }
        _suggestions = suggestions;
        _remainingRequests = remaining;
        _busy = false;
      });
    } catch (error) {
      if (!mounted) return;
      final messageText = error is _AiRequestException
          ? error.message
          : AppStrings.select(
              en: 'I could not reach the AI assistant. Please try again.',
              ru: 'Не удалось связаться с ИИ-помощником. Попробуйте ещё раз.',
              uz: 'AI yordamchiga ulanib bo‘lmadi. Qayta urinib ko‘ring.',
            );
      setState(() {
        _messages.add(_AiMessage.assistant(messageText, isError: true));
        _busy = false;
      });
    } finally {
      _scrollToBottom();
    }
  }

  Future<void> _openOffer(_AiOfferItem item) async {
    final rawUrl = item.clickUrl.isNotEmpty ? item.clickUrl : item.pageUrl;
    final uri = Uri.tryParse(rawUrl);
    if (uri == null) return;
    final opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!opened && mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(AppStrings.couldNotOpenLink)));
    }
  }

  Future<void> _copyCode(String code) async {
    await Clipboard.setData(ClipboardData(text: code));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          AppStrings.select(
            en: 'Promo code copied',
            ru: 'Промокод скопирован',
            uz: 'Promokod nusxalandi',
          ),
        ),
      ),
    );
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 260),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Finder'),
        actions: [
          IconButton(
            tooltip: AppStrings.select(
              en: 'New chat',
              ru: 'Новый чат',
              uz: 'Yangi chat',
            ),
            onPressed: _busy ? null : _reset,
            icon: const Icon(Icons.refresh_rounded),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView(
              controller: _scrollController,
              keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
              padding: const EdgeInsets.fromLTRB(16, 6, 16, 14),
              children: [
                _AiHero(remainingRequests: _remainingRequests),
                const SizedBox(height: 16),
                for (final message in _messages) ...[
                  _MessageBubble(
                    message: message,
                    onOpenOffer: _openOffer,
                    onCopyCode: _copyCode,
                  ),
                  const SizedBox(height: 12),
                ],
                if (_busy) ...[
                  const _TypingBubble(),
                  const SizedBox(height: 12),
                ],
                if (_suggestions.isNotEmpty && !_busy) ...[
                  const SizedBox(height: 2),
                  _SuggestionChips(
                    suggestions: _suggestions,
                    onSelected: _submit,
                  ),
                ],
              ],
            ),
          ),
          _Composer(controller: _controller, busy: _busy, onSend: _submit),
        ],
      ),
    );
  }
}

class _AiHero extends StatelessWidget {
  const _AiHero({required this.remainingRequests});

  final int? remainingRequests;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: AppTheme.brandGradient,
        borderRadius: BorderRadius.circular(28),
        boxShadow: AppTheme.softShadow,
      ),
      child: Row(
        children: [
          Container(
            width: 54,
            height: 54,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(19),
              border: Border.all(color: Colors.white.withValues(alpha: 0.25)),
            ),
            child: const Icon(
              Icons.auto_awesome_rounded,
              color: Colors.white,
              size: 28,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  AppStrings.select(
                    en: 'Find real offers with natural language',
                    ru: 'Ищите реальные предложения обычными словами',
                    uz: 'Haqiqiy takliflarni oddiy so‘zlar bilan toping',
                  ),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w900,
                    height: 1.15,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  AppStrings.select(
                    en: 'Searches DiscountHub deals, promo codes and partner offers.',
                    ru: 'Ищет по скидкам, промокодам и партнёрским предложениям DiscountHub.',
                    uz: 'DiscountHub chegirmalari, promokodlari va hamkor takliflarini qidiradi.',
                  ),
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.86),
                    fontSize: 12.5,
                    fontWeight: FontWeight.w700,
                    height: 1.3,
                  ),
                ),
                if (remainingRequests != null) ...[
                  const SizedBox(height: 6),
                  Text(
                    AppStrings.select(
                      en: '$remainingRequests AI requests remaining this hour',
                      ru: 'Осталось AI-запросов в этом часу: $remainingRequests',
                      uz: 'Bu soatda $remainingRequests ta AI so‘rovi qoldi',
                    ),
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.72),
                      fontSize: 11.5,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Composer extends StatelessWidget {
  const _Composer({
    required this.controller,
    required this.busy,
    required this.onSend,
  });

  final TextEditingController controller;
  final bool busy;
  final Future<void> Function([String? value]) onSend;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      elevation: 8,
      shadowColor: AppTheme.navy.withValues(alpha: 0.08),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Expanded(
                child: TextField(
                  controller: controller,
                  enabled: !busy,
                  minLines: 1,
                  maxLines: 4,
                  textCapitalization: TextCapitalization.sentences,
                  decoration: InputDecoration(
                    hintText: AppStrings.select(
                      en: 'What would you like to find?',
                      ru: 'Что вы хотите найти?',
                      uz: 'Nimani topmoqchisiz?',
                    ),
                  ),
                  onSubmitted: busy ? null : (value) => onSend(value),
                ),
              ),
              const SizedBox(width: 10),
              SizedBox(
                width: 52,
                height: 52,
                child: FilledButton(
                  onPressed: busy ? null : () => onSend(),
                  style: FilledButton.styleFrom(
                    minimumSize: const Size(52, 52),
                    padding: EdgeInsets.zero,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(17),
                    ),
                  ),
                  child: busy
                      ? const SizedBox(
                          width: 21,
                          height: 21,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.4,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.arrow_upward_rounded),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SuggestionChips extends StatelessWidget {
  const _SuggestionChips({required this.suggestions, required this.onSelected});

  final List<String> suggestions;
  final Future<void> Function([String? value]) onSelected;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: suggestions
          .map(
            (value) => ActionChip(
              avatar: const Icon(Icons.auto_awesome_rounded, size: 17),
              label: Text(value),
              onPressed: () => onSelected(value),
            ),
          )
          .toList(),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({
    required this.message,
    required this.onOpenOffer,
    required this.onCopyCode,
  });

  final _AiMessage message;
  final ValueChanged<_AiOfferItem> onOpenOffer;
  final ValueChanged<String> onCopyCode;

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == _AiRole.user;
    final bubbleColor = isUser
        ? AppTheme.primary
        : message.isError
        ? AppTheme.softRed
        : Colors.white;
    final textColor = isUser ? Colors.white : AppTheme.text;

    return Column(
      crossAxisAlignment: isUser
          ? CrossAxisAlignment.end
          : CrossAxisAlignment.start,
      children: [
        Align(
          alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
          child: Container(
            constraints: const BoxConstraints(maxWidth: 560),
            padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
            decoration: BoxDecoration(
              color: bubbleColor,
              borderRadius: BorderRadius.circular(20).copyWith(
                bottomRight: isUser ? const Radius.circular(6) : null,
                bottomLeft: !isUser ? const Radius.circular(6) : null,
              ),
              border: isUser ? null : Border.all(color: AppTheme.line),
              boxShadow: isUser ? null : AppTheme.cardShadow,
            ),
            child: Text(
              message.text,
              style: TextStyle(
                color: textColor,
                fontSize: 14,
                fontWeight: FontWeight.w700,
                height: 1.4,
              ),
            ),
          ),
        ),
        if (message.items.isNotEmpty) ...[
          const SizedBox(height: 10),
          for (final item in message.items) ...[
            _AiOfferCard(
              item: item,
              onOpen: () => onOpenOffer(item),
              onCopyCode: item.code == null
                  ? null
                  : () => onCopyCode(item.code!),
            ),
            const SizedBox(height: 10),
          ],
        ],
      ],
    );
  }
}

class _TypingBubble extends StatelessWidget {
  const _TypingBubble();

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppTheme.line),
        ),
        child: const SizedBox(
          width: 22,
          height: 22,
          child: CircularProgressIndicator(strokeWidth: 2.4),
        ),
      ),
    );
  }
}

class _AiOfferCard extends StatelessWidget {
  const _AiOfferCard({
    required this.item,
    required this.onOpen,
    this.onCopyCode,
  });

  final _AiOfferItem item;
  final VoidCallback onOpen;
  final VoidCallback? onCopyCode;

  @override
  Widget build(BuildContext context) {
    final currentPrice = item.currentPrice == null
        ? ''
        : UserSettingsStore.formatNativeAmount(
            item.currentPrice!,
            item.currency ?? 'USD',
          );
    final oldPrice = item.oldPrice == null
        ? ''
        : UserSettingsStore.formatNativeAmount(
            item.oldPrice!,
            item.currency ?? 'USD',
          );

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: AppTheme.line),
        boxShadow: AppTheme.cardShadow,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _OfferImage(url: item.imageUrl, kind: item.kind),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    _OfferBadge(text: item.kindLabel),
                    if (item.badge.isNotEmpty)
                      _OfferBadge(text: item.badge, highlighted: true),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  item.title,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppTheme.text,
                    fontSize: 15,
                    fontWeight: FontWeight.w900,
                    height: 1.25,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  item.merchant,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppTheme.mutedText,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                if (currentPrice.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Text(
                        currentPrice,
                        style: const TextStyle(
                          color: AppTheme.text,
                          fontSize: 16,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      if (oldPrice.isNotEmpty && oldPrice != currentPrice)
                        Text(
                          oldPrice,
                          style: const TextStyle(
                            color: AppTheme.mutedText,
                            fontSize: 12,
                            decoration: TextDecoration.lineThrough,
                          ),
                        ),
                    ],
                  ),
                ],
                if (item.code != null) ...[
                  const SizedBox(height: 8),
                  InkWell(
                    borderRadius: BorderRadius.circular(10),
                    onTap: onCopyCode,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 7,
                      ),
                      decoration: BoxDecoration(
                        color: AppTheme.softBlue,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: AppTheme.primaryLight),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            item.code!,
                            style: const TextStyle(
                              color: AppTheme.primaryDark,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          const SizedBox(width: 6),
                          const Icon(
                            Icons.copy_rounded,
                            size: 15,
                            color: AppTheme.primary,
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: 10),
                FilledButton.icon(
                  onPressed: onOpen,
                  icon: const Icon(Icons.open_in_new_rounded, size: 18),
                  label: Text(
                    AppStrings.select(
                      en: 'Open offer',
                      ru: 'Открыть',
                      uz: 'Taklifni ochish',
                    ),
                  ),
                  style: FilledButton.styleFrom(
                    minimumSize: const Size.fromHeight(42),
                    textStyle: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _OfferImage extends StatelessWidget {
  const _OfferImage({required this.url, required this.kind});

  final String? url;
  final String kind;

  @override
  Widget build(BuildContext context) {
    final fallback = Container(
      color: AppTheme.softBlue,
      alignment: Alignment.center,
      child: Icon(
        kind == 'promotion'
            ? Icons.local_offer_rounded
            : kind == 'partner_offer'
            ? Icons.handshake_rounded
            : Icons.percent_rounded,
        color: AppTheme.primary,
      ),
    );

    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: SizedBox(
        width: 82,
        height: 82,
        child: url == null || url!.trim().isEmpty
            ? fallback
            : CachedNetworkImage(
                imageUrl: url!,
                fit: BoxFit.cover,
                placeholder: (_, _) => fallback,
                errorWidget: (_, _, _) => fallback,
              ),
      ),
    );
  }
}

class _OfferBadge extends StatelessWidget {
  const _OfferBadge({required this.text, this.highlighted = false});

  final String text;
  final bool highlighted;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: highlighted ? AppTheme.softGreen : AppTheme.surfaceSoft,
        borderRadius: BorderRadius.circular(9),
      ),
      child: Text(
        text,
        style: TextStyle(
          color: highlighted ? AppTheme.secondary : AppTheme.primaryDark,
          fontSize: 10.5,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}

enum _AiRole { user, assistant }

class _AiMessage {
  const _AiMessage({
    required this.role,
    required this.text,
    this.items = const <_AiOfferItem>[],
    this.isError = false,
  });

  factory _AiMessage.user(String text) {
    return _AiMessage(role: _AiRole.user, text: text);
  }

  factory _AiMessage.assistant(
    String text, {
    List<_AiOfferItem> items = const <_AiOfferItem>[],
    bool isError = false,
  }) {
    return _AiMessage(
      role: _AiRole.assistant,
      text: text,
      items: items,
      isError: isError,
    );
  }

  final _AiRole role;
  final String text;
  final List<_AiOfferItem> items;
  final bool isError;
}

class _AiOfferItem {
  const _AiOfferItem({
    required this.kind,
    required this.title,
    required this.merchant,
    required this.badge,
    required this.clickUrl,
    required this.pageUrl,
    this.code,
    this.currentPrice,
    this.oldPrice,
    this.currency,
    this.imageUrl,
  });

  final String kind;
  final String title;
  final String merchant;
  final String badge;
  final String clickUrl;
  final String pageUrl;
  final String? code;
  final double? currentPrice;
  final double? oldPrice;
  final String? currency;
  final String? imageUrl;

  String get kindLabel {
    switch (kind) {
      case 'promotion':
        return 'Promo';
      case 'partner_offer':
        return 'Partner';
      default:
        return 'Deal';
    }
  }

  factory _AiOfferItem.fromJson(Map<String, dynamic> json) {
    return _AiOfferItem(
      kind: (json['kind'] ?? 'deal').toString(),
      title: (json['title'] ?? 'DiscountHub offer').toString(),
      merchant: (json['merchant'] ?? 'DiscountHub').toString(),
      badge: (json['badge'] ?? '').toString(),
      clickUrl: (json['clickUrl'] ?? json['click_url'] ?? '').toString(),
      pageUrl: (json['pageUrl'] ?? json['page_url'] ?? '').toString(),
      code: _nullableString(json['code']),
      currentPrice: _nullableDouble(
        json['currentPrice'] ?? json['current_price'],
      ),
      oldPrice: _nullableDouble(json['oldPrice'] ?? json['old_price']),
      currency: _nullableString(json['currency']),
      imageUrl: _nullableString(json['imageUrl'] ?? json['image_url']),
    );
  }

  static List<_AiOfferItem> listFromJson(dynamic value) {
    if (value is! List) return const <_AiOfferItem>[];
    return value
        .whereType<Map>()
        .map(
          (item) => _AiOfferItem.fromJson(
            item.map((key, value) => MapEntry(key.toString(), value)),
          ),
        )
        .toList(growable: false);
  }

  static String? _nullableString(dynamic value) {
    final text = value?.toString().trim();
    return text == null || text.isEmpty ? null : text;
  }

  static double? _nullableDouble(dynamic value) {
    if (value is num) return value.toDouble();
    return double.tryParse(value?.toString() ?? '');
  }
}

class _AiRequestException implements Exception {
  const _AiRequestException(this.message);

  final String message;
}

List<String> _stringList(dynamic value) {
  if (value is! List) return const <String>[];
  return value
      .map((item) => item.toString().trim())
      .where((item) => item.isNotEmpty)
      .toList(growable: false);
}

int? _int(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.round();
  return int.tryParse(value?.toString() ?? '');
}
