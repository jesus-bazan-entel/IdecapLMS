import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors } from '../../theme';
import { speakPt } from '../../lib/feedback';
import DuoButton from '../DuoButton';

export function PromptTitle({ children }: { children: string }) {
  return <Text style={styles.title}>{children}</Text>;
}

export function SpeakerButton({ text, big }: { text: string; big?: boolean }) {
  return (
    <Pressable
      onPress={() => speakPt(text)}
      style={[styles.speaker, big && styles.speakerBig]}
      accessibilityLabel="Escuchar"
    >
      <Text style={{ fontSize: big ? 40 : 22 }}>🔊</Text>
    </Pressable>
  );
}

export function CheckFooter({
  ready,
  onCheck,
  label = 'Comprobar',
}: {
  ready: boolean;
  onCheck: () => void;
  label?: string;
}) {
  return (
    <View style={styles.footer}>
      <DuoButton label={label} onPress={onCheck} disabled={!ready} />
    </View>
  );
}

/** Chip de palabra del banco */
export function WordChip({
  word,
  onPress,
  ghost,
  disabled,
}: {
  word: string;
  onPress?: () => void;
  ghost?: boolean;
  disabled?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || ghost}
      style={({ pressed }) => [
        styles.chip,
        ghost && styles.chipGhost,
        pressed && { transform: [{ translateY: 2 }], borderBottomWidth: 2 },
      ]}
    >
      <Text style={[styles.chipText, ghost && { color: 'transparent' }]}>{word}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  title: {
    fontSize: 22,
    fontWeight: '800',
    color: colors.text,
    marginBottom: 16,
  },
  speaker: {
    backgroundColor: colors.blue,
    borderRadius: 14,
    padding: 10,
    borderBottomWidth: 4,
    borderBottomColor: colors.blueDark,
  },
  speakerBig: { padding: 22, borderRadius: 20 },
  footer: { marginTop: 'auto', paddingTop: 12 },
  chip: {
    backgroundColor: '#fff',
    borderWidth: 2,
    borderColor: colors.grayLight,
    borderBottomWidth: 4,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
    margin: 4,
  },
  chipGhost: { backgroundColor: colors.grayLight, borderColor: colors.grayLight },
  chipText: { fontSize: 17, fontWeight: '600', color: colors.text },
});
