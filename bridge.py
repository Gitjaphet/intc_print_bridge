#!/usr/bin/env python3
"""INTC Print Bridge (PC) : reçoit des octets ESC/POS en HTTP et les envoie en Bluetooth.

Même contrat que l'appli Android INTC Bridge : POST /rawprint, corps = octets bruts.
Connexion Bluetooth RFCOMM ouverte à chaque impression, avec un délai maximum.
"""
import json
import os
import socket
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.environ.get('BRIDGE_PORT', 8080))
PRINTER_MAC = os.environ.get('PRINTER_MAC', 'DC:0D:30:20:FD:90')
PRINTER_CHANNEL = int(os.environ.get('PRINTER_CHANNEL', 6))
TIMEOUT = float(os.environ.get('PRINTER_TIMEOUT', 10))


def envoyer(data):
    """Ouvre une connexion Bluetooth RFCOMM, envoie les octets, puis referme."""
    with socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM) as s:
        s.settimeout(TIMEOUT)
        s.connect((PRINTER_MAC, PRINTER_CHANNEL))
        s.sendall(data)
        time.sleep(1)  # laisse partir les derniers octets avant de couper


class Handler(BaseHTTPRequestHandler):

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
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
            self._json(200, {'status': 'ok', 'app': 'INTC Print Bridge (PC)',
                             'printer': PRINTER_MAC, 'channel': PRINTER_CHANNEL})
        else:
            self._json(404, {'status': 'error', 'message': 'Route inconnue'})

    def do_POST(self):
        if self.path != '/rawprint':
            return self._json(404, {'status': 'error', 'message': 'Route inconnue'})
        data = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        if not data:
            return self._json(400, {'status': 'error', 'message': 'Corps vide'})
        try:
            envoyer(data)
        except TimeoutError:
            return self._json(504, {'status': 'error', 'message':
                'Imprimante injoignable (en veille ?) : réveillez-la et réessayez.'})
        except OSError as e:
            return self._json(502, {'status': 'error', 'message': f'Bluetooth : {e}'})
        self._json(200, {'status': 'ok', 'bytes': len(data)})


if __name__ == '__main__':
    print(f'INTC Print Bridge : http://localhost:{PORT} -> {PRINTER_MAC} canal {PRINTER_CHANNEL}')
    HTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
