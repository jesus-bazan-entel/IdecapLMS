import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Exercise } from '../../types';
import { colors } from '../../theme';
import { hapticTap } from '../../lib/feedback';
import { CheckFooter, PromptTitle } from './common';

type FillEx = Extract<Exercise, { type: 'fillBlank' }>;

export default function FillBlankExercise({
  exercise,
  locked,
  onAnswered,
}: {
  exercise: FillEx;
  locked: boolean;
  onAnswered: (correct: boolean, correctAnswer: string) => void;
}) {
  const [selected, setSelected] = useState<number | null>(null);

  const sentenceShown =
    selected === null
      ? exercise.sentence
      : exercise.sentence.replace('___', exercise.options[selected]);

  return (
    <View style={styles.container}>
      <PromptTitle>Completa la frase</PromptTitle>
      <View style={styles.sentenceBox}>
        <Text style={styles.sentence}>{sentenceShown}</Text>
        <Text style={styles.translation}>{exercise.translation}</Text>
      </View>
      <View style={styles.options}>
        {exercise.options.map((opt, i) => (
          <Pressable
            key={i}
            disabled={locked}
            onPress={() => {
              hapticTap();
              setSelected(i);
            }}
            style={[styles.option, selected === i && styles.optionSelected]}
          >
            <Text style={[styles.optionText, selected === i && { color: colors.blueDark }]}>
              {opt}
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
              exercise.options[exercise.correctIndex]
            )
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  sentenceBox: {
    borderWidth: 2,
    borderColor: colors.grayLight,
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
  },
  sentence: { fontSize: 22, fontWeight: '700', color: colors.text, marginBottom: 8 },
  translation: { fontSize: 15, color: colors.textSecondary },
  options: { gap: 10 },
  option: {
    borderWidth: 2,
    borderColor: colors.grayLight,
    borderBottomWidth: 4,
    borderRadius: 14,
    paddingVertical: 14,
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  optionSelected: { borderColor: colors.blue, backgroundColor: colors.blueLight },
  optionText: { fontSize: 17, fontWeight: '700', color: colors.text },
});
