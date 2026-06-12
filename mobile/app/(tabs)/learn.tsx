import React from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import StatsHeader from '../../src/components/StatsHeader';
import { COURSE } from '../../src/data/course';
import { selectXpToday, useStore } from '../../src/store/useStore';
import { colors, unitColors } from '../../src/theme';

const ZIGZAG = [0, 45, 70, 45, 0, -45, -70, -45];

export default function LearnScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const completedLessons = useStore((s) => s.completedLessons);
  const hearts = useStore((s) => s.hearts);
  const xpToday = useStore(selectXpToday);
  const dailyGoalXp = useStore((s) => s.dailyGoalXp);
  const mistakes = useStore((s) => s.mistakes);

  // Una lección está desbloqueada si todas las anteriores tienen al menos 1 corona
  const flat = COURSE.flatMap((u) => u.lessons);
  const firstIncomplete = flat.findIndex((l) => !completedLessons[l.id]);
  const unlockedCount = firstIncomplete === -1 ? flat.length : firstIncomplete + 1;

  const openLesson = (lessonId: string, locked: boolean) => {
    if (locked) {
      Alert.alert('Lección bloqueada', 'Completa las lecciones anteriores para desbloquearla.');
      return;
    }
    if (hearts <= 0) {
      Alert.alert(
        '¡Te quedaste sin corazones!',
        'Practica para recuperar un corazón, espera a que se recarguen o compra una recarga en la tienda.',
        [
          { text: 'Practicar', onPress: () => router.push('/lesson/practice') },
          { text: 'OK', style: 'cancel' },
        ]
      );
      return;
    }
    router.push(`/lesson/${lessonId}`);
  };

  let globalIdx = 0;
  const goalProgress = Math.min(1, xpToday / dailyGoalXp);

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <StatsHeader />
      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Meta diaria */}
        <View style={styles.goalCard}>
          <View style={{ flex: 1 }}>
            <Text style={styles.goalTitle}>Meta diaria</Text>
            <View style={styles.goalBarBg}>
              <View style={[styles.goalBarFill, { width: `${goalProgress * 100}%` }]} />
            </View>
            <Text style={styles.goalText}>
              {xpToday} / {dailyGoalXp} XP {goalProgress >= 1 ? '· ¡Meta cumplida! 🎉' : ''}
            </Text>
          </View>
          <Text style={{ fontSize: 36 }}>⚡</Text>
        </View>

        {/* Práctica de errores */}
        <Pressable style={styles.practiceCard} onPress={() => router.push('/lesson/practice')}>
          <Text style={{ fontSize: 28 }}>💪</Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.practiceTitle}>Práctica personalizada</Text>
            <Text style={styles.practiceSub}>
              {mistakes.length >= 4
                ? `Repasa tus ${mistakes.length} errores y recupera un corazón`
                : 'Repasa lo aprendido y recupera un corazón'}
            </Text>
          </View>
        </Pressable>

        {COURSE.map((unit, ui) => {
          const palette = unitColors[ui % unitColors.length];
          return (
            <View key={unit.id}>
              <View style={[styles.unitBanner, { backgroundColor: palette.main }]}>
                <Text style={styles.unitTitle}>{unit.title}</Text>
                <Text style={styles.unitDesc}>{unit.description}</Text>
              </View>
              <View style={styles.path}>
                {unit.lessons.map((lesson) => {
                  const idx = globalIdx++;
                  const done = !!completedLessons[lesson.id];
                  const locked = idx >= unlockedCount;
                  const isCurrent = idx === unlockedCount - 1 && !done;
                  const crowns = completedLessons[lesson.id]?.times ?? 0;
                  return (
                    <View
                      key={lesson.id}
                      style={[styles.nodeWrap, { transform: [{ translateX: ZIGZAG[idx % ZIGZAG.length] }] }]}
                    >
                      {isCurrent && (
                        <View style={styles.startBubble}>
                          <Text style={styles.startText}>EMPIEZA</Text>
                        </View>
                      )}
                      <Pressable
                        onPress={() => openLesson(lesson.id, locked)}
                        style={[
                          styles.node,
                          {
                            backgroundColor: locked
                              ? colors.locked
                              : done
                                ? colors.gold
                                : palette.main,
                            borderBottomColor: locked
                              ? colors.lockedDark
                              : done
                                ? colors.goldDark
                                : palette.dark,
                          },
                        ]}
                      >
                        <Text style={{ fontSize: 30, opacity: locked ? 0.5 : 1 }}>
                          {done ? '👑' : locked ? '🔒' : lesson.icon}
                        </Text>
                      </Pressable>
                      <Text style={styles.nodeLabel}>{lesson.title}</Text>
                      {done && (
                        <Text style={styles.crowns}>
                          {crowns} {crowns === 1 ? 'corona' : 'coronas'}
                        </Text>
                      )}
                    </View>
                  );
                })}
              </View>
            </View>
          );
        })}
        <Text style={styles.endText}>🎓 ¡Más unidades muy pronto!</Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  scroll: { padding: 16, paddingBottom: 40 },
  goalCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    borderWidth: 2,
    borderColor: colors.grayLight,
    borderRadius: 16,
    padding: 14,
    marginBottom: 12,
  },
  goalTitle: { fontSize: 15, fontWeight: '800', color: colors.text, marginBottom: 6 },
  goalBarBg: {
    height: 14,
    backgroundColor: colors.grayLight,
    borderRadius: 7,
    overflow: 'hidden',
    marginBottom: 6,
  },
  goalBarFill: { height: '100%', backgroundColor: colors.gold, borderRadius: 7 },
  goalText: { fontSize: 13, color: colors.textSecondary },
  practiceCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    borderWidth: 2,
    borderColor: colors.blue,
    backgroundColor: colors.blueLight,
    borderRadius: 16,
    padding: 14,
    marginBottom: 16,
  },
  practiceTitle: { fontSize: 15, fontWeight: '800', color: colors.blueDark },
  practiceSub: { fontSize: 13, color: colors.textSecondary },
  unitBanner: { borderRadius: 16, padding: 18, marginTop: 8, marginBottom: 20 },
  unitTitle: { color: '#fff', fontSize: 18, fontWeight: '900' },
  unitDesc: { color: '#ffffffdd', fontSize: 14, marginTop: 4 },
  path: { alignItems: 'center', gap: 18, marginBottom: 16 },
  nodeWrap: { alignItems: 'center' },
  node: {
    width: 72,
    height: 72,
    borderRadius: 36,
    alignItems: 'center',
    justifyContent: 'center',
    borderBottomWidth: 6,
  },
  nodeLabel: { marginTop: 6, fontSize: 13, fontWeight: '700', color: colors.textSecondary },
  crowns: { fontSize: 11, color: colors.goldDark, fontWeight: '700' },
  startBubble: {
    backgroundColor: '#fff',
    borderWidth: 2,
    borderColor: colors.grayLight,
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginBottom: 6,
  },
  startText: { color: colors.green, fontWeight: '900', fontSize: 12, letterSpacing: 0.5 },
  endText: {
    textAlign: 'center',
    color: colors.gray,
    fontWeight: '700',
    marginTop: 12,
    fontSize: 15,
  },
});
