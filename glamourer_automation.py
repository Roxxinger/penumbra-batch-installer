"""
glamourer_automation.py — Glamourer Automation-Regeln verwalten

Liest/schreibt die automation.json und erstellt Job→Design-Verknüpfungen.
"""

import json
import os
import shutil
from typing import Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
GLAMOURER_DIR = os.path.join(APPDATA, "XIVLauncher", "pluginConfigs", "Glamourer")
AUTOMATION_FILE = os.path.join(GLAMOURER_DIR, "automation.json")

# JobGroup Map (Glamourer verwendet Gruppen, nicht einzelne Job-IDs)
# 1 = Tanks (PLD, WAR, DRK, GNB)
# 2 = Melee DPS (MNK, DRG, NIN, SAM, RPR, VPR)
# 3 = Physical Ranged (BRD, MCH, DNC)
# 4 = Magical Ranged (BLM, SMN, RDM, PCT)
# 5 = Healers (WHM, SCH, AST, SGE)
# 6 = Crafters (CRP, BSM, ARM, GSM, LTW, WVR, ALC, CUL)
# 7 = Gatherers (MIN, BTN, FSH)
#
# Für einzelne Jobs: Type=31, Conditions: {"JobGroup": <job_id>} und Gearset=-1
JOB_TO_GROUP = {
    19: 1, 20: 2, 21: 1, 22: 2, 23: 3, 24: 5, 25: 4, 26: 4,
    27: 4, 28: 5, 29: 2, 30: 2, 31: 3, 32: 1, 33: 5, 34: 2,
    35: 4, 36: 6, 37: 1, 38: 3, 39: 2, 40: 5, 41: 2, 42: 4,
}


def load_automation() -> dict:
    """Lädt die Glamourer automation.json."""
    if not os.path.exists(AUTOMATION_FILE):
        return {"Version": 1, "Data": []}
    with open(AUTOMATION_FILE, "rb") as f:
        raw = f.read()
    return json.loads(raw.decode("utf-8-sig"))


def save_automation(auto: dict):
    """Speichert automation.json (mit Backup)."""
    # Backup erstellen
    if os.path.exists(AUTOMATION_FILE):
        bak = AUTOMATION_FILE + ".bak"
        if not os.path.exists(bak):
            shutil.copy2(AUTOMATION_FILE, bak)
            print(f"  Backup: {bak}")

    with open(AUTOMATION_FILE, "wb") as f:
        f.write(b"\xef\xbb\xbf")
        json_str = json.dumps(auto, indent=2, ensure_ascii=False)
        f.write(json_str.encode("utf-8"))
    print(f"✅ automation.json gespeichert ({len(auto.get('Data', []))} automation sets)")


def design_name_to_folder(design_name: str) -> str:
    """Erzeugt einen Ordnernamen aus einem Design-Namen (für //Random)."""
    return design_name.replace(" ", "_").replace("/", "_")[:50]


def add_automation_rule(
    player_name: str,
    world_id: int,
    design_identifier: str,
    job_id: int,
    set_name: str = "Auto-Glamour",
    reset_on_redraw: bool = True,
    enabled: bool = True,
):
    """Fügt eine Automation-Regel hinzu.

    Args:
        player_name: Charaktername (z.B. "Roxxinger Balboa")
        world_id: HomeWorld-ID (z.B. 400)
        design_identifier: UUID des Designs
        job_id: Job-ID (CLASS_JOB)
        set_name: Name des Automation-Sets
    """
    auto = load_automation()

    # Prüfen ob bereits ein Automation-Set für diesen Spieler existiert
    existing_set = None
    for ds in auto["Data"]:
        ident = ds.get("Identifier", {})
        if (ident.get("Type") == "Player" and
                ident.get("PlayerName") == player_name and
                ident.get("HomeWorld") == world_id and
                ds.get("Name") == set_name):
            existing_set = ds
            break

    if existing_set is None:
        # Neues Automation-Set erstellen
        existing_set = {
            "Name": set_name,
            "Identifier": {
                "Type": "Player",
                "PlayerName": player_name,
                "HomeWorld": world_id,
            },
            "Enabled": enabled,
            "Priority": 0,
            "BaseState": "Game",
            "ResetTemporarySettings": "True",
            "Designs": [],
        }
        auto["Data"].append(existing_set)

    # Prüfen ob bereits eine Regel für diesen Job existiert
    for rule in existing_set.get("Designs", []):
        conditions = rule.get("Conditions", {})
        if conditions.get("JobGroup") == job_id and conditions.get("Gearset") == -1:
            print(f"⚠️  Regel für Job {job_id} existiert bereits → überspringe")
            return

    # Neue Regel hinzufügen
    rule = {
        "Design": design_identifier,
        "Type": 1,  # Apply (kein Random)
        "Conditions": {
            "Gearset": -1,
            "JobGroup": job_id,
        },
        "Restrictions": "",
        "ResetOnRedraw": reset_on_redraw,
    }
    existing_set["Designs"].append(rule)
    save_automation(auto)
    print(f"✅ Automation-Regel hinzugefügt: Job {job_id} → Design {design_identifier[:8]}…")


