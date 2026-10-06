"""Transports : comment les octets ESC/POS arrivent jusqu'à l'imprimante."""
import socket
import time


class BluetoothTransport:
    """Connexion RFCOMM directe par adresse MAC (Linux et Windows)."""

    def __init__(self, mac, channel=1, timeout=10):
        self.mac = mac
        self.channel = channel
        self.timeout = timeout

    def send(self, data):
        with socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM,
                           socket.BTPROTO_RFCOMM) as s:
            s.settimeout(self.timeout)
            s.connect((self.mac, self.channel))
            s.sendall(data)
            time.sleep(1)  # laisse partir les derniers octets avant de couper


class SerialTransport:
    """Port COM : imprimante Bluetooth appairée (SPP) ou USB-série."""

    def __init__(self, port, baudrate=9600, timeout=10):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

    def send(self, data):
        import serial  # pyserial, importé seulement si ce mode est utilisé
        with serial.Serial(self.port, self.baudrate, timeout=self.timeout,
                           write_timeout=self.timeout) as s:
            s.write(data)
            s.flush()
            time.sleep(1)


def build_transport(cfg):
    """Crée le bon transport à partir de la configuration (dict)."""
    mode = cfg.get('mode', 'bluetooth')
    timeout = float(cfg.get('timeout', 10))
    if mode == 'bluetooth':
        return BluetoothTransport(cfg['mac'], int(cfg.get('channel', 1)), timeout)
    if mode == 'serial':
        return SerialTransport(cfg['port'], int(cfg.get('baudrate', 9600)), timeout)
    raise ValueError(f"Mode d'impression inconnu : {mode}")
