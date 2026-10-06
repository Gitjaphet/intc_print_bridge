"""Interface de configuration d'INTC Print Bridge."""
import sys

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (QApplication, QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QSpinBox, QStackedWidget,
                               QVBoxLayout, QWidget)

from intc_bridge import config, discovery
from intc_bridge.server import friendly_error
from intc_bridge.transports import build_transport, detect_bluetooth_channel

MODES = [('bluetooth', 'Bluetooth'), ('serial', 'Port COM'),
         ('network', 'Réseau (IP)'), ('windows', 'Imprimante Windows')]
REQUIRED = {'bluetooth': ('mac', "Choisissez un appareil Bluetooth."),
            'serial': ('port', "Choisissez un port COM."),
            'network': ('host', "Saisissez l'adresse IP de l'imprimante."),
            'windows': ('printer_name', "Choisissez une imprimante Windows.")}
# ESC @ (init), centré, texte, avance papier, coupe
TEST_TICKET = b'\x1b@\x1ba\x01INTC Print Bridge\nTest d\'impression OK\n\n\n\n\x1dVB\x00'


class _Signals(QObject):
    done = Signal(object, object)


class _Task(QRunnable):
    """Exécute fn() hors de l'interface, puis rappelle callback(résultat, erreur)."""

    def __init__(self, fn, callback):
        super().__init__()
        self.fn = fn
        self.signals = _Signals()
        self.signals.done.connect(callback)

    def run(self):
        try:
            result, error = self.fn(), None
        except Exception as e:
            result, error = None, e
        self.signals.done.emit(result, error)


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('INTC Print Bridge')
        self.setMinimumWidth(520)
        self.cfg = config.load()
        self._tasks = set()

        self.mode = QComboBox()
        for key, label in MODES:
            self.mode.addItem(label, key)
        self.pages = QStackedWidget()
        for page in (self._page_bluetooth(), self._page_serial(),
                     self._page_network(), self._page_windows()):
            self.pages.addWidget(page)
        self.mode.currentIndexChanged.connect(self.pages.setCurrentIndex)

        self.btn_test = QPushButton("Imprimer un ticket de test")
        self.btn_test.clicked.connect(self.test_print)
        self.status = QLabel()
        self.status.setWordWrap(True)

        box = QGroupBox('Imprimante')
        col = QVBoxLayout(box)
        for w in (self.mode, self.pages, self.btn_test, self.status):
            col.addWidget(w)
        QVBoxLayout(self).addWidget(box)

        self.refresh_lists()
        self._load_form()

    # ---------- pages par mode ----------
    def _page_bluetooth(self):
        page, form = QWidget(), None
        form = QFormLayout(page)
        self.bt_device = QComboBox()
        refresh = QPushButton('Actualiser')
        refresh.clicked.connect(self.refresh_lists)
        row = QHBoxLayout()
        row.addWidget(self.bt_device, 1)
        row.addWidget(refresh)
        form.addRow('Appareil appairé', row)
        self.bt_channel = QSpinBox()
        self.bt_channel.setRange(1, 30)
        self.btn_detect = QPushButton('Détecter')
        self.btn_detect.clicked.connect(self.detect_channel)
        row2 = QHBoxLayout()
        row2.addWidget(self.bt_channel)
        row2.addWidget(self.btn_detect)
        row2.addStretch()
        form.addRow('Canal', row2)
        return page

    def _page_serial(self):
        page = QWidget()
        form = QFormLayout(page)
        self.com_port = QComboBox()
        self.com_baud = QComboBox()
        self.com_baud.setEditable(True)
        self.com_baud.addItems(['9600', '19200', '38400', '57600', '115200'])
        form.addRow('Port', self.com_port)
        form.addRow('Vitesse (bauds)', self.com_baud)
        return page

    def _page_network(self):
        page = QWidget()
        form = QFormLayout(page)
        self.net_host = QLineEdit()
        self.net_host.setPlaceholderText('ex. 192.168.1.50')
        self.net_port = QSpinBox()
        self.net_port.setRange(1, 65535)
        form.addRow('Adresse IP', self.net_host)
        form.addRow('Port', self.net_port)
        return page

    def _page_windows(self):
        page = QWidget()
        form = QFormLayout(page)
        self.win_printer = QComboBox()
        form.addRow('Imprimante', self.win_printer)
        note = QLabel("Pour une imprimante partagée (\\\\PC\\Imprimante), "
                      "préférez le mode Réseau (IP).")
        note.setWordWrap(True)
        form.addRow(note)
        return page

    # ---------- formulaire <-> config ----------
    @staticmethod
    def _select(combo, value):
        idx = combo.findData(value)
        if idx < 0 and value:
            combo.addItem(f'{value} (introuvable)', value)
            idx = combo.count() - 1
        combo.setCurrentIndex(idx)

    def refresh_lists(self):
        keep = (self.bt_device.currentData(), self.com_port.currentData(),
                self.win_printer.currentData())
        self.bt_device.clear()
        for d in discovery.list_bluetooth_devices():
            self.bt_device.addItem(f"{d['name']}  ({d['mac']})", d['mac'])
        self.com_port.clear()
        for p in discovery.list_serial_ports():
            tag = '  [Bluetooth]' if p['bluetooth'] else ''
            self.com_port.addItem(f"{p['port']} – {p['description']}{tag}", p['port'])
        self.win_printer.clear()
        for name in discovery.list_windows_printers():
            self.win_printer.addItem(name, name)
        for combo, value in zip((self.bt_device, self.com_port, self.win_printer), keep):
            if value:
                self._select(combo, value)

    def _load_form(self):
        p = self.cfg['printer']
        self.mode.setCurrentIndex(max(0, self.mode.findData(p['mode'])))
        self._select(self.bt_device, p['mac'])
        self.bt_channel.setValue(int(p['channel']))
        self._select(self.com_port, p['port'])
        self.com_baud.setCurrentText(str(p['baudrate']))
        self.net_host.setText(p['host'])
        self.net_port.setValue(int(p['net_port']))
        self._select(self.win_printer, p['printer_name'])

    def printer_cfg(self):
        p = dict(self.cfg['printer'])
        p.update(mode=self.mode.currentData(),
                 mac=self.bt_device.currentData() or '',
                 channel=self.bt_channel.value(),
                 port=self.com_port.currentData() or '',
                 baudrate=int(self.com_baud.currentText() or 9600),
                 host=self.net_host.text().strip(),
                 net_port=self.net_port.value(),
                 printer_name=self.win_printer.currentData() or '')
        return p

    # ---------- actions ----------
    def _run(self, fn, callback):
        def done(result, error):
            self._tasks.discard(task)
            callback(result, error)
        task = _Task(fn, done)
        task.setAutoDelete(False)
        self._tasks.add(task)
        QThreadPool.globalInstance().start(task)

    def _set_status(self, text, ok=None):
        color = {True: '#1a7f37', False: '#c62828'}.get(ok, '')
        self.status.setStyleSheet(f'color: {color}' if color else '')
        self.status.setText(text)

    def _error_text(self, error):
        if isinstance(error, OSError):
            return friendly_error(error)[1]
        return str(error)

    def test_print(self):
        p = self.printer_cfg()
        field, message = REQUIRED[p['mode']]
        if not p[field]:
            return self._set_status(message, False)
        self.btn_test.setEnabled(False)
        self._set_status("Envoi du ticket de test…")
        self._run(lambda: build_transport(p).send(TEST_TICKET), self._on_test)

    def _on_test(self, _, error):
        self.btn_test.setEnabled(True)
        if error:
            self._set_status(self._error_text(error), False)
        else:
            self._set_status("Ticket envoyé. S'il est sorti, la configuration est bonne.", True)

    def detect_channel(self):
        mac = self.bt_device.currentData()
        if not mac:
            return self._set_status(REQUIRED['bluetooth'][1], False)
        self.btn_detect.setEnabled(False)
        self._set_status("Recherche du canal (jusqu'à une minute)…")
        self._run(lambda: detect_bluetooth_channel(mac), self._on_detect)

    def _on_detect(self, channel, error):
        self.btn_detect.setEnabled(True)
        if error:
            self._set_status(self._error_text(error), False)
        elif channel is None:
            self._set_status("Aucun canal ne répond : essayez le mode Port COM.", False)
        else:
            self.bt_channel.setValue(channel)
            self._set_status(f"Canal {channel} détecté.", True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
