#!/usr/bin/env python3
"""
Penumbra Batch Installer v3 — API-basiert mit KI-gestützter Ordner-Zuweisung
via Dateipfad-Analyse im .pmp/.ttmp2.

Nutzung:
  python install_pmp_mod.py                          # scannt D:\Telegram Desktop
  python install_pmp_mod.py --dir "D:\pfad\zu\quelle"
  python install_pmp_mod.py --retry-failed
  python install_pmp_mod.py --list-only
"""

import os
import sys
import json
import hashlib
import subprocess
import tempfile
import urllib.request
import urllib.error
import time
import re
import argparse
import zipfile
from datetime import datetime
from pathlib import Path

# ─── Konfiguration ───────────────────────────────────────────────────────────

PENUMBRA_API = "http://localhost:42069/api"
SEVEN_ZIP = r"C:\Program Files\7-Zip\7z.exe"
HELPER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PenumbraHelper")

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "install_log.json")
HASH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "installed_hashes.txt")
PMP_HASH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "installed_pmp_hashes.txt")
TEMP_DIR_PARENT = r"D:\temp\penumbra_install"

JOBS_SHORT = {k.lower(): k for k in [
    "PLD","WAR","DRK","GNB","WHM","SCH","AST","SGE",
    "MNK","DRG","NIN","SAM","RPR","VPR",
    "BRD","MCH","DNC","BLM","SMN","RDM","PCT","BLU"
]}

# ─── Dateipfad → Kategorie ──────────────────────────────────────────────────
# Analyse der internen Dateipfade im .pmp (zip) für präzise Kategorisierung.

# Equipment-Slot-Namen basierend auf eXXXX-IDs
KNOWN_EQUIP_SLOTS = {
    # Head
    6015: "Gear/Slots/Head",  # Head (e.g., Emperor's Hat)
    6016: "Gear/Slots/Head",  # Head (variants)
    6017: "Gear/Slots/Head",
    6018: "Gear/Slots/Head",
    6019: "Gear/Slots/Head",
    6020: "Gear/Slots/Head",
    6021: "Gear/Slots/Head",
    6022: "Gear/Slots/Head",
    6023: "Gear/Slots/Head",
    6024: "Gear/Slots/Head",
    6025: "Gear/Slots/Head",
    6026: "Gear/Slots/Head",
    6027: "Gear/Slots/Head",
    6028: "Gear/Slots/Head",
    6029: "Gear/Slots/Head",
    6030: "Gear/Slots/Head",
    6031: "Gear/Slots/Head",
    6032: "Gear/Slots/Head",
    6033: "Gear/Slots/Head",
    6034: "Gear/Slots/Head",
    6035: "Gear/Slots/Head",
    6036: "Gear/Slots/Head",
    6037: "Gear/Slots/Head",
    6038: "Gear/Slots/Head",
    6039: "Gear/Slots/Head",
    6040: "Gear/Slots/Head",
    6041: "Gear/Slots/Head",
    6042: "Gear/Slots/Head",
    6043: "Gear/Slots/Head",
    6044: "Gear/Slots/Head",
    6045: "Gear/Slots/Head",
    6046: "Gear/Slots/Head",
    6047: "Gear/Slots/Head",
    6048: "Gear/Slots/Head",
    6049: "Gear/Slots/Head",
    6050: "Gear/Slots/Head",
    6051: "Gear/Slots/Head",
    6052: "Gear/Slots/Head",
    6053: "Gear/Slots/Head",
    6054: "Gear/Slots/Head",
    # Body/Chest (e02XX)
    6055: "Gear/Slots/Chest",
    6056: "Gear/Slots/Chest",
    6057: "Gear/Slots/Chest",
    6058: "Gear/Slots/Chest",
    6059: "Gear/Slots/Chest",
    6060: "Gear/Slots/Chest",
    6061: "Gear/Slots/Chest",
    # Hands (e03XX)
    6062: "Gear/Slots/Hands",
    6063: "Gear/Slots/Hands",
    6064: "Gear/Slots/Hands",
    6065: "Gear/Slots/Hands",
    # Legs (e04XX)
    6066: "Gear/Slots/Legs",
    6067: "Gear/Slots/Legs",
    6068: "Gear/Slots/Legs",
    6069: "Gear/Slots/Legs",
    # Feet (e05XX)
    6070: "Gear/Slots/Feet",
    6071: "Gear/Slots/Feet",
    # Ears (e06XX)
    6072: "Gear/Slots/Ears",
    6073: "Gear/Slots/Ears",
    6074: "Gear/Slots/Ears",
    # Neck (e07XX)
    6075: "Gear/Slots/Neck",
    6076: "Gear/Slots/Neck",
    # Wrists (e08XX)
    6077: "Gear/Slots/Wrists",
    6078: "Gear/Slots/Wrists",
    # Rings (e09XX)
    6079: "Gear/Slots/Rings",
    6080: "Gear/Slots/Rings",
    6081: "Gear/Slots/Rings",
    6082: "Gear/Slots/Rings",
    6083: "Gear/Slots/Rings",
    6084: "Gear/Slots/Rings",
    6085: "Gear/Slots/Rings",
    6086: "Gear/Slots/Rings",
    6087: "Gear/Slots/Rings",
    6088: "Gear/Slots/Rings",
    6089: "Gear/Slots/Rings",
    6090: "Gear/Slots/Rings",
    6091: "Gear/Slots/Rings",
    6092: "Gear/Slots/Rings",
    6093: "Gear/Slots/Rings",
    6094: "Gear/Slots/Rings",
}

