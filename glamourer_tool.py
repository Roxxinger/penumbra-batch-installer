"""
glamourer_tool.py — Glamourer Automation CLI

Einheitliches Tool für alle Glamourer-Design-Operationen.

Verwendung:
  python glamourer_tool.py status                    # Alles auf einen Blick
  python glamourer_tool.py list-mods                 # Penumbra-Mods anzeigen
  python glamourer_tool.py create <name> [--job PLD] # Leeres Design anlegen
  python glamourer_tool.py capture <name>            # Aktuelle Mods als Design speichern
  python glamourer_tool.py link <design> <job>       # Design mit Job verknüpfen
  python glamourer_tool.py add-gearset <name> <job>  # Gearset zur Config hinzufügen
  python glamourer_tool.py list-designs              # Alle Designs anzeigen
  python glamourer_tool.py list-rules                # Automation-Regeln anzeigen
"""

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def cmd_status(args):
    """Kompletter Status: Designs, Mods, Automation."""
    from glamourer_designer import design_status
    from glamourer_capture import get_penumbra_mods
    from gearset_config import load_config, CLASS_JOBS

    # Penumbra
    mods = get_penumbra_mods()
    print(f"📦 Penumbra: {len(mods)} Mods installiert")

    # Glamourer Designs
    status = design_status()
    print(f"\n🎨 Glamourer Designs: {status['total']}")
    for d in status['designs']:
        mods_count = len(d.get("Mods", []))
        eq_apply = sum(1 for s, v in d.get("Equipment", {}).items()
                       if isinstance(v, dict) and v.get("Apply"))
        quick = "⚡" if d.get("QuickDesign") else "📋"
        print(f"  {quick} {d['Name'][:40]:40s} [{d['Identifier'][:8]}…] "
              f"mods={mods_count} eq={eq_apply}")

    # Automation
    from glamourer_automation import list_rules
    rules = list_rules()
    print(f"\n⚙️  Automation-Regeln: {len(rules)}")
    for r in rules:
        job_name = CLASS_JOBS.get(r["job_group"], f"?{r['job_group']}")
        print(f"  {'✅' if r['enabled'] else '⏸️'} {r['player']:20s} "
              f"{job_name:5s} → {r['design'][:36]}")

    # Gearset Config
    cfg = load_config()
    gearset_count = len(cfg.get("gearsets", []))
    print(f"\n📋 Gearset-Config: {gearset_count} gear sets")
    for gs in cfg.get("gearsets", []):
        job_name = CLASS_JOBS.get(gs["job_id"], "?")
        print(f"  • {gs['name']:30s} → {job_name:4s}")


def cmd_create(args):
    """Leeres Design anlegen."""
    from glamourer_designer import make_design, save_design
    design = make_design(args.name)
    path = save_design(design, dry_run=args.dry_run)
    if args.dry_run:
        print(f"☐ Würde erstellen: {path}")
    else:
        print(f"✅ Design '{args.name}' erstellt")
        print(f"   UUID: {design['Identifier']}")

        # Optional gleich mit Job verknüpfen
        if args.job:
            from gearset_config import JOB_NAMES
            from glamourer_automation import add_automation_rule
            job_id = JOB_NAMES.get(args.job.upper())
            if job_id is not None:
                add_automation_rule(
                    args.player or "Roxxinger Balboa",
                    args.world or 400,
                    design["Identifier"],
                    job_id,
                )


def cmd_capture(args):
    """Aktuellen Mod-Zustand als Design speichern + optional verlinken."""
    from penumbra_api import require_api
    require_api()
    from glamourer_capture import capture_current_as_design
    design = capture_current_as_design(args.name, dry_run=args.dry_run)
    if design and not args.dry_run and args.job:
        from gearset_config import JOB_NAMES
        from glamourer_automation import add_automation_rule
        job_id = JOB_NAMES.get(args.job.upper())
        if job_id is not None:
            add_automation_rule(
                args.player or "Roxxinger Balboa",
                args.world or 400,
                design["Identifier"],
                job_id,
            )


def cmd_link(args):
    """Design mit Job verknüpfen."""
    from gearset_config import JOB_NAMES
    from glamourer_automation import add_automation_rule

    job_id = JOB_NAMES.get(args.job.upper())
    if job_id is None:
        print(f"❌ Unbekannter Job '{args.job}'")
        print(f"  Verfügbar: {', '.join(sorted(JOB_NAMES.keys()))}")
        exit(1)

    add_automation_rule(
        args.player or "Roxxinger Balboa",
        args.world or 400,
        args.design,
        job_id,
    )


