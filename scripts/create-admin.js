/**
 * Script para crear usuario admin en Firestore
 */

const admin = require('firebase-admin');
const bcrypt = require('bcryptjs');

// Inicializar Firebase Admin
if (!admin.apps.length) {
  admin.initializeApp({
    projectId: 'apololms'
  });
}

const db = admin.firestore();

const adminUser = {
  email: 'admin@idecap.edu.pe',
  name: 'Administrador IDECAP',
  role: ['admin'],
  platform: 'web',
  isDisbaled: false,
  createdAt: admin.firestore.FieldValue.serverTimestamp()
};

const password = 'Idecap.2026';

async function createAdmin() {
  try {
    // Hash password
    const salt = bcrypt.genSaltSync(10);
    const passwordHash = bcrypt.hashSync(password, salt);

    adminUser.passwordHash = passwordHash;

    // Check if user already exists
    const usersRef = db.collection('users');
    const snapshot = await usersRef.where('email', '==', adminUser.email).get();

    if (!snapshot.empty) {
      // Update existing user
      const doc = snapshot.docs[0];
      await doc.ref.update({
        passwordHash: passwordHash,
        role: ['admin']
      });
      console.log(`✅ Usuario admin actualizado: ${doc.id}`);
    } else {
      // Create new user
      const docRef = await usersRef.add(adminUser);
      console.log(`✅ Usuario admin creado: ${docRef.id}`);
    }

    console.log(`   Email: ${adminUser.email}`);
    console.log(`   Password: ${password}`);
    console.log(`   Role: admin`);

  } catch (error) {
    console.error('❌ Error:', error.message);
  }

  process.exit(0);
}

createAdmin();
