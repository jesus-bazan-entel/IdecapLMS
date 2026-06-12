import React, { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import StatsHeader from '../../src/components/StatsHeader';
import {
  botXp,
  LEAGUE_BOTS,
  LEAGUES,
  msUntilWeekEnd,
} from '../../src/data/gamification';
import { useStore } from '../../src/store/useStore';
import { colors } from '../../src/theme';

export default function LeaderboardScreen() {
  const insets = useSafeAreaInsets();
  const leagueXp = useStore((s) => s.leagueXp);
  const leagueTier = useStore((s) => s.leagueTier);
  const username = useStore((s) => s.username);
  const avatar = useStore((s) => s.avatar);
  const lastResult = useStore((s) => s.lastLeagueResult);

  // Refresca el XP de los bots cada minuto
  const [, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 60000);
    return () => clearInterval(t);
  }, []);

  const league = LEAGUES[Math.min(leagueTier, LEAGUES.length - 1)];

  const entries = [
    ...LEAGUE_BOTS.map((b) => ({ name: b.name, avatar: b.avatar, xp: botXp(b), me: false })),
    { name: username, avatar, xp: leagueXp, me: true },
  ].sort((a, b) => b.xp - a.xp);

  const ms = msUntilWeekEnd();
  const days = Math.floor(ms / 86400000);
  const hours = Math.floor((ms % 86400000) / 3600000);

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <StatsHeader />
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.leagueIcon}>{league.icon}</Text>
        <Text style={styles.title}>Liga {league.name}</Text>
        <Text style={styles.subtitle}>
          Los 3 primeros suben de liga · Termina en {days}d {hours}h
        </Text>

        {lastResult && (
          <View
            style={[
              styles.resultBanner,
              {
                backgroundColor: lastResult.promoted
                  ? colors.greenLight
                  : lastResult.demoted
                    ? colors.redLight
                    : colors.blueLight,
              },
            ]}
          >
            <Text style={styles.resultText}>
              {lastResult.promoted
                ? `🎉 ¡Subiste de liga! Quedaste #${lastResult.placement} (+50 💎)`
                : lastResult.demoted
                  ? `📉 Bajaste de liga. Quedaste #${lastResult.placement}`
                  : `Semana pasada quedaste #${lastResult.placement}`}
            </Text>
          </View>
        )}

        <View style={styles.list}>
          {entries.map((e, i) => {
            const inPromo = i < 3;
            const inDemo = i >= entries.length - 3;
            return (
              <View key={e.name + i}>
                {i === 3 && (
                  <Text style={[styles.zoneLabel, { color: colors.green }]}>
                    ▲ ZONA DE ASCENSO ▲
                  </Text>
                )}
                {i === entries.length - 3 && (
                  <Text style={[styles.zoneLabel, { color: colors.red }]}>
                    ▼ ZONA DE DESCENSO ▼
                  </Text>
                )}
                <View style={[styles.row, e.me && styles.rowMe]}>
                  <Text
                    style={[
                      styles.rank,
                      inPromo && { color: colors.green },
                      inDemo && { color: colors.red },
                    ]}
                  >
                    {i + 1}
                  </Text>
                  <Text style={styles.avatar}>{e.avatar}</Text>
                  <Text style={[styles.name, e.me && { color: colors.blueDark }]} numberOfLines={1}>
                    {e.name} {e.me ? '(tú)' : ''}
                  </Text>
                  <Text style={styles.xp}>{e.xp} XP</Text>
                </View>
              </View>
            );
          })}
        </View>
        <Text style={styles.hint}>Gana XP completando lecciones para subir posiciones 💪</Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  scroll: { padding: 16, paddingBottom: 40 },
  leagueIcon: { fontSize: 64, textAlign: 'center', marginTop: 8 },
  title: { fontSize: 26, fontWeight: '900', color: colors.text, textAlign: 'center' },
  subtitle: {
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 4,
    marginBottom: 16,
  },
  resultBanner: { borderRadius: 14, padding: 12, marginBottom: 12 },
  resultText: { fontWeight: '700', color: colors.text, textAlign: 'center' },
  list: { borderWidth: 2, borderColor: colors.grayLight, borderRadius: 16, overflow: 'hidden' },
  zoneLabel: {
    textAlign: 'center',
    fontWeight: '900',
    fontSize: 12,
    paddingVertical: 6,
    letterSpacing: 1,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 14,
    gap: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.grayLight,
  },
  rowMe: { backgroundColor: colors.blueLight },
  rank: { width: 26, fontWeight: '900', fontSize: 15, color: colors.textSecondary },
  avatar: { fontSize: 24 },
  name: { flex: 1, fontWeight: '700', fontSize: 15, color: colors.text },
  xp: { fontWeight: '800', fontSize: 14, color: colors.textSecondary },
  hint: { textAlign: 'center', color: colors.gray, marginTop: 16, fontSize: 13 },
});
