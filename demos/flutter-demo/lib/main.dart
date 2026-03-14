import 'dart:async';
import 'package:flutter/material.dart';

void main() => runApp(const RampinatorApp());

// ---- Theme ----
class AppColors {
  static const bg = Color(0xFF0D0D1A);
  static const panel = Color(0xFF12122B);
  static const entry = Color(0xFF1A1A3E);
  static const accent = Color(0xFFC8A84B);
  static const accent2 = Color(0xFF8B6914);
  static const green = Color(0xFF4CFF91);
  static const red = Color(0xFFFF4C4C);
  static const orange = Color(0xFFFFAA33);
  static const muted = Color(0xFF666688);
  static const fg = Color(0xFFD8D4C0);
  static const selected = Color(0xFF1E1E4A);
}

// ---- Data ----
class SearchEntry {
  final String id;
  final String name;
  final String league;
  String status;
  int hits;
  bool enabled;

  SearchEntry({
    required this.id,
    required this.name,
    required this.league,
    this.status = 'Idle',
    this.hits = 0,
    this.enabled = true,
  });

  Color get statusColor {
    switch (status) {
      case 'Live':
        return AppColors.green;
      case 'Connecting...':
        return AppColors.orange;
      case 'Error':
        return AppColors.red;
      default:
        return AppColors.muted;
    }
  }
}

class LogEntry {
  final String time;
  final String message;
  final String tag;

  LogEntry({required this.time, required this.message, this.tag = 'info'});

  Color get color {
    switch (tag) {
      case 'hit':
        return AppColors.green;
      case 'error':
        return AppColors.red;
      case 'warn':
        return AppColors.orange;
      default:
        return AppColors.muted;
    }
  }
}

// ---- App ----
class RampinatorApp extends StatelessWidget {
  const RampinatorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Rampinator — Flutter Demo',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        scaffoldBackgroundColor: AppColors.bg,
        appBarTheme: const AppBarTheme(
          backgroundColor: AppColors.panel,
          foregroundColor: AppColors.accent,
          elevation: 0,
        ),
        colorScheme: ColorScheme.dark(
          primary: AppColors.accent,
          secondary: AppColors.accent2,
          surface: AppColors.panel,
        ),
        cardTheme: const CardThemeData(
          color: AppColors.panel,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(10)),
            side: BorderSide(color: AppColors.entry),
          ),
        ),
        textTheme: const TextTheme(
          bodyMedium: TextStyle(color: AppColors.fg),
          bodySmall: TextStyle(color: AppColors.muted),
        ),
      ),
      home: const DashboardScreen(),
    );
  }
}

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final List<SearchEntry> _searches = [
    SearchEntry(id: 's1', name: 'Mageblood', league: 'Settlers', status: 'Live', hits: 42),
    SearchEntry(id: 's2', name: 'Mirror of Kalandra', league: 'Standard', status: 'Live', hits: 7),
    SearchEntry(id: 's3', name: 'Headhunter', league: 'Settlers', status: 'Connecting...', hits: 0),
    SearchEntry(id: 's4', name: 'Divination Cards', league: 'Settlers', status: 'Error', hits: 18, enabled: false),
  ];

  final List<LogEntry> _logs = [
    LogEntry(time: '14:32:01', message: 'NEW LISTING: Mageblood — 3 item(s)', tag: 'hit'),
    LogEntry(time: '14:31:45', message: 'Connected to Settlers/Yp9QVzq7IY', tag: 'info'),
    LogEntry(time: '14:31:12', message: 'Reconnecting Divination Cards...', tag: 'warn'),
    LogEntry(time: '14:30:58', message: 'Auth rejected — verify POESESSID', tag: 'error'),
    LogEntry(time: '14:30:02', message: 'POESESSID saved. Starting monitors...', tag: 'info'),
  ];

  Timer? _simTimer;

  @override
  void initState() {
    super.initState();
    // Simulate incoming hits every few seconds
    _simTimer = Timer.periodic(const Duration(seconds: 4), (_) {
      setState(() {
        final s = _searches[0];
        s.hits++;
        final now = TimeOfDay.now();
        final ts = '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}:00';
        _logs.insert(0, LogEntry(time: ts, message: 'NEW LISTING: ${s.name} — 1 item(s)', tag: 'hit'));
      });
    });
  }

  @override
  void dispose() {
    _simTimer?.cancel();
    super.dispose();
  }

  int get _activeCount => _searches.where((s) => s.status == 'Live' || s.status == 'Connecting...').length;
  int get _totalHits => _searches.fold(0, (sum, s) => sum + s.hits);
  int get _errorCount => _searches.where((s) => s.status == 'Error').length;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            const Text('Rampinator', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(width: 10),
            Text('Flutter Demo', style: TextStyle(fontSize: 12, color: AppColors.muted)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined, color: AppColors.muted),
            onPressed: () {},
          ),
          IconButton(
            icon: const Icon(Icons.settings_outlined, color: AppColors.muted),
            onPressed: () {},
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Column(
        children: [
          // Stats row
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                _StatCard(label: 'Active Searches', value: '$_activeCount', valueColor: AppColors.green),
                const SizedBox(width: 12),
                _StatCard(label: 'Total Hits', value: '$_totalHits', valueColor: AppColors.accent),
                const SizedBox(width: 12),
                _StatCard(label: 'Errors', value: '$_errorCount', valueColor: AppColors.red),
              ],
            ),
          ),

          // Section header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Row(
              children: [
                const Text('LIVE SEARCHES', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.accent, letterSpacing: 0.5)),
                const Spacer(),
                _ActionButton(label: '+ Add Search', accent: true, onTap: () {
                  setState(() {
                    final ts = TimeOfDay.now();
                    final timeStr = '${ts.hour.toString().padLeft(2, '0')}:${ts.minute.toString().padLeft(2, '0')}:00';
                    _logs.insert(0, LogEntry(time: timeStr, message: 'Add Search dialog would open here...', tag: 'info'));
                  });
                }),
              ],
            ),
          ),
          const SizedBox(height: 8),

          // Search list
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              itemCount: _searches.length,
              itemBuilder: (ctx, i) => _SearchTile(
                entry: _searches[i],
                onToggle: () => setState(() => _searches[i].enabled = !_searches[i].enabled),
              ),
            ),
          ),

          // Activity log
          Container(
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: AppColors.entry)),
            ),
            padding: const EdgeInsets.all(12),
            height: 160,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('ACTIVITY LOG', style: TextStyle(fontSize: 11, color: AppColors.muted, letterSpacing: 0.5)),
                const SizedBox(height: 6),
                Expanded(
                  child: ListView.builder(
                    itemCount: _logs.length,
                    itemBuilder: (ctx, i) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 1),
                      child: Row(
                        children: [
                          Text(_logs[i].time, style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: AppColors.muted)),
                          const SizedBox(width: 10),
                          Expanded(child: Text(_logs[i].message, style: TextStyle(fontSize: 11, fontFamily: 'monospace', color: _logs[i].color))),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Status bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            color: AppColors.panel,
            child: Row(
              children: [
                Text('Last hit: Mageblood @ 14:32:01 — $_totalHits total hits', style: const TextStyle(fontSize: 11, color: AppColors.muted)),
                const Spacer(),
                const Text('Flutter Demo', style: TextStyle(fontSize: 11, color: AppColors.muted)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ---- Widgets ----

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final Color valueColor;

  const _StatCard({required this.label, required this.value, required this.valueColor});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label.toUpperCase(), style: const TextStyle(fontSize: 10, color: AppColors.muted, letterSpacing: 0.5)),
              const SizedBox(height: 4),
              Text(value, style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: valueColor)),
            ],
          ),
        ),
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final String label;
  final bool accent;
  final VoidCallback onTap;

  const _ActionButton({required this.label, this.accent = false, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        decoration: BoxDecoration(
          color: accent ? AppColors.accent2 : Colors.transparent,
          border: Border.all(color: accent ? AppColors.accent2 : AppColors.entry),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(label, style: TextStyle(fontSize: 12, color: accent ? const Color(0xFFF0E6C0) : AppColors.muted)),
      ),
    );
  }
}

