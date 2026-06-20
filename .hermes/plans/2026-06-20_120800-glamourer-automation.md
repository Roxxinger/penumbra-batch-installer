# Glamourer Design Automation — Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** For jedes FFXIV-Gearset automatisch ein Glamourer-Design erstellen, das beim Job-Wechsel die richtigen Penumbra-Mods + Equipment lädt.

**Architecture:** Hybrid aus Python-Tool (für Design-Erstellung & Datei-Manipulation) + optionalem Dalamud-Helper (für State-Capture per IPC). 

**Tech Stack:** Python 3.11 (bestehend), Glamourer IPC, Penumbra API (localhost:42069), Gearset-DAT-Parser.

---
## Current Context

### Bestehende Daten
| Asset | Status |
|---|---|
| **Penumbra** | 32 Mods installiert (via API `http://localhost:42069`) |
| **Glamourer designs/** | 514 .bak-Dateien (gelöschte Backups), 1 leeres .json |
| **Glamourer automation.json** | 2 Regeln (Roxxi Balboa und Roxxinger Balboa) |
| **Gear-Sets (GEARSET.DAT)** | 4 Character-Folder mit je ~45KB |
| **Glamaholic plates** | 57 Plates mit Equipment-IDs |
| **Penumbra Batch Installer** | `C:\coding\penumbra-batch-installer\` (GitHub) |

### Glamourer Design JSON — Aufbau
```
{
  "FileVersion": 2,
  "Identifier": "<UUID>",
  "Name": "<Design-Name>",
  "Equipment": {
    "MainHand": {"ItemId": 42881, "Apply": true, "Stain": 0, "Stain2": 0},
    "Head":     {"ItemId": 42646, "Apply": true, "Stain": 0, ...},
    "Body":     {...},
    ...
    "Hat": {"Show": true, "Apply": false},
    "Visor": {"IsToggled": false, "Apply": false},
    "VieraEars": {"Show": true, "Apply": false},
    "Weapon": {"Show": true, "Apply": false}
  },
  "Customize": { ... character appearance ... },
  "Mods": [ {"Name": "Bunnymaid_v1.3", "Directory": "Bunnymaid_v1.3", "Enabled": false} ],
  "QuickDesign": true,
  "WriteProtected": false
}
```

### GEARSET.DAT (bekannt)
- Binärformat in `%USERPROFILE%\Documents\My Games\FINAL FANTASY XIV - A Realm Reborn\FFXIV_CHR*\GEARSET.DAT`
- Enthält gear set slots (max 100 sets), jeder mit:
  - Name (UTF-8 String)
  - 13 Equipment-Slots (je ItemID + Container)
  - Job-Klasse (ClassJob)

---

## Approach

### Phase 1: GEARSET.DAT Parser (Python)

Ein reiner Python-Parser für GEARSET.DAT ohne externe Abhängigkeiten.

**Known format (community reverse-engineered):**
- Header: 4 bytes magic/version
- 100 gear set entries, each:
  - 1 byte job_id
  - String (shift-JIS or UTF-8) name, null-terminated
  - 13 equipment entries × (item_id: 4 bytes uint + container: 2 bytes)
  - Padding/size alignment

**Output:** Python-Dataclass `GearSet { job_id, name, slot_items, container_info }`

### Phase 2: Item-ID zu Item-Name Mapping

Glamourer-Designs brauchen keine Item-Namen, nur IDs. Aber für UI/Logging ist der Name hilfreich.

**Option A:** Nutze XIVAPI / universis API für Item-Lookup (network)
```python
# GET https://xivapi.com/Item/{itemId}
# → liefert Name, Icon, etc.
```

**Option B:** Extrahiere aus bestehenden Glamaholic-Daten (57 plates haben bereits IDs)
**Option C:** Aus SaintCoinach/FFDED-Daten (lokal, wenn vorhanden)

Empfehlung: **Option A** (einfach, benötigt nur 1 API-Call pro Item, kann gecached werden).

### Phase 3: Glamourer Design Generator (Python)

Erzeugt für jedes Gearset eine gültige Glamourer-Design-JSON:

```python
def create_design(name: str, gear_set: GearSet, uuid: str = None) -> dict:
    return {
        "FileVersion": 2,
        "Identifier": uuid or str(uuid4()),
        "Name": name,
        "Equipment": {
            slot: {"ItemId": item_id, "Apply": True, "Stain": 0, "Stain2": 0}
            for slot, item_id in gear_set.equipment.items()
        },
        "Customize": {...},  # Default-Werte oder aus Template
        "Mods": [],  # Phase 4
        "QuickDesign": True,
        ...
    }
```

Ohne Customize-Daten und ohne Mods sind die Designs "Quick Designs" — sie ändern nur Equipment, nicht Aussehen oder Mods.

### Phase 4: Penumbra-Mod-Zuordnung (schwierigster Teil)

Jedes Gearset (bzw. jeder Job) soll bestimmte Penumbra-Mods aktivieren.

**Ansatz A — Manuelles Setup pro Job:**
- Für jeden Job eine Liste von Mods definieren (z.B. in YAML: `PLD: [Bunnymaid_v1.3, ...]`)
- Script fügt die Mods in die Design-JSON ein

**Ansatz B — Aktuellen State per IPC erfassen (braucht Dalamud-Helper):**
- Kleiner Dalamud-Plugin `GearsetDesigner`:
  1. Hört auf Gearset-Wechsel-Events
  2. Ruft Glamourer IPC `GetMods()` und `GetCustomize()` auf
  3. Speichert den State als JSON-Datei (z.B. `captures/PLD_Raid_Set.json`)
- Python-Script liest die Captures und erstellt daraus vollständige Designs

**Ansatz C — Bestehende .bak-Designs restaurieren:**
- 514 .bak-Dateien sind Backups alter Designs
- Mit einem Script die .bak → .json umbenennen und in Glamourer importieren
- Plus: Namen aus den JSONs auslesen, in automation.json verlinken

**Empfehlung:** **Ansatz C zuerst** (niedrigste Hürde), dann **Ansatz A** für neue Sets, später **Ansatz B** für vollständige Automation.

### Phase 5: Automation Rules (automation.json)

Nachdem Designs existieren, in `automation.json` pro Job einen Eintrag hinzufügen:

```json
{
  "Name": "PLD Automation",
  "Identifier": { "Type": "Player", "PlayerName": "Roxxinger Balboa", "HomeWorld": 400 },
  "Designs": [
    { "Design": "<DesignUUID>", "Type": 31, "Conditions": { "Gearset": -1, "JobGroup": 19 } }
  ]
}
```

`JobGroup` = ClassJob ID (19 = PLD, 21 = WAR, 32 = DRK, 37 = GNB, etc.)

---

## Tasks

### Task 1: GEARSET.DAT Parser

**Objective:** Python-Funktion die GEARSET.DAT liest und GearSet-Objekte zurückgibt

**Files:**
- Create: `C:\coding\penumbra-batch-installer\gearset_parser.py`

**Step 1:** Recherchiere das GEARSET.DAT-Format (Community-Dokumentation)

Search: `Gearset.dat file format ffxiv site:github.com` oder nutze bekannte Parser von:
- https://github.com/goatcorp/FFXIVQuickLauncher (Dalamud intern)
- https://github.com/xivapi/SaintCoinach (C#)

**Step 2:** Schreibe den Parser

```python
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import os

@dataclass
class GearSet:
    slot: int
    name: str
    job_id: int
    items: Dict[str, int]  # slot_name → item_id

def parse_gearset(path: str) -> List[GearSet]:
    """Liest GEARSET.DAT und gibt alle Gear-Sets zurück."""
    with open(path, 'rb') as f:
        data = f.read()
    # TODO: Parser-Implementierung
    pass
```

**Step 3:** Teste mit existierenden GEARSET.DAT-Dateien (~45KB, 4 Character)

Run: `python gearset_parser.py` → Erwartet: N gear sets extrahiert

**Step 4:** Commit

### Task 2: Item-Name Lookup (optional)

**Objective:** Item-ID zu Name auflösen via XIVAPI + lokaler Cache

**Files:**
- Create: `C:\coding\penumbra-batch-installer\item_lookup.py`

**Step 1:** Schreibe API-Lookup mit SQLite-Cache
```python
import sqlite3, requests
CACHE_DB = os.path.join(SCRIPT_DIR, "item_cache.db")
```

**Step 2:** Teste mit bekannten Item-IDs aus Glamaholic (42881, 42646, etc.)

Run: `python item_lookup.py 42881` → Erwartet: Name des Items

**Step 3:** Commit

### Task 3: Glamourer Design Generator

**Objective:** Erzeugt aus GearSet-Liste gültige Glamourer-Design-JSONs

**Files:**
- Create: `C:\coding\penumbra-batch-installer\glamourer_designer.py`
- Modify: `C:\coding\penumbra-batch-installer\gearset_parser.py` (import)

**Step 1:** Template für Glamourer-Design-JSON erstellen

```python
DESIGN_TEMPLATE = {
    "FileVersion": 2,
    "Identifier": "",
    "Name": "",
    "Description": "",
    "ForcedRedraw": False,
    "QuickDesign": True,
    "Equipment": {},
    "Bonus": {"Glasses": {"ItemId": 0, "Apply": False}},
    "Customize": {},
    "Parameters": {},
    "Mods": [],
    "Links": {"Before": "", "After": ""}
}
```

**Step 2:** UUID pro Design generieren

**Step 3:** Designs in `GLAMOURER_DESIGNS_DIR` speichern
```python
DESIGNS_DIR = os.path.expandvars(
    r"%APPDATA%\XIVLauncher\pluginConfigs\Glamourer\designs"
)
```

**Step 4:** Teste mit 1 Gearset → erwartet: gültige JSON-Datei im designs/-Ordner

**Step 5:** Commit

### Task 4: Automation-Regeln schreiben

**Objective:** Generiere `automation.json` mit Job→Design-Verknüpfung

**Files:**
- Create: `C:\coding\penumbra-batch-installer\glamourer_automation.py`

**Step 1:** Job-ID → JobName Mapping
```python
CLASS_JOBS = {
    0: "ADV", 1: "GLA", 2: "PGL", 3: "MRD", 4: "LNC", 5: "ARC",
    6: "CNJ", 7: "THM", 8: "CRP", 9: "BSM", 10: "ARM", 11: "GSM",
    12: "LTW", 13: "WVR", 14: "ALC", 15: "CUL", 16: "MIN", 17: "BTN",
    18: "FSH", 19: "PLD", 20: "MNK", 21: "WAR", 22: "DRG", 23: "BRD",
    24: "WHM", 25: "BLM", 26: "ACN", 27: "SMN", 28: "SCH", 29: "ROG",
    30: "NIN", 31: "MCH", 32: "DRK", 33: "AST", 34: "SAM", 35: "RDM",
    36: "BLU", 37: "GNB", 38: "DNC", 39: "RPR", 40: "SGE", 41: "VPR",
    42: "PCT"
}
```

**Step 2:** automation.json parsen + neuen Eintrag pro Job hinzufügen

**Step 3:** Existierende automation.json backup-en + überschreiben

**Step 4:** Test — Glamourer sollte die neuen Automation Rules anzeigen

**Step 5:** Commit

### Task 5: Complete CLI-Integration

**Objective:** Einheitliches CLI-Tool `glamourer_tool.py` für alle Operationen

**Files:**
- Create: `C:\coding\penumbra-batch-installer\glamourer_tool.py`

```bash
python glamourer_tool.py parse-gearsets              # Task 1
python glamourer_tool.py generate-designs             # Task 3
python glamourer_tool.py set-automation               # Task 4
python glamourer_tool.py restore-baks                 # Task 5
python glamourer_tool.py status                       # Übersicht
```

**Step 1:** CLI mit argparse
**Step 2:** Alle Tasks als Subcommands
**Step 3:** Integration-Test: parse → generate → verify
**Step 4:** Commit

---

## Dependencies & Risiken

| Risiko | Auswirkung | Lösung |
|--------|-----------|--------|
| GEARSET.DAT-Format unbekannt | Parser schlägt fehl | Community-Code als Referenz, Hex-Dump-Analyse |
| Glamourer liest Änderungen nicht sofort | Designs erscheinen nicht | Glamourer neustarten oder Designs aktualisieren lassen |
| Item-ID veraltet (Patch-Update) | Falsche Items | Item-Cache löschen, neu laden |
| JobGroup IDs stimmen nicht | Automation zündet nicht | Mit Glamourer UI verifizieren |
| `.bak`-Dateien sind alt/korrupt | Kein Quick Win | 1–2 ignorieren, Rest meist intakt |
| Keine IPC-Anbindung (Phase 4+) | Keine Mods in Designs | Ansatz A (manuelle Config) als Pragmatismus |
| FFXIV läuft nicht während Script läuft | Keine API-Calls an Penumbra | Script kann trotzdem Dateien schreiben; API-Calls nur bei laufendem FFXIV |

---

## Prüfkriterien

- [ ] `python glamourer_tool.py parse-gearsets` gibt Gear-Sets mit Namen + Job aus
- [ ] `python glamourer_tool.py generate-designs` erzeugt .json-Dateien in Glamourer/designs/
- [ ] Glamourer UI zeigt neue Designs an
- [ ] `python glamourer_tool.py set-automation` verlinkt Jobs → Designs
- [ ] Gearset-Wechsel in FFXIV wendet Design automatisch an
- [ ] Nur `.json` (keine `.bak`) werden geschrieben — kein Datenverlust
