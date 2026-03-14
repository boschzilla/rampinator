import React, { useState, useEffect, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Animated,
  SafeAreaView,
  StatusBar,
  Switch,
  FlatList,
} from "react-native";

// ---- Theme ----
const C = {
  bg: "#0d0d1a",
  panel: "#12122b",
  entry: "#1a1a3e",
  accent: "#c8a84b",
  accent2: "#8b6914",
  green: "#4cff91",
  red: "#ff4c4c",
  orange: "#ffaa33",
  muted: "#666688",
  fg: "#d8d4c0",
  selected: "#1e1e4a",
};

const statusColor = (status) => {
  switch (status) {
    case "Live": return C.green;
    case "Connecting...": return C.orange;
    case "Error": return C.red;
    default: return C.muted;
  }
};

// ---- Pulsing dot ----
const StatusDot = ({ status }) => {
  const pulse = useRef(new Animated.Value(1)).current;
  const shouldPulse = status === "Live" || status === "Connecting...";

  useEffect(() => {
    if (shouldPulse) {
      const anim = Animated.loop(
        Animated.sequence([
          Animated.timing(pulse, { toValue: 0.3, duration: 600, useNativeDriver: true }),
          Animated.timing(pulse, { toValue: 1, duration: 600, useNativeDriver: true }),
        ])
      );
      anim.start();
      return () => anim.stop();
    }
  }, [shouldPulse]);

  return (
    <Animated.View
      style={[
        styles.statusDot,
        { backgroundColor: statusColor(status), opacity: shouldPulse ? pulse : 1 },
      ]}
    />
  );
};

// ---- Stat Card ----
const StatCard = ({ label, value, color }) => (
  <View style={styles.statCard}>
    <Text style={styles.statLabel}>{label}</Text>
    <Text style={[styles.statValue, { color }]}>{value}</Text>
  </View>
);

// ---- Search Card ----
const SearchCard = ({ entry, onToggle }) => (
  <View style={styles.searchCard}>
    <Switch
      value={entry.enabled}
      onValueChange={onToggle}
      trackColor={{ false: C.entry, true: C.green }}
      thumbColor="#fff"
      style={{ transform: [{ scaleX: 0.8 }, { scaleY: 0.8 }] }}
    />
    <View style={styles.searchInfo}>
      <Text style={styles.searchName}>{entry.name}</Text>
      <Text style={styles.searchLeague}>{entry.league}</Text>
    </View>
    <View style={styles.searchStatus}>
      <StatusDot status={entry.status} />
      <Text style={[styles.searchStatusText, { color: statusColor(entry.status) }]}>
        {entry.status}
      </Text>
    </View>
    <View style={styles.hitsBadge}>
      <Text style={styles.hitsText}>{entry.hits}</Text>
    </View>
  </View>
);

// ---- Log Entry ----
const LogRow = ({ log }) => {
  const color =
    log.tag === "hit" ? C.green :
    log.tag === "error" ? C.red :
    log.tag === "warn" ? C.orange : C.muted;

  return (
    <View style={styles.logRow}>
      <Text style={styles.logTime}>{log.time}</Text>
      <Text style={[styles.logMsg, { color }]} numberOfLines={1}>{log.message}</Text>
    </View>
  );
};

