"""Configuration du pont : un config.json partagé entre l'interface et le service."""
import copy
import json
import os
import secrets
import sys
from pathlib import Path

APP_NAME = 'INTC Bridge'

DEFAULTS = {
    'port': 8080,
    'token': '',
    'printer': {
        'mode': 'bluetooth',   # bluetooth | serial | network | windows
        'mac': '',
        'channel': 1,
        'port': '',            # ex. COM5 (mode serial)
        'baudrate': 9600,
        'host': '',            # mode network
        'net_port': 9100,
        'printer_name': '',    # mode windows
        'timeout': 10,
    },
}


def config_dir():
    if sys.platform == 'win32':
        return Path(os.environ.get('PROGRAMDATA', r'C:\ProgramData')) / APP_NAME
    return Path.home() / '.config' / 'intc-bridge'


def config_path():
    return config_dir() / 'config.json'


def load():
    cfg = copy.deepcopy(DEFAULTS)
    path = config_path()
    if path.exists():
        data = json.loads(path.read_text(encoding='utf-8'))
        cfg['printer'].update(data.pop('printer', {}))
        cfg.update(data)
    if not cfg['token']:
        cfg['token'] = secrets.token_urlsafe(24)
        save(cfg)
    return cfg


def save(cfg):
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(tmp, path)
