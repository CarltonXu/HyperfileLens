const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 5000;

// Get the directory where this script is located
const SCRIPT_DIR = __dirname;
// The dist folder is where this script is located
const SERVE_DIR = SCRIPT_DIR;

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
      res.end('File not found: ' + filePath);
      return;
    }
    res.writeHead(200, { 'Content-Type': contentType });
    res.end(data);
  });
}

const server = http.createServer((req, res) => {
  // Log request
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
  
  let urlPath = req.url === '/' ? '/index.html' : req.url;
  
  // Remove query string if any
  urlPath = urlPath.split('?')[0];
  
  // Security: prevent directory traversal
  const safePath = path.normalize(urlPath).replace(/^(\.\.[\/\\])+/, '');
  const fullPath = path.join(SERVE_DIR, safePath);
  
  // Check if path is within SERVE_DIR
  if (!fullPath.startsWith(SERVE_DIR)) {
    res.writeHead(403, { 'Content-Type': 'text/plain' });
    res.end('Forbidden');
    return;
  }
  
  // Check if file exists
  fs.stat(fullPath, (err, stats) => {
    if (err || !stats.isFile()) {
      // Serve index.html for SPA routing
      const indexPath = path.join(SERVE_DIR, 'index.html');
      console.log(`  -> 404, serving index.html from: ${indexPath}`);
      serveFile(res, indexPath);
      return;
    }
    console.log(`  -> 200 OK: ${fullPath}`);
    serveFile(res, fullPath);
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log('='.repeat(60));
  console.log(`Static server running at http://localhost:${PORT}`);
  console.log(`Serving files from: ${SERVE_DIR}`);
  console.log('='.repeat(60));
});
