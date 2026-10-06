"""Service Windows « INTC Print Bridge » : enveloppe pywin32 autour de BridgeRunner.
Usage manuel : bridge_service.exe --startup auto install | start | stop | remove"""
import sys

import servicemanager
import win32event
import win32service
import win32serviceutil

from intc_bridge.runner import BridgeRunner, log, setup_logging


class BridgeService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'INTCPrintBridge'
    _svc_display_name_ = 'INTC Print Bridge'
    _svc_description_ = "Reçoit les impressions d'Odoo et les envoie à l'imprimante thermique."

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.runner = BridgeRunner()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        setup_logging()
        try:
            self.runner.start()
        except Exception:
            log.exception('Démarrage du pont impossible')
            raise
        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
        self.runner.stop()


if __name__ == '__main__':
    if len(sys.argv) == 1:
        # Lancé par le gestionnaire de services Windows (cas de l'exe PyInstaller)
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(BridgeService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Lancé à la main avec une commande : install, start, stop, remove...
        win32serviceutil.HandleCommandLine(BridgeService)
