import React, { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import DuoButton from '../src/components/DuoButton';
import { useStore } from '../src/store/useStore';
import { colors } from '../src/theme';

const AVATARS = ['🦜', '🐵', '🦊', '🐸', '🐱', '🦄', '🐼', '🐯'];
const GOALS = [
  { xp: 10, label: 'Relajado', detail: '5 min/día' },
  { xp: 30, label: 'Normal', detail: '10 min/día' },
  { xp: 50, label: 'Serio', detail: '15 min/día' },
  { xp: 80, label: 'Intenso', detail: '20+ min/día' },
];

export default function Onboarding() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const completeOnboarding = useStore((s) => s.completeOnboarding);

  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [avatar, setAvatar] = useState('🦜');
  const [goal, setGoal] = useState(30);

  const finish = () => {
    completeOnboarding(name.trim() || 'Estudiante', avatar, goal);
    router.replace('/(tabs)/learn');
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={[styles.container, { paddingTop: insets.top + 24, paddingBottom: insets.bottom + 16 }]}
    >
      {step === 0 && (
        <View style={styles.body}>
          <Text style={styles.mascot}>🦜</Text>
          <Text style={styles.h1}>¡Bem-vindo a Falaê!</Text>
          <Text style={styles.p}>
            Aprende portugués brasileño con lecciones cortas y divertidas: gana XP, cuida tu racha
            y compite en las ligas. ¡Bora lá!
          </Text>
          <View style={styles.footer}>
            <DuoButton label="Empezar" onPress={() => setStep(1)} />
          </View>
        </View>
      )}

      {step === 1 && (
        <View style={styles.body}>
          <Text style={styles.h1}>Crea tu perfil</Text>
          <Text style={styles.label}>¿Cómo te llamas?</Text>
          <TextInput
            style={styles.input}
            value={name}
            onChangeText={setName}
            placeholder="Tu nombre"
            placeholderTextColor={colors.gray}
            maxLength={20}
          />
          <Text style={styles.label}>Elige tu avatar</Text>
          <View style={styles.avatarGrid}>
            {AVATARS.map((a) => (
              <Pressable
                key={a}
                onPress={() => setAvatar(a)}
                style={[styles.avatarCell, avatar === a && styles.avatarSelected]}
              >
                <Text style={{ fontSize: 34 }}>{a}</Text>
              </Pressable>
            ))}
          </View>
          <View style={styles.footer}>
            <DuoButton label="Continuar" onPress={() => setStep(2)} />
          </View>
        </View>
      )}

      {step === 2 && (
        <View style={styles.body}>
          <Text style={styles.h1}>Elige tu meta diaria</Text>
          <Text style={styles.p}>Podrás cambiarla luego en tu perfil.</Text>
          <View style={{ gap: 10, marginTop: 12 }}>
            {GOALS.map((g) => (
              <Pressable
                key={g.xp}
                onPress={() => setGoal(g.xp)}
                style={[styles.goalRow, goal === g.xp && styles.goalSelected]}
              >
                <Text style={styles.goalLabel}>{g.label}</Text>
                <Text style={styles.goalDetail}>
                  {g.detail} · {g.xp} XP
                </Text>
              </Pressable>
            ))}
          </View>
          <View style={styles.footer}>
            <DuoButton label="¡Empezar a aprender!" onPress={finish} />
          </View>
        </View>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', paddingHorizontal: 24 },
  body: { flex: 1 },
  mascot: { fontSize: 90, textAlign: 'center', marginTop: 40, marginBottom: 16 },
  h1: {
    fontSize: 28,
    fontWeight: '900',
    color: colors.text,
    textAlign: 'center',
    marginBottom: 12,
  },
  p: { fontSize: 16, color: colors.textSecondary, textAlign: 'center', lineHeight: 24 },
  label: { fontSize: 15, fontWeight: '700', color: colors.text, marginTop: 24, marginBottom: 8 },
  input: {
    borderWidth: 2,
    borderColor: colors.grayLight,
    borderRadius: 14,
    backgroundColor: colors.cardBg,
    padding: 14,
    fontSize: 17,
    color: colors.text,
  },
  avatarGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  avatarCell: {
    width: 64,
    height: 64,
    borderRadius: 16,
    borderWidth: 2,
    borderColor: colors.grayLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarSelected: { borderColor: colors.green, backgroundColor: colors.greenLight },
  goalRow: {
    borderWidth: 2,
    borderColor: colors.grayLight,
    borderRadius: 14,
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  goalSelected: { borderColor: colors.green, backgroundColor: colors.greenLight },
  goalLabel: { fontSize: 17, fontWeight: '800', color: colors.text },
  goalDetail: { fontSize: 14, color: colors.textSecondary },
  footer: { marginTop: 'auto', paddingTop: 16 },
});
