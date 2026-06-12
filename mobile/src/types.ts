// ---------- Contenido del curso ----------

export interface VocabItem {
  pt: string;
  es: string;
  emoji?: string;
}

export interface SentenceItem {
  pt: string;
  es: string;
}

export interface LessonData {
  id: string;
  title: string;
  icon: string;
  vocab: VocabItem[];
  sentences: SentenceItem[];
}

export interface Unit {
  id: string;
  title: string;
  description: string;
  lessons: LessonData[];
}

// ---------- Ejercicios ----------

export type Exercise =
  | {
      type: 'select';
      /** Pregunta: «¿Cuál de estas es "la manzana"?» */
      prompt: string;
      options: { text: string; emoji?: string }[];
      correctIndex: number;
      /** Texto pt-BR que se reproduce al elegir la opción correcta */
      speak?: string;
    }
  | {
      type: 'translate';
      direction: 'pt-es' | 'es-pt';
      prompt: string;
      answer: string;
      wordBank: string[];
      speak?: string;
    }
  | {
      type: 'listen';
      sentence: string;
      translation: string;
      wordBank: string[];
    }
  | {
      type: 'match';
      pairs: { pt: string; es: string }[];
    }
  | {
      type: 'fillBlank';
      /** Frase con «___» donde va la palabra */
      sentence: string;
      translation: string;
      options: string[];
      correctIndex: number;
    }
  | {
      type: 'type';
      prompt: string;
      answer: string;
      speak?: string;
    };

// ---------- Gamificación ----------

export interface QuestDef {
  id: string;
  title: (n: number) => string;
  metric: 'xpToday' | 'lessonsToday' | 'perfectToday' | 'practiceToday' | 'bestComboToday';
  target: number;
  rewardGems: number;
  icon: string;
}

export interface AchievementDef {
  id: string;
  title: string;
  description: (n: number) => string;
  metric: 'xpTotal' | 'streakBest' | 'lessonsCompleted' | 'perfectLessons' | 'wordsLearned';
  tiers: number[];
  icon: string;
}
