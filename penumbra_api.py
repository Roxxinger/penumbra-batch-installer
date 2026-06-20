"""
penumbra_api.py — Penumbra HTTP-API Hilfsfunktionen

Einheitlicher Zugriff auf die Penumbra-API mit Health-Check.
"""

import json
import time
import urllib.request
import urllib.error
import sys

PENUMBRA_API = "http://localhost:42069/api"


def api_health(timeout: int = 3) -> bool:
    """Prüft ob die Penumbra-API erreichbar ist.

    Sendet GET an /api/mods und prüft ob gültiges JSON zurückkommt.

    Returns:
        True wenn API antwortet, False sonst
    """
    try:
        req = urllib.request.Request(f"{PENUMBRA_API}/mods", method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, urllib.error.HTTPError,
            ConnectionRefusedError, TimeoutError, OSError):
        pass

    # Fallback: GET mit kurzem Timeout
    try:
        req = urllib.request.Request(f"{PENUMBRA_API}/mods")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            json.loads(resp.read().decode("utf-8"))
            return True
    except (urllib.error.URLError, urllib.error.HTTPError,
            ConnectionRefusedError, TimeoutError, OSError,
            json.JSONDecodeError):
        return False


def get_mods(timeout: int = 10) -> list[dict] | None:
    """Holt alle installierten Mods von der API.

    Returns:
        Liste von {Name, Directory} Dicts, oder None bei Fehler
    """
    try:
        req = urllib.request.Request(f"{PENUMBRA_API}/mods")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  ⚠️  API-Fehler (mods): {e}", file=sys.stderr)
        return None

    if isinstance(data, dict):
        return [{"Name": v, "Directory": k} for k, v in data.items()]
    elif isinstance(data, list):
        return [{"Name": str(i), "Directory": str(i)} for i in data]
    return []


def require_api(timeout: int = 3) -> None:
    """Prüft API-Health und beendet mit Exit 1 wenn nicht erreichbar.

    Verwendung am Anfang von Scripts die Penumbra brauchen.
    """
    if not api_health(timeout):
        print("❌ Penumbra-API nicht erreichbar (localhost:42069)")
        print("   Stelle sicher dass FFXIV mit aktiviertem Penumbra läuft.")
        sys.exit(1)