# Bekannte Job-Waffen eIDs (e09XX-e12XX Bereich, je nach Job)
JOB_WEAPON_IDS = {
    "PLD": (6061, 30000, 30001, 30002, 30003, 30004, 30005),
    "WAR": (6062, 30010, 30011, 30012, 30013, 30014, 30015),
    "DRK": (6063, 30020, 30021, 30022, 30023, 30024, 30025),
    "GNB": (6064, 30030, 30031, 30032, 30033, 30034, 30035),
    "WHM": (6065, 30040, 30041, 30042, 30043, 30044, 30045),
    "SCH": (6066, 30050, 30051, 30052, 30053, 30054, 30055),
    "AST": (6067, 30060, 30061, 30062, 30063, 30064, 30065),
    "SGE": (6068, 30070, 30071, 30072, 30073, 30074, 30075),
    "MNK": (6069, 30080, 30081, 30082, 30083, 30084, 30085),
    "DRG": (6070, 30090, 30091, 30092, 30093, 30094, 30095),
    "NIN": (6071, 30100, 30101, 30102, 30103, 30104, 30105),
    "SAM": (6072, 30110, 30111, 30112, 30113, 30114, 30115),
    "RPR": (6073, 30120, 30121, 30122, 30123, 30124, 30125),
    "VPR": (6074, 30130, 30131, 30132, 30133, 30134, 30135),
    "BRD": (6075, 30140, 30141, 30142, 30143, 30144, 30145),
    "MCH": (6076, 30150, 30151, 30152, 30153, 30154, 30155),
    "DNC": (6077, 30160, 30161, 30162, 30163, 30164, 30165),
    "BLM": (6078, 30170, 30171, 30172, 30173, 30174, 30175),
    "SMN": (6079, 30180, 30181, 30182, 30183, 30184, 30185),
    "RDM": (6080, 30190, 30191, 30192, 30193, 30194, 30195),
    "PCT": (6081, 30200, 30201, 30202, 30203, 30204, 30205),
    "BLU": (6082, 30210, 30211, 30212, 30213, 30214, 30215),
}

# Bekannte Body-Types für Gear-Filter
BODY_TYPES = {
    "lavabod": ["lavabod", "lb", "lb+", "lavabod+", "lava bod"],
    "rue": ["rue", "rue+", "rue plus", "larue"],
    "skip": ["bibo", "bibo+", "yab", "yab+", "yabplus", "yet another body",
             "tre", "tre+", "skelomae", "skelomae+",
             "muse", "muse+"],
}

