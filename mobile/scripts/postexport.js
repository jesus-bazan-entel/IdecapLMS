/* Ajustes post-export para la PWA:
   - copia los archivos de public/ a dist/ si el export no lo hizo
   - inyecta el manifest y las metaetiquetas de instalación en index.html */
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const dist = path.join(root, 'dist');
const pub = path.join(root, 'public');

if (!fs.existsSync(dist)) {
  console.error('No existe dist/. Ejecuta antes: npx expo export --platform web');
  process.exit(1);
}

for (const file of fs.readdirSync(pub)) {
  const target = path.join(dist, file);
  if (!fs.existsSync(target)) {
    fs.copyFileSync(path.join(pub, file), target);
    console.log('copiado', file);
  }
}

const indexPath = path.join(dist, 'index.html');
let html = fs.readFileSync(indexPath, 'utf8');

const tags = [
  '<link rel="manifest" href="/manifest.json"/>',
  '<meta name="theme-color" content="#58CC02"/>',
  '<link rel="apple-touch-icon" href="/apple-touch-icon.png"/>',
  '<meta name="apple-mobile-web-app-capable" content="yes"/>',
  '<meta name="mobile-web-app-capable" content="yes"/>',
  '<meta name="apple-mobile-web-app-status-bar-style" content="default"/>',
  '<meta name="apple-mobile-web-app-title" content="Falaê"/>',
  '<meta name="description" content="Aprende portugués brasileño con lecciones cortas y divertidas"/>',
].filter((t) => !html.includes(t));

if (tags.length > 0) {
  html = html.replace('</head>', `${tags.join('')}</head>`);
  fs.writeFileSync(indexPath, html);
}
console.log('index.html listo para PWA');
