import React from 'react';
import { Pressable, StyleSheet, Text, ViewStyle } from 'react-native';
import { colors } from '../theme';
import { hapticTap } from '../lib/feedback';

interface Props {
  label: string;
  onPress: () => void;
  variant?: 'primary' | 'blue' | 'danger' | 'white' | 'disabled' | 'gold';
  style?: ViewStyle;
  disabled?: boolean;
}

const palette = {
  primary: { bg: colors.green, shadow: colors.greenShadow, text: '#fff' },
  blue: { bg: colors.blue, shadow: colors.blueDark, text: '#fff' },
  danger: { bg: colors.red, shadow: colors.redDark, text: '#fff' },
  gold: { bg: colors.gold, shadow: colors.goldDark, text: '#785000' },
  white: { bg: '#fff', shadow: colors.grayLight, text: colors.blue },
  disabled: { bg: colors.grayLight, shadow: colors.grayLight, text: colors.gray },
};

/** Botón estilo Duolingo con sombra 3D inferior */
export default function DuoButton({ label, onPress, variant = 'primary', style, disabled }: Props) {
  const p = palette[disabled ? 'disabled' : variant];
  return (
    <Pressable
      disabled={disabled}
      onPress={() => {
        hapticTap();
        onPress();
      }}
      style={({ pressed }) => [
        styles.btn,
        {
          backgroundColor: p.bg,
          borderBottomColor: p.shadow,
          borderBottomWidth: pressed || disabled ? 0 : 4,
          marginTop: pressed && !disabled ? 4 : 0,
          borderWidth: variant === 'white' ? 2 : 0,
          borderColor: colors.grayLight,
        },
        style,
      ]}
    >
      <Text style={[styles.label, { color: p.text }]}>{label.toUpperCase()}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  btn: {
    borderRadius: 16,
    paddingVertical: 14,
    paddingHorizontal: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    fontSize: 16,
    fontWeight: '800',
    letterSpacing: 0.8,
  },
});
