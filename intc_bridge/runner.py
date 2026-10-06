"""Démarre/arrête le serveur dans un thread, avec logs fichier.
Utilisé par le service Windows et par le lanceur Linux."""
import logging
import threading
from logging.handlers import RotatingFileHandler

from . import config
from .server import make_server

log = logging.getLogger('intc_bridge')


def setup_logging():
    if log.handlers:  # déjà configuré
        return
    log_dir = config.config_dir() / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_dir / 'bridge.log', maxBytes=1_000_000,
                                  backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


class BridgeRunner:

    def __init__(self):
        self.server = None
        self.thread = None

    def start(self, cfg=None):
        cfg = cfg or config.load()
        self.server = make_server(cfg)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        log.info('Pont démarré sur 127.0.0.1:%s (mode %s)', cfg['port'], cfg['printer']['mode'])

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            log.info('Pont arrêté')
