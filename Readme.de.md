<div align="center">

# UpdateWulf

### Deine Updates. Deine Systeme. Deine Entscheidung.

**Sieh ausstehende Updates auf deinen Rechnern. Starte die nativen Paketaktualisierungen, wenn du es möchtest.**

[Download](#download) · [Schnellstart](#quick-start) · [Installation](#installation) · [Handbuch](docs/manual.md) · [Fehlerbehebung](docs/troubleshooting.md)

[English](Readme.md) · **Deutsch** · [Français](Readme.fr.md) · [Русский](Readme.ru.md) · [Español](Readme.es.md) · [Polski](Readme.pl.md) · [Português](Readme.pt.md)

</div>

![UpdateWulf-Terminalvorschau mit Beispieldaten](docs/assets/terminal-preview.svg)

---

| Alles im Blick | Gezielte Steuerung | Separate Programmaktualisierung |
| :--- | :--- | :--- |
| Zwischengespeicherter Status der eingebundenen Rechner, einschließlich veralteter Daten und Offline-Zustände. | Eine authentifizierte Anforderung startet die native Paketaktualisierung auf dem Zielrechner. | UpdateWulf aktualisiert seine eigenen Programmdateien aus seinem öffentlichen GitHub-Repository. |

## Auf einen Blick

UpdateWulf ist ein Python-Dienst und Kommandozeilenwerkzeug für eine kleine Gruppe vertrauenswürdiger Rechner. Ein HTTPS-Hub empfängt die Update-Berichte; auf jedem eingebundenen Rechner läuft ein Worker als Hintergrundprozess. Die Shell-Integration zeigt zwischengespeicherte Ergebnisse an, ohne bei jeder Eingabeaufforderung das Netzwerk abzufragen.

Der öffentliche Quellcode meldet derzeit **Version 2.1.0**. Er enthält Adapter für **APT, pacman, NetBSD pkgin und Windows Update Agent**. Die Plattformadapter und die nativen Abnahmetests sind unterschiedlich weit abgedeckt; siehe [Voraussetzungen](#requirements) und [Prüfnachweis](docs/documentation-status.md). Die sieben README-Sprachen bedeuten **keine** vollständig in sieben Sprachen übersetzte Programmoberfläche: Einige Laufzeitmeldungen sind weiterhin deutsch.

### Anwendungsbereiche

- Ein Heimlabor oder eine kleine Rechnergruppe, deren Update-Status du in einem Terminal sehen möchtest.
- Linux-, Windows- und NetBSD-Rechner mit ihren vorhandenen nativen Paketverwaltungen.
- SSH-Sitzungen, in denen eine kompakte Statuszeile hilfreicher ist als ein Dashboard.
- Anwender, die den Zeitpunkt von Paketaktualisierungen selbst bestimmen und das vorhandene Rechtekonzept des Betriebssystems beibehalten möchten.

UpdateWulf ist kein Sicherungssystem und keine allgemeine Plattform zur Softwareverteilung. Es implementiert weder winget, Flatpak, Snap oder Homebrew noch eine automatische Neustartverwaltung. Die Repository-Synchronisierung bleibt als ältere Kompatibilitätsfunktion erhalten; neue Git-Synchronisierung gehört zu GitSyncWulf.

## Schnellstart

<a id="quick-start"></a>

**Das Programm zunächst kennenlernen:** Für die lokalen Programmaufrufe benötigst du Python 3.9+. Das gezeigte `git clone` benötigt zusätzlich Git; alternativ kannst du die Quellcode-ZIP herunterladen und entpacken. Ein Dienst oder eine Konfiguration ist dafür nicht nötig.

```sh
git clone https://github.com/n-e-o-w-u-l-f/UpdateWulf.git
cd UpdateWulf
python3 pc_mesh.py --version
python3 pc_mesh.py --help
```

Verwende unter Windows `py -3` anstelle von `python3`, wenn du Python über diesen Launcher aufrufst.

**Bereits installiert und eingebunden?** Öffne ein neues Terminal:

```sh
updatewulf status
updatewulf status --json
updatewulf diagnose
updatewulf --self update --check
```

`status` liest eine lokale Momentaufnahme. `diagnose` prüft den konfigurierten HTTPS-Hub. `--self update --check` liest den öffentlichen Release-Branch, ohne ihn zu installieren. Eine leere Momentaufnahme beweist nicht, dass alle Rechner aktuell sind.

## Voraussetzungen

<a id="requirements"></a>

| Plattform | Laufzeit und nativer Adapter | Installationsweg | Aktuelle Einschränkungen |
| :--- | :--- | :--- | :--- |
| Debian / Raspberry Pi OS | Python 3.9+, `apt-get` | Benutzerdienst; systemweiter systemd-Dienst | Neue Prüfungen verwenden einen separaten Metadaten-Cache. |
| Arch Linux | Python 3.9+, `pacman`, `vercmp` | Benutzerdienst; systemweiter systemd-Dienst | Repository-Metadaten und Paketaktualisierungen benötigen Netzwerkzugriff. |
| Windows | Python 3.9+ mit einer tatsächlichen `python.exe`; Windows PowerShell und Windows Update Agent | Geplante Benutzeraufgabe; systemweite Aufgaben mit erhöhten Rechten | Kein winget-Adapter; in dieser Dokumentationssitzung wurden keine nativen Windows-Tests ausgeführt. |
| NetBSD | Python 3.9+, `pkgin` | Benutzer-cron als Ausweichlösung; nativer `rc.d`-Dienst | Prüfungen ohne root-Rechte können zwischengespeicherte pkgin-Metadaten verwenden. |
| Android / Termux | Python 3.9+, APT, tatsächliches Termux-Benutzerkonto | Termux-Startskript | Für den Start nach einem Neustart ist Termux:Boot erforderlich; aktualisiert nicht das Android-Betriebssystem. |
| Andere Plattformen | Die CLI kann unter Python möglicherweise ausgeführt werden | Keine vollständige native Installationsanleitung | Nicht unterstützte Erfassungsmodule melden `UNSUPPORTED` und nicht null Updates. |

Alle über das Netzwerk verbundenen Worker benötigen eine Konfiguration für ihre Einbindung, einen HTTPS-Hub, dessen vertrauenswürdiges Zertifikat, ein eindeutiges Teilnehmertoken und einen beschreibbaren Zustandsspeicher. **Git ist für die Selbstaktualisierung des Programms erforderlich.** Die Unix-Benutzerinstallation benötigt einen funktionierenden systemd-Benutzermanager oder `crontab`; für `scripts/install.sh` ist Bash erforderlich. Optionale ältere Hilfsprogramme zur Einbindung verwenden Paramiko; der Kerndienst verwendet die Python-Standardbibliothek.

## Download

<a id="download"></a>

- [Aktuellen Quellcode als ZIP herunterladen](https://github.com/n-e-o-w-u-l-f/UpdateWulf/archive/refs/heads/main.zip).
- [Quellcode ansehen](https://github.com/n-e-o-w-u-l-f/UpdateWulf).
- [Veröffentlichte Releases prüfen](https://github.com/n-e-o-w-u-l-f/UpdateWulf/releases).

Zum geprüften Ausgangsstand dieser Dokumentation waren keine Download-Dateien für getaggte Releases und keine MSI-, EXE-, DEB- oder PKG-Installationspakete veröffentlicht. Die ZIP-Datei folgt dem veränderlichen Branch `main`. Für eine reproduzierbare Installation dokumentierst du bei einem Git-Klon den heruntergeladenen Commit mit `git rev-parse HEAD`. Behandle die ZIP-Datei nicht wie ein signiertes natives Installationspaket.

## Installation

<a id="installation"></a>

### Installationsumfang wählen

| Du benötigst … | Wähle … | Das wird geändert |
| :--- | :--- | :--- |
| Befehle und eine Shell-Statuszeile für dein Benutzerkonto | Benutzerinstallation | Deine Aufrufskripte, verwaltete Blöcke in Shell-Profilen und ein optionaler Benutzer-Worker. |
| Einen Worker, der mit dem Rechner startet und autorisierte Betriebssystemaktualisierungen ausführen kann | Systemweiten Dienst | Nativer Dienst bzw. native Aufgabe des Betriebssystems, geschütztes Hilfsprogramm für Paketaktualisierungen und eine ausdrücklich festgelegte Besitzerkonfiguration. |
| Nur einen ersten Einblick in das Werkzeug | Quellcode-Verzeichnis | `pc_mesh.py --help` / `--version` ausführen; keine Installation erforderlich. |

**Zuerst die Einbindung konfigurieren:** Folge der Anleitung zur [Einrichtung von Hub und Teilnehmern](docs/configuration.md#first-setup). Die Dateien unter [examples/](examples/) enthalten Platzhalter und keine verwendbaren Zugangsdaten. Speichere deine fertig ausgefüllte Konfiguration außerhalb des Quellcode-Verzeichnisses, normalerweise unter `~/.config/pc-mesh/config.json` (unter Windows `%USERPROFILE%\.config\pc-mesh\config.json`). Bewahre das heruntergeladene Programmverzeichnis an einem dauerhaften Ort auf: Die Installationsskripte verweisen darauf.

### Für deinen Benutzer installieren

Führe die Befehle im heruntergeladenen Quellcode-Verzeichnis mit dem Benutzerkonto aus, das UpdateWulf verwenden wird:

```sh
# Unix: Aufrufskripte, Shell-Integration und dauerhaften Benutzer-Worker installieren.
python3 install.py
```

```powershell
# Windows PowerShell: die tatsächliche Python-Programmdatei verwenden, keinen Store-Alias.
$Python = (Get-Command python.exe -ErrorAction Stop).Source
& $Python -c "import sys; assert sys.version_info >= (3, 9)"
.\install_windows.ps1 -Python $Python
```

Für die reine Shell-Integration verwendest du `python3 install.py --prompt-only` oder `.\install_windows.ps1 -Python $Python -PromptOnly`. Dabei wird kein neuer Status erfasst; die Integration benötigt den Cache eines bereits vorhandenen Workers. Unter Termux führst du `python install_termux.py` in der tatsächlichen Termux-Sitzung aus. Programmaktualisierungen unter Termux erfordern derzeit eine manuelle native Übergabe; belasse `auto_self_update: false`, da der allgemeine Aktualisierer das Termux-Startskript nicht erneuert.

Öffne ein neues Terminal und führe `updatewulf --version`, `updatewulf diagnose` und `updatewulf status` aus. Die [Installationsanleitung](docs/installation.md) erklärt Pfade, Autostart, Prüfung und Rückkehr zur vorherigen Version.

### Systemweit installieren

Eine systemweite Installation stellt einen nativen Hintergrundprozess für den Rechner und kontrollierte Rechte zur Paketaktualisierung bereit; sie richtet nicht automatisch die Shell jedes Benutzers ein. Bereite zuerst ein eigenes Dienstkonto und dessen Konfiguration für die Einbindung vor. Verwende einen dauerhaften, durch den Administrator kontrollierten Quellcode-Pfad und befolge die Schritte zur plattformspezifischen Übergabe:

- [Linux / systemd](docs/installation.md#linux-systemwide): `enable_machine_updates.py --user … --config … --state … --source …`, in einer tatsächlichen root-Sitzung.
- [Windows](docs/installation.md#windows-systemwide): `enable_machine_updates_windows.ps1 -Python … -Config … -Owner …`, in einer Konsole des verantwortlichen Benutzers mit erhöhten Rechten.
- [NetBSD](docs/installation.md#netbsd-systemwide): `enable_machine_updates_netbsd.py --config … --state … --python …`, in einer tatsächlichen root-Sitzung.

Diese Installationsskripte erhöhen ihre Rechte nicht selbst. Eine systemweit verwaltete Installation verwendet ihre native Übergabe an die neue Programmversion und nicht das Selbstaktualisierungsprogramm der Benutzerinstallation.

## Beispiele für den Alltag

Ersetze `workstation.local` durch einen gemeldeten bzw. eingebundenen Hostnamen oder verwende die genaue Teilnehmer-ID. Sowohl die Schreibweise mit dem Hostnamen zuerst als auch die Schreibweise mit der Aktion zuerst wird akzeptiert.

| Ziel | Befehl | Wirkung |
| :--- | :--- | :--- |
| Zwischengespeicherten Status aller Rechner lesen | `updatewulf status` | Lokaler Lesezugriff. |
| Einen einzelnen Rechner abfragen | `updatewulf workstation.local status` | Lokal gefilterte Momentaufnahme. |
| Status exportieren | `updatewulf status --json` | Unverarbeitete Momentaufnahme einschließlich Zeitstempeln. |
| CLI-Farben abschalten | `updatewulf status --no-color` | Unformatierter Text. |
| Verbindung prüfen | `updatewulf diagnose` | Authentifiziertes `GET /fleet`; kein Update-Auftrag. |
| Neue Prüfung anfordern | `updatewulf workstation.local refresh --wait 60` | Reiht eine Prüfung ein und wartet bis zu 60 Sekunden. |
| Betriebssystem-Paketaktualisierungen installieren | `updatewulf workstation.local update --wait 600` | Ausdrückliche Anforderung einer nativen Aktualisierung; erfordert Einbindung und die nötigen Rechte auf dem Zielrechner. |
| Auftrag einreihen, ohne zu warten | `updatewulf workstation.local update --wait 0` | Zeigt den eingereihten Auftrag an; bestätigt nicht dessen Abschluss. |
| Menü öffnen | `updatewulf tui` | Interaktives Bedienmenü; siehe den bekannten Fehler bei einer leeren Rechnergruppe. |
| UpdateWulf selbst auf Updates prüfen | `updatewulf --self update --check` | Liest den öffentlichen Programm-Branch. |
| UpdateWulf selbst aktualisieren | `updatewulf --self update` | Bereitet den Programmquellcode vor, prüft ihn und aktiviert ihn für eine unterstützte Benutzerinstallation. |

`updatewulf all update` fordert Aktualisierungen für **alle eingebundenen Zielrechner** an. Verwende diesen Befehl nur, wenn du genau diesen Umfang beabsichtigst. Eine Zeitüberschreitung der CLI bricht eine bereits laufende Paketverwaltung nicht ab. Die vollständige Referenz aller Aktionen, Optionen und Rückgabecodes findest du im [Handbuch](docs/manual.md).

## Konfiguration

Die Konfiguration verwendet JSON. Beginne mit [Client](examples/config.client.json), [Hub](examples/config.hub.json) oder [Bedienkonto](examples/control.json) und folge anschließend der [vollständigen Konfigurationsreferenz](docs/configuration.md). Pfade in JSON werden wörtlich behandelt: Verwende absolute Pfade; `~` und Umgebungsvariablen werden innerhalb von JSON-Zeichenfolgen im Allgemeinen nicht aufgelöst.

| Einstellung | Standardwert im Code | Bedeutung |
| :--- | :--- | :--- |
| `scan_interval` | `1800` Sekunden | Zeit zwischen Paketprüfungen. |
| `report_interval` | `20` Sekunden | Zeit zwischen Berichten an den Hub. |
| `auto_self_update` | `true` | Aktiviert die Programmaktualisierung, soweit der Worker-Modus sie zulässt. |
| `self_update_interval` | `21600` Sekunden | Prüfintervall für das Programm; auf 1–24 Stunden begrenzt, nach einer anfänglichen Wartezeit von 5 Minuten. |
| `self_update_branch` | `main` | Öffentlicher Programm-Branch. |
| `announce_only` | `false` | Deaktiviert ältere Git-Funktionen; mit `machine_control: false` wird außerdem der Worker für Anforderungen deaktiviert. |
| `machine_control` | `false` | Aktiviert Prüf- und Installationsanforderungen im reinen Meldemodus. |
| `native_installer` | `false` | Leitet Installationen an ein zuvor eingerichtetes natives Hilfsprogramm weiter. |

Die Beispiele setzen bewusst `auto_self_update: false`, damit die Ersteinrichtung vorhersehbar bleibt. Aktiviere die Funktion, nachdem du eine Benutzerinstallation aus dem öffentlichen Repository geprüft hast. Bei Bedienbefehlen hat eine `control.json` im Standardpfad Vorrang vor `config.json`; ein ausdrücklich angegebener, vom Standard abweichender `--config`-Pfad wählt diese Datei aus. Für angepasste Konfigurations- und Zustandspfade bestehen Einschränkungen bei der Selbstaktualisierung; siehe [bekannte Fehler](docs/troubleshooting.md#known-issues).

## Dienste, Status und Selbstaktualisierung

Der Benutzerdienst heißt unter systemd `updatewulf.service` oder in der Windows-Aufgabenplanung `UpdateWulf-User`. Die Namen der systemweiten Dienste unterscheiden sich; die [Installationsanleitung](docs/installation.md) führt sie einzeln auf. Protokolle und Momentaufnahmen liegen normalerweise unter `~/.local/state/pc-mesh/`, darunter `service.log`, `heartbeat.json`, `fleet.json` und `executed-commands.json`.

Mögliche Statuswerte sind `OK`, `CACHED`, `CHECKING`, `UNKNOWN`, `ERROR` und `UNSUPPORTED`. Zwischengespeicherte Daten und Daten nicht erreichbarer Rechner bleiben sichtbar, ohne als neue erfolgreiche Prüfung dargestellt zu werden. Aufträge haben eigene Zustände, darunter `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `NEEDS_ADMIN`, `EXPIRED` und `INTERRUPTED`.

Die Selbstaktualisierung prüft die Repository-Identität, die Integrität der Git-Objekte und die Abstammung der Commits, führt die Prüfungen der vorbereiteten Version aus und behält die aktuelle sowie die vorherige Programmversion. Die Git-Prüfung ist kein Signaturverfahren für Releases. Die erstmalige Migration erfordert einen ausdrücklich ausgeführten Bedienbefehl. Vorhandene Konfiguration und Einbindungsdaten liegen außerhalb des Versionsverzeichnisses. Die Rückkehr zur vorherigen Version und die vorsichtigen Grenzen der automatischen Bereinigung werden im [Handbuch](docs/manual.md#application-self-update) erklärt.

## Bekannte Fehler und Fehlerbehebung

Die [Fehlerübersicht](docs/troubleshooting.md#known-issues) beschreibt konkrete Einschränkungen und Abhilfen. Derzeit gilt:

- Es gibt keine vollständige plattformübergreifende Deinstallation; folge der [Anleitung zur manuellen Entfernung](docs/installation.md#uninstall).
- Die Selbstaktualisierung der Benutzerinstallation übernimmt angepasste Unix-Zustands- und Konfigurationspfade nicht zuverlässig; verwende Standardpfade oder eine manuelle native Übergabe.
- Unter Termux verwendet die Selbstaktualisierung `install.py` statt des Installationsskripts für den Start-Hook. Die anschließende Aktivierung ist deshalb nicht vollständig auf Termux abgestimmt; aktualisiere Termux-Installationen manuell und lasse `auto_self_update: false` gesetzt.
- Die TUI kann beim Navigieren in einer leeren Rechnergruppe fehlschlagen; verwende `status` und `diagnose`, bis ein Teilnehmer eingebunden ist.
- Die Bash-Prompt-Integration berücksichtigt `NO_COLOR` nicht vollständig; verwende `status --no-color` für garantiert unformatierte CLI-Ausgabe.
- Unbekannte Inhalte einer Programmversion, darunter zusätzliche Dokumentationsverzeichnisse, verhindern vorsorglich das automatische Löschen alter Versionen.
- Adapter für macOS/Homebrew, winget, Flatpak und Snap sowie eine vollständige Übersetzung der Programmausgaben sind nicht implementiert.

Wenn ein Befehl fehlt, öffne eine neue Shell und prüfe dein Benutzer-bin-Verzeichnis. Prüfe bei `NEEDS_ADMIN` das native Hilfsprogramm und die Berechtigung `allow_install` des Teilnehmers. Prüfe bei TLS- oder Authentifizierungsfehlern Zertifikat, Hostname und Einbindung. Ersetze eine fehlgeschlagene Prüfung nicht durch die Annahme, es seien null Updates vorhanden.

## Handbuch und Projektinformationen

| Dokumentation | Inhalt |
| :--- | :--- |
| [Installation](docs/installation.md) | Benutzer- und Systemeinrichtung, Dienste, Prüfung, Rückkehr zur vorherigen Version und Deinstallation. |
| [Handbuch](docs/manual.md) | Alle CLI-Aktionen und Optionen, Beispiele, Statuswerte, Protokolle und Selbstaktualisierung. |
| [Konfiguration](docs/configuration.md) | Einrichtung von Hub, Teilnehmern und Bedienkonto, Schlüssel, Standardwerte, Pfade und Vorrangregeln. |
| [Fehlerbehebung](docs/troubleshooting.md) | Symptome, bekannte Fehler, praktische Abhilfen und häufige Fragen. |
| [Prüfnachweis](docs/documentation-status.md) | Was geprüft wurde und was noch einen nativen Plattformtest benötigt. |
| [README-Vorlage](docs/README_TEMPLATE.md) | Wiederverwendbare Vorgaben für die Projektvorstellung in sieben Sprachen. |
| [Gestaltungsrecherche](docs/readme-design-research.md) | Zehn README-Vorbilder aus Primärquellen und die daraus übernommenen Gestaltungsentscheidungen. |

Das ausführliche technische Handbuch wird derzeit **auf Englisch** gepflegt; jede der sieben README-Dateien bietet denselben lokalisierten Einstieg und Überblick über die Bedienung.

**Mitwirken / Hilfe erhalten:** [Erstelle einen Fehlerbericht](https://github.com/n-e-o-w-u-l-f/UpdateWulf/issues) mit Betriebssystem, Python-Version, UpdateWulf-Commit, genauem Befehl und bereinigter Ausgabe. Füge niemals Tokens, private Schlüssel oder tatsächlich verwendete Konfigurationsdateien bei. Siehe [Prüfungen für Mitwirkende](docs/manual.md#contributing).

**Lizenz:** Das Repository enthält derzeit keine Lizenzdatei. Diese Dokumentation legt keine Lizenz fest und erteilt keine Nutzungsrechte; frage den Maintainer nach den erlaubten Möglichkeiten der Weiterverwendung.

---

<div align="center">

[Nach oben](#updatewulf) · [Quellcode herunterladen](https://github.com/n-e-o-w-u-l-f/UpdateWulf/archive/refs/heads/main.zip) · [Handbuch lesen](docs/manual.md)

</div>
