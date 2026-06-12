import React from 'react';
import { Exercise } from '../../types';
import SelectExercise from './SelectExercise';
import TranslateExercise from './TranslateExercise';
import MatchExercise from './MatchExercise';
import FillBlankExercise from './FillBlankExercise';
import TypeExercise from './TypeExercise';

export default function ExerciseView({
  exercise,
  locked,
  onAnswered,
}: {
  exercise: Exercise;
  locked: boolean;
  onAnswered: (correct: boolean, correctAnswer: string) => void;
}) {
  switch (exercise.type) {
    case 'select':
      return <SelectExercise exercise={exercise} locked={locked} onAnswered={onAnswered} />;
    case 'translate':
    case 'listen':
      return <TranslateExercise exercise={exercise} locked={locked} onAnswered={onAnswered} />;
    case 'match':
      return <MatchExercise exercise={exercise} locked={locked} onAnswered={onAnswered} />;
    case 'fillBlank':
      return <FillBlankExercise exercise={exercise} locked={locked} onAnswered={onAnswered} />;
    case 'type':
      return <TypeExercise exercise={exercise} locked={locked} onAnswered={onAnswered} />;
  }
}
