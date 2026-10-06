"""Transports : comment les octets ESC/POS arrivent jusqu'à l'imprimante."""
import socket
import sys
import time

# Linux EHOSTDOWN / EHOSTUNREACH, Windows WSAEHOSTDOWN / WSAEHOSTUNREACH
HOST_DOWN = {112, 113, 10064, 10065}
# Refus ou coupure (Linux ECONNREFUSED/ECONNRESET, Windows WSAECONNREFUSED/WSAECONNRESET) : appareil allumé, mauvais canal
REFUSED = {111, 104, 10061, 10054}


def _bt_socket():
    return socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)


def _connect_bt(mac, channel, timeout):
    """Ouvre une connexion RFCOMM et renvoie le socket connecté."""
    s = _bt_socket()
    try:
        if sys.platform == 'win32':
            # Sous Windows, un connect() Bluetooth avec délai (mode non bloquant)
            # peut se dire réussi sans l'être : on se connecte en mode bloquant.
            s.connect((mac, channel))
        else:
            s.settimeout(timeout)
            s.connect((mac, channel))
        s.settimeout(timeout)  # délai pour l'envoi, une fois connecté
        return s
    except BaseException:
        s.close()
        raise


class BluetoothTransport:
    """Connexion RFCOMM directe par adresse MAC (Linux et Windows)."""

    def __init__(self, mac, channel=1, timeout=10):
        self.mac = mac
        self.channel = channel
        self.timeout = timeout

    def send(self, data):
        with _connect_bt(self.mac, self.channel, self.timeout) as s:
            s.sendall(data)
            time.sleep(1)  # laisse partir les derniers octets avant de couper


class SerialTransport:
    """Port COM : imprimante Bluetooth appairée (SPP) ou USB-série."""

    def __init__(self, port, baudrate=9600, timeout=10):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

    def send(self, data):
        import serial  # pyserial
        with serial.Serial(self.port, self.baudrate, timeout=self.timeout,
                           write_timeout=self.timeout) as s:
            s.write(data)
            s.flush()
            time.sleep(1)


class NetworkTransport:
    """Imprimante Ethernet / Wi-Fi sur le port RAW (9100 par défaut)."""

    def __init__(self, host, port=9100, timeout=10):
        self.host = host
        self.port = port
        self.timeout = timeout

    def send(self, data):
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as s:
            s.sendall(data)


class WindowsPrinterTransport:
    """Imprimante installée dans Windows (USB, partagée) : envoi RAW au spouleur."""

    def __init__(self, name):
        self.name = name

    def send(self, data):
        import win32print  # pywin32, Windows uniquement
        handle = win32print.OpenPrinter(self.name)
        try:
            win32print.StartDocPrinter(handle, 1, ('INTC Bridge', None, 'RAW'))
            try:
                win32print.StartPagePrinter(handle)
                win32print.WritePrinter(handle, data)
                win32print.EndPagePrinter(handle)
            finally:
                win32print.EndDocPrinter(handle)
        finally:
            win32print.ClosePrinter(handle)


def detect_bluetooth_channel(mac, channels=None, timeout=4, on_try=None, max_timeouts=3):
    """Essaie les canaux RFCOMM et renvoie le premier qui accepte la connexion.
    Abandonne si l'imprimante ne répond plus (éteinte, hors de portée)."""
    channels = channels or [1, 6, 2, 3, 4, 5] + list(range(7, 31))
    timeouts = 0
    for channel in channels:
        if on_try:
            on_try(channel)
        try:
            with _connect_bt(mac, channel, timeout):
                return channel
        except TimeoutError:
            timeouts += 1
            if timeouts >= max_timeouts:
                raise
        except OSError as e:
            code = getattr(e, 'winerror', None) or e.errno
            if code not in REFUSED:
                raise
            timeouts = 0
        time.sleep(0.5)  # laisse la pile Bluetooth respirer entre deux essais
    return None


def build_transport(cfg):
    """Crée le bon transport à partir de la configuration de l'imprimante (dict)."""
    mode = cfg.get('mode', 'bluetooth')
    timeout = float(cfg.get('timeout', 10))
    if mode == 'bluetooth':
        return BluetoothTransport(cfg['mac'], int(cfg.get('channel', 1)), timeout)
    if mode == 'serial':
        return SerialTransport(cfg['port'], int(cfg.get('baudrate', 9600)), timeout)
    if mode == 'network':
        return NetworkTransport(cfg['host'], int(cfg.get('net_port', 9100)), timeout)
    if mode == 'windows':
        return WindowsPrinterTransport(cfg['printer_name'])
    raise ValueError(f"Mode d'impression inconnu : {mode}")
