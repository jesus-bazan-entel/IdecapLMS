import React, { useMemo, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Exercise } from '../../types';
import { colors } from '../../theme';
import { hapticError, hapticTap, speakPt } from '../../lib/feedback';
import { PromptTitle } from './common';

type MatchEx = Extract<Exercise, { type: 'match' }>;

function shuffleArr<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/** Emparejar pares pt↔es. No quita corazones; errores marcan la sesión como imperfecta. */
export default function MatchExercise({
  exercise,
  locked,
  onAnswered,
}: {
  exercise: MatchEx;
  locked: boolean;
  onAnswered: (correct: boolean, correctAnswer: string) => void;
}) {
  const left = useMemo(() => shuffleArr(exercise.pairs.map((p) => p.pt)), [exercise]);
  const right = useMemo(() => shuffleArr(exercise.pairs.map((p) => p.es)), [exercise]);
  const [selLeft, setSelLeft] = useState<string | null>(null);
  const [selRight, setSelRight] = useState<string | null>(null);
  const [done, setDone] = useState<Set<string>>(new Set());
  const [wrongFlash, setWrongFlash] = useState<string | null>(null);
  const hadErrorRef = useRef(false);

  const tryMatch = (pt: string | null, es: string | null) => {
    if (!pt || !es) return;
    const pair = exercise.pairs.find((p) => p.pt === pt);
    if (pair && pair.es === es) {
      const newDone = new Set(done);
      newDone.add(pt);
      newDone.add(es);
      setDone(newDone);
      setSelLeft(null);
      setSelRight(null);
      if (newDone.size === exercise.pairs.length * 2) {
        setTimeout(() => onAnswered(!hadErrorRef.current, ''), 350);
      }
    } else {
      hadErrorRef.current = true;
      hapticError();
      setWrongFlash(`${pt}|${es}`);
      setTimeout(() => {
        setWrongFlash(null);
        setSelLeft(null);
        setSelRight(null);
      }, 500);
    }
  };

  const renderBtn = (word: string, side: 'left' | 'right') => {
    const selected = side === 'left' ? selLeft === word : selRight === word;
    const isDone = done.has(word);
    const isWrong =
      wrongFlash !== null &&
      ((side === 'left' && wrongFlash.startsWith(word + '|')) ||
        (side === 'right' && wrongFlash.endsWith('|' + word)));
    return (
      <Pressable
        key={word}
        disabled={locked || isDone}
        onPress={() => {
          hapticTap();
          if (side === 'left') {
            speakPt(word);
            setSelLeft(word);
            tryMatch(word, selRight);
          } else {
            setSelRight(word);
            tryMatch(selLeft, word);
          }
        }}
        style={[
          styles.matchBtn,
          selected && styles.matchSelected,
          isDone && styles.matchDone,
          isWrong && styles.matchWrong,
        ]}
      >
        <Text
          style={[
            styles.matchText,
            isDone && { color: colors.gray },
            selected && { color: colors.blueDark },
            isWrong && { color: colors.redDark },
          ]}
        >
          {word}
        </Text>
      </Pressable>
    );
  };

  return (
    <View style={styles.container}>
      <PromptTitle>Une las parejas</PromptTitle>
      <View style={styles.columns}>
        <View style={styles.col}>{left.map((w) => renderBtn(w, 'left'))}</View>
        <View style={styles.col}>{right.map((w) => renderBtn(w, 'right'))}</View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  columns: { flexDirection: 'row', gap: 10 },
  col: { flex: 1, gap: 8 },
  matchBtn: {
    borderWidth: 2,
    borderColor: colors.grayLight,
    borderBottomWidth: 4,
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 8,
    alignItems: 'center',
    backgroundColor: '#fff',
    minHeight: 56,
    justifyContent: 'center',
  },
  matchSelected: { borderColor: colors.blue, backgroundColor: colors.blueLight },
  matchDone: { borderColor: colors.grayLight, backgroundColor: colors.cardBg, opacity: 0.5 },
  matchWrong: { borderColor: colors.red, backgroundColor: colors.redLight },
  matchText: { fontSize: 15, fontWeight: '700', color: colors.text, textAlign: 'center' },
});
