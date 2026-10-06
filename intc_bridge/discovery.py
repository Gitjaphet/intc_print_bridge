"""Découverte des imprimantes disponibles sur ce PC, pour remplir les listes de l'interface.
Chaque fonction renvoie une liste vide plutôt que de planter si rien n'est disponible."""
import subprocess
import sys


def list_bluetooth_devices():
    """Appareils Bluetooth appairés : [{'mac': 'DC:0D:...', 'name': '...'}]."""
    if sys.platform == 'win32':
        return _bt_windows()
    return _bt_linux()


def _bt_windows():
    import winreg
    devices = []
    path = r'SYSTEM\CurrentControlSet\Services\BTHPORT\Parameters\Devices'
    try:
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
    except OSError:
        return devices  # pas de Bluetooth sur ce PC
    with root:
        i = 0
        while True:
            try:
                key_name = winreg.EnumKey(root, i)
            except OSError:
                break
            i += 1
            mac = ':'.join(key_name[j:j + 2] for j in range(0, 12, 2)).upper()
            try:
                with winreg.OpenKey(root, key_name) as key:
                    raw, _ = winreg.QueryValueEx(key, 'Name')
                name = bytes(raw).split(b'\x00')[0].decode('utf-8', 'replace')
            except OSError:
                name = 'Appareil inconnu'
            devices.append({'mac': mac, 'name': name})
    return devices


def _bt_linux():
    try:
        out = subprocess.run(['bluetoothctl', 'devices', 'Paired'],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    devices = []
    for line in out.splitlines():
        parts = line.split(' ', 2)  # "Device DC:0D:30:20:FD:90 Nom"
        if len(parts) == 3 and parts[0] == 'Device':
            devices.append({'mac': parts[1], 'name': parts[2]})
    return devices


def list_serial_ports():
    """Ports COM : [{'port': 'COM5', 'description': '...', 'bluetooth': True}]."""
    try:
        from serial.tools import list_ports
    except ImportError:
        return []
    return [{'port': p.device, 'description': p.description,
             'bluetooth': 'BTHENUM' in (p.hwid or '').upper()
                          or 'bluetooth' in (p.description or '').lower()}
            for p in list_ports.comports()]


def list_windows_printers():
    """Imprimantes installées dans Windows : ['XP-58', ...]."""
    try:
        import win32print
    except ImportError:
        return []
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    return [p['pPrinterName'] for p in win32print.EnumPrinters(flags, None, 4)]