def cmd_add_gearset(args):
    """Gearset zur Config hinzufügen."""
    from gearset_config import add_gearset, JOB_NAMES
    job_id = JOB_NAMES.get(args.job.upper())
    if job_id is None:
        print(f"❌ Unbekannter Job '{args.job}'")
        exit(1)
    add_gearset(args.name, job_id)


def cmd_list_mods(args):
    """Penumbra-Mods auflisten."""
    from glamourer_capture import get_penumbra_mods
    mods = get_penumbra_mods()
    if not mods:
        print("❌ Keine Mods (Penumbra läuft?)")
        print("  Stelle sicher dass FFXIV mit Penumbra läuft")
    else:
        print(f"📦 Penumbra Mods ({len(mods)}):")
        for m in mods:
            print(f"  {m['Name'][:50]:50s}")


def cmd_list_designs(args):
    """Alle Glamourer Designs anzeigen."""
    from glamourer_designer import list_designs
    designs = list_designs()
    if not designs:
        print("❌ Keine Designs gefunden")
    else:
        print(f"🎨 {len(designs)} Designs:")
        for d in designs:
            mods = len(d.get("Mods", []))
            eq = sum(1 for s, v in d.get("Equipment", {}).items()
                     if isinstance(v, dict) and v.get("Apply"))
            quick = "⚡" if d.get("QuickDesign") else "📋"
            print(f"  {quick} {d['Name'][:45]:45s}  {d['Identifier']}  "
                  f"({mods} mods, {eq} eq)")


def cmd_list_rules(args):
    """Automation-Regeln anzeigen."""
    from gearset_config import CLASS_JOBS
    from glamourer_automation import list_rules
    rules = list_rules()
    if not rules:
        print("❌ Keine Automation-Regeln")
    else:
        print(f"⚙️  {len(rules)} Regel(n):")
        for r in rules:
            job_name = CLASS_JOBS.get(r["job_group"], f"?{r['job_group']}")
            status = "✅" if r["enabled"] else "⏸️"
            print(f"  {status} {r['player']:20s} {job_name:5s} → {r['design'][:36]}")


def main():
    parser = argparse.ArgumentParser(
        description="🎨 Glamourer Automation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--player", default="Roxxinger Balboa",
                        help="Charaktername")
    parser.add_argument("--world", type=int, default=400,
                        help="HomeWorld-ID")
    parser.add_argument("--dry-run", action="store_true",
                        help="Nur simulieren, nichts schreiben")

    sub = parser.add_subparsers(dest="command", help="Befehl")

    p_status = sub.add_parser("status", help="Kompletter Status")
    p_status.set_defaults(func=cmd_status)

    p_list_mods = sub.add_parser("list-mods", help="Penumbra-Mods anzeigen")
    p_list_mods.set_defaults(func=cmd_list_mods)

    p_create = sub.add_parser("create", help="Leeres Design anlegen")
    p_create.add_argument("name", help="Design-Name")
    p_create.add_argument("--job", help="Job zur automatischen Verknüpfung")
    p_create.set_defaults(func=cmd_create)

    p_capture = sub.add_parser("capture", help="Aktuelle Mods als Design speichern")
    p_capture.add_argument("name", help="Design-Name")
    p_capture.add_argument("--job", help="Job zur automatischen Verknüpfung")
    p_capture.set_defaults(func=cmd_capture)

    p_link = sub.add_parser("link", help="Design mit Job verknüpfen")
    p_link.add_argument("design", help="Design-UUID")
    p_link.add_argument("job", help="Job-Kürzel (z.B. PLD)")
    p_link.set_defaults(func=cmd_link)

    p_gearset = sub.add_parser("add-gearset", help="Gearset zur Config hinzufügen")
    p_gearset.add_argument("name", help="Gearset-Name")
    p_gearset.add_argument("job", help="Job-Kürzel")
    p_gearset.set_defaults(func=cmd_add_gearset)

    p_designs = sub.add_parser("list-designs", help="Alle Designs anzeigen")
    p_designs.set_defaults(func=cmd_list_designs)

    p_rules = sub.add_parser("list-rules", help="Automation-Regeln anzeigen")
    p_rules.set_defaults(func=cmd_list_rules)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