class _SearchTile extends StatelessWidget {
  final SearchEntry entry;
  final VoidCallback onToggle;

  const _SearchTile({required this.entry, required this.onToggle});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.panel,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.entry, width: 0.5),
      ),
      child: Row(
        children: [
          // Toggle switch
          GestureDetector(
            onTap: onToggle,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 38,
              height: 22,
              decoration: BoxDecoration(
                color: entry.enabled ? AppColors.green : AppColors.entry,
                borderRadius: BorderRadius.circular(11),
              ),
              child: AnimatedAlign(
                duration: const Duration(milliseconds: 200),
                alignment: entry.enabled ? Alignment.centerRight : Alignment.centerLeft,
                child: Container(
                  width: 18,
                  height: 18,
                  margin: const EdgeInsets.all(2),
                  decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle),
                ),
              ),
            ),
          ),
          const SizedBox(width: 14),
          // Name + league
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(entry.name, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: AppColors.fg)),
                Text(entry.league, style: const TextStyle(fontSize: 11, color: AppColors.muted)),
              ],
            ),
          ),
          // Status
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _StatusDot(status: entry.status),
              const SizedBox(width: 6),
              Text(entry.status, style: TextStyle(fontSize: 12, color: entry.statusColor)),
            ],
          ),
          const SizedBox(width: 20),
          // Hits
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
            decoration: BoxDecoration(color: AppColors.entry, borderRadius: BorderRadius.circular(12)),
            child: Text('${entry.hits}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.accent)),
          ),
        ],
      ),
    );
  }
}

class _StatusDot extends StatefulWidget {
  final String status;
  const _StatusDot({required this.status});

  @override
  State<_StatusDot> createState() => _StatusDotState();
}

class _StatusDotState extends State<_StatusDot> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1200))..repeat(reverse: true);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Color get _color {
    switch (widget.status) {
      case 'Live':
        return AppColors.green;
      case 'Connecting...':
        return AppColors.orange;
      case 'Error':
        return AppColors.red;
      default:
        return AppColors.muted;
    }
  }

  @override
  Widget build(BuildContext context) {
    final shouldPulse = widget.status == 'Connecting...' || widget.status == 'Live';
    if (shouldPulse) {
      return AnimatedBuilder(
        animation: _ctrl,
        builder: (_, __) => Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: _color.withValues(alpha: 0.5 + _ctrl.value * 0.5),
            boxShadow: [BoxShadow(color: _color.withValues(alpha: 0.4), blurRadius: 4 + _ctrl.value * 4)],
          ),
        ),
      );
    }
    return Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(shape: BoxShape.circle, color: _color),
    );
  }
}

// AnimatedBuilder is just an alias
class AnimatedBuilder extends AnimatedWidget {
  final Widget Function(BuildContext, Widget?) builder;
  const AnimatedBuilder({super.key, required super.listenable, required this.builder});

  @override
  Widget build(BuildContext context) => builder(context, null);

  Animation<double> get animation => listenable as Animation<double>;
}
