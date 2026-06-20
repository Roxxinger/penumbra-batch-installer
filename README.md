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
- **C#-Helper** — Direkter LiteDB-Zugriff für Ordner-Zuweisung
- **`--fix-generals`** — Nachträgliche Ordner-Korrektur für "General"-Mods

## Nutzung

```bash
# Alle Mods aus D:\Telegram Desktop installieren
python install_pmp_mod.py

# Trockentest (nur anzeigen was passieren würde)
python install_pmp_mod.py --list-only

# Bestimmtes Verzeichnis
python install_pmp_mod.py --dir "D:\Meine Mods"

# Fehlgeschlagene erneut versuchen
python install_pmp_mod.py --retry-failed

# "General"-Ordner nachträglich korrigieren
python install_pmp_mod.py --fix-generals
```

## Projekt-Struktur

```
penumbra-batch-installer/
├── install_pmp_mod.py         # Haupt-Skript
├── PenumbraHelper/            # C#-Helper für LiteDB-Zugriff
│   ├── Program.cs
│   └── PenumbraHelper.csproj
├── .gitignore
└── README.md
```

## Anforderungen

- **Python 3.11+** (keine externen Pakete — nur stdlib)
- **.NET 10.0+** (für C#-Helper)
- **7-Zip** (für `.7z`-Extraktion)
- **FFXIV mit Penumbra** (API unter `http://localhost:42069`)