// ---- Main App ----
export default function App() {
  const [searches, setSearches] = useState([
    { id: "s1", name: "Mageblood", league: "Settlers", status: "Live", hits: 42, enabled: true },
    { id: "s2", name: "Mirror of Kalandra", league: "Standard", status: "Live", hits: 7, enabled: true },
    { id: "s3", name: "Headhunter", league: "Settlers", status: "Connecting...", hits: 0, enabled: true },
    { id: "s4", name: "Divination Cards", league: "Settlers", status: "Error", hits: 18, enabled: false },
  ]);

  const [logs, setLogs] = useState([
    { time: "14:32:01", message: "NEW LISTING: Mageblood — 3 item(s)", tag: "hit" },
    { time: "14:31:45", message: "Connected to Settlers/Yp9QVzq7IY", tag: "info" },
    { time: "14:31:12", message: "Reconnecting Divination Cards...", tag: "warn" },
    { time: "14:30:58", message: "Auth rejected — verify POESESSID", tag: "error" },
    { time: "14:30:02", message: "POESESSID saved. Starting monitors...", tag: "info" },
  ]);

  // Simulate incoming hits
  useEffect(() => {
    const interval = setInterval(() => {
      setSearches((prev) => {
        const updated = [...prev];
        updated[0] = { ...updated[0], hits: updated[0].hits + 1 };
        return updated;
      });
      const now = new Date();
      const ts = now.toTimeString().slice(0, 8);
      setLogs((prev) => [
        { time: ts, message: "NEW LISTING: Mageblood — 1 item(s)", tag: "hit" },
        ...prev.slice(0, 49),
      ]);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const toggleSearch = (id) => {
    setSearches((prev) =>
      prev.map((s) => (s.id === id ? { ...s, enabled: !s.enabled } : s))
    );
  };

  const activeCount = searches.filter((s) => s.status === "Live" || s.status === "Connecting...").length;
  const totalHits = searches.reduce((sum, s) => sum + s.hits, 0);
  const errorCount = searches.filter((s) => s.status === "Error").length;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={C.panel} />

      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Rampinator</Text>
        <Text style={styles.headerSub}>React Native Demo</Text>
      </View>

      {/* Stats */}
      <View style={styles.statsRow}>
        <StatCard label="Active" value={activeCount} color={C.green} />
        <StatCard label="Total Hits" value={totalHits} color={C.accent} />
        <StatCard label="Errors" value={errorCount} color={C.red} />
      </View>

      {/* Section header */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>LIVE SEARCHES</Text>
        <TouchableOpacity
          style={styles.addButton}
          onPress={() => {
            const ts = new Date().toTimeString().slice(0, 8);
            setLogs((prev) => [
              { time: ts, message: "Add Search dialog would open here...", tag: "info" },
              ...prev,
            ]);
          }}
        >
          <Text style={styles.addButtonText}>+ Add Search</Text>
        </TouchableOpacity>
      </View>

      {/* Search list */}
      <FlatList
        data={searches}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <SearchCard entry={item} onToggle={() => toggleSearch(item.id)} />
        )}
        style={styles.searchList}
        contentContainerStyle={{ paddingHorizontal: 12 }}
      />

      {/* Activity log */}
      <View style={styles.logSection}>
        <Text style={styles.logHeader}>ACTIVITY LOG</Text>
        <FlatList
          data={logs}
          keyExtractor={(_, i) => `log-${i}`}
          renderItem={({ item }) => <LogRow log={item} />}
          style={{ maxHeight: 120 }}
        />
      </View>

      {/* Status bar */}
      <View style={styles.statusBar}>
        <Text style={styles.statusBarText}>
          Last hit: Mageblood — {totalHits} total hits
        </Text>
        <Text style={styles.statusBarText}>React Native</Text>
      </View>
    </SafeAreaView>
  );
}

// ---- Styles ----
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: C.bg },

  header: {
    flexDirection: "row",
    alignItems: "center",
    padding: 14,
    backgroundColor: C.panel,
    borderBottomWidth: 1,
    borderBottomColor: C.entry,
  },
  headerTitle: { fontSize: 16, fontWeight: "bold", color: C.accent },
  headerSub: { fontSize: 12, color: C.muted, marginLeft: 10 },

  statsRow: { flexDirection: "row", padding: 12, gap: 10 },
  statCard: {
    flex: 1,
    backgroundColor: C.panel,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: C.entry,
    padding: 14,
  },
  statLabel: { fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: 0.5 },
  statValue: { fontSize: 24, fontWeight: "bold", marginTop: 4 },

  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  sectionTitle: { fontSize: 12, fontWeight: "600", color: C.accent, letterSpacing: 0.5 },
  addButton: {
    backgroundColor: C.accent2,
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 4,
  },
  addButtonText: { fontSize: 12, color: "#f0e6c0" },

  searchList: { flex: 1 },
  searchCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: C.panel,
    borderRadius: 8,
    borderWidth: 0.5,
    borderColor: C.entry,
    padding: 10,
    marginBottom: 4,
  },
  searchInfo: { flex: 1, marginLeft: 10 },
  searchName: { fontSize: 13, fontWeight: "500", color: C.fg },
  searchLeague: { fontSize: 11, color: C.muted },
  searchStatus: { flexDirection: "row", alignItems: "center", marginRight: 14 },
  searchStatusText: { fontSize: 12, marginLeft: 6 },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  hitsBadge: {
    backgroundColor: C.entry,
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 2,
  },
  hitsText: { fontSize: 12, fontWeight: "600", color: C.accent },

  logSection: {
    borderTopWidth: 1,
    borderTopColor: C.entry,
    padding: 12,
  },
  logHeader: { fontSize: 11, color: C.muted, letterSpacing: 0.5, marginBottom: 6 },
  logRow: { flexDirection: "row", paddingVertical: 1 },
  logTime: { fontSize: 11, fontFamily: "monospace", color: C.muted, marginRight: 10 },
  logMsg: { fontSize: 11, fontFamily: "monospace", flex: 1 },

  statusBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: C.panel,
    borderTopWidth: 1,
    borderTopColor: C.entry,
  },
  statusBarText: { fontSize: 11, color: C.muted },
});
