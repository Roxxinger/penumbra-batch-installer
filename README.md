# Penumbra Batch Installer

API-basierter Batch-Installer für Penumbra-Mods (`.pmp`/`.ttmp2`) mit KI-gestützter Ordner-Zuweisung via Dateipfad-Analyse.

## Features

- **Batch-Install** von `.7z`-Archiven aus einem Quellverzeichnis
- **Deduplizierung** — Hash-Dedup + Version-Dedup + Name-Check + PMP-Hash-Dedup
- **Version-Aware** — nur neueste Version jeder Mod wird installiert
- **Body-Type-Filter** — Nur Lavabod/Rue-kompatible Gear-Mods (Bibo/YAB/Muse/Tre werden übersprungen)
- **Ordner-Kategorisierung** via Dateipfad-Scoring:
  - VFX/Jobs/{Job}, VFX, Gear/Weapons/{Job}, Gear/Sets, etc.
  - **Emotes/{Name}/** — Subfolder pro Emote
- **File Watcher** — Automatische Installation bei neuen Dateien in `D:\Telegram Desktop`
- **Delete-Protection** — Mehrstufige Sicherung gegen versehentliches Löschen aller Mods
- **C#-Helper** — Direkter LiteDB-Zugriff für Ordner-Zuweisung

## Nutzung

### Einmaliger Batch

```bash
# Alle Mods aus D:\Telegram Desktop installieren
python install_pmp_mod.py

# Trockentest (nur anzeigen was passieren würde)
python install_pmp_mod.py --list-only

# Bestimmtes Verzeichnis
python install_pmp_mod.py --dir "D:\Meine Mods"
```

### File Watcher (empfohlen)

```bash
# Watcher starten (überwacht D:\Telegram Desktop)
python watch_telegram.py

# Status prüfen
python watch_telegram.py --status

# Watcher stoppen
python watch_telegram.py --stop
```

Der Watcher startet den Installer automatisch 60s nach der letzten Dateiänderung.

### Weitere Optionen

```bash
# Fehlgeschlagene erneut versuchen
python install_pmp_mod.py --retry-failed

# "General"-Ordner nachträglich korrigieren
python install_pmp_mod.py --fix-generals

# Destruktive Aktionen (Force)
python install_pmp_mod.py --force
```

## Delete-Protection

Das Löschen aller Mods (`delete-all`) ist mehrstufig geschützt:

1. **`--force` Flag** im Python-Skript erforderlich
2. **`confirm` Parameter** für den C#-Helper (`delete-all confirm --yes`)
3. **Safelock-Datei** — leere Datei `SAFELOCK` im Projekt-Root blockiert `delete-all` komplett
4. **Interaktive Bestätigung** — auch mit Flag wird `yes` abgefragt

## Projekt-Struktur

```
penumbra-batch-installer/
├── install_pmp_mod.py         # Haupt-Skript
├── watch_telegram.py          # File Watcher
├── PenumbraHelper/            # C#-Helper für LiteDB-Zugriff
│   ├── Program.cs
│   └── PenumbraHelper.csproj
├── .gitignore
└── README.md
```

## Anforderungen

- **Python 3.11+** (keine externen Pakete — nur stdlib; watchdog optional für Watcher)
- **.NET 10.0+** (für C#-Helper)
- **7-Zip** (für `.7z`-Extraktion)
- **FFXIV mit Penumbra** (API unter `http://localhost:42069`)
