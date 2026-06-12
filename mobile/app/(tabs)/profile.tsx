import React from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Switch, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import StatsHeader from '../../src/components/StatsHeader';
import { COURSE, TOTAL_WORDS } from '../../src/data/course';
import { ACHIEVEMENTS, LEAGUES } from '../../src/data/gamification';
import { levelFromXp, todayKey, useStore } from '../../src/store/useStore';
import { colors } from '../../src/theme';

const ACHIEVEMENT_GEMS = 15;

export default function ProfileScreen() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const s = useStore();

  const lessonsCompleted = Object.keys(s.completedLessons).filter((id) => id !== 'practice').length;
  const wordsLearned = COURSE.flatMap((u) => u.lessons)
    .filter((l) => s.completedLessons[l.id])
    .reduce((acc, l) => acc + l.vocab.length, 0);

  const metricValues = {
    xpTotal: s.xpTotal,
    streakBest: s.streakBest,
    lessonsCompleted,
    perfectLessons: s.perfectLessons,
    wordsLearned,
  };

  const { level, into, needed } = levelFromXp(s.xpTotal);
  const league = LEAGUES[Math.min(s.leagueTier, LEAGUES.length - 1)];

  // Últimos 7 días para el gráfico
  const days: { label: string; xp: number }[] = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const key = todayKey(d);
    days.push({
      label: ['D', 'L', 'M', 'X', 'J', 'V', 'S'][d.getDay()],
      xp: s.xpByDay[key] ?? 0,
    });
  }
  const maxXp = Math.max(s.dailyGoalXp, ...days.map((d) => d.xp), 1);

  const joined = new Date(s.joinedAt);
  const joinedLabel = joined.toLocaleDateString('es', { month: 'long', year: 'numeric' });

  const confirmReset = () => {
    Alert.alert('Reiniciar progreso', '¿Seguro? Se borrará todo tu progreso.', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Borrar todo',
        style: 'destructive',
        onPress: () => {
          s.resetAll();
          router.replace('/onboarding');
        },
      },
    ]);
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <StatsHeader />
      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Cabecera de perfil */}
        <View style={styles.profileHeader}>
          <Text style={styles.avatar}>{s.avatar}</Text>
          <Text style={styles.name}>{s.username}</Text>
          <Text style={styles.joined}>Aprendiendo portugués 🇧🇷 desde {joinedLabel}</Text>
          <View style={styles.levelBox}>
            <Text style={styles.levelText}>Nivel {level}</Text>
            <View style={styles.levelBarBg}>
              <View style={[styles.levelBarFill, { width: `${(into / needed) * 100}%` }]} />
            </View>
            <Text style={styles.levelXp}>
              {into} / {needed} XP
            </Text>
          </View>
        </View>

        {/* Estadísticas */}
        <Text style={styles.sectionTitle}>Estadísticas</Text>
        <View style={styles.statsGrid}>
          <Stat icon="🔥" value={s.streak} label="Racha actual" />
          <Stat icon="⚡" value={s.xpTotal} label="XP total" />
          <Stat icon={league.icon} value={league.name} label="Liga" />
          <Stat icon="📖" value={`${wordsLearned}/${TOTAL_WORDS}`} label="Palabras" />
          <Stat icon="📚" value={lessonsCompleted} label="Lecciones" />
          <Stat icon="🎯" value={s.perfectLessons} label="Perfectas" />
        </View>

        {/* XP semanal */}
        <Text style={styles.sectionTitle}>Tu semana</Text>
        <View style={styles.chart}>
          {days.map((d, i) => (
            <View key={i} style={styles.chartCol}>
              <View style={styles.chartBarArea}>
                <View
                  style={[
                    styles.chartBar,
                    {
                      height: `${(d.xp / maxXp) * 100}%`,
                      backgroundColor: d.xp >= s.dailyGoalXp ? colors.green : colors.gold,
                    },
                  ]}
                />
              </View>
              <Text style={styles.chartLabel}>{d.label}</Text>
              <Text style={styles.chartXp}>{d.xp}</Text>
            </View>
          ))}
        </View>

        {/* Logros */}
        <Text style={styles.sectionTitle}>Logros</Text>
        {ACHIEVEMENTS.map((a) => {
          const value = metricValues[a.metric];
          const numericValue = typeof value === 'number' ? value : 0;
          const achievedTiers = a.tiers.filter((t) => numericValue >= t).length;
          const nextTier = a.tiers[Math.min(achievedTiers, a.tiers.length - 1)];
          const unclaimed: string[] = [];
          for (let t = 0; t < achievedTiers; t++) {
            const key = `${a.id}:${t}`;
            if (!s.claimedAchievements.includes(key)) unclaimed.push(key);
          }
          return (
            <View key={a.id} style={styles.achCard}>
              <Text style={[styles.achIcon, { opacity: achievedTiers > 0 ? 1 : 0.35 }]}>
                {a.icon}
              </Text>
              <View style={{ flex: 1 }}>
                <Text style={styles.achTitle}>
                  {a.title} {achievedTiers > 0 ? `· Nivel ${achievedTiers}` : ''}
                </Text>
                <Text style={styles.achDesc}>{a.description(nextTier)}</Text>
                <View style={styles.achBarBg}>
                  <View
                    style={[
                      styles.achBarFill,
                      { width: `${Math.min(100, (numericValue / nextTier) * 100)}%` },
                    ]}
                  />
                </View>
              </View>
              {unclaimed.length > 0 && (
                <Pressable
                  style={styles.claimBtn}
                  onPress={() => {
                    unclaimed.forEach((k) => s.claimAchievement(k, ACHIEVEMENT_GEMS));
                    Alert.alert('¡Logro!', `+${unclaimed.length * ACHIEVEMENT_GEMS} 💎`);
                  }}
                >
                  <Text style={styles.claimText}>💎 {unclaimed.length * ACHIEVEMENT_GEMS}</Text>
                </Pressable>
              )}
            </View>
          );
        })}

        {/* Ajustes */}
        <Text style={styles.sectionTitle}>Ajustes</Text>
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>🔊 Sonido</Text>
          <Switch
            value={s.soundEnabled}
            onValueChange={(v) => s.setSettings({ soundEnabled: v })}
            trackColor={{ true: colors.green }}
          />
        </View>
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>📳 Vibración</Text>
          <Switch
            value={s.hapticsEnabled}
            onValueChange={(v) => s.setSettings({ hapticsEnabled: v })}
            trackColor={{ true: colors.green }}
          />
        </View>
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>⚡ Meta diaria</Text>
          <View style={{ flexDirection: 'row', gap: 6 }}>
            {[10, 30, 50, 80].map((g) => (
              <Pressable
                key={g}
                onPress={() => s.setProfile({ dailyGoalXp: g })}
                style={[styles.goalChip, s.dailyGoalXp === g && styles.goalChipActive]}
              >
                <Text
                  style={[
                    styles.goalChipText,
                    s.dailyGoalXp === g && { color: colors.greenDark },
                  ]}
                >
                  {g}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>

        <Pressable onPress={confirmReset} style={styles.resetBtn}>
          <Text style={styles.resetText}>Reiniciar progreso</Text>
        </Pressable>
      </ScrollView>
    </View>
  );
}

function Stat({ icon, value, label }: { icon: string; value: string | number; label: string }) {
  return (
    <View style={styles.statCard}>
      <Text style={{ fontSize: 24 }}>{icon}</Text>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  scroll: { padding: 16, paddingBottom: 40 },
  profileHeader: { alignItems: 'center', marginTop: 8 },
  avatar: { fontSize: 70 },
  name: { fontSize: 24, fontWeight: '900', color: colors.text, marginTop: 4 },
  joined: { fontSize: 13, color: colors.textSecondary, marginTop: 2 },
  levelBox: { width: '100%', marginTop: 14 },
  levelText: { fontWeight: '800', color: colors.text, marginBottom: 6 },
  levelBarBg: { height: 12, backgroundColor: colors.grayLight, borderRadius: 6, overflow: 'hidden' },
  levelBarFill: { height: '100%', backgroundColor: colors.purple, borderRadius: 6 },
  levelXp: { fontSize: 12, color: colors.textSecondary, marginTop: 4 },
  sectionTitle: { fontSize: 18, fontWeight: '900', color: colors.text, marginTop: 22, marginBottom: 10 },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  statCard: {
    width: '31%',
    borderWidth: 2,
    borderColor: colors.grayLight,
    borderRadius: 14,
    padding: 10,
    alignItems: 'center',
  },
  statValue: { fontSize: 15, fontWeight: '900', color: colors.text, marginTop: 4 },
  statLabel: { fontSize: 11, color: colors.textSecondary, marginTop: 2, textAlign: 'center' },
  chart: {
    flexDirection: 'row',
    borderWidth: 2,
    borderColor: colors.grayLight,
    borderRadius: 16,
    padding: 12,
    height: 150,
  },
  chartCol: { flex: 1, alignItems: 'center' },
  chartBarArea: { flex: 1, width: 16, justifyContent: 'flex-end' },
  chartBar: { width: '100%', borderRadius: 8, minHeight: 2 },
  chartLabel: { fontSize: 12, fontWeight: '800', color: colors.textSecondary, marginTop: 6 },
  chartXp: { fontSize: 10, color: colors.gray },
  achCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    borderWidth: 2,
    borderColor: colors.grayLight,
    borderRadius: 16,
    padding: 12,
    marginBottom: 10,
  },
  achIcon: { fontSize: 34 },
  achTitle: { fontSize: 15, fontWeight: '800', color: colors.text },
  achDesc: { fontSize: 12, color: colors.textSecondary, marginVertical: 4 },
  achBarBg: { height: 8, backgroundColor: colors.grayLight, borderRadius: 4, overflow: 'hidden' },
  achBarFill: { height: '100%', backgroundColor: colors.gold, borderRadius: 4 },
  claimBtn: {
    backgroundColor: colors.gold,
    borderRadius: 12,
    paddingVertical: 8,
    paddingHorizontal: 10,
  },
  claimText: { fontWeight: '900', color: '#785000' },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.grayLight,
  },
  settingLabel: { fontSize: 15, fontWeight: '700', color: colors.text },
  goalChip: {
    borderWidth: 2,
    borderColor: colors.grayLight,
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  goalChipActive: { borderColor: colors.green, backgroundColor: colors.greenLight },
  goalChipText: { fontWeight: '800', color: colors.textSecondary },
  resetBtn: { marginTop: 24, alignItems: 'center', padding: 12 },
  resetText: { color: colors.red, fontWeight: '800' },
});
