"""Vista previa de la demo original sin exponer archivos privados del proyecto."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import mimetypes

ROOT = Path(__file__).resolve().parent
ALLOWED = {'style.css', 'js/demo-app.js', 'js/domain.js', 'js/register-form.js', 'js/charts.js', 'js/comparisons.js', 'js/storage.js', 'vendor/chart.umd.js', 'demo.html'}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        name = urlsplit(self.path).path.lstrip('/')
        if name in ['', 'index.html']:
            name = 'demo.html'
        if name not in ALLOWED:
            self.send_error(404)
            return
        payload = (ROOT / name).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mimetypes.guess_type(name)[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(payload)


if __name__ == '__main__':
    print('Demo local original: http://127.0.0.1:8000 (Ctrl+C para detener)')
    ThreadingHTTPServer(('127.0.0.1', 8000), Handler).serve_forever()
