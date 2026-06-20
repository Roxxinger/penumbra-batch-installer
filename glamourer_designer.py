"""
glamourer_designer.py — Erzeugt/verwaltet Glamourer-Design-JSONs

Erstellt gültige Glamourer-Design-Dateien im richtigen Format
und speichert sie im Glamourer designs/-Verzeichnis.
"""

import json
import os
import uuid as uuid_mod
import shutil
from datetime import datetime, timezone
from typing import Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Glamourer-Designs-Verzeichnis
APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
GLAMOURER_DIR = os.path.join(APPDATA, "XIVLauncher", "pluginConfigs", "Glamourer")
DESIGNS_DIR = os.path.join(GLAMOURER_DIR, "designs")
AUTOMATION_FILE = os.path.join(GLAMOURER_DIR, "automation.json")


def ensure_dirs():
    """Stellt sicher dass das designs/-Verzeichnis existiert."""
    os.makedirs(DESIGNS_DIR, exist_ok=True)


def new_uuid() -> str:
    """Erzeugt eine UUID im Glamourer-Format (lowercase, kein Bindestrich-Strip)."""
    return str(uuid_mod.uuid4()).lower()


def make_design(name: str, identifier: Optional[str] = None) -> dict:
    """Erzeugt ein leeres Glamourer-Design-Template.

    Args:
        name: Anzeigename des Designs
        identifier: UUID (wird generiert wenn None)

    Returns:
        Dict im Glamourer-Design-Format (FileVersion 2)
    """
    now = datetime.now(timezone.utc).isoformat()
    return {
        "FileVersion": 2,
        "Identifier": identifier or new_uuid(),
        "Name": name,
        "Description": "",
        "CreationDate": now,
        "LastEdit": now,
        "ForcedRedraw": False,
        "ResetAdvancedDyes": False,
        "ResetTemporarySettings": False,
        "Color": "",
        "QuickDesign": True,
        "Tags": [],
        "WriteProtected": False,
        "Equipment": {
            "MainHand": {"ItemId": 0, "Crest": 0, "Apply": False, "ApplyStain": False,
                         "ApplyCrest": False, "Stain": 0, "Stain2": 0},
            "OffHand": {"ItemId": 0, "Crest": 0, "Apply": False, "ApplyStain": False,
                        "ApplyCrest": False, "Stain": 0, "Stain2": 0},
            "Head": {"ItemId": 0, "Crest": 0, "Apply": False, "ApplyStain": False,
                     "ApplyCrest": False, "Stain": 0, "Stain2": 0},
            "Body": {"ItemId": 0, "Crest": 0, "Apply": False, "ApplyStain": False,
                     "ApplyCrest": False, "Stain": 0, "Stain2": 0},
            "Hands": {"ItemId": 0, "Crest": 0, "Apply": False, "ApplyStain": False,
                      "ApplyCrest": False, "Stain": 0, "Stain2": 0},
            "Legs": {"ItemId": 0, "Crest": 0, "Apply": False, "ApplyStain": False,
                     "ApplyCrest": False, "Stain": 0, "Stain2": 0},
            "Feet": {"ItemId": 0, "Crest": 0, "Apply": False, "ApplyStain": False,
                     "ApplyCrest": False, "Stain": 0, "Stain2": 0},
            "Ears": {"ItemId": 0, "Crest": 0, "Apply": False, "ApplyStain": False,
                     "ApplyCrest": False, "Stain": 0, "Stain2": 0},
            "Neck": {"ItemId": 0, "Crest": 0, "Apply": False, "ApplyStain": False,
                     "ApplyCrest": False, "Stain": 0, "Stain2": 0},
            "Wrists": {"ItemId": 0, "Crest": 0, "Apply": False, "ApplyStain": False,
                       "ApplyCrest": False, "Stain": 0, "Stain2": 0},
            "RFinger": {"ItemId": 0, "Crest": 0, "Apply": False, "ApplyStain": False,
                        "ApplyCrest": False, "Stain": 0, "Stain2": 0},
            "LFinger": {"ItemId": 0, "Crest": 0, "Apply": False, "ApplyStain": False,
                        "ApplyCrest": False, "Stain": 0, "Stain2": 0},
            "Hat": {"Show": True, "Apply": False},
            "VieraEars": {"Show": True, "Apply": False},
            "Visor": {"IsToggled": False, "Apply": False},
            "Weapon": {"Show": True, "Apply": False},
        },
        "Bonus": {
            "Glasses": {"ItemId": 0, "Apply": False},
        },
        "Customize": {},
        "Parameters": {},
        "Materials": {},
        "Mods": [],
        "Links": {"Before": "", "After": ""},
    }


