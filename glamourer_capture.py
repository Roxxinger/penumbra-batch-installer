"""
glamourer_capture.py — Erfasst aktuellen Zustand von Penumbra-Mods

Liest die aktuell aktiven Penumbra-Mods über die HTTP-API
und speichert sie in einem Glamourer-Design.
"""

import json
import os
import sys
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

PENUMBRA_API = "http://localhost:42069"

APPDATA = os.environ.get("APPDATA", os.path.expanduser("~"))
GLAMOURER_DIR = os.path.join(APPDATA, "XIVLauncher", "pluginConfigs", "Glamourer")
DESIGNS_DIR = os.path.join(GLAMOURER_DIR, "designs")


def get_penumbra_mods() -> list[dict]:
    """Holt alle Penumbra-Mods über die HTTP-API.

    Returns:
        Liste von Mod-Infos: [{"Name": "...", "Directory": "..."}]
    """
    try:
        req = urllib.request.Request(f"{PENUMBRA_API}/api/mods")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, ConnectionRefusedError,
            json.JSONDecodeError, TimeoutError) as e:
        print(f"⚠️  Penumbra API nicht erreichbar: {e}")
        return []
    except Exception as e:
        print(f"⚠️  Fehler bei Penumbra API: {e}")
        return []

    # Format: dict[str, str] oder list[str]
    if isinstance(data, dict):
        return [{"Name": v, "Directory": k} for k, v in data.items()]
    elif isinstance(data, list):
        return [{"Name": str(item), "Directory": str(item)} for item in data]
    return []


def capture_current_as_design(
    design_name: str,
    identifier: str = None,
    dry_run: bool = False,
) -> dict | None:
    """Erfasst aktuellen Penumbra-Mod-Zustand und speichert als Design.

    Args:
        design_name: Name des zu erstellenden Designs
        identifier: UUID (wird generiert wenn None)
        dry_run: Wenn True, nichts speichern

    Returns:
        Design-Dict oder None bei Fehler
    """
    from glamourer_designer import make_design, save_design, new_uuid

    mods = get_penumbra_mods()
    if not mods:
        print("⚠️  Keine Mods von Penumbra-API erhalten")
        return None

    print(f"  Gefundene Mods: {len(mods)}")

    design = make_design(design_name, identifier=identifier)
    design["Mods"] = [
        {
            "Name": m["Name"],
            "Directory": m["Directory"],
            "Enabled": True,  # Alle aktuellen Mods als aktiv markieren
        }
        for m in mods
    ]
    design["LastEdit"] = design["CreationDate"]

    path = save_design(design, dry_run=dry_run)
    if dry_run:
        print(f"  ☐ Würde speichern als: {path}")
    else:
        print(f"  ✅ Design gespeichert: {path}")
        print(f"  UUID: {design['Identifier']}")
        print(f"  Mods: {len(design['Mods'])}")

    return design


def add_mod_to_design(identifier: str, mod_name: str, mod_dir: str) -> bool:
    """Fügt einen Mod zu einem bestehenden Design hinzu."""
    from glamourer_designer import load_design, save_design
    design = load_design(identifier)
    if design is None:
        print(f"❌ Design {identifier} nicht gefunden")
        return False

    # Prüfen ob Mod bereits existiert
    for m in design.get("Mods", []):
        if m.get("Directory") == mod_dir:
            print(f"  ⚠️  Mod '{mod_name}' bereits im Design")
            return False

    design.setdefault("Mods", []).append({
        "Name": mod_name,
        "Directory": mod_dir,
        "Enabled": True,
    })
    design["QuickDesign"] = False  # Nicht mehr leer
    save_design(design)
    print(f"  ✅ Mod '{mod_name}' zu Design hinzugefügt")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Penumbra Mod Capture")
    parser.add_argument("action", nargs="?", choices=["capture", "list-mods"],
                        default="capture", help="Aktion")
    parser.add_argument("--name", help="Design-Name")
    parser.add_argument("--dry-run", action="store_true", help="Nur simulieren")

    args = parser.parse_args()

    if args.action == "list-mods":
        mods = get_penumbra_mods()
        if not mods:
            print("❌ Keine Mods (Penumbra läuft?)")
        else:
            print(f"Penumbra Mods ({len(mods)}):")
            for m in mods:
                print(f"  • {m['Name'][:50]:50s} [{m['Directory'][:30]}]")

    elif args.action == "capture":
        if not args.name:
            print("❌ --name ist erforderlich")
            exit(1)
        capture_current_as_design(args.name, dry_run=args.dry_run)
