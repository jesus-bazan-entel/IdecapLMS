import React, { useEffect } from 'react';
import { AppState, Platform } from 'react-native';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useStore } from '../src/store/useStore';

export default function RootLayout() {
  const tick = useStore((s) => s.tick);

  // PWA: service worker para que la web funcione offline y sea instalable
  useEffect(() => {
    if (Platform.OS === 'web' && typeof navigator !== 'undefined' && 'serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {});
    }
  }, []);

  // Recalcula corazones, racha, día y semana al abrir y al volver a la app
  useEffect(() => {
    tick();
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') tick();
    });
    const interval = setInterval(tick, 60 * 1000);
    return () => {
      sub.remove();
      clearInterval(interval);
    };
  }, [tick]);

  return (
    <>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="onboarding" />
        <Stack.Screen name="(tabs)" />
        <Stack.Screen
          name="lesson/[id]"
          options={{ presentation: 'fullScreenModal', gestureEnabled: false }}
        />
      </Stack>
    </>
  );
}
