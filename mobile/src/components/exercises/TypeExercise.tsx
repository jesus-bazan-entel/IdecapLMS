import React, { useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import { Exercise } from '../../types';
import { colors } from '../../theme';
import { normalizeAnswer } from '../../data/generator';
import { CheckFooter, PromptTitle } from './common';

type TypeEx = Extract<Exercise, { type: 'type' }>;

export default function TypeExercise({
  exercise,
  locked,
  onAnswered,
}: {
  exercise: TypeEx;
  locked: boolean;
  onAnswered: (correct: boolean, correctAnswer: string) => void;
}) {
  const [text, setText] = useState('');

  return (
    <View style={styles.container}>
      <PromptTitle>Escribe en portugués</PromptTitle>
      <View style={styles.promptBox}>
        <Text style={styles.promptText}>«{exercise.prompt}»</Text>
      </View>
      <TextInput
        style={styles.input}
        value={text}
        onChangeText={setText}
        editable={!locked}
        autoCapitalize="none"
        autoCorrect={false}
        placeholder="Escribe en portugués…"
        placeholderTextColor={colors.gray}
      />
      <Text style={styles.hint}>Las tildes no cuentan como error</Text>
      {!locked && (
        <CheckFooter
          ready={text.trim().length > 0}
          onCheck={() =>
            onAnswered(normalizeAnswer(text) === normalizeAnswer(exercise.answer), exercise.answer)
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  promptBox: {
    borderWidth: 2,
    borderColor: colors.grayLight,
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
  },
  promptText: { fontSize: 20, fontWeight: '700', color: colors.text },
  input: {
    borderWidth: 2,
    borderColor: colors.grayLight,
    borderRadius: 14,
    backgroundColor: colors.cardBg,
    padding: 16,
    fontSize: 18,
    color: colors.text,
  },
  hint: { marginTop: 8, color: colors.gray, fontSize: 13 },
});
