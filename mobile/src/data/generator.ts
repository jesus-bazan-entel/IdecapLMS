import { Exercise, LessonData, Unit, VocabItem } from '../types';
import { getLesson } from './course';

// RNG determinista (mulberry32) para que cada repetición de una lección
// produzca una sesión distinta pero reproducible.
function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashString(s: string) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function shuffle<T>(arr: T[], rnd: () => number): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function pick<T>(arr: T[], n: number, rnd: () => number): T[] {
  return shuffle(arr, rnd).slice(0, n);
}

const tokenize = (s: string) =>
  s
    .replace(/[.,!?¡¿;:]/g, '')
    .split(/\s+/)
    .filter(Boolean);

/** Banco de palabras: palabras de la respuesta + distractores del pool */
function buildWordBank(answer: string, pool: string[], rnd: () => number): string[] {
  const words = tokenize(answer);
  const lowerWords = new Set(words.map((w) => w.toLowerCase()));
  const distractors = pick(
    [...new Set(pool.map((w) => w.toLowerCase()))].filter((w) => !lowerWords.has(w)),
    Math.min(4, Math.max(2, 8 - words.length)),
    rnd
  );
  return shuffle([...words, ...distractors], rnd);
}

function makeSelect(
  item: VocabItem,
  unitVocab: VocabItem[],
  rnd: () => number
): Exercise {
  const distractors = pick(
    unitVocab.filter((v) => v.pt !== item.pt),
    3,
    rnd
  );
  const options = shuffle(
    [item, ...distractors].map((v) => ({ text: v.pt, emoji: v.emoji })),
    rnd
  );
  return {
    type: 'select',
    prompt: `¿Cuál de estas es «${item.es}»?`,
    options,
    correctIndex: options.findIndex((o) => o.text === item.pt),
    speak: item.pt,
  };
}

function makeMatch(unitVocab: VocabItem[], rnd: () => number): Exercise {
  const pairs = pick(unitVocab, 5, rnd).map((v) => ({ pt: v.pt, es: v.es }));
  return { type: 'match', pairs };
}

function makeFillBlank(lesson: LessonData, unit: Unit, rnd: () => number): Exercise | null {
  const candidates = lesson.sentences.filter((s) => tokenize(s.pt).length >= 3);
  if (candidates.length === 0) return null;
  const sentence = candidates[Math.floor(rnd() * candidates.length)];
  const words = tokenize(sentence.pt);
  // Evita ocultar la primera palabra para mantener contexto
  const idx = 1 + Math.floor(rnd() * (words.length - 1));
  const hidden = words[idx];
  const pool = [
    ...new Set(
      unit.lessons
        .flatMap((l) => l.sentences.flatMap((s) => tokenize(s.pt)))
        .filter((w) => w.toLowerCase() !== hidden.toLowerCase())
    ),
  ];
  const options = shuffle([hidden, ...pick(pool, 2, rnd)], rnd);
  const blanked = sentence.pt.replace(hidden, '___');
  return {
    type: 'fillBlank',
    sentence: blanked,
    translation: sentence.es,
    options,
    correctIndex: options.indexOf(hidden),
  };
}

/**
 * Genera la sesión de ejercicios de una lección.
 * `attempt` cambia la semilla para que repetir una lección dé otra sesión.
 */
export function generateLessonExercises(lessonId: string, attempt = 0): Exercise[] {
  const found = getLesson(lessonId);
  if (!found) return [];
  const { unit, lesson } = found;
  const rnd = mulberry32(hashString(lessonId) + attempt * 7919);

  const unitVocab = unit.lessons.flatMap((l) => l.vocab);
  const ptPool = unitVocab.map((v) => v.pt).concat(lesson.sentences.flatMap((s) => tokenize(s.pt)));
  const esPool = unitVocab.map((v) => v.es).concat(lesson.sentences.flatMap((s) => tokenize(s.es)));

  const exercises: Exercise[] = [];

  // 1. Introducir vocabulario nuevo (3 selección múltiple)
  for (const item of pick(lesson.vocab, 3, rnd)) {
    exercises.push(makeSelect(item, unitVocab, rnd));
  }

  // 2. Emparejar pares
  exercises.push(makeMatch(lesson.vocab, rnd));

  // 3. Traducciones con banco de palabras (es→pt y pt→es)
  const sentences = shuffle(lesson.sentences, rnd);
  sentences.slice(0, 2).forEach((s) => {
    exercises.push({
      type: 'translate',
      direction: 'es-pt',
      prompt: s.es,
      answer: s.pt,
      wordBank: buildWordBank(s.pt, ptPool, rnd),
    });
  });
  sentences.slice(2, 3).forEach((s) => {
    exercises.push({
      type: 'translate',
      direction: 'pt-es',
      prompt: s.pt,
      answer: s.es,
      wordBank: buildWordBank(s.es, esPool, rnd),
      speak: s.pt,
    });
  });

  // 4. Ejercicio de escucha
  const listenSentence = sentences[sentences.length - 1];
  exercises.push({
    type: 'listen',
    sentence: listenSentence.pt,
    translation: listenSentence.es,
    wordBank: buildWordBank(listenSentence.pt, ptPool, rnd),
  });

  // 5. Completar el espacio
  const fb = makeFillBlank(lesson, unit, rnd);
  if (fb) exercises.push(fb);

  // 6. Escribir la traducción de una palabra del vocabulario
  const typeItem = lesson.vocab[Math.floor(rnd() * lesson.vocab.length)];
  exercises.push({
    type: 'type',
    prompt: typeItem.es,
    answer: typeItem.pt,
    speak: typeItem.pt,
  });

  // Mezcla manteniendo los «select» introductorios al inicio
  const intro = exercises.slice(0, 3);
  const rest = shuffle(exercises.slice(3), rnd);
  return [...intro, ...rest];
}

/** Sesión de práctica a partir de lecciones completadas */
export function generatePracticeExercises(completedLessonIds: string[]): Exercise[] {
  const rnd = mulberry32(Date.now() % 2147483647);
  const ids = pick(completedLessonIds, Math.min(3, completedLessonIds.length), rnd);
  const exercises = ids.flatMap((id) => {
    const all = generateLessonExercises(id, Math.floor(rnd() * 1000));
    return pick(all, 3, rnd);
  });
  return shuffle(exercises, rnd).slice(0, 8);
}

/** Normaliza respuestas para comparar (minúsculas, sin tildes ni puntuación) */
export function normalizeAnswer(s: string): string {
  return s
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[.,!?¡¿;:]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}
