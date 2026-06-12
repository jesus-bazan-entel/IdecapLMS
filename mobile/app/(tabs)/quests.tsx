import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import DuoButton from '../../src/components/DuoButton';
import StatsHeader from '../../src/components/StatsHeader';
import { questsForDay } from '../../src/data/gamification';
import { selectXpToday, todayKey, useStore } from '../../src/store/useStore';
import { colors } from '../../src/theme';

export default function QuestsScreen() {
  const insets = useSafeAreaInsets();
  const s = useStore();
  const xpToday = useStore(selectXpToday);

  const metrics = {
    xpToday,
    lessonsToday: s.lessonsToday,
    perfectToday: s.perfectToday,
    practiceToday: s.practiceToday,
    bestComboToday: s.bestComboToday,
  };

  const quests = questsForDay(todayKey());

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <StatsHeader />
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>Misiones del día</Text>
        <Text style={styles.subtitle}>Se renuevan cada día a medianoche 🕛</Text>

        {quests.map((q) => {
          const progress = Math.min(metrics[q.metric], q.target);
          const done = progress >= q.target;
          const claimed = s.claimedQuests.includes(q.id);
          return (
            <View key={q.id} style={styles.card}>
              <Text style={styles.icon}>{q.icon}</Text>
              <View style={{ flex: 1 }}>
                <Text style={styles.questTitle}>{q.title(q.target)}</Text>
                <View style={styles.barBg}>
                  <View
                    style={[styles.barFill, { width: `${(progress / q.target) * 100}%` }]}
                  />
                </View>
                <Text style={styles.progressText}>
                  {progress} / {q.target}
                </Text>
              </View>
              <View style={styles.rewardCol}>
                {claimed ? (
                  <Text style={styles.claimed}>✅</Text>
                ) : done ? (
                  <DuoButton
                    label="Reclamar"
                    variant="gold"
                    style={styles.claimBtn}
                    onPress={() => s.claimQuest(q.id, q.rewardGems)}
                  />
                ) : (
                  <Text style={styles.rewardText}>💎 {q.rewardGems}</Text>
                )}
              </View>
            </View>
          );
        })}

        <View style={styles.tipCard}>
          <Text style={{ fontSize: 28 }}>🦜</Text>
          <Text style={styles.tipText}>
            Completa misiones para ganar gemas y canjearlas en la tienda por protectores de racha,
            corazones y potenciadores.
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  scroll: { padding: 16, paddingBottom: 40 },
  title: { fontSize: 24, fontWeight: '900', color: colors.text, marginTop: 8 },
  subtitle: { fontSize: 14, color: colors.textSecondary, marginBottom: 16 },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    borderWidth: 2,
    borderColor: colors.grayLight,
    borderRadius: 16,
    padding: 14,
    marginBottom: 12,
  },
  icon: { fontSize: 32 },
  questTitle: { fontSize: 15, fontWeight: '800', color: colors.text, marginBottom: 6 },
  barBg: {
    height: 12,
    backgroundColor: colors.grayLight,
    borderRadius: 6,
    overflow: 'hidden',
    marginBottom: 4,
  },
  barFill: { height: '100%', backgroundColor: colors.gold, borderRadius: 6 },
  progressText: { fontSize: 12, color: colors.textSecondary },
  rewardCol: { alignItems: 'center', minWidth: 64 },
  rewardText: { fontWeight: '800', color: colors.blue },
  claimed: { fontSize: 24 },
  claimBtn: { paddingVertical: 8, paddingHorizontal: 10, borderRadius: 12 },
  tipCard: {
    flexDirection: 'row',
    gap: 12,
    alignItems: 'center',
    backgroundColor: colors.blueLight,
    borderRadius: 16,
    padding: 14,
    marginTop: 8,
  },
  tipText: { flex: 1, color: colors.text, fontSize: 13, lineHeight: 19 },
});
