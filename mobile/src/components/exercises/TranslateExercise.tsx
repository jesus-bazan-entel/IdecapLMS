import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Exercise } from '../../types';
import { colors } from '../../theme';
import { normalizeAnswer } from '../../data/generator';
import { speakPt } from '../../lib/feedback';
import { CheckFooter, PromptTitle, SpeakerButton, WordChip } from './common';

type TranslateEx = Extract<Exercise, { type: 'translate' }>;
type ListenEx = Extract<Exercise, { type: 'listen' }>;

/** Traducción / escucha con banco de palabras */
export default function TranslateExercise({
  exercise,
  locked,
  onAnswered,
}: {
  exercise: TranslateEx | ListenEx;
  locked: boolean;
  onAnswered: (correct: boolean, correctAnswer: string) => void;
}) {
  const isListen = exercise.type === 'listen';
  const answer = isListen ? exercise.sentence : exercise.answer;
  const bank = exercise.wordBank;
  const [chosen, setChosen] = useState<number[]>([]);

  // En ejercicios de escucha reproduce el audio al entrar
  useEffect(() => {
    if (isListen) {
      const t = setTimeout(() => speakPt(answer), 400);
      return () => clearTimeout(t);
    }
  }, []);

  const title = isListen
    ? 'Escribe lo que escuchas'
    : exercise.direction === 'es-pt'
      ? 'Escribe esto en portugués'
      : 'Escribe esto en español';

  const speakText = isListen
    ? exercise.sentence
    : exercise.type === 'translate' && exercise.speak
      ? exercise.speak
      : null;

  return (
    <View style={styles.container}>
      <PromptTitle>{title}</PromptTitle>

      <View style={styles.promptRow}>
        {speakText ? <SpeakerButton text={speakText} big={isListen} /> : null}
        {!isListen && <Text style={styles.promptText}>{exercise.prompt}</Text>}
      </View>

      {/* Zona de respuesta */}
      <View style={styles.answerZone}>
        {chosen.length === 0 && <View style={styles.answerLine} />}
        <View style={styles.chipsRow}>
          {chosen.map((bankIdx, i) => (
            <WordChip
              key={`${bankIdx}-${i}`}
              word={bank[bankIdx]}
              disabled={locked}
              onPress={() => setChosen(chosen.filter((_, j) => j !== i))}
            />
          ))}
        </View>
      </View>

      {/* Banco de palabras */}
      <View style={styles.chipsRow}>
        {bank.map((word, i) =>
          chosen.includes(i) ? (
            <WordChip key={i} word={word} ghost />
          ) : (
            <WordChip
              key={i}
              word={word}
              disabled={locked}
              onPress={() => setChosen([...chosen, i])}
            />
          )
        )}
      </View>

      {!locked && (
        <CheckFooter
          ready={chosen.length > 0}
          onCheck={() => {
            const user = chosen.map((i) => bank[i]).join(' ');
            onAnswered(normalizeAnswer(user) === normalizeAnswer(answer), answer);
          }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  promptRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 20,
    justifyContent: 'flex-start',
  },
  promptText: { fontSize: 19, color: colors.text, fontWeight: '600', flexShrink: 1 },
  answerZone: {
    minHeight: 56,
    borderBottomWidth: 2,
    borderTopWidth: 2,
    borderColor: colors.grayLight,
    justifyContent: 'center',
    marginBottom: 24,
    paddingVertical: 6,
  },
  answerLine: { height: 2 },
  chipsRow: { flexDirection: 'row', flexWrap: 'wrap' },
});
