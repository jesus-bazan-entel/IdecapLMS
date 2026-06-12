import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Exercise } from '../../types';
import { colors } from '../../theme';
import { hapticTap, speakPt } from '../../lib/feedback';
import { CheckFooter, PromptTitle } from './common';

type SelectEx = Extract<Exercise, { type: 'select' }>;

export default function SelectExercise({
  exercise,
  locked,
  onAnswered,
}: {
  exercise: SelectEx;
  locked: boolean;
  onAnswered: (correct: boolean, correctAnswer: string) => void;
}) {
  const [selected, setSelected] = useState<number | null>(null);

  return (
    <View style={styles.container}>
      <PromptTitle>{exercise.prompt}</PromptTitle>
      <View style={styles.grid}>
        {exercise.options.map((opt, i) => (
          <Pressable
            key={i}
            disabled={locked}
            onPress={() => {
              hapticTap();
              setSelected(i);
              speakPt(opt.text);
            }}
            style={[styles.card, selected === i && styles.cardSelected]}
          >
            {opt.emoji ? <Text style={styles.emoji}>{opt.emoji}</Text> : null}
            <Text style={[styles.cardText, selected === i && { color: colors.blueDark }]}>
              {opt.text}
            </Text>
          </Pressable>
        ))}
      </View>
      {!locked && (
        <CheckFooter
          ready={selected !== null}
          onCheck={() =>
            onAnswered(
              selected === exercise.correctIndex,
              exercise.options[exercise.correctIndex].text
            )
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: 10,
  },
  card: {
    width: '47%',
    aspectRatio: 1,
    borderWidth: 2,
    borderColor: colors.grayLight,
    borderBottomWidth: 4,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 8,
    backgroundColor: '#fff',
  },
  cardSelected: {
    borderColor: colors.blue,
    backgroundColor: colors.blueLight,
  },
  emoji: { fontSize: 44, marginBottom: 8 },
  cardText: { fontSize: 16, fontWeight: '700', color: colors.text, textAlign: 'center' },
});
