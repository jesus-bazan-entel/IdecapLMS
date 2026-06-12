# 🦜 Falaê — Aprende portugués brasileño

Aplicación móvil de aprendizaje de portugués brasileño (pt-BR) para hispanohablantes, estilo Duolingo. Construida con **React Native + Expo (TypeScript)** y **expo-router**.

## Funcionalidades

### Aprendizaje
- **Ruta de aprendizaje** con 5 unidades y 20 lecciones (164 palabras): saludos, presentaciones, familia, comida, números, tiempo y viajes. Las lecciones se desbloquean secuencialmente y al completarlas ganan coronas 👑 (hasta 5 por lección, cada repetición genera una sesión distinta).
- **6 tipos de ejercicios** generados dinámicamente desde el vocabulario y frases de cada lección:
  - Selección múltiple con emojis
  - Traducción español → portugués con banco de palabras
  - Traducción portugués → español con banco de palabras
  - Escucha (TTS en pt-BR con `expo-speech`) y construye la frase
  - Unir parejas pt ↔ es
  - Completar el espacio en blanco
  - Escribir la traducción (las tildes no cuentan como error)
- Los ejercicios fallados se **reintentan al final de la lección** y se guardan para la **práctica personalizada de errores**.

### Gamificación (como Duolingo)
- ❤️ **Corazones**: 5 vidas, pierdes una por error, se regeneran 1 cada 30 min. La práctica recupera un corazón.
- 🔥 **Racha diaria** con **protectores de racha** que se consumen automáticamente.
- ⚡ **XP y meta diaria** configurable (10/30/50/80 XP), con bonus por lección perfecta y combos.
- 💎 **Gemas** como moneda, ganadas con lecciones, misiones y logros.
- 🏆 **Liga semanal** (Bronce → Diamante, 10 ligas) con tabla de posiciones, zona de ascenso/descenso y rivales simulados que avanzan durante la semana.
- 🎯 **Misiones diarias** (3 al día, rotan a medianoche) con recompensas en gemas.
- 🏅 **Logros por niveles** (racha, XP, palabras, lecciones, perfectas).
- 🛍️ **Tienda**: recarga de vidas, protector de racha y potenciador XP x2.
- 📊 **Perfil** con nivel, estadísticas y gráfico de XP de los últimos 7 días.

Todo el progreso se persiste localmente con AsyncStorage (offline-first).

## Ejecutar

```bash
cd mobile
npm install
npx expo start
```

Escanea el código QR con la app **Expo Go** (Android/iOS), o pulsa `a`/`i` para abrir en emulador, o `w` para la versión web.

## Estructura

```
mobile/
├── app/                    # Pantallas (expo-router)
│   ├── _layout.tsx         # Stack raíz + tick periódico (corazones, racha, liga)
│   ├── index.tsx           # Splash + redirección
│   ├── onboarding.tsx      # Bienvenida, perfil y meta diaria
│   ├── (tabs)/             # Pestañas: aprender, liga, misiones, tienda, perfil
│   └── lesson/[id].tsx     # Reproductor de lecciones (id = lección o "practice")
└── src/
    ├── data/course.ts      # Contenido del curso (unidades/lecciones/vocabulario)
    ├── data/generator.ts   # Generador determinista de ejercicios
    ├── data/gamification.ts# Misiones, logros, ligas y bots
    ├── store/useStore.ts   # Estado global persistido (zustand)
    ├── lib/feedback.ts     # TTS pt-BR y háptica
    └── components/         # UI compartida y ejercicios
```

## Añadir contenido

Edita `src/data/course.ts`: añade unidades/lecciones con `vocab` (pares pt/es + emoji) y `sentences` (frases pt/es). El generador crea automáticamente todos los tipos de ejercicios a partir de esos datos.

## Próximos pasos sugeridos

- Sincronizar progreso con el backend FastAPI del repositorio (endpoints de student portal).
- Ejercicios de habla con reconocimiento de voz.
- Notificaciones push de recordatorio de racha (`expo-notifications`).
- Historias interactivas y más unidades.