def remove_automation_rule(player_name: str, world_id: int, job_id: int):
    """Entfernt eine Automation-Regel für einen bestimmten Job."""
    auto = load_automation()
    changed = False
    for ds in auto["Data"]:
        ident = ds.get("Identifier", {})
        if (ident.get("Type") != "Player" or
                ident.get("PlayerName") != player_name or
                ident.get("HomeWorld") != world_id):
            continue
        before = len(ds.get("Designs", []))
        ds["Designs"] = [r for r in ds.get("Designs", [])
                         if r.get("Conditions", {}).get("JobGroup") != job_id]
        if len(ds["Designs"]) != before:
            changed = True
            print(f"  ✅ Regel für Job {job_id} entfernt")

    if changed:
        save_automation(auto)


def list_rules() -> list[dict]:
    """Listet alle Automation-Regeln auf."""
    auto = load_automation()
    rules = []
    for ds in auto.get("Data", []):
        ident = ds.get("Identifier", {})
        for design in ds.get("Designs", []):
            cond = design.get("Conditions", {})
            rules.append({
                "set_name": ds.get("Name", "?"),
                "player": ident.get("PlayerName", "?"),
                "world": ident.get("HomeWorld", 0),
                "design": design.get("Design", "?"),
                "type": design.get("Type", 0),
                "job_group": cond.get("JobGroup", -1),
                "enabled": ds.get("Enabled", True),
            })
    return rules


if __name__ == "__main__":
    import argparse
    from gearset_config import CLASS_JOBS

    parser = argparse.ArgumentParser(description="Glamourer Automation")
    parser.add_argument("action", nargs="?", choices=["list", "add", "remove"],
                        default="list", help="Aktion")
    parser.add_argument("--player", default="Roxxinger Balboa",
                        help="Charaktername (default: Roxxinger Balboa)")
    parser.add_argument("--world", type=int, default=400,
                        help="HomeWorld-ID (default: 400 = Twintania)")
    parser.add_argument("--job", help="Job-Kürzel (z.B. PLD)")
    parser.add_argument("--design", help="Design-UUID oder Name")

    args = parser.parse_args()

    if args.action == "list":
        rules = list_rules()
        if not rules:
            print("❌ Keine Automation-Regeln gefunden")
        else:
            print(f"Gefunden: {len(rules)} Regel(n)")
            for r in rules:
                job_name = CLASS_JOBS.get(r["job_group"], f"Group {r['job_group']}")
                status = "✅" if r["enabled"] else "⏸️"
                print(f"  {status} {r['player']:20s} {job_name:5s} → "
                      f"{r['design'][:36]}")

    elif args.action == "add":
        if not args.job or not args.design:
            print("❌ --job und --design sind erforderlich")
            exit(1)
        from gearset_config import JOB_NAMES
        job_id = JOB_NAMES.get(args.job.upper())
        if job_id is None:
            print(f"❌ Unbekannter Job '{args.job}'")
            exit(1)
        add_automation_rule(args.player, args.world, args.design, job_id)

    elif args.action == "remove":
        if not args.job:
            print("❌ --job ist erforderlich")
            exit(1)
        from gearset_config import JOB_NAMES
        job_id = JOB_NAMES.get(args.job.upper())
        if job_id is None:
            print(f"❌ Unbekannter Job '{args.job}'")
            exit(1)
        remove_automation_rule(args.player, args.world, job_id)
