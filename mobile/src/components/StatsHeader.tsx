import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme';
import { useStore } from '../store/useStore';

/** Barra superior con racha, gemas y corazones (como Duolingo) */
export default function StatsHeader() {
  const streak = useStore((s) => s.streak);
  const gems = useStore((s) => s.gems);
  const hearts = useStore((s) => s.hearts);
  const boostActive = useStore((s) => s.xpBoostUntil > Date.now());

  return (
    <View style={styles.row}>
      <View style={styles.item}>
        <Text style={styles.emoji}>🔥</Text>
        <Text style={[styles.value, { color: streak > 0 ? colors.orange : colors.gray }]}>
          {streak}
        </Text>
      </View>
      {boostActive && (
        <View style={styles.item}>
          <Text style={styles.emoji}>⚡</Text>
          <Text style={[styles.value, { color: colors.gold }]}>x2</Text>
        </View>
      )}
      <View style={styles.item}>
        <Text style={styles.emoji}>💎</Text>
        <Text style={[styles.value, { color: colors.blue }]}>{gems}</Text>
      </View>
      <View style={styles.item}>
        <Text style={styles.emoji}>❤️</Text>
        <Text style={[styles.value, { color: colors.red }]}>{hearts}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 2,
    borderBottomColor: colors.grayLight,
  },
  item: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  emoji: { fontSize: 20 },
  value: { fontSize: 17, fontWeight: '800' },
});
