import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { Exercise } from '../types';
import { botXp, LEAGUE_BOTS, LEAGUES, weekKey } from '../data/gamification';

export const MAX_HEARTS = 5;
export const HEART_REGEN_MS = 30 * 60 * 1000;
export const COSTS = { refillHearts: 350, streakFreeze: 200, xpBoost: 150 } as const;
export const MAX_STREAK_FREEZES = 2;

export function todayKey(d = new Date()): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
    d.getDate()
  ).padStart(2, '0')}`;
}

function yesterdayKey(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return todayKey(d);
}

function daysBetween(a: string, b: string): number {
  const [y1, m1, d1] = a.split('-').map(Number);
  const [y2, m2, d2] = b.split('-').map(Number);
  const t1 = new Date(y1, m1 - 1, d1).getTime();
  const t2 = new Date(y2, m2 - 1, d2).getTime();
  return Math.round((t2 - t1) / 86400000);
}

export interface LessonResult {
  lessonId: string;
  perfect: boolean;
  comboBest: number;
  mistakes: Exercise[];
  isPractice: boolean;
}

interface StoreState {
  // Perfil
  onboarded: boolean;
  username: string;
  avatar: string;
  dailyGoalXp: number;
  joinedAt: number;

  // Progreso
  xpTotal: number;
  xpByDay: Record<string, number>;
  completedLessons: Record<string, { times: number; perfect: boolean }>;
  mistakes: Exercise[];
  perfectLessons: number;

  // Economía
  gems: number;
  hearts: number;
  heartsUpdatedAt: number;
  streakFreezes: number;
  xpBoostUntil: number;

  // Racha
  streak: number;
  streakBest: number;
  lastActiveDay: string | null;

  // Liga semanal
  weekKey: string;
  leagueXp: number;
  leagueTier: number;
  lastLeagueResult: { placement: number; promoted: boolean; demoted: boolean } | null;

  // Contadores del día (misiones)
  dayKey: string;
  lessonsToday: number;
  perfectToday: number;
  practiceToday: number;
  bestComboToday: number;
  claimedQuests: string[];
  claimedAchievements: string[];

  // Ajustes
  soundEnabled: boolean;
  hapticsEnabled: boolean;

  // Acciones
  completeOnboarding: (name: string, avatar: string, goal: number) => void;
  tick: () => void;
  loseHeart: () => void;
  buyRefillHearts: () => boolean;
  buyStreakFreeze: () => boolean;
  buyXpBoost: () => boolean;
  completeLesson: (result: LessonResult) => { xpEarned: number; gemsEarned: number };
  clearMistakes: (count: number) => void;
  claimQuest: (id: string, gems: number) => void;
  claimAchievement: (key: string, gems: number) => void;
  setSettings: (s: Partial<{ soundEnabled: boolean; hapticsEnabled: boolean }>) => void;
  setProfile: (p: Partial<{ username: string; avatar: string; dailyGoalXp: number }>) => void;
  resetAll: () => void;
}

const initialState = {
  onboarded: false,
  username: 'Estudiante',
  avatar: '🦜',
  dailyGoalXp: 30,
  joinedAt: Date.now(),
  xpTotal: 0,
  xpByDay: {} as Record<string, number>,
  completedLessons: {} as Record<string, { times: number; perfect: boolean }>,
  mistakes: [] as Exercise[],
  perfectLessons: 0,
  gems: 100,
  hearts: MAX_HEARTS,
  heartsUpdatedAt: Date.now(),
  streakFreezes: 0,
  xpBoostUntil: 0,
  streak: 0,
  streakBest: 0,
  lastActiveDay: null as string | null,
  weekKey: weekKey(),
  leagueXp: 0,
  leagueTier: 0,
  lastLeagueResult: null as StoreState['lastLeagueResult'],
  dayKey: todayKey(),
  lessonsToday: 0,
  perfectToday: 0,
  practiceToday: 0,
  bestComboToday: 0,
  claimedQuests: [] as string[],
  claimedAchievements: [] as string[],
  soundEnabled: true,
  hapticsEnabled: true,
};

export const useStore = create<StoreState>()(
  persist(
    (set, get) => ({
      ...initialState,

      completeOnboarding: (name, avatar, goal) =>
        set({
          onboarded: true,
          username: name || 'Estudiante',
          avatar,
          dailyGoalXp: goal,
          joinedAt: Date.now(),
        }),

      tick: () => {
        const s = get();
        const now = Date.now();
        const today = todayKey();
        const patch: Partial<StoreState> = {};

        // Regeneración de corazones (1 cada 30 min)
        if (s.hearts >= MAX_HEARTS) {
          patch.heartsUpdatedAt = now;
        } else {
          const gained = Math.floor((now - s.heartsUpdatedAt) / HEART_REGEN_MS);
          if (gained > 0) {
            const hearts = Math.min(MAX_HEARTS, s.hearts + gained);
            patch.hearts = hearts;
            patch.heartsUpdatedAt =
              hearts >= MAX_HEARTS ? now : s.heartsUpdatedAt + gained * HEART_REGEN_MS;
          }
        }

        // Racha: días perdidos consumen protectores o reinician
        if (s.lastActiveDay && s.lastActiveDay !== today) {
          const missed = daysBetween(s.lastActiveDay, today) - 1;
          if (missed > 0 && s.streak > 0) {
            if (missed <= s.streakFreezes) {
              patch.streakFreezes = s.streakFreezes - missed;
              patch.lastActiveDay = yesterdayKey();
            } else {
              patch.streak = 0;
              patch.lastActiveDay = null;
            }
          }
        }

        // Cambio de día: reinicia contadores de misiones
        if (s.dayKey !== today) {
          patch.dayKey = today;
          patch.lessonsToday = 0;
          patch.perfectToday = 0;
          patch.practiceToday = 0;
          patch.bestComboToday = 0;
          patch.claimedQuests = [];
        }

        // Cambio de semana: resultado de liga
        const wk = weekKey();
        if (s.weekKey !== wk) {
          const [y, m, d] = s.weekKey.split('-').map(Number);
          const prevWeekEnd = new Date(y, m - 1, d);
          prevWeekEnd.setDate(prevWeekEnd.getDate() + 7);
          prevWeekEnd.setMilliseconds(-1);
          const finalBots = LEAGUE_BOTS.map((b) => botXp(b, prevWeekEnd));
          const placement = finalBots.filter((xp) => xp > s.leagueXp).length + 1;
          const promoted = placement <= 3 && s.leagueTier < LEAGUES.length - 1;
          const demoted = placement > LEAGUE_BOTS.length - 2 && s.leagueTier > 0;
          patch.weekKey = wk;
          patch.leagueXp = 0;
          patch.lastLeagueResult = s.leagueXp > 0 ? { placement, promoted, demoted } : null;
          if (s.leagueXp > 0) {
            if (promoted) {
              patch.leagueTier = s.leagueTier + 1;
              patch.gems = s.gems + 50;
            } else if (demoted) {
              patch.leagueTier = s.leagueTier - 1;
            }
          }
        }

        if (Object.keys(patch).length > 0) set(patch);
      },

      loseHeart: () => {
        const s = get();
        if (s.hearts <= 0) return;
        set({
          hearts: s.hearts - 1,
          heartsUpdatedAt: s.hearts === MAX_HEARTS ? Date.now() : s.heartsUpdatedAt,
        });
      },

      buyRefillHearts: () => {
        const s = get();
        if (s.gems < COSTS.refillHearts || s.hearts >= MAX_HEARTS) return false;
        set({ gems: s.gems - COSTS.refillHearts, hearts: MAX_HEARTS, heartsUpdatedAt: Date.now() });
        return true;
      },

      buyStreakFreeze: () => {
        const s = get();
        if (s.gems < COSTS.streakFreeze || s.streakFreezes >= MAX_STREAK_FREEZES) return false;
        set({ gems: s.gems - COSTS.streakFreeze, streakFreezes: s.streakFreezes + 1 });
        return true;
      },

      buyXpBoost: () => {
        const s = get();
        if (s.gems < COSTS.xpBoost || s.xpBoostUntil > Date.now()) return false;
        set({ gems: s.gems - COSTS.xpBoost, xpBoostUntil: Date.now() + 15 * 60 * 1000 });
        return true;
      },

      completeLesson: (result) => {
        const s = get();
        const today = todayKey();

        // XP: base 10, +5 perfecta, +3 combo de 5+, práctica 10 fijo
        let xp = result.isPractice ? 10 : 10;
        if (!result.isPractice && result.perfect) xp += 5;
        if (!result.isPractice && result.comboBest >= 5) xp += 3;
        const boosted = s.xpBoostUntil > Date.now();
        if (boosted) xp *= 2;

        const firstTime = !result.isPractice && !s.completedLessons[result.lessonId];
        const gemsEarned = result.isPractice ? 0 : firstTime ? 10 : 5;

        // Racha
        let streak = s.streak;
        if (s.lastActiveDay !== today) {
          streak = s.lastActiveDay === yesterdayKey() ? s.streak + 1 : 1;
        }

        const completedLessons = { ...s.completedLessons };
        if (!result.isPractice) {
          const prev = completedLessons[result.lessonId];
          completedLessons[result.lessonId] = {
            times: Math.min(5, (prev?.times ?? 0) + 1),
            perfect: (prev?.perfect ?? false) || result.perfect,
          };
        }

        const mistakes = [...s.mistakes, ...result.mistakes].slice(-30);

        set({
          xpTotal: s.xpTotal + xp,
          xpByDay: { ...s.xpByDay, [today]: (s.xpByDay[today] ?? 0) + xp },
          leagueXp: s.leagueXp + xp,
          gems: s.gems + gemsEarned,
          streak,
          streakBest: Math.max(s.streakBest, streak),
          lastActiveDay: today,
          completedLessons,
          mistakes,
          perfectLessons: s.perfectLessons + (!result.isPractice && result.perfect ? 1 : 0),
          lessonsToday: s.lessonsToday + (result.isPractice ? 0 : 1),
          perfectToday: s.perfectToday + (!result.isPractice && result.perfect ? 1 : 0),
          practiceToday: s.practiceToday + (result.isPractice ? 1 : 0),
          bestComboToday: Math.max(s.bestComboToday, result.comboBest),
          // La práctica recupera un corazón
          hearts: result.isPractice ? Math.min(MAX_HEARTS, s.hearts + 1) : s.hearts,
        });

        return { xpEarned: xp, gemsEarned };
      },

      clearMistakes: (count) => set({ mistakes: get().mistakes.slice(count) }),

      claimQuest: (id, gems) => {
        const s = get();
        if (s.claimedQuests.includes(id)) return;
        set({ claimedQuests: [...s.claimedQuests, id], gems: s.gems + gems });
      },

      claimAchievement: (key, gems) => {
        const s = get();
        if (s.claimedAchievements.includes(key)) return;
        set({ claimedAchievements: [...s.claimedAchievements, key], gems: s.gems + gems });
      },

      setSettings: (p) => set(p),
      setProfile: (p) => set(p),
      resetAll: () => set({ ...initialState, joinedAt: Date.now(), heartsUpdatedAt: Date.now() }),
    }),
    {
      name: 'falae-store-v1',
      storage: createJSONStorage(() => AsyncStorage),
    }
  )
);

/** XP de hoy (selector) */
export const selectXpToday = (s: StoreState) => s.xpByDay[todayKey()] ?? 0;

/** Nivel a partir del XP total */
export function levelFromXp(xp: number): { level: number; into: number; needed: number } {
  let level = 1;
  let threshold = 60;
  let remaining = xp;
  while (remaining >= threshold) {
    remaining -= threshold;
    level += 1;
    threshold = Math.floor(threshold * 1.25);
  }
  return { level, into: remaining, needed: threshold };
}
