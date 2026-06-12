import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Redirect } from 'expo-router';
import { useStore } from '../src/store/useStore';
import { colors } from '../src/theme';

export default function Index() {
  const [hydrated, setHydrated] = useState(useStore.persist.hasHydrated());
  const onboarded = useStore((s) => s.onboarded);

  useEffect(() => {
    const unsub = useStore.persist.onFinishHydration(() => setHydrated(true));
    return unsub;
  }, []);

  if (!hydrated) {
    return (
      <View style={styles.splash}>
        <Text style={styles.logo}>🦜</Text>
        <Text style={styles.title}>Falaê</Text>
      </View>
    );
  }

  return <Redirect href={onboarded ? '/(tabs)/learn' : '/onboarding'} />;
}

const styles = StyleSheet.create({
  splash: {
    flex: 1,
    backgroundColor: colors.green,
    alignItems: 'center',
    justifyContent: 'center',
  },
  logo: { fontSize: 80, marginBottom: 12 },
  title: { fontSize: 40, fontWeight: '900', color: '#fff', letterSpacing: 1 },
});