def save_design(design: dict, dry_run: bool = False) -> str:
    """Speichert ein Design als JSON im Glamourer designs/-Verzeichnis.

    Args:
        design: Design-Dict
        dry_run: Wenn True, nur Pfad anzeigen ohne zu schreiben

    Returns:
        Pfad zur gespeicherten Datei
    """
    ensure_dirs()
    identifier = design["Identifier"]
    path = os.path.join(DESIGNS_DIR, f"{identifier}.json")

    if not dry_run:
        # Mit UTF-8 BOM schreiben (Glamourer erwartet das)
        with open(path, "wb") as f:
            f.write(b"\xef\xbb\xbf")
            json_str = json.dumps(design, indent=2, ensure_ascii=False)
            f.write(json_str.encode("utf-8"))
    return path


def load_design(identifier: str) -> Optional[dict]:
    """Lädt ein Design anhand seiner UUID."""
    path = os.path.join(DESIGNS_DIR, f"{identifier}.json")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        raw = f.read()
    return json.loads(raw.decode("utf-8-sig"))


def list_designs() -> list[dict]:
    """Listet alle Designs im Glamourer-Verzeichnis."""
    ensure_dirs()
    designs = []
    for fname in os.listdir(DESIGNS_DIR):
        if fname.endswith(".json") and not fname.endswith(".bak"):
            path = os.path.join(DESIGNS_DIR, fname)
            # Null-Byte-Dateien überspringen
            if os.path.getsize(path) < 50:
                continue
            try:
                with open(path, "rb") as f:
                    raw = f.read()
                d = json.loads(raw.decode("utf-8-sig"))
                designs.append(d)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
    return designs


def design_status() -> dict:
    """Zeigt Status aller Designs an."""
    designs = list_designs()
    bak_count = len([f for f in os.listdir(DESIGNS_DIR)
                     if f.endswith(".bak") and os.path.getsize(
                     os.path.join(DESIGNS_DIR, f)) > 50])

    automation_exists = os.path.exists(AUTOMATION_FILE)
    automation_rules = 0
    if automation_exists:
        with open(AUTOMATION_FILE, "rb") as f:
            auto = json.loads(f.read().decode("utf-8-sig"))
        automation_rules = sum(len(a.get("Designs", [])) for a in auto.get("Data", []))

    return {
        "designs": designs,
        "total": len(designs),
        "bak_files": bak_count,
        "automation_rules": automation_rules,
        "designs_dir": DESIGNS_DIR,
        "automation_file": AUTOMATION_FILE,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Glamourer Design Generator")
    parser.add_argument("action", nargs="?", choices=["list", "create", "status"],
                        default="status", help="Aktion")
    parser.add_argument("--name", help="Design-Name (für create)")
    parser.add_argument("--job", help="Job-Kürzel (für create, z.B. PLD)")
    parser.add_argument("--dry-run", action="store_true", help="Nur anzeigen")

    args = parser.parse_args()

    if args.action == "status":
        status = design_status()
        print(f"Glamourer Designs: {status['total']}")
        print(f"  .bak-Dateien: {status['bak_files']}")
        print(f"  Automation-Regeln: {status['automation_rules']}")
        print(f"  designs/: {status['designs_dir']}")
        for d in status['designs']:
            mods = len(d.get("Mods", []))
            eq_applied = sum(1 for s, v in d.get("Equipment", {}).items()
                           if isinstance(v, dict) and v.get("Apply"))
            print(f"  • {d['Name'][:40]:40s} [{d['Identifier'][:8]}…] "
                  f"mods={mods} eq_slots={eq_applied}")

    elif args.action == "list":
        designs = list_designs()
        if not designs:
            print("❌ Keine Designs gefunden")
        else:
            print(f"Gefunden: {len(designs)} Designs")
            for d in designs:
                print(f"  • {d['Name'][:45]:45s}  {d['Identifier']}")

    elif args.action == "create":
        if not args.name:
            print("❌ --name ist erforderlich")
            exit(1)
        design = make_design(args.name)
        path = save_design(design, dry_run=args.dry_run)
        if args.dry_run:
            print(f"☐ Würde speichern nach: {path}")
        else:
            print(f"✅ Design '{args.name}' erstellt: {path}")
            print(f"   UUID: {design['Identifier']}")
