/**
 * HyperFileLens Frontend Static Server
 * 
 * This server serves the built frontend files from the dist/ directory
 * and proxies API requests to the backend server.
 * 
 * Run from: frontend/ directory (parent of dist/)
 * Command: node server.cjs
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 5000;  // Hardcoded to avoid environment variable conflicts
const SERVE_DIR = path.join(__dirname, 'dist');
const API_PROXY_HOST = 'localhost';
const API_PROXY_PORT = 8000;

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.map': 'application/json',
  '.webp': 'image/webp',
  '.ttf': 'font/ttf',
  '.eot': 'application/vnd.ms-fontobject'
};

function serveFile(res, filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';
  
  fs.readFile(filePath, (err, data) => {
    if (err) {
      console.error(`File not found: ${filePath}`);
      res.writeHead(404);
      res.end('Not Found');
    } else {
      res.writeHead(200, { 
        'Content-Type': contentType,
        'Cache-Control': 'no-cache'
      });
      res.end(data);
    }
  });
}

function proxyRequest(req, res) {
  // Log authorization header for debugging
  if (req.headers.authorization) {
    console.log(`[Proxy] Authorization header present: ${req.headers.authorization.substring(0, 20)}...`);
  } else {
    console.log('[Proxy] Warning: No Authorization header');
  }

  const options = {
    hostname: API_PROXY_HOST,
    port: API_PROXY_PORT,
    path: req.url,
    method: req.method,
    headers: {
      ...req.headers,
      host: `${API_PROXY_HOST}:${API_PROXY_PORT}`
    }
  };

  const proxyReq = http.request(options, (proxyRes) => {
    // Copy response headers with CORS
    const headers = {
      ...proxyRes.headers,
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    };
    
    res.writeHead(proxyRes.statusCode, headers);
    proxyRes.pipe(res);
  });

  proxyReq.on('error', (err) => {
    console.error(`Proxy error: ${err.message}`);
    res.writeHead(502, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Backend service unavailable' }));
  });

  req.pipe(proxyReq);
}

const server = http.createServer((req, res) => {
  // Always add CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  // Handle preflight requests
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  console.log(`${req.method} ${req.url}`);

  // Proxy API requests to backend
  if (req.url.startsWith('/api/')) {
    proxyRequest(req, res);
    return;
  }

  // Proxy static files (downloads) to backend
  if (req.url.startsWith('/static/')) {
    proxyRequest(req, res);
    return;
  }

  // Handle static files
  let urlPath = req.url.split('?')[0];
  
  // Remove leading slash
  if (urlPath.startsWith('/')) {
    urlPath = urlPath.substring(1);
  }
  
  // Default to index.html for root
  if (urlPath === '' || urlPath === '/') {
    urlPath = 'index.html';
  }
  
  const filePath = path.join(SERVE_DIR, urlPath);
  
  // Security: prevent directory traversal
  const normalizedPath = path.normalize(filePath);
  if (!normalizedPath.startsWith(SERVE_DIR)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }

  // Check if file exists
  fs.stat(normalizedPath, (err, stats) => {
    if (!err && stats.isFile()) {
      serveFile(res, normalizedPath);
    } else {
      // SPA fallback: serve index.html for client-side routing
      const indexPath = path.join(SERVE_DIR, 'index.html');
      fs.stat(indexPath, (indexErr, indexStats) => {
        if (!indexErr && indexStats.isFile()) {
          serveFile(res, indexPath);
        } else {
          res.writeHead(404, { 'Content-Type': 'text/html' });
          res.end(`
            <html>
              <head><title>HyperFileLens</title></head>
              <body>
                <h1>HyperFileLens</h1>
                <p>Frontend not built. Please run: <code>pnpm run build</code></p>
              </body>
            </html>
          `);
        }
      });
    }
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log('='.repeat(50));
  console.log('HyperFileLens Frontend Server');
  console.log('='.repeat(50));
  console.log(`Server running at: http://localhost:${PORT}`);
  console.log(`Serving files from: ${SERVE_DIR}`);
  console.log(`API proxy target: http://${API_PROXY_HOST}:${API_PROXY_PORT}`);
  console.log('='.repeat(50));
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`Port ${PORT} is already in use`);
    process.exit(1);
  } else {
    console.error('Server error:', err);
  }
});