# Version-Patterns in Dateinamen
VERSION_PATTERNS = [
    (r'\[(\d+\.\d+(?:\.\d+)?(?:[a-z])?)\]\s*[-–—]?\s*', True),   # [1.0.4] - or [1.2.0] - 
    (r'_(\d+_\d+(?:_\d+)?[a-z]?)_', True),                         # _1_0_5b_
    (r'[\(\[]?v?(\d+\.\d+(?:\.\d+)?[a-z]?)[\)\]]?\s*[-–—]?\s*', False), # v1.0.4, 1.0.5b (generic)
]
JOB_KEYWORDS = {
    "PLD": ["pld", "paladin", "holy", "oath", "sword oath", "shield oath"],
    "WAR": ["war", "warrior", "beast", "inner release", "fell cleave", "chaotic cyclone"],
    "DRK": ["drk", "dark knight", "darkness", "shadow", "flood", "edge", "bloodspiller"],
    "GNB": ["gnb", "gunbreaker", "gunblade", "continuation", "rough divide"],
    "WHM": ["whm", "white mage", "white", "healing", "lily", "heal"],
    "SCH": ["sch", "scholar", "fairy", "seraph", "deployment", "adlo"],
    "AST": ["ast", "astrologian", "astral", "cards", "divination", "draw"],
    "SGE": ["sge", "sage", "nouliths", "eukrasia", "dyskrasia"],
    "MNK": ["mnk", "monk", "fist", "chakra", "bootshine", "perfect balance"],
    "DRG": ["drg", "dragoon", "dragon", "jump", "heavens", "thrust"],
    "NIN": ["nin", "ninja", "dagger", "mudra", "raijin", "suiton", "huton"],
    "SAM": ["sam", "samurai", "katana", "iaijutsu", "midare", "higanbana", "kenki"],
    "RPR": ["rpr", "reaper", "scythe", "avatar", "lemure", "void", "soul"],
    "VPR": ["vpr", "viper", "dual blades", "rattling coil", "twinfang"],
    "BRD": ["brd", "bard", "bow", "song", "apex", "ballad", "minne"],
    "MCH": ["mch", "machinist", "gun", "drill", "chainsaw", "automaton", "queen"],
    "DNC": ["dnc", "dancer", "chakram", "fan dance", "cascade", "saber"],
    "BLM": ["blm", "black mage", "fire", "flare", "foul", "xenoglossy", "despair"],
    "SMN": ["smn", "summoner", "primal", "bahamut", "phoenix", "carbuncle", "garuda", "titan", "ifrit"],
    "RDM": ["rdm", "red mage", "rapier", "verfire", "verthunder", "scorch", "resolution"],
    "PCT": ["pct", "pictomancer", "paint", "canvas", "moogle", "madeen", "pom"],
    "BLU": ["blu", "blue mage", "spell", "mimicry"],
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def compute_hash(filepath):
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_hash_log():
    if not os.path.isfile(HASH_FILE):
        return set()
    with open(HASH_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())


def save_hash(h):
    with open(HASH_FILE, "a") as f:
        f.write(f"{h}\n")


def load_pmp_hashes():
    if not os.path.isfile(PMP_HASH_FILE):
        return set()
    with open(PMP_HASH_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())


def save_pmp_hash(h):
    with open(PMP_HASH_FILE, "a") as f:
        f.write(f"{h}\n")


def normalize_mod_name(name):
    """Normalisiert Mod-Namen für Duplikatserkennung + Gruppierung."""
    n = name.lower().strip()
    # (2), (3) etc. entfernen
    n = re.sub(r'\s*\(\d+\)\s*$', '', n)
    # Version-Patterns entfernen: 1.0, 1.0.1, 1.0.5b, v2, etc.
    n = re.sub(r'\s*v?\d+(?:\.\d+)*(?:[a-z])?\s*$', ' ', n)
    # Mid-name version patterns like "Package 1.0.5" → "Package"
    n = re.sub(r'\s+v?\d+(?:\.\d+)*(?:[a-z])?\s*[-,]?\s*', ' ', n)
    # Spezielle Zeichen normalisieren
    n = re.sub(r'[\[\]\(\)]', '', n)
    # Unicode-Normalisierung
    import unicodedata
    n = unicodedata.normalize('NFKD', n)
    n = re.sub(r'[^a-z0-9\s\-_]', '', n).strip()
    # Mehrfach-Leerzeichen komprimieren
    n = re.sub(r'\s+', ' ', n)
    # Numerische Suffixe entfernen (damit "package 10" = "package 105")
    # Aber nur wenn sie als Versionsnummer erkennbar sind (1-3 Ziffern mit optionalem Punkt)
    n = re.sub(r'\s+\d{1,3}(?:\.\d{1,3}){0,2}[a-z]?\s*$', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def is_mod_installed(display_name, existing_mods):
    """Prüft ob ein Mod bereits installiert ist (via API)."""
    needle = normalize_mod_name(display_name)
    if not needle or len(needle) < 3:
        return False
    for existing_name in existing_mods.values():
        haystack = normalize_mod_name(existing_name)
        # Exakter Match
        if needle == haystack:
            return True
        # Einer enthält den anderen (min 5 chars)
        if len(needle) >= 5 and len(haystack) >= 5:
            if needle in haystack or haystack in needle:
                return True
    return False


def parse_version_from_name(name):
    """Extrahiert Version (major, minor, patch, suffix) aus Dateinamen."""
    base = os.path.splitext(os.path.basename(name))[0]
    for pattern, anchored in VERSION_PATTERNS:
        m = re.search(pattern, base)
        if m:
            ver_str = m.group(1).replace('_', '.')
            # Parse: 1.0.5b → (1, 0, 5, 'b')
            parts = re.findall(r'\d+|[a-z]+', ver_str)
            nums = []
            suffix = ''
            for p in parts:
                if p.isdigit():
                    nums.append(int(p))
                else:
                    suffix = p
            # Auffüllen auf 3 Nummern + suffix
            while len(nums) < 3:
                nums.append(0)
            return tuple(nums[:3]), suffix, m
    return (0, 0, 0), '', None


def dedup_archives_by_hash(archives):
    """
    Entfernt exakte Duplikate (gleicher MD5-Hash).
    Gibt (unique_list, removed_count) zurück.
    """
    seen = {}
    unique = []
    removed = 0
    for a in sorted(archives):
        h = compute_hash(a)
        if h in seen:
            log(f"  ⏭️  Doppelt (gleicher Hash): {os.path.basename(a)}")
            removed += 1
        else:
            seen[h] = a
            unique.append(a)
    return unique, removed


def get_base_mod_name(name):
    """Entfernt Version aus Dateinamen → Gruppen-Key für Deduplizierung."""
    base = os.path.splitext(os.path.basename(name))[0]
    # (2), (3) etc. Kopien entfernen
    base = re.sub(r'\s*\(\d+\)\s*$', '', base)
    # Unterstriche durch Leerzeichen ersetzen für konsistentes Matching
    base = base.replace('_', ' ')
    # Version-Patterns entfernen
    for pattern, anchored in VERSION_PATTERNS:
        pattern_clean = pattern.replace('_', '[ _]') if '_' in pattern else pattern
        try:
            base = re.sub(pattern_clean, ' ', base, count=1)
        except:
            base = re.sub(pattern, ' ', base, count=1)
    # Klammern mit Tags entfernen: [Challenge], [Rumi, Mira, Zoey], etc.
    base = re.sub(r'\[(?:Challenge|Rumi|Mira|Zoey|NSFW)\].*$', '', base, flags=re.IGNORECASE)
    base = re.sub(r'\s*\(\d+\)\s*', '', base)
    base = re.sub(r'\s*[-–—]\s*[A-Za-z]+.*$', '', base)  # remove artist
    base = re.sub(r'\s+', ' ', base).strip()
    return base.lower()


def dedup_archives_by_version(archives):
    """
    Gruppiert Archive nach Basis-Name, behält nur die höchste Version pro Gruppe.
    Gibt (final_list, skipped_count) zurück.
    """
    groups = {}  # base_name → [(version_tuple, suffix, full_path)]
    
    for a in archives:
        base_key = get_base_mod_name(a)
        nums, suffix, m = parse_version_from_name(a)
        
        if base_key not in groups:
            groups[base_key] = []
        groups[base_key].append((nums, suffix, a))
    
    final = []
    skipped = 0
    for base_key, items in groups.items():
        if len(items) == 1:
            final.append(items[0][2])
            continue
        
        # Sortieren: Version DESC, dann suffix DESC
        def sort_key(item):
            nums, suffix, path = item
            return (nums[0], nums[1], nums[2], suffix or '')
        
        items.sort(key=sort_key, reverse=True)
        final.append(items[0][2])  # höchste Version
        skipped += len(items) - 1
        log(f"  📌 '{base_key}' → {len(items)} Versionen, neueste: {os.path.basename(items[0][2])}")
    
    return final, skipped


def is_gear_for_lb_rue(mod_name, archive_name, description=""):
    """
    Prüft, ob ein Gear-Mod nur für Lavabod/Rue ausgelegt ist.
    Gibt True zurück wenn OK (keine Einschränkung, oder LB/Rue).
    Gibt False zurück wenn für anderen Body-Typ (Bibo, YAB, etc.)
    """
    text = f"{mod_name} {archive_name} {description}".lower()

    def kw_match(kw):
        """Word-boundary-aware keyword match (verhindert false positives wie 'lb' in 'Gilberta')."""
        return bool(re.search(r'\b' + re.escape(kw) + r'\b', text))

    found_body_types = set()
    for btype, keywords in BODY_TYPES.items():
        for kw in keywords:
            if kw_match(kw):
                found_body_types.add(btype)

    # Kein Body-Typ im Namen → Standalone Gear, immer OK
    if not found_body_types:
        return True

    # LB oder Rue gefunden → OK
    if "lavabod" in found_body_types or "rue" in found_body_types:
        # Wenn NUR LB/Rue → OK. Wenn auch skip → prüfe genauer
        if "skip" not in found_body_types:
            return True
        # LB+Rue UND Skip → gewichtet entscheiden (mehrere Keywords)
        skip_matches = sum(1 for kw in BODY_TYPES["skip"] if kw_match(kw))
        lb_matches = sum(1 for kw in BODY_TYPES["lavabod"] if kw_match(kw))
        rue_matches = sum(1 for kw in BODY_TYPES["rue"] if kw_match(kw))
        return (lb_matches + rue_matches) >= skip_matches

    # Nur Skip gefunden → nicht installieren
    return False


def load_install_log():
    if not os.path.isfile(LOG_FILE):
        return {"installed": [], "failed": [], "skipped": []}
    with open(LOG_FILE, "r") as f:
        return json.load(f)


def save_install_log(data):
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def extract_7z(archive_path, dest_dir):
    """Extrahiert 7z mit 7-Zip."""
    result = subprocess.run(
        [SEVEN_ZIP, "x", archive_path, f"-o{dest_dir}", "-y"],
        capture_output=True, text=True, timeout=600
    )
    return result.returncode in (0, 1)


def find_installable_files(directory):
    """Findet .pmp/.ttmp2/.ttmp Dateien rekursiv."""
    results = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(('.pmp', '.ttmp2', '.ttmp')):
                results.append(os.path.join(root, f))
    return results


def read_pmp_meta(pmp_path):
    """Liest meta.json und scanned Dateipfade in einer .pmp-Datei."""
    info = {
        "name": "",
        "author": "",
        "description": "",
        "version": "",
        "tags": [],
        "file_paths": [],
        "equip_ids": [],
        "has_vfx": False,
        "has_body": False,
        "has_face": False,
        "has_hair": False,
        "has_ui": False,
        "has_weapon": False,
        "job_hints": [],
    }

    for attempt in range(3):
        try:
            with zipfile.ZipFile(pmp_path, 'r') as z:
                # meta.json
                if 'meta.json' in z.namelist():
                    with z.open('meta.json') as f:
                        meta = json.load(f)
                    info["name"] = meta.get("Name", "")
                    info["author"] = meta.get("Author", "")
                    info["description"] = meta.get("Description", "")
                    info["version"] = meta.get("Version", "")
                    info["tags"] = meta.get("ModTags", [])

                # Dateipfade analysieren
                for name in z.namelist():
                    if name.startswith('chara/'):
                        # Equipment
                        equip_match = re.search(r'chara/equipment/e0(\d{3})', name)
                        if equip_match:
                            eid = int(equip_match.group(1))
                            info["equip_ids"].append(eid)

                        # VFX
                        if '/vfx/eff/' in name or '.avfx' in name:
                            info["has_vfx"] = True

                        # Body
                        if '/body/' in name or '/b0' in name.lower():
                            info["has_body"] = True

                        # Face
                        if '/face/' in name or 'face' in name.lower():
                            info["has_face"] = True

                        # Hair
                        if '/hair/' in name or 'hair' in name.lower():
                            info["has_hair"] = True

                        # Weapon
                        if '/weapon/' in name or 'weap' in name.lower():
                            info["has_weapon"] = True

                    elif name.startswith('ui/'):
                        info["has_ui"] = True

                    info["file_paths"].append(name)
            break  # Erfolg
        except PermissionError:
            if attempt < 2:
                time.sleep(1)
                continue
            log(f"  ⚠️  Konnte .pmp nicht lesen (locked): {os.path.basename(pmp_path)}")
        except Exception as e:
            log(f"  ⚠️  Konnte .pmp nicht lesen: {e}")
            break

    return info


def read_ttmp2_meta(ttmp2_path):
    """Liest eine .ttmp2-Datei (TexTools ModPack) ansatzweise aus."""
    info = {
        "name": "",
        "description": "",
        "file_paths": [],
        "has_vfx": False,
    }
    try:
        with zipfile.ZipFile(ttmp2_path, 'r') as z:
            # TTMP2 hat eine manifest/json
            for name in z.namelist():
                info["file_paths"].append(name)
                if name.endswith('.json') and ('manifest' in name.lower() or 'modpack' in name.lower()):
                    try:
                        with z.open(name) as f:
                            data = json.load(f)
                        info["name"] = data.get("Name", "") or data.get("name", "")
                        info["description"] = data.get("Description", "") or data.get("description", "")
                    except:
                        pass
                if '.avfx' in name or '/vfx/' in name:
                    info["has_vfx"] = True
    except:
        pass
    return info


def detect_job(text):
    """Erkennt Job aus Text (Name, Description, Dateipfad)."""
    text_lower = text.lower()
    for job, keywords in JOB_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return job
    return None


EMOTE_NAMES = [
    "sit", "dance", "wave", "pray", "clap", "twerk", "pole dance",
    "salute", "bow", "cheer", "laugh", "cry", "flex", "point",
    "hug", "kiss", "slap", "flip", "backflip", "jump", "hop",
    "kneel", "prostrate", "grovel", "panic", "lookout", "shiver",
    "blow kiss", "blowkiss", "cross arms", "folded arms", "arms crossed",
    "idle", "pose", "walk", "run", "sprint",
    "cutscene", "photo", "selfie", "repose",
    "lean", "lounge", "lean back", "laying", "lying",
    "spread out", "splay", "lazed",
    "float", "meditation",
    "threaten", "taunt", "beckon", "victory", "rally",
    "stretch", "yawn", "sneeze", "cough",
    "frightened", "scared", "surprise", "shock",
    "disappointed", "facepalm", "despair",
    "joy", "excited", "exuberant",
    "confused", "think", "ponder", "chin stroke",
    "yes", "nod", "shake head", "shrug",
    "squat", "hurry", "hastened", "ready",
    "ranged", "curing", "casting", "weapon draw",
    "intro", "outro", "victory", "defeated",
    "mosh", "headbang", "rock out", "air guitar",
]


def extract_emote_name(mod_name, archive_name=""):
    """Extrahiert den spezifischen Emote-Namen für Emotes/<Name>/ Ordner."""
    text = (mod_name + " " + archive_name).lower()

    # 0) Vorreinigung: Underscores in Leerzeichen, Versionen/Author-Infos raus
    text = re.sub(r'[_\-\.]', ' ', text)
    text = re.sub(r'\b(by|author|v[\d\.]+|[\d\.]+[a-z]?)\b', ' ', text)

    # 1) Generische Trigger-Wörter entfernen (das sind Kategorien, keine Emote-Namen)
    trigger_words = ["emote", "animation", "anim", "motion", "mod", "replacement",
                     "replace", "vfx", "effect", "pose", "walk", "run", "idle",
                     "pack", "final", "new", "custom",
                     "poses", "packs", "mods", "replacements", "versions",
                     "by", "author", "collection", "creator"]
    for word in trigger_words:
        text = re.sub(r'\b' + re.escape(word) + r'\b', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip().strip("- _")

    if not text:
        # Nichts übrig → Fallback auf den ersten Teil des Mod-Namens
        cleaned = re.sub(r'[\[\(].*?[\]\)]', '', mod_name)
        cleaned = re.sub(r'\s*[-–—].*$', '', cleaned)
        cleaned = cleaned.strip(" \t-_.,:;")
        if cleaned and len(cleaned) > 2:
            return cleaned[:30].replace(" ", "_")
        return "Other"

    # 2) Bekannte Emote-Namen im Rest suchen (längste zuerst)
    for emote in sorted(EMOTE_NAMES, key=len, reverse=True):
        if re.search(r'\b' + re.escape(emote) + r'\b', text):
            return emote.title().replace(" ", "_")

    # 3) Nichts bekanntes → den bereinigten Text als Namen nehmen (sinnvoll kürzen)
    text = re.sub(r'\b\w{1,2}\b', '', text)  # kurze Wörter entfernen
    text = re.sub(r'\s+', ' ', text).strip()
    # Duplikate entfernen
    words = text.split()
    deduped = []
    for w in words:
        if w not in deduped:
            deduped.append(w)
    text = ' '.join(deduped)
    # Wenn nur Rauschen übrig ist →
    words = text.split()
    if not text:
        return "Other"
    # Einzelnes Wort, das kein bekannter Emote-Name ist → vermutlich Authorname
    if len(words) == 1:
        w = words[0]
        if len(w) >= 8:  # "fancyauthor" etc.
            return "Other"
        # Prüfen ob es wie ein bekannter Emote aussieht
        if len(w) > 2 and w.lower() not in [e.lower() for e in EMOTE_NAMES]:
            pass  # Einzelwort > 2 Buchstaben kann legitimer Emote sein
    return text[:30].replace(" ", "_")


def categorize_pmp(info, mod_name, archive_name=""):
    """
    Bestimmt den Penumbra-Ordner mittels Scoring-System:
    - Zählt Dateien pro Kategorie (VFX, Body, Face, Hair, UI, Weapon, Equipment)
    - Höchster Score gewinnt
    - Namens-Hintergrundchecks als Tiebreaker
    """
    combined_text = f"{info['name']} {info['description']} {mod_name} {archive_name}"
    combined_lower = combined_text.lower()
    total_files = len(info["file_paths"]) or 1

    # ── 1) Datei-basiertes Scoring ──
    scores = {
        "VFX": {"count": 0, "job": None},
        "Weapon": {"count": 0, "job": None},
        "Body": {"count": 0},
        "Face": {"count": 0},
        "Hair": {"count": 0},
        "UI": {"count": 0},
        "Gear": {"count": 0},
        "Animation": {"count": 0},
    }

    equip_slots_found = {}
    weapon_jobs_found = {}

    for fp in info["file_paths"]:
        fpl = fp.lower()
        # VFX
        if ".avfx" in fpl or "/vfx/eff/" in fpl:
            scores["VFX"]["count"] += 1
            job = detect_job(fp)
            if job:
                scores["VFX"]["job"] = job
        # Weapon
        if "/weapon/" in fpl or "weap" in fpl:
            scores["Weapon"]["count"] += 1
            job = detect_job(fp)
            if job:
                scores["Weapon"]["job"] = job
        # Body
        if "/body/" in fpl or re.search(r'/b\d{4}', fpl):
            scores["Body"]["count"] += 1
        # Face
        if "/face/" in fpl:
            scores["Face"]["count"] += 1
        # Hair
        if "/hair/" in fpl:
            scores["Hair"]["count"] += 1
        # UI
        if fpl.startswith("ui/"):
            scores["UI"]["count"] += 1
        # Gear/Equipment
        equip = re.search(r"equipment/e0(\d{3})", fpl)
        if equip:
            eid = int(equip.group(1))
            if eid in KNOWN_EQUIP_SLOTS:
                slot = KNOWN_EQUIP_SLOTS[eid]
                equip_slots_found[slot] = equip_slots_found.get(slot, 0) + 1
            # Prüfe Job-Waffen
            for job, eids in JOB_WEAPON_IDS.items():
                if eid in eids:
                    weapon_jobs_found[job] = weapon_jobs_found.get(job, 0) + 1
            scores["Gear"]["count"] += 1

    # ── 2) Kategorie mit Höchstpunktzahl ermitteln ──
    best_cat = "Misc"
    best_score = 0

    # VFX-Check
    vfx_ratio = scores["VFX"]["count"] / total_files
    if vfx_ratio >= 0.3 or scores["VFX"]["count"] >= 3:
        if scores["VFX"]["job"]:
            return f"VFX/Jobs/{scores['VFX']['job']}"
        if vfx_ratio > 0.5:
            return "VFX"
        best_cat, best_score = "VFX", scores["VFX"]["count"]

    # Weapon-Check
    wpn_ratio = scores["Weapon"]["count"] / total_files
    if wpn_ratio >= 0.3 or scores["Weapon"]["count"] >= 3:
        if scores["Weapon"]["job"]:
            return f"Gear/Weapons/{scores['Weapon']['job']}"
        if wpn_ratio > 0.5:
            return "Gear/Weapons"
        if scores["Weapon"]["count"] > best_score:
            best_cat, best_score = "Gear/Weapons", scores["Weapon"]["count"]

    # Equipment-Slots
    if equip_slots_found:
        # Mehrere verschiedene Slots → Gear/Sets
        if len(equip_slots_found) > 2:
            return "Gear/Sets"
        # Ein Slot dominiert → den nehmen
        dominant_slot = max(equip_slots_found, key=equip_slots_found.get)
        slot_ratio = equip_slots_found[dominant_slot] / sum(equip_slots_found.values())
        if slot_ratio >= 0.7:
            return dominant_slot
        return "Gear/Sets"

    # Waffen-eIDs
    if weapon_jobs_found:
        dominant_job = max(weapon_jobs_found, key=weapon_jobs_found.get)
        return f"Gear/Weapons/{dominant_job}"

    # UI (hohe Spezifität)
    ui_ratio = scores["UI"]["count"] / total_files
    if ui_ratio >= 0.3:
        return "UI"
    if scores["UI"]["count"] > best_score and ui_ratio >= 0.1:
        best_cat, best_score = "UI", scores["UI"]["count"]

    # Face
    face_ratio = scores["Face"]["count"] / total_files
    if face_ratio >= 0.3:
        return "Face"
    if scores["Face"]["count"] > best_score and face_ratio >= 0.15:
        best_cat, best_score = "Face", scores["Face"]["count"]

    # Hair
    hair_ratio = scores["Hair"]["count"] / total_files
    if hair_ratio >= 0.3:
        return "Hair"
    if scores["Hair"]["count"] > best_score and hair_ratio >= 0.15:
        best_cat, best_score = "Hair", scores["Hair"]["count"]

    # Body
    body_ratio = scores["Body"]["count"] / total_files
    if body_ratio >= 0.3:
        return "Body/Heliosphere"
    if scores["Body"]["count"] > best_score and body_ratio >= 0.15:
        best_cat, best_score = "Body/Heliosphere", scores["Body"]["count"]

    # Gear (Equip ohne spezifischen Slot)
    gear_ratio = scores["Gear"]["count"] / total_files
    if gear_ratio >= 0.3:
        return "Gear/Sets"
    if scores["Gear"]["count"] > best_score:
        best_cat, best_score = "Gear/Sets", scores["Gear"]["count"]

    # Animation
    anim_ratio = scores["Animation"]["count"] / total_files

    # Wenn wir basierend auf Dateien was gefunden haben
    if best_score > 0:
        return best_cat

    # ── 3) Namensbasierte Erkennung (Fallback wenn Datei-Scan nichts ergab) ──
    name_lower = (mod_name + " " + archive_name).lower()

    # Body-Mods (HS etc.)
    if any(w in name_lower for w in ["body", "rue", "bibo", "lavabod", "tre ", "yab", "yeti",
                                       "skeleton", "puffy", "helio", "skelomae", "body+",
                                       "tiddy", "heroic spirit"]):
        return "Body/Heliosphere"
    # UI
    if any(w in name_lower for w in ["ui", "delvui", "splatoon", "materia ui", "title bar",
                                       "hotbar", "job gauge", "minimap", "hover board", "aetheris",
                                       "material ui"]):
        return "UI"
    # Face (inkl. Rassenvarianten wie Aerin Miqote/Viera)
    if any(w in name_lower for w in ["face", "eyebrow", "eyelash", "lip", "eye", "freckle",
                                       "facial", "mole", "scar", "decal", "mask", "odd-eye",
                                       "brow", "miqote", "viera", "aura", "hyur", "elezen",
                                       "roegadyn", "lalafell", "hrothgar"]):
        return "Face"
    # Hair
    if any(w in name_lower for w in ["hair", "hairstyle", "fringe", "ponytail", "bangs", "braid",
                                       "dread", "mohawk", "wig"]):
        return "Hair"
    # Makeup
    if any(w in name_lower for w in ["makeup", "blush", "lipstick", "foundation", "cosmetic"]):
        return "Makeup"
    # Tattoo
    if any(w in name_lower for w in ["tattoo", "bodypaint", "skin texture", "overlay", "glow body"]):
        return "Tattoos"
    # Sculpt
    if any(w in name_lower for w in ["sculpt", "slider", "muscle", "waist", "hip", "thigh", "bust", "glute"]):
        return "Sculpt"
    # Gear/Sets
    if any(w in name_lower for w in ["set", "armor", "outfit", "cosplay", "attire", "uniform",
                                       "robes", "ensemble", "costume", "gown"]):
        return "Gear/Sets"
    # VFX (allgemein)
    if any(w in name_lower for w in ["vfx", "effect", "aura", "glow", "particle", "magic"]):
        return "VFX"
    # Animation → Emotes/<Name>/
    if any(w in name_lower for w in ["animation", "anim", "emote", "idle", "pose", "walk", "run", "motion"]):
        return "Emotes/" + extract_emote_name(mod_name, archive_name)
    # Gear/Slots
    if any(w in name_lower for w in ["head", "helmet", "crown", "diadem", "mask", "hat", "beret",
                                       "hood", "visor", "glasses", "monocle"]):
        return "Gear/Slots/Head"
    if any(w in name_lower for w in ["chest", "torso", "cuirass", "robe", "vest", "jacket", "coat",
                                       "shirt", "top", "corset", "dress"]):
        return "Gear/Slots/Chest"
    if any(w in name_lower for w in ["hands", "gauntlet", "glove", "bracer", "armlet", "wrist"]):
        return "Gear/Slots/Hands"
    if any(w in name_lower for w in ["legs", "pants", "trouser", "shorts", "skirt", "chaps", "breeches"]):
        return "Gear/Slots/Legs"
    if any(w in name_lower for w in ["feet", "boot", "shoe", "sandal", "sneaker", "sabatons"]):
        return "Gear/Slots/Feet"
    if any(w in name_lower for w in ["ears", "earring", "ear stud", "ear cuff", "ear ring"]):
        return "Gear/Slots/Ears"
    if any(w in name_lower for w in ["neck", "necklace", "choker", "pendant", "amulet", "gorget", "collar"]):
        return "Gear/Slots/Neck"
    if any(w in name_lower for w in ["wrists", "wristband", "bracelet", "bangle"]):
        return "Gear/Slots/Wrists"
    if any(w in name_lower for w in ["ring", "band", "signet"]):
        return "Gear/Slots/Rings"
    # Waffen (allgemein)
    if any(w in name_lower for w in ["weapon", "sword", "axe", "blade", "staff", "bow", "gun", "shield",
                                       "katana", "scythe", "chakram", "brush", "rapier", "greatsword",
                                       "spear", "lance", "dagger", "noulith", "gunblade", "fist"]):
        job = detect_job(combined_text)
        if job:
            return f"Gear/Weapons/{job}"
        return "Gear"
    # VFX-Remakes (Alter SMN, Alter BLM etc. — Name enthält oft nur Job)
    if any(w in name_lower for w in ["alter", "remake", "vfx", "effect"]):
        job = detect_job(combined_text)
        if job:
            return f"VFX/Jobs/{job}"
        return "VFX"
    # Job-VFX/Weapons aus Description (allgemein)
    job = detect_job(combined_text)
    if job:
        return f"Gear/Weapons/{job}"

    # 4) Ganz zum Schluss: Misc
    return "Misc"


def get_api_mods():
    """Gibt dict {internal_id: display_name} von der API zurück."""
    try:
        req = urllib.request.Request(f"{PENUMBRA_API}/mods")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log(f"  ⚠️  API-Fehler (mods): {e}")
        return None


def install_via_api(mod_path):
    """Installiert über Penumbra HTTP-API. Pfad in Windows-Format."""
    win_path = mod_path.replace("/", "\\")
    body = json.dumps({"Path": win_path}).encode("utf-8")
    req = urllib.request.Request(
        f"{PENUMBRA_API}/installmod",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30):
            return True
    except urllib.error.HTTPError as e:
        log(f"  ❌ API-Fehler (HTTP {e.code}): {e.read().decode(errors='replace')[:200]}")
        return False
    except Exception as e:
        log(f"  ❌ API-Fehler: {e}")
        return False


def find_new_mod_id(old_mods, display_name, max_wait=25):
    """Pollt API bis neuer Mod erscheint. Gibt (mod_id, mod_name)."""
    for _ in range(max_wait):
        time.sleep(1)
        new_mods = get_api_mods()
        if not new_mods:
            continue
        # Neuer Eintrag?
        diff = set(new_mods.keys()) - set(old_mods.keys())
        if len(diff) == 1:
            kid = list(diff)[0]
            return kid, new_mods[kid]
        elif len(diff) > 1:
            # Mehrere auf einmal — nimm den mit ähnlichstem Namen
            best = None
            best_score = 0
            for kid in diff:
                score = 0
                if display_name.lower() in kid.lower():
                    score += 5
                if display_name.lower() in new_mods[kid].lower():
                    score += 3
                # Edit distance approx
                common = len(set(display_name.lower()) & set(kid.lower()))
                score += common / max(len(display_name), 1)
                if score > best_score:
                    best_score = score
                    best = kid
            if best:
                return best, new_mods[best]
    return None, None


def set_mod_folder_via_db(mod_id, folder, max_retries=3):
    """Setzt Ordner via C# LiteDB-Helper mit Retry."""
    import shlex  # not needed for Windows
    
    for attempt in range(max_retries):
        result = subprocess.run(
            ["dotnet", "run", "--", "set-folder", mod_id, folder],
            cwd=HELPER_DIR,
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and "✅" in result.stdout:
            return True
        if attempt < max_retries - 1:
            time.sleep(2)
    log(f"  ⚠️  set-folder (nach {max_retries} Versuchen): {result.stderr[:200]}")
    return False


def process_archive(archive, log_data, installed_hashes, retry_failed=False):
    """Verarbeitet ein einzelnes .7z-Archiv."""
    arc_name = os.path.basename(archive)
    arc_hash = compute_hash(archive)

    log(f"\n📦 {arc_name}")

    if not retry_failed and arc_hash in installed_hashes:
        log("  ⏭️  Bereits installiert (Hash)")
        log_data["skipped"].append(archive)
        return

    with tempfile.TemporaryDirectory(dir=TEMP_DIR_PARENT, ignore_cleanup_errors=True) as tmpdir:
        if not extract_7z(archive, tmpdir):
            log("  ❌ 7z-Extraktion fehlgeschlagen")
            log_data["failed"].append(archive)
            return

        # Kurz warten, damit 7z File-Handles freigeben kann
        time.sleep(1)

        mod_files = find_installable_files(tmpdir)
        if not mod_files:
            log("  ⚠️  Keine .pmp/.ttmp2 im Archiv")
            log_data["failed"].append(archive)
            return

        log(f"  📋 {len(mod_files)} Mod-Dateien")

        old_mods = get_api_mods()
        if old_mods is None:
            log("  ❌ API nicht erreichbar")
            log_data["failed"].append(archive)
            return

        all_ok = True
        installed_pmp_hashes = load_pmp_hashes()

        # ── Vorab: Metadaten aller .pmp lesen + Version-Dedup innerhalb Archiv ──
        pmp_meta_cache = {}  # mf_path → info
        pmp_groups = {}     # base_name → [(ver_tuple, suffix, mf_path, info)]
        for mf in mod_files:
            ext = os.path.splitext(mf)[1].lower()
            if ext == '.pmp':
                info = read_pmp_meta(mf)
                pmp_meta_cache[mf] = info
                display_name = info["name"] or os.path.splitext(os.path.basename(mf))[0]
                base_key = normalize_mod_name(display_name)
                if not base_key:
                    base_key = os.path.splitext(os.path.basename(mf))[0].lower()
                # Version aus meta.json oder filename
                ver_str = info.get("version", "")
                if ver_str:
                    parts = re.findall(r'\d+|[a-z]+', ver_str)
                    nums = tuple(int(p) for p in parts if p.isdigit()) or (0, 0, 0)
                    suffix = ''.join(p for p in parts if not p.isdigit())
                else:
                    nums, suffix, _ = parse_version_from_name(mf)
                if base_key not in pmp_groups:
                    pmp_groups[base_key] = []
                pmp_groups[base_key].append((nums, suffix, mf, info))
            else:
                # .ttmp2 — einfach direkt behandeln (Cache-Dummy)
                pmp_meta_cache[mf] = {"name": os.path.splitext(os.path.basename(mf))[0], "description": "", "file_paths": []}
                base_key = os.path.splitext(os.path.basename(mf))[0].lower()
                pmp_groups.setdefault(base_key, []).append(((0,0,0), '', mf, pmp_meta_cache[mf]))

        # Nur höchste Version pro Gruppe
        deduped_files = []
        ver_skipped = 0
        for base_key, items in pmp_groups.items():
            if len(items) <= 1:
                deduped_files.append(items[0][2])
                continue
            items.sort(key=lambda x: (x[0][0], x[0][1], x[0][2], x[1]), reverse=True)
            deduped_files.append(items[0][2])
            ver_skipped += len(items) - 1
            log(f"  📌 {len(items)} Versionen von '{base_key}', nur {os.path.basename(items[0][2])}")

        if ver_skipped:
            log(f"     ⏭️  {ver_skipped} ältere .pmp-Versionen übersprungen")

        for mf in deduped_files:
            ext = os.path.splitext(mf)[1].lower()
            base = os.path.basename(mf)

            # ── Metadaten aus Cache (bereits gelesen) ──
            info = pmp_meta_cache.get(mf, {})
            mod_display_name = info.get("name", "") or os.path.splitext(base)[0]
            folder = categorize_pmp(info, mod_display_name, arc_name)

            log(f"  📄 {base} → {mod_display_name}")

            # ── Duplikatsprüfung vor der API-Installation ──
            pmp_hash = compute_hash(mf)
            if pmp_hash in installed_pmp_hashes:
                log(f"     ⏭️  Bereits installiert (PMP-Hash)")
                continue

            if is_mod_installed(mod_display_name, old_mods):
                log(f"     ⏭️  Bereits installiert (Name: {mod_display_name})")
                save_pmp_hash(pmp_hash)
                continue

            # ── Body-Type-Filter: Nur Lavabod/Rue ──
            # Prüft ob die Mod explizit einen Body-Typ erwähnt
            if not is_gear_for_lb_rue(mod_display_name, arc_name, info.get("description", "")):
                log(f"     ⏭️  Nicht LB/Rue-kompatibel: {mod_display_name}")
                save_pmp_hash(pmp_hash)
                continue

            if not install_via_api(mf):
                all_ok = False
                continue

            new_id, new_name = find_new_mod_id(old_mods, mod_display_name)
            if not new_id:
                log("  ⚠️  Mod nicht in API gefunden (setze Ordner später)")
                continue

            log(f"     ✅ {new_id}")
            log(f"     📁 Ordner: {folder}")

            if set_mod_folder_via_db(new_id, folder):
                log(f"     ✅ Ordner gesetzt")
            else:
                log(f"     ⚠️  Ordner-Zuweisung fehlgeschlagen")

            save_pmp_hash(pmp_hash)
            old_mods[new_id] = new_name

        if all_ok:
            save_hash(arc_hash)
            log_data["installed"].append(archive)
            log("  ✅ Archiv fertig")
        else:
            log_data["failed"].append(archive)
            log("  ⚠️  Archiv mit Fehlern")


def process_archives(source_dir, retry_failed=False):
    """Hauptschleife."""
    os.makedirs(TEMP_DIR_PARENT, exist_ok=True)
    log_data = load_install_log()
    installed_hashes = load_hash_log()

    archives = sorted([
        os.path.join(root, f)
        for root, dirs, files in os.walk(source_dir)
        for f in files if f.lower().endswith('.7z')
    ])
    if not archives:
        log("❌ Keine .7z-Archive gefunden")
        return
    log(f"📦 {len(archives)} Archive gefunden")

    # ── Hash-Dedup: Exakte (2)-Kopien entfernen ──
    log("🔍 Prüfe auf Hash-Kopien...")
    archives, hash_dup = dedup_archives_by_hash(archives)
    if hash_dup:
        log(f"   ⏭️  {hash_dup} exakte Duplikate entfernt")

    # ── Version-Dedup: Nur neueste Version pro Mod ──
    log("🔍 Prüfe auf Mehrfachversionen...")
    archives, ver_skipped = dedup_archives_by_version(archives)
    if ver_skipped:
        log(f"   ⏭️  {ver_skipped} ältere Versionen übersprungen")
    log(f"📦 {len(archives)} Archive nach Dedup")

    if retry_failed:
        failed_paths = set(log_data.get("failed", []))
        archives = [a for a in archives if a in failed_paths]
        log(f"🔄 Wiederhole {len(archives)} fehlgeschlagene")

    for i, archive in enumerate(archives, 1):
        log(f"\n{'='*50}")
        log(f"[{i}/{len(archives)}]")
        process_archive(archive, log_data, installed_hashes, retry_failed)

    save_install_log(log_data)

    log(f"\n{'='*50}")
    log(f"✅ Installiert: {len(log_data['installed'])}")
    log(f"⏭️  Übersprungen: {len(log_data['skipped'])}")
    log(f"❌ Fehlgeschlagen: {len(log_data['failed'])}")


def list_archives(source_dir):
    archives = sorted([
        os.path.join(root, f)
        for root, dirs, files in os.walk(source_dir)
        for f in files if f.lower().endswith('.7z')
    ])
    log(f"📦 {len(archives)} Archive:")
    for a in archives:
        size = os.path.getsize(a)
        log(f"  {os.path.basename(a)} ({size//1024//1024} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Penumbra Batch Installer v3 (API + Pfadanalyse)")
    parser.add_argument("--dir", default=r"D:\Telegram Desktop", help="Quellverzeichnis")
    parser.add_argument("--retry-failed", action="store_true", help="Fehlgeschlagene wiederholen")
    parser.add_argument("--list-only", action="store_true", help="Nur auflisten")
    parser.add_argument("--fix-folders", action="store_true",
                        help="Bestehende Mods neu kategorisieren (nach Batch)")
    parser.add_argument("--fix-generals", action="store_true",
                        help="Nur Mods in 'general' oder leerem Ordner neu zuweisen")
    args = parser.parse_args()

    if args.list_only:
        list_archives(args.dir)
        sys.exit(0)

    if args.fix_folders:
        # Alle bereits installierten Mods neu kategorisieren
        log("🔄 Kategorisiere alle installierten Mods neu...")
        mods = get_api_mods()
        if not mods:
            log("❌ API nicht erreichbar")
            sys.exit(1)
        fixed = 0
        for kid, kname in mods.items():
            # Suche passende .pmp im Archiv-Cache (falls vorhanden)
            folder = categorize_pmp({"name": kname, "description": "", "file_paths": [],
                                      "equip_ids": [], "has_vfx": False, "has_body": False,
                                      "has_face": False, "has_hair": False, "has_ui": False,
                                      "has_weapon": False, "job_hints": [], "tags": []},
                                     kname, "")
            if folder != "Misc":
                if set_mod_folder_via_db(kid, folder):
                    log(f"  ✅ {kname[:50]:50s} → {folder}")
                    fixed += 1
                else:
                    log(f"  ⚠️  {kname[:50]:50s} → FEHLER")
        log(f"\n✅ {fixed} Mods kategorisiert")
        sys.exit(0)

    if args.fix_generals:
        log("🔄 Fixe Mods in 'general'...")
        mods = get_api_mods()
        if not mods:
            log("❌ API nicht erreichbar")
            sys.exit(1)
        result = subprocess.run(
            ["dotnet", "run", "--", "list"],
            cwd=HELPER_DIR, capture_output=True, text=True, timeout=30
        )
        fixed = 0
        for line in result.stdout.split("\n"):
            parts = line.strip().split(None, 1)
            if len(parts) < 2:
                continue
            folder = parts[0].strip().lower()
            mod_id = parts[1].strip()
            if folder in ("general", "(root)", ""):
                kname = mods.get(mod_id, mod_id)
                new_folder = categorize_pmp({"name": kname, "description": "", "file_paths": [],
                                              "equip_ids": [], "has_vfx": False, "has_body": False,
                                              "has_face": False, "has_hair": False, "has_ui": False,
                                              "has_weapon": False, "job_hints": [], "tags": []},
                                             kname, "")
                if new_folder not in ("Misc", "general", ""):
                    if set_mod_folder_via_db(mod_id, new_folder):
                        log(f"  ✅ {kname[:45]:45s} {folder:10s} \u2192 {new_folder}")
                        fixed += 1
                    else:
                        log(f"  ⚠️  {kname[:45]:45s} {folder:10s} \u2192 FEHLER")
        log(f"\n✅ {fixed} Mods aus general kategorisiert")
        sys.exit(0)

    process_archives(args.dir, retry_failed=args.retry_failed)
