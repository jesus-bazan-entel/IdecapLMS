/**
 * Configuración del proyecto Firebase «portulingo-3aac5».
 *
 * Hoy la app es offline-first y no usa el SDK de Firebase; esta configuración
 * queda lista para cuando se agregue autenticación, sincronización del
 * progreso (Firestore) o Analytics:
 *
 *   npx expo install firebase
 *   import { initializeApp } from 'firebase/app';
 *   const app = initializeApp(firebaseConfig);
 *
 * Nota: la apiKey web de Firebase no es un secreto; identifica el proyecto
 * y puede estar en el repositorio. La seguridad la dan las reglas de
 * Firestore/Storage y los dominios autorizados de Auth.
 */
export const firebaseConfig = {
  apiKey: 'AIzaSyCwRJAYXiFLN9pIlLJhPsubrzEt4_F6T-8',
  authDomain: 'portulingo-3aac5.firebaseapp.com',
  projectId: 'portulingo-3aac5',
  storageBucket: 'portulingo-3aac5.firebasestorage.app',
  messagingSenderId: '403027495754',
  appId: '1:403027495754:web:4250570f41955bc17c4fb3',
  measurementId: 'G-MDV0Y27582',
};
