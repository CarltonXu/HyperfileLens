const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 5000;
// Get the directory where this script is located
const SCRIPT_DIR = __dirname;
// If running from frontend/, use current directory; if running from frontend/dist/, go up one level
const DIST_DIR = path.basename(SCRIPT_DIR) === 'dist' ? SCRIPT_DIR : path.join(SCRIPT_DIR, 'dist');

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.map': 'application/json'
};

function serveFile(res, filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';
  
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('File not found');
      return;
    }
    res.writeHead(200, { 'Content-Type': contentType });
    res.end(data);
  });
}

const server = http.createServer((req, res) => {
  let filePath = req.url === '/' ? '/index.html' : req.url;
  
  // Remove query string if any
  filePath = filePath.split('?')[0];
  
  // Security: prevent directory traversal
  const safePath = path.normalize(filePath).replace(/^(\.\.[\/\\])+/, '');
  const fullPath = path.join(DIST_DIR, safePath);
  
  // Check if path is within DIST_DIR
  if (!fullPath.startsWith(DIST_DIR)) {
    res.writeHead(403, { 'Content-Type': 'text/plain' });
    res.end('Forbidden');
    return;
  }
  
  // Check if file exists
  fs.stat(fullPath, (err, stats) => {
    if (err || !stats.isFile()) {
      // Serve index.html for SPA routing
      serveFile(res, path.join(DIST_DIR, 'index.html'));
      return;
    }
    serveFile(res, fullPath);
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Static server running at http://localhost:${PORT}`);
  console.log(`Serving files from: ${DIST_DIR}`);
});
