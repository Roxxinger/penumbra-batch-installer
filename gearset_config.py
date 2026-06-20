"""
gearset_config.py — Gear-Set-Konfiguration für Glamourer-Design-Automation

Liest/schreibt eine einfache Konfigurationsdatei mit Gear-Set-Name → Job-Zuordnung.
Kann später durch GEARSET.DAT-Parser ersetzt werden.
"""

import json
import os
from typing import Dict, List, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "gearsets.json")

CLASS_JOBS = {
    0: "ADV", 1: "GLA", 2: "PGL", 3: "MRD", 4: "LNC", 5: "ARC",
    6: "CNJ", 7: "THM", 8: "CRP", 9: "BSM", 10: "ARM", 11: "GSM",
    12: "LTW", 13: "WVR", 14: "ALC", 15: "CUL", 16: "MIN", 17: "BTN",
    18: "FSH", 19: "PLD", 20: "MNK", 21: "WAR", 22: "DRG", 23: "BRD",
    24: "WHM", 25: "BLM", 26: "ACN", 27: "SMN", 28: "SCH", 29: "ROG",
    30: "NIN", 31: "MCH", 32: "DRK", 33: "AST", 34: "SAM", 35: "RDM",
    36: "BLU", 37: "GNB", 38: "DNC", 39: "RPR", 40: "SGE", 41: "VPR", 42: "PCT",
}

JOB_NAMES = {v: k for k, v in CLASS_JOBS.items()}
JOB_NAMES["ADV"] = 0
JOB_NAMES["CRP"] = 8


def default_config() -> dict:
    """Leere Konfiguration mit Job-ID-Map als Referenz."""
    return {
        "gearsets": [],
        "job_ids": CLASS_JOBS,
    }


def load_config() -> dict:
    """Lädt gearsets.json oder erstellt leere Konfig."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    cfg = default_config()
    save_config(cfg)
    return cfg


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print(f"✅ gearsets.json gespeichert ({len(cfg.get('gearsets', []))} gear sets)")


def add_gearset(name: str, job_id: int, items: Optional[Dict[str, int]] = None):
    """Fügt ein Gearset zur Config hinzu."""
    cfg = load_config()
    # Prüfen ob bereits vorhanden
    for gs in cfg["gearsets"]:
        if gs["name"] == name:
            print(f"⚠️  Gearset '{name}' existiert bereits, überspringe")
            return
    cfg["gearsets"].append({
        "name": name,
        "job_id": job_id,
        "items": items or {},
    })
    save_config(cfg)


def list_gearsets():
    """Listet alle konfigurierten Gear-Sets."""
    cfg = load_config()
    if not cfg["gearsets"]:
        print("❌ Keine Gear-Sets konfiguriert")
        print("  Füge welche hinzu mit: python gearset_config.py add <name> <job>")
        print(f"  Verfügbare Jobs: {', '.join(sorted(CLASS_JOBS.values()))}")
        return
    for gs in cfg["gearsets"]:
        job_name = CLASS_JOBS.get(gs["job_id"], "?")
        item_count = len(gs.get("items", {}))
        print(f"  {gs['name']:30s} → {job_name:4s} (ID {gs['job_id']:2d})  [{item_count} items]")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gear-Set-Konfiguration")
    parser.add_argument("action", nargs="?", choices=["list", "add"], default="list",
                        help="Aktion (default: list)")
    parser.add_argument("name", nargs="?", help="Gear-Set-Name")
    parser.add_argument("job", nargs="?", help="Job-Name (z.B. PLD, WAR, BLM)")

    args = parser.parse_args()

    if args.action == "list":
        list_gearsets()
        # Auch Penumbra-Mods anzeigen
        print(f"\nVerfügbare Jobs: {', '.join(sorted(CLASS_JOBS.values()))}")

    elif args.action == "add":
        if not args.name or not args.job:
            print("❌ Bitte Name und Job angeben: python gearset_config.py add <name> <job>")
            print(f"  Jobs: {', '.join(sorted(CLASS_JOBS.values()))}")
            exit(1)
        job_id = JOB_NAMES.get(args.job.upper())
        if job_id is None:
            print(f"❌ Unbekannter Job '{args.job}'")
            print(f"  Verfügbar: {', '.join(sorted(CLASS_JOBS.values()))}")
            exit(1)
        add_gearset(args.name, job_id)
