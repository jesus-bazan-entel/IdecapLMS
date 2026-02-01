/**
 * Script para restablecer contraseña de usuario en Firebase Auth
 *
 * Uso: node reset-password.js
 *
 * Requiere: firebase-admin y un archivo de service account
 */

const admin = require('firebase-admin');

// Inicializar Firebase Admin (usa credenciales por defecto o service account)
if (!admin.apps.length) {
  admin.initializeApp({
    projectId: 'apololms'
  });
}

const email = 'admin@idecap.edu.pe';
const newPassword = 'Idecap.2026';

async function resetPassword() {
  try {
    // Buscar usuario por email
    const user = await admin.auth().getUserByEmail(email);
    console.log('Usuario encontrado:', user.uid);

    // Actualizar contraseña
    await admin.auth().updateUser(user.uid, {
      password: newPassword
    });

    console.log(`✅ Contraseña actualizada exitosamente para ${email}`);
    console.log(`   Nueva contraseña: ${newPassword}`);
  } catch (error) {
    if (error.code === 'auth/user-not-found') {
      console.log('Usuario no encontrado. Creando nuevo usuario...');

      // Crear usuario si no existe
      const newUser = await admin.auth().createUser({
        email: email,
        password: newPassword,
        emailVerified: true
      });

      console.log(`✅ Usuario creado exitosamente: ${newUser.uid}`);
      console.log(`   Email: ${email}`);
      console.log(`   Contraseña: ${newPassword}`);
    } else {
      console.error('❌ Error:', error.message);
    }
  }

  process.exit(0);
}

resetPassword();
