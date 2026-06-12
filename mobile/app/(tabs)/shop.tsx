import React, { useEffect, useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import DuoButton from '../../src/components/DuoButton';
import StatsHeader from '../../src/components/StatsHeader';
import {
  COSTS,
  MAX_HEARTS,
  MAX_STREAK_FREEZES,
  useStore,
} from '../../src/store/useStore';
import { colors } from '../../src/theme';

export default function ShopScreen() {
  const insets = useSafeAreaInsets();
  const gems = useStore((s) => s.gems);
  const hearts = useStore((s) => s.hearts);
  const streakFreezes = useStore((s) => s.streakFreezes);
  const xpBoostUntil = useStore((s) => s.xpBoostUntil);
  const buyRefillHearts = useStore((s) => s.buyRefillHearts);
  const buyStreakFreeze = useStore((s) => s.buyStreakFreeze);
  const buyXpBoost = useStore((s) => s.buyXpBoost);

  const [, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 10000);
    return () => clearInterval(t);
  }, []);

  const boostActive = xpBoostUntil > Date.now();
  const boostMin = Math.max(0, Math.ceil((xpBoostUntil - Date.now()) / 60000));

  const buy = (fn: () => boolean, successMsg: string) => {
    if (fn()) {
      Alert.alert('¡Compra realizada!', successMsg);
    } else {
      Alert.alert('No se pudo comprar', 'No tienes suficientes gemas o ya tienes el máximo.');
    }
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <StatsHeader />
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>Tienda</Text>
        <View style={styles.balance}>
          <Text style={styles.balanceText}>Tu saldo: 💎 {gems}</Text>
        </View>

        <View style={styles.card}>
          <Text style={styles.itemIcon}>❤️</Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.itemTitle}>Recarga de vidas</Text>
            <Text style={styles.itemDesc}>
              Rellena tus corazones al máximo ({hearts}/{MAX_HEARTS} ahora). También se recargan 1
              cada 30 minutos.
            </Text>
          </View>
          <DuoButton
            label={`💎 ${COSTS.refillHearts}`}
            variant="danger"
            style={styles.buyBtn}
            disabled={hearts >= MAX_HEARTS || gems < COSTS.refillHearts}
            onPress={() => buy(buyRefillHearts, 'Corazones al máximo ❤️❤️❤️❤️❤️')}
          />
        </View>

        <View style={styles.card}>
          <Text style={styles.itemIcon}>🧊</Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.itemTitle}>Protector de racha</Text>
            <Text style={styles.itemDesc}>
              Protege tu racha un día si no practicas (tienes {streakFreezes}/
              {MAX_STREAK_FREEZES}).
            </Text>
          </View>
          <DuoButton
            label={`💎 ${COSTS.streakFreeze}`}
            variant="blue"
            style={styles.buyBtn}
            disabled={streakFreezes >= MAX_STREAK_FREEZES || gems < COSTS.streakFreeze}
            onPress={() => buy(buyStreakFreeze, 'Tu racha está protegida 🧊')}
          />
        </View>

        <View style={styles.card}>
          <Text style={styles.itemIcon}>⚡</Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.itemTitle}>Potenciador de XP</Text>
            <Text style={styles.itemDesc}>
              {boostActive
                ? `¡Activo! XP x2 durante ${boostMin} min más.`
                : 'Gana el doble de XP durante 15 minutos.'}
            </Text>
          </View>
          <DuoButton
            label={`💎 ${COSTS.xpBoost}`}
            variant="gold"
            style={styles.buyBtn}
            disabled={boostActive || gems < COSTS.xpBoost}
            onPress={() => buy(buyXpBoost, '¡XP x2 durante 15 minutos! ⚡')}
          />
        </View>

        <Text style={styles.hint}>
          Gana gemas completando lecciones, misiones diarias y logros.
        </Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  scroll: { padding: 16, paddingBottom: 40 },
  title: { fontSize: 24, fontWeight: '900', color: colors.text, marginTop: 8, marginBottom: 8 },
  balance: {
    backgroundColor: colors.blueLight,
    borderRadius: 14,
    padding: 12,
    marginBottom: 16,
  },
  balanceText: { fontWeight: '800', fontSize: 16, color: colors.blueDark },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    borderWidth: 2,
    borderColor: colors.grayLight,
    borderRadius: 16,
    padding: 14,
    marginBottom: 12,
  },
  itemIcon: { fontSize: 36 },
  itemTitle: { fontSize: 16, fontWeight: '800', color: colors.text, marginBottom: 4 },
  itemDesc: { fontSize: 13, color: colors.textSecondary, lineHeight: 18 },
  buyBtn: { paddingVertical: 10, paddingHorizontal: 12, borderRadius: 12 },
  hint: { textAlign: 'center', color: colors.gray, marginTop: 12, fontSize: 13 },
});
