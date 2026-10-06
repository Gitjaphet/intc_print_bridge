"""Serveur HTTP du pont : même contrat que l'appli Android (POST /rawprint)."""
import hmac
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .transports import build_transport

log = logging.getLogger('intc_bridge')

# Linux EHOSTDOWN / EHOSTUNREACH, Windows WSAEHOSTDOWN / WSAEHOSTUNREACH
HOST_DOWN = {112, 113, 10064, 10065}


def friendly_error(exc):
    """Traduit une erreur technique en (code HTTP, message lisible par le client)."""
    if isinstance(exc, TimeoutError):
        return 504, "Imprimante injoignable (en veille ?) : réveillez-la et réessayez."
    if getattr(exc, 'winerror', None) in HOST_DOWN or getattr(exc, 'errno', None) in HOST_DOWN:
        return 502, "Imprimante éteinte ou hors de portée."
    return 502, f"Erreur d'impression : {exc}"


class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        log.info(fmt, *args)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Bridge-Token')
        self.send_header('Access-Control-Allow-Private-Network', 'true')

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == '/health':
            return self._json(200, {'status': 'ok', 'app': 'INTC Print Bridge',
                                    'mode': self.server.cfg['printer']['mode']})
        self._json(404, {'status': 'error', 'message': 'Route inconnue'})

    def do_POST(self):
        if self.path != '/rawprint':
            return self._json(404, {'status': 'error', 'message': 'Route inconnue'})
        token = self.headers.get('X-Bridge-Token', '')
        if not hmac.compare_digest(token, self.server.cfg['token']):
            return self._json(401, {'status': 'error', 'message': 'Jeton invalide'})
        data = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        if not data:
            return self._json(400, {'status': 'error', 'message': 'Corps vide'})
        try:
            with self.server.print_lock:
                self.server.transport.send(data)
        except OSError as e:
            code, message = friendly_error(e)
            log.warning('Impression échouée : %s', e)
            return self._json(code, {'status': 'error', 'message': message})
        self._json(200, {'status': 'ok', 'bytes': len(data)})


def make_server(cfg):
    """Crée le serveur (sans le démarrer) : le service appellera serve_forever / shutdown."""
    server = ThreadingHTTPServer(('127.0.0.1', int(cfg['port'])), Handler)
    server.cfg = cfg
    server.transport = build_transport(cfg['printer'])
    server.print_lock = threading.Lock()
    return server
