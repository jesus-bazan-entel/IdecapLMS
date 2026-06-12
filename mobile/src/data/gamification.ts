import { AchievementDef, QuestDef } from '../types';

// ---------- Misiones diarias ----------

export const QUEST_POOL: QuestDef[] = [
  { id: 'xp30', title: (n) => `Gana ${n} XP`, metric: 'xpToday', target: 30, rewardGems: 10, icon: '⚡' },
  { id: 'xp60', title: (n) => `Gana ${n} XP`, metric: 'xpToday', target: 60, rewardGems: 20, icon: '⚡' },
  { id: 'lessons2', title: (n) => `Completa ${n} lecciones`, metric: 'lessonsToday', target: 2, rewardGems: 15, icon: '📚' },
  { id: 'lessons3', title: (n) => `Completa ${n} lecciones`, metric: 'lessonsToday', target: 3, rewardGems: 25, icon: '📚' },
  { id: 'perfect1', title: () => 'Logra 1 lección perfecta', metric: 'perfectToday', target: 1, rewardGems: 20, icon: '🎯' },
  { id: 'combo5', title: (n) => `Acierta ${n} seguidas en una lección`, metric: 'bestComboToday', target: 5, rewardGems: 10, icon: '🔥' },
  { id: 'combo8', title: (n) => `Acierta ${n} seguidas en una lección`, metric: 'bestComboToday', target: 8, rewardGems: 20, icon: '🔥' },
  { id: 'practice1', title: () => 'Haz 1 sesión de práctica', metric: 'practiceToday', target: 1, rewardGems: 15, icon: '💪' },
];

/** Selección determinista de 3 misiones para un día dado */
export function questsForDay(dateKey: string): QuestDef[] {
  let h = 0;
  for (let i = 0; i < dateKey.length; i++) h = (h * 31 + dateKey.charCodeAt(i)) >>> 0;
  const pool = [...QUEST_POOL];
  const out: QuestDef[] = [];
  const usedMetrics = new Set<string>();
  while (out.length < 3 && pool.length > 0) {
    h = (h * 1103515245 + 12345) >>> 0;
    const idx = h % pool.length;
    const q = pool.splice(idx, 1)[0];
    if (usedMetrics.has(q.metric)) continue;
    usedMetrics.add(q.metric);
    out.push(q);
  }
  return out;
}

// ---------- Logros ----------

export const ACHIEVEMENTS: AchievementDef[] = [
  {
    id: 'wildfire',
    title: 'Incendiario',
    description: (n) => `Alcanza una racha de ${n} días`,
    metric: 'streakBest',
    tiers: [3, 7, 14, 30, 60],
    icon: '🔥',
  },
  {
    id: 'sage',
    title: 'Sabio',
    description: (n) => `Gana ${n} XP en total`,
    metric: 'xpTotal',
    tiers: [100, 500, 1000, 2500, 5000],
    icon: '🦉',
  },
  {
    id: 'scholar',
    title: 'Erudito',
    description: (n) => `Aprende ${n} palabras nuevas`,
    metric: 'wordsLearned',
    tiers: [20, 50, 100, 150, 170],
    icon: '📖',
  },
  {
    id: 'champion',
    title: 'Campeón',
    description: (n) => `Completa ${n} lecciones`,
    metric: 'lessonsCompleted',
    tiers: [5, 10, 20, 40, 80],
    icon: '🏆',
  },
  {
    id: 'sharpshooter',
    title: 'Francotirador',
    description: (n) => `Completa ${n} lecciones sin errores`,
    metric: 'perfectLessons',
    tiers: [1, 5, 10, 25, 50],
    icon: '🎯',
  },
];

// ---------- Ligas ----------

export const LEAGUES = [
  { name: 'Bronce', icon: '🥉', color: '#CD7F32' },
  { name: 'Plata', icon: '🥈', color: '#A8A8A8' },
  { name: 'Oro', icon: '🥇', color: '#FFC800' },
  { name: 'Zafiro', icon: '💠', color: '#1CB0F6' },
  { name: 'Rubí', icon: '♦️', color: '#FF4B4B' },
  { name: 'Esmeralda', icon: '💚', color: '#58CC02' },
  { name: 'Amatista', icon: '🔮', color: '#CE82FF' },
  { name: 'Perla', icon: '🤍', color: '#F0EAE0' },
  { name: 'Obsidiana', icon: '🖤', color: '#3C3C3C' },
  { name: 'Diamante', icon: '💎', color: '#7AD4F0' },
] as const;

interface Bot {
  name: string;
  avatar: string;
  /** XP por hora aproximado */
  rate: number;
}

export const LEAGUE_BOTS: Bot[] = [
  { name: 'Camila S.', avatar: '🦊', rate: 3.1 },
  { name: 'Rafael M.', avatar: '🐻', rate: 2.7 },
  { name: 'Lucía P.', avatar: '🐱', rate: 2.4 },
  { name: 'Thiago R.', avatar: '🐸', rate: 2.0 },
  { name: 'Valentina G.', avatar: '🦋', rate: 1.7 },
  { name: 'Mateo L.', avatar: '🐼', rate: 1.5 },
  { name: 'Isabella F.', avatar: '🦄', rate: 1.2 },
  { name: 'Diego C.', avatar: '🐯', rate: 1.0 },
  { name: 'Sofía A.', avatar: '🐰', rate: 0.8 },
  { name: 'Bruno T.', avatar: '🐨', rate: 0.6 },
  { name: 'Mariana V.', avatar: '🦜', rate: 0.45 },
  { name: 'Gabriel H.', avatar: '🐢', rate: 0.3 },
  { name: 'Julieta N.', avatar: '🐙', rate: 0.2 },
  { name: 'Felipe D.', avatar: '🦥', rate: 0.1 },
];

/** Lunes 00:00 de la semana actual (hora local) */
export function weekStart(now = new Date()): Date {
  const d = new Date(now);
  d.setHours(0, 0, 0, 0);
  const day = d.getDay(); // 0=domingo
  const diff = day === 0 ? 6 : day - 1;
  d.setDate(d.getDate() - diff);
  return d;
}

export function weekKey(now = new Date()): string {
  const start = weekStart(now);
  return `${start.getFullYear()}-${start.getMonth() + 1}-${start.getDate()}`;
}

/** XP determinista de un bot en función del tiempo transcurrido de la semana */
export function botXp(bot: Bot, now = new Date()): number {
  const hours = (now.getTime() - weekStart(now).getTime()) / 3600000;
  // Variación suave por bot para que no sea lineal
  let h = 0;
  const seedStr = bot.name + weekKey(now);
  for (let i = 0; i < seedStr.length; i++) h = (h * 31 + seedStr.charCodeAt(i)) >>> 0;
  const phase = (h % 100) / 100;
  const wobble = 0.75 + 0.5 * Math.abs(Math.sin(hours / 9 + phase * Math.PI * 2));
  return Math.max(0, Math.floor(bot.rate * hours * wobble));
}

export function msUntilWeekEnd(now = new Date()): number {
  const start = weekStart(now);
  const end = new Date(start);
  end.setDate(end.getDate() + 7);
  return end.getTime() - now.getTime();
}
