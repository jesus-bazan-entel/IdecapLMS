import React, { useMemo, useRef, useState } from 'react';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import DuoButton from '../../src/components/DuoButton';
import ExerciseView from '../../src/components/exercises/ExerciseView';
import { getLesson } from '../../src/data/course';
import {
  generateLessonExercises,
  generatePracticeExercises,
} from '../../src/data/generator';
import { hapticError, hapticSuccess, stopSpeech } from '../../src/lib/feedback';
import { COSTS, useStore } from '../../src/store/useStore';
import { Exercise } from '../../src/types';
import { colors } from '../../src/theme';

type Status = 'answering' | 'correct' | 'wrong' | 'finished' | 'noHearts';

export default function LessonScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();

  const isPractice = id === 'practice';
  const store = useStore;
  const hearts = useStore((s) => s.hearts);

  const initialQueue = useMemo<Exercise[]>(() => {
    if (isPractice) {
      const s = store.getState();
      if (s.mistakes.length >= 4) return s.mistakes.slice(0, 8);
      const completed = Object.keys(s.completedLessons);
      if (completed.length > 0) return generatePracticeExercises(completed);
      return generateLessonExercises('u1l1', Math.floor(Math.random() * 100));
    }
    const attempt = store.getState().completedLessons[id!]?.times ?? 0;
    return generateLessonExercises(id!, attempt);
  }, [id]);

  const usedMistakes = useMemo(
    () => isPractice && store.getState().mistakes.length >= 4,
    [isPractice]
  );

  const [queue, setQueue] = useState<Exercise[]>(initialQueue);
  const [idx, setIdx] = useState(0);
  const [status, setStatus] = useState<Status>('answering');
  const [correctAnswer, setCorrectAnswer] = useState('');
  const [combo, setCombo] = useState(0);
  const comboBestRef = useRef(0);
  const mistakesRef = useRef<Exercise[]>([]);
  const errorCountRef = useRef(0);
  const [reward, setReward] = useState({ xpEarned: 0, gemsEarned: 0 });

  const lessonMeta = !isPractice && id ? getLesson(id) : null;
  const exercise = queue[idx];
  const progress = queue.length > 0 ? idx / queue.length : 0;

  const handleAnswered = (correct: boolean, answer: string) => {
    stopSpeech();
    const soft = exercise.type === 'match';
    if (correct) {
      hapticSuccess();
      const newCombo = combo + 1;
      setCombo(newCombo);
      comboBestRef.current = Math.max(comboBestRef.current, newCombo);
      setStatus('correct');
    } else {
      hapticError();
      setCombo(0);
      errorCountRef.current += 1;
      setCorrectAnswer(answer);
      if (!soft) {
        mistakesRef.current = [...mistakesRef.current, exercise].slice(-10);
        if (!isPractice) {
          store.getState().loseHeart();
          if (store.getState().hearts <= 0) {
            setStatus('noHearts');
            return;
          }
        }
        // Reintenta el ejercicio al final, como Duolingo
        setQueue((q) => [...q, exercise]);
      }
      setStatus('wrong');
    }
  };

  const advance = () => {
    if (idx + 1 >= queue.length) {
      finish();
      return;
    }
    setIdx(idx + 1);
    setStatus('answering');
    setCorrectAnswer('');
  };

  const finish = () => {
    const result = store.getState().completeLesson({
      lessonId: isPractice ? 'practice' : id!,
      perfect: errorCountRef.current === 0,
      comboBest: comboBestRef.current,
      mistakes: mistakesRef.current,
      isPractice,
    });
    if (usedMistakes) store.getState().clearMistakes(initialQueue.length);
    setReward(result);
    setStatus('finished');
  };

  const confirmExit = () => {
    Alert.alert('¿Quieres salir?', 'Perderás el progreso de esta lección.', [
      { text: 'Seguir aprendiendo', style: 'cancel' },
      { text: 'Salir', style: 'destructive', onPress: () => router.back() },
    ]);
  };

  // ---------- Pantalla final ----------
  if (status === 'finished') {
    const accuracy =
      queue.length > 0
        ? Math.round(((queue.length - errorCountRef.current) / queue.length) * 100)
        : 100;
    return (
      <View style={[styles.container, styles.center, { paddingTop: insets.top }]}>
        <Text style={{ fontSize: 80 }}>{errorCountRef.current === 0 ? '🏆' : '🎉'}</Text>
        <Text style={styles.finishTitle}>
          {errorCountRef.current === 0 ? '¡Lección perfecta!' : '¡Lección completada!'}
        </Text>
        <View style={styles.rewardRow}>
          <View style={[styles.rewardCard, { borderColor: colors.gold }]}>
            <Text style={styles.rewardLabel}>XP</Text>
            <Text style={[styles.rewardValue, { color: colors.goldDark }]}>
              ⚡ {reward.xpEarned}
            </Text>
          </View>
          <View style={[styles.rewardCard, { borderColor: colors.blue }]}>
            <Text style={styles.rewardLabel}>Precisión</Text>
            <Text style={[styles.rewardValue, { color: colors.blue }]}>🎯 {Math.max(0, accuracy)}%</Text>
          </View>
          {reward.gemsEarned > 0 && (
            <View style={[styles.rewardCard, { borderColor: colors.purple }]}>
              <Text style={styles.rewardLabel}>Gemas</Text>
              <Text style={[styles.rewardValue, { color: colors.purpleDark }]}>
                💎 {reward.gemsEarned}
              </Text>
            </View>
          )}
        </View>
        {isPractice && (
          <Text style={styles.practiceNote}>+1 ❤️ por practicar</Text>
        )}
        <View style={[styles.finishFooter, { paddingBottom: insets.bottom + 16 }]}>
          <DuoButton label="Continuar" onPress={() => router.back()} />
        </View>
      </View>
    );
  }

  // ---------- Sin corazones ----------
  if (status === 'noHearts') {
    const gems = store.getState().gems;
    return (
      <View style={[styles.container, styles.center, { paddingTop: insets.top }]}>
        <Text style={{ fontSize: 80 }}>💔</Text>
        <Text style={styles.finishTitle}>¡Te quedaste sin corazones!</Text>
        <Text style={styles.noHeartsText}>
          Practica para recuperar corazones o canjea gemas para seguir.
        </Text>
        <View style={[styles.finishFooter, { paddingBottom: insets.bottom + 16, gap: 10 }]}>
          <DuoButton
            label={`Recargar vidas · 💎 ${COSTS.refillHearts}`}
            variant="danger"
            disabled={gems < COSTS.refillHearts}
            onPress={() => {
              if (store.getState().buyRefillHearts()) {
                setStatus('wrong');
              }
            }}
          />
          <DuoButton label="Salir" variant="white" onPress={() => router.back()} />
        </View>
      </View>
    );
  }

  if (!exercise) {
    return (
      <View style={[styles.container, styles.center]}>
        <Text style={styles.finishTitle}>No hay ejercicios disponibles</Text>
        <DuoButton label="Volver" onPress={() => router.back()} />
      </View>
    );
  }

  const locked = status !== 'answering';

  return (
    <View style={[styles.container, { paddingTop: insets.top + 8 }]}>
      {/* Cabecera: salir + progreso + corazones */}
      <View style={styles.header}>
        <Pressable onPress={confirmExit} hitSlop={12}>
          <Text style={styles.close}>✕</Text>
        </Pressable>
        <View style={styles.progressBg}>
          <View style={[styles.progressFill, { width: `${Math.max(4, progress * 100)}%` }]} />
        </View>
        <Text style={styles.hearts}>❤️ {isPractice ? '∞' : hearts}</Text>
      </View>

      {lessonMeta && idx === 0 && (
        <Text style={styles.lessonName}>
          {lessonMeta.lesson.icon} {lessonMeta.lesson.title}
        </Text>
      )}
      {combo >= 3 && status === 'answering' && (
        <Text style={styles.combo}>🔥 ¡{combo} seguidas!</Text>
      )}

      <View style={styles.body}>
        <ExerciseView
          key={idx}
          exercise={exercise}
          locked={locked}
          onAnswered={handleAnswered}
        />
      </View>

      {/* Banner de resultado */}
      {(status === 'correct' || status === 'wrong') && (
        <View
          style={[
            styles.banner,
            {
              backgroundColor: status === 'correct' ? colors.greenLight : colors.redLight,
              paddingBottom: insets.bottom + 16,
            },
          ]}
        >
          <Text
            style={[
              styles.bannerTitle,
              { color: status === 'correct' ? colors.greenDark : colors.redDark },
            ]}
          >
            {status === 'correct' ? '¡Muy bien! ✅' : 'Incorrecto ❌'}
          </Text>
          {status === 'wrong' && correctAnswer !== '' && (
            <Text style={styles.bannerAnswer}>Respuesta correcta: {correctAnswer}</Text>
          )}
          <DuoButton
            label="Continuar"
            variant={status === 'correct' ? 'primary' : 'danger'}
            onPress={advance}
          />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  center: { alignItems: 'center', justifyContent: 'center', padding: 24 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  close: { fontSize: 22, color: colors.gray, fontWeight: '700' },
  progressBg: {
    flex: 1,
    height: 14,
    backgroundColor: colors.grayLight,
    borderRadius: 7,
    overflow: 'hidden',
  },
  progressFill: { height: '100%', backgroundColor: colors.green, borderRadius: 7 },
  hearts: { fontSize: 16, fontWeight: '800', color: colors.red },
  lessonName: {
    textAlign: 'center',
    color: colors.textSecondary,
    fontWeight: '700',
    marginBottom: 4,
  },
  combo: { textAlign: 'center', color: colors.orange, fontWeight: '800', marginBottom: 4 },
  body: { flex: 1, padding: 20 },
  banner: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    padding: 20,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    gap: 10,
  },
  bannerTitle: { fontSize: 20, fontWeight: '900' },
  bannerAnswer: { fontSize: 15, color: colors.text, marginBottom: 4 },
  finishTitle: {
    fontSize: 26,
    fontWeight: '900',
    color: colors.text,
    textAlign: 'center',
    marginVertical: 16,
  },
  rewardRow: { flexDirection: 'row', gap: 10, marginTop: 8 },
  rewardCard: {
    borderWidth: 2,
    borderRadius: 16,
    paddingVertical: 12,
    paddingHorizontal: 16,
    alignItems: 'center',
    minWidth: 90,
  },
  rewardLabel: { fontSize: 12, fontWeight: '800', color: colors.textSecondary, marginBottom: 4 },
  rewardValue: { fontSize: 18, fontWeight: '900' },
  practiceNote: { marginTop: 16, fontSize: 15, color: colors.red, fontWeight: '700' },
  noHeartsText: {
    fontSize: 15,
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: 8,
  },
  finishFooter: { width: '100%', marginTop: 'auto' },
});
