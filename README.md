# INTC Print Bridge — Windows

Pont d'impression local pour **PC Windows** : il reçoit les impressions envoyées par **Odoo** depuis le navigateur et les transmet à une **imprimante thermique ESC/POS** (Bluetooth, port COM, réseau ou imprimante Windows).

Livré sous forme d'**installateur Windows** : un **service** qui démarre avec Windows et une **interface** de configuration avec ticket de test.

- **Version de référence** : v0.1.2
- **Plateforme** : Windows 10 / 11 (64 bits)
- **Éditeur** : INTC

---

## Sommaire

1. [Fonctionnalités](#fonctionnalités)
2. [Installation chez un client](#installation-chez-un-client)
3. [L'interface](#linterface)
4. [Modes d'impression](#modes-dimpression)
5. [API HTTP](#api-http)
6. [Fichiers sur le PC](#fichiers-sur-le-pc)
7. [Dépannage](#dépannage)
8. [Développement](#développement)
9. [Publier une nouvelle version](#publier-une-nouvelle-version)
10. [Structure du dépôt](#structure-du-dépôt)
11. [Projets liés](#projets-liés)

---

## Fonctionnalités

- **Service Windows** `INTCPrintBridge` :
  - démarrage automatique avec Windows, avant même l'ouverture de session ;
  - relance automatique en cas de plantage (3 tentatives) ;
  - fonctionne fenêtre fermée.
- **Quatre modes d'impression** : Bluetooth direct, port COM, réseau (IP), imprimante Windows.
- **Découverte automatique** : appareils Bluetooth appairés, ports COM, imprimantes installées. Le client choisit dans une liste, il ne tape rien de technique.
- **Détection automatique du canal Bluetooth** (bouton *Détecter*).
- **Ticket de test** avant de valider la configuration.
- **Jeton de sécurité** : seul Odoo, avec le bon jeton, peut imprimer.
- **File d'impression** : deux impressions simultanées passent l'une après l'autre au lieu d'échouer.
- **Messages d'erreur clairs** (imprimante éteinte, occupée, injoignable…).
- **Journaux** rotatifs consultables depuis l'interface.

---

## Installation chez un client

1. **Appairer l'imprimante** (si Bluetooth) : *Paramètres Windows* → *Bluetooth et appareils* → *Ajouter un appareil* → choisir l'imprimante, code PIN `0000` (ou `1234`).
2. **Télécharger** `INTC-Bridge-Setup-x.y.z.exe` depuis les [Releases](../../releases).
3. **Lancer l'installateur**.
   Windows SmartScreen affiche *« Windows a protégé votre ordinateur »* (installateur non signé) → **Informations complémentaires** → **Exécuter quand même**.
4. **Suivant → Suivant → Terminer**, en laissant cochée *Ouvrir INTC Print Bridge*.
5. Dans l'interface :
   1. choisir l'imprimante ;
   2. **Détecter** (mode Bluetooth) ;
   3. **Imprimer un ticket de test** → le ticket doit sortir ;
   4. **Enregistrer et redémarrer** ;
   5. **Copier** le jeton.
6. Dans **Odoo**, à la première impression depuis ce PC, coller le jeton quand il est demandé.

Ensuite, plus rien à faire : la fenêtre peut être fermée, le service imprime en arrière-plan, y compris après un redémarrage du PC.

**Mise à jour** : lancer le nouvel installateur par-dessus l'ancien. Le service est arrêté, remplacé et redémarré ; la configuration et le jeton sont **conservés**.

**Désinstallation** : *Paramètres* → *Applications* → *INTC Print Bridge* → Désinstaller (le service est arrêté et supprimé).

---

## L'interface

### Section *Imprimante*
| Élément | Rôle |
|---|---|
| Liste des modes | Bluetooth, Port COM, Réseau (IP), Imprimante Windows |
| Appareil appairé / Actualiser | Liste des imprimantes Bluetooth appairées dans Windows |
| Canal / Détecter | Canal RFCOMM ; *Détecter* le trouve automatiquement |
| Ouvrir les paramètres Bluetooth de Windows | Raccourci vers l'appairage |
| Imprimer un ticket de test | Vérifie la configuration avant de l'enregistrer |

### Section *Service Windows*
| Élément | Rôle |
|---|---|
| Port local | Port d'écoute du pont (8080 par défaut) |
| Jeton (pour Odoo) / Copier | Jeton à coller dans Odoo à la première impression |
| État | En marche / Arrêté / Non installé |
| Enregistrer et redémarrer | Sauvegarde la configuration et redémarre le service |
| Démarrer / Arrêter | Pilotage manuel du service |
| Journaux | Ouvre le dossier des logs |

L'interface demande les droits administrateur (nécessaires pour piloter le service et écrire la configuration).

---

## Modes d'impression

| Mode | Pour quoi | Réglages |
|---|---|---|
| **Bluetooth** | Imprimante Bluetooth classique (ex. Nigachi) | Appareil appairé + canal (détecté automatiquement) |
| **Port COM** | Bluetooth exposé en port série, ou imprimante USB-série | Port (`COM5`…) + vitesse (9600 par défaut) |
| **Réseau (IP)** | Imprimante Ethernet / Wi-Fi | Adresse IP + port (9100 par défaut) |
| **Imprimante Windows** | Imprimante USB installée avec son pilote | Nom de l'imprimante (envoi RAW au spouleur) |

> **Imprimante partagée** (`\\PC\Imprimante`) : préférer le mode **Réseau (IP)**. Le service tourne sous le compte *SYSTEM*, qui ne voit pas les imprimantes connectées par l'utilisateur.

> **Bluetooth** : une imprimante n'accepte **qu'une connexion à la fois**. Le pont ouvre la connexion à chaque impression puis la referme, mais aucun autre appareil (téléphone, autre PC) ne doit rester connecté à l'imprimante.

---

## API HTTP

Le pont écoute uniquement sur `127.0.0.1` (port 8080 par défaut) : il n'est pas joignable depuis le réseau.

### `GET /health`
Vérifie que le pont tourne (sans jeton).
```json
{"status": "ok", "app": "INTC Print Bridge", "mode": "bluetooth"}
```

### `POST /rawprint`
Envoie des octets ESC/POS bruts à l'imprimante.

- **En-tête obligatoire** : `X-Bridge-Token: <jeton>`
- **Corps** : octets bruts (`Content-Type: application/octet-stream`)

| Code | Réponse |
|---|---|
| 200 | `{"status": "ok", "bytes": 17}` |
| 400 | Corps vide |
| 401 | Jeton invalide |
| 404 | Route inconnue |
| 502 | Erreur d'impression (imprimante éteinte, occupée…) |
| 504 | Imprimante injoignable (délai dépassé) |

Le pont répond aux requêtes préalables CORS (`OPTIONS`) et envoie `Access-Control-Allow-Private-Network: true`, nécessaire pour qu'un site HTTPS (Odoo) puisse appeler `localhost` depuis Chrome.

Exemple PowerShell (lit le jeton dans la configuration) :
```powershell
$cfg = Get-Content "$env:ProgramData\INTC Bridge\config.json" | ConvertFrom-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$($cfg.port)/rawprint" `
  -Headers @{'X-Bridge-Token' = $cfg.token} -ContentType 'application/octet-stream' `
  -Body ([Text.Encoding]::ASCII.GetBytes("Test`n`n`n`n"))
```

---

## Fichiers sur le PC

| Élément | Emplacement |
|---|---|
| Programmes | `C:\Program Files\INTC Print Bridge\` (`service\` et `gui\`) |
| Configuration | `C:\ProgramData\INTC Bridge\config.json` |
| Journaux | `C:\ProgramData\INTC Bridge\logs\bridge.log` (1 Mo × 3 archives) |
| Service | `INTCPrintBridge` (*INTC Print Bridge* dans `services.msc`) |

Vérification rapide (PowerShell administrateur) :
```powershell
Get-Service INTCPrintBridge | Select-Object Status, StartType
Invoke-RestMethod http://127.0.0.1:8080/health
Get-Content "$env:ProgramData\INTC Bridge\logs\bridge.log" -Tail 20
```

---

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| *Imprimante éteinte ou hors de portée* | Imprimante éteinte, en veille ou trop loin | L'allumer / la rapprocher, réessayer |
| *Imprimante injoignable (en veille ?)* | Délai de connexion dépassé | Réveiller l'imprimante |
| *Imprimante occupée ou connexion interrompue* (WinError 10058) | Un autre appareil est connecté à l'imprimante | Déconnecter le téléphone / l'autre PC |
| *Aucun canal ne répond* | Pilote Bluetooth incompatible avec RFCOMM direct | Passer en mode **Port COM** |
| État *Non installé* | Service absent | Réinstaller avec l'installateur |
| Odoo : *pont injoignable* | Service arrêté | Interface → **Démarrer** |
| Odoo : *Jeton invalide* | Jeton différent | Recopier le jeton depuis l'interface |
| SmartScreen bloque l'installateur | Exécutable non signé | *Informations complémentaires* → *Exécuter quand même* |

En cas de problème persistant, envoyer le fichier `bridge.log` (bouton **Journaux**).

---

## Développement

Le cœur du pont est en Python standard et se développe/teste sous **Linux** ; seuls le service et l'installateur sont propres à Windows.

```bash
python3 -m venv .venv
.venv/bin/pip install pyside6-essentials pyserial
.venv/bin/python bridge_gui.py          # interface (les fonctions service sont désactivées hors Windows)
```

Tests rapides du cœur :
```bash
# Découverte des imprimantes
python3 -c "from intc_bridge import discovery as d; print(d.list_bluetooth_devices())"

# Détection du canal Bluetooth
python3 -c "from intc_bridge.transports import detect_bluetooth_channel as d; print(d('AA:BB:CC:DD:EE:FF'))"

# Serveur de test sur le port 8081
python3 -c "from intc_bridge import config, server; c = config.load(); c['port'] = 8081; server.make_server(c).serve_forever()"
```

Sous Linux, la configuration est dans `~/.config/intc-bridge/config.json`.

Le script historique `bridge.py` (variables d'environnement `BRIDGE_PORT`, `PRINTER_MAC`, `PRINTER_CHANNEL`, sans jeton) reste disponible comme lanceur Linux simple.

---

## Publier une nouvelle version

La compilation se fait sur **GitHub Actions** (runner `windows-latest`) : PyInstaller ne peut pas produire d'exécutable Windows depuis Linux.

```bash
git add -A && git commit -m "..." && git tag v0.1.3 && git push && git push --tags
```

Le workflow `.github/workflows/build-windows.yml` :
1. installe Python 3.12 et `requirements-windows.txt` ;
2. compile avec **PyInstaller** :
   - `INTCBridgeService` (service, `--hidden-import win32timezone`) ;
   - `INTCBridge` (interface, `--windowed --uac-admin`) ;
3. construit l'installateur avec **Inno Setup** (`installer/setup.iss`) ;
4. publie `INTC-Bridge-Setup-x.y.z.exe` dans les **Releases**.

Le workflow peut aussi être lancé à la main depuis l'onglet *Actions* (`workflow_dispatch`).

---

## Structure du dépôt

```
intc_print_bridge/
├── intc_bridge/
│   ├── transports.py   # Bluetooth, port COM, réseau, imprimante Windows + détection du canal
│   ├── discovery.py    # liste des appareils Bluetooth, ports COM, imprimantes Windows
│   ├── config.py       # config.json (ProgramData sous Windows, ~/.config sous Linux) + jeton
│   ├── server.py       # serveur HTTP : /health, /rawprint, CORS, jeton, file d'impression
│   └── runner.py       # démarrage/arrêt du serveur dans un thread + journaux rotatifs
├── bridge_service.py   # service Windows (pywin32)
├── bridge_gui.py       # interface PySide6
├── bridge.py           # lanceur Linux historique
├── installer/setup.iss # installateur Inno Setup
├── requirements-windows.txt
└── .github/workflows/build-windows.yml
```

---

## Projets liés

- [`Gitjaphet/product_barcode_print_intc`](https://github.com/Gitjaphet/product_barcode_print_intc) — module Odoo qui envoie les impressions au pont.
- [`Gitjaphet/intc_bridge_android`](https://github.com/Gitjaphet/intc_bridge_android) — même pont pour **Android**, même contrat HTTP.
