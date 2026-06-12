import * as Haptics from 'expo-haptics';
import * as Speech from 'expo-speech';
import { Platform } from 'react-native';
import { useStore } from '../store/useStore';

/** Pronuncia un texto en portugués brasileño */
export function speakPt(text: string, rate = 1.0) {
  if (!useStore.getState().soundEnabled) return;
  Speech.stop();
  Speech.speak(text, { language: 'pt-BR', rate });
}

export function stopSpeech() {
  Speech.stop();
}

export function hapticSuccess() {
  if (!useStore.getState().hapticsEnabled || Platform.OS === 'web') return;
  Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
}

export function hapticError() {
  if (!useStore.getState().hapticsEnabled || Platform.OS === 'web') return;
  Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
}

export function hapticTap() {
  if (!useStore.getState().hapticsEnabled || Platform.OS === 'web') return;
  Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
}
