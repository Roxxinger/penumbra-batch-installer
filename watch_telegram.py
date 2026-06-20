#!/usr/bin/env python3
"""
watch_telegram.py — File Watcher für Penumbra Batch Installer
============================================================
Überwacht D:\\Telegram Desktop auf neue .7z-Dateien und triggert
automatisch den Batch-Installer.

Start:  python watch_telegram.py
Stop:   Strg+C
Status: python watch_telegram.py --status  (zeigt ob Watcher läuft)

Der Watcher hat eine 60s-Cooldown nach der letzten Änderung,
damit Telegram Zeit hat, alle Dateien fertig zu laden.
"""

import os
import sys
import time
import subprocess
import threading
import json
import signal
from pathlib import Path
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("❌ watchdog nicht installiert. Installiere mit: uv pip install watchdog")
    sys.exit(1)

# ─── Konfiguration ───────────────────────────────────────────────────────────

WATCH_DIR = r"D:\Telegram Desktop"
INSTALLER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "install_pmp_mod.py")
PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".watcher.pid")
COOLDOWN = 60  # Sekunden nach letzter Änderung
VALID_EXTENSIONS = (".7z", ".zip", ".rar", ".pmp", ".ttmp2")
DEBOUNCE_CHECK_INTERVAL = 5  # Sekunden zwischen Cooldown-Checks

# ─── Event Handler ───────────────────────────────────────────────────────────

class ModFileHandler(FileSystemEventHandler):
    """Überwacht Dateiänderungen und triggert den Installer mit Cooldown.

    Triggert NUR bei neuen Dateien (on_created, on_moved) — nicht bei
    on_modified, da Lesen/Listen bereits modified-Events auslöst.
    """

    def __init__(self, watch_dir):
        self.watch_dir = os.path.abspath(watch_dir)
        # Snapshot: welche Dateien existieren bereits beim Start?
        self.known_files = set()
        self._init_known_files()
        self.timer = None
        self.lock = threading.Lock()
        self.last_run = 0

    def _init_known_files(self):
        """Erfasst alle existierenden Dateien beim Watcher-Start,
        damit sie nicht fälschlich als 'neu' erkannt werden."""
        if not os.path.isdir(self.watch_dir):
            return
        try:
            for f in os.listdir(self.watch_dir):
                fpath = os.path.join(self.watch_dir, f)
                if os.path.isfile(fpath):
                    self.known_files.add(os.path.normcase(fpath))
        except PermissionError:
            pass
        print(f"   📋 Bestehende Dateien gesnapshotet: {len(self.known_files)}")

    def _is_new_file(self, filepath):
        """Prüft ob eine Datei wirklich neu ist (nicht vorher bekannt)."""
        norm = os.path.normcase(filepath)
        if norm in self.known_files:
            return False
        self.known_files.add(norm)
        return True

    def _is_mod_file(self, path):
        """Prüft ob die Datei eine Mod-Datei ist."""
        return any(path.lower().endswith(ext) for ext in VALID_EXTENSIONS) and \
               os.path.isfile(path)

    def on_created(self, event):
        if event.is_directory:
            return
        if self._is_mod_file(event.src_path) and self._is_new_file(event.src_path):
            self._schedule(f"📥 Neu: {os.path.basename(event.src_path)}")

    def on_moved(self, event):
        if event.is_directory:
            return
        if self._is_mod_file(event.dest_path) and self._is_new_file(event.dest_path):
            self._schedule(f"📥 Verschoben: {os.path.basename(event.dest_path)}")

    def _schedule(self, reason=""):
        with self.lock:
            if self.timer and self.timer.is_alive():
                self.timer.cancel()
            self.timer = threading.Timer(COOLDOWN, self._run_installer, args=[reason])
            self.timer.daemon = True
            self.timer.start()
            ts = datetime.now().strftime("%H:%M:%S")
            if reason:
                print(f"  [{ts}] ⏳ Watcher: {reason}")
            print(f"  [{ts}] ⏳ Installer startet in {COOLDOWN}s (bei weiteren Änderungen wird neu gezählt)")

    def _run_installer(self, reason=""):
        """Führt den Batch-Installer aus."""
        now = time.time()
        if now - self.last_run < COOLDOWN:
            return  # Cooldown-Schutz

        self.last_run = now
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{ts}] 🚀 Starte Batch-Installer...")
        
        try:
            result = subprocess.run(
                [sys.executable, INSTALLER],
                capture_output=True, text=True, timeout=600
            )
            elapsed = time.time() - now
            output = result.stdout.strip()
            errors = result.stderr.strip()

            print(f"[{ts}] ✅ Installer beendet ({elapsed:.0f}s)")
            if output:
                # Nur die letzten Zeilen anzeigen
                lines = output.split("\n")
                summary = [l for l in lines if any(kw in l.lower() 
                          for kw in ["✅", "❌", "⏭️", "📦", "🔍", "installiert", "übersprungen", "fehlgeschlagen"])]
                for s in summary[-10:]:
                    print(f"  {s}")
            if errors and "Warnung" not in errors:
                print(f"  ⚠️  STDERR: {errors[-500:]}")
        except subprocess.TimeoutExpired:
            print(f"  ❌ Installer timeout (>10 Minuten)")
        except Exception as e:
            print(f"  ❌ Installer Fehler: {e}")

        print()  # Leerzeile für Lesbarkeit


# ─── Watcher Management ─────────────────────────────────────────────────────

def write_pid():
    """Schreibt PID-Datei."""
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    print(f"  📝 PID {os.getpid()} gespeichert")

def remove_pid():
    """Entfernt PID-Datei."""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

def is_running():
    """Prüft ob Watcher bereits läuft (Windows-kompatibel)."""
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        # Windows: tasklist /FI "PID eq <pid>" prüfen
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, timeout=5
        )
        return str(pid) in result.stdout
    except (OSError, ValueError, subprocess.TimeoutExpired):
        remove_pid()
        return False

def show_status():
    """Zeigt Watcher-Status."""
    if is_running():
        with open(PID_FILE) as f:
            pid = f.read().strip()
        print(f"✅ Watcher läuft (PID: {pid})")
        print(f"   Überwacht: {WATCH_DIR}")
    else:
        print("❌ Watcher läuft nicht")
    return 0

def stop_watcher():
    """Stoppt laufenden Watcher."""
    if not os.path.exists(PID_FILE):
        print("❌ Kein Watcher-Prozess gefunden")
        return 1
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
        remove_pid()
        print(f"✅ Watcher (PID {pid}) gestoppt")
        return 0
    except Exception as e:
        print(f"❌ Fehler beim Stoppen: {e}")
        remove_pid()
        return 1


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    # Status-Anzeige
    if "--status" in sys.argv:
        return show_status()

    if "--stop" in sys.argv:
        return stop_watcher()

    # Prüfen ob bereits ein Watcher läuft
    if is_running():
        print("❌ Watcher läuft bereits! Nutze --status oder --stop")
        return 1

    # Prüfen ob das Watch-Verzeichnis existiert
    if not os.path.isdir(WATCH_DIR):
        print(f"❌ Verzeichnis existiert nicht: {WATCH_DIR}")
        return 1

    # Prüfen ob der Installer existiert
    if not os.path.isfile(INSTALLER):
        print(f"❌ Installer nicht gefunden: {INSTALLER}")
        return 1

    # PID speichern
    write_pid()

    # Watcher starten
    event_handler = ModFileHandler(WATCH_DIR)
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)

    print(f"\n{'='*60}")
    print(f"🔍 Penumbra File Watcher")
    print(f"{'='*60}")
    print(f"   Überwacht:    {WATCH_DIR}")
    print(f"   Installer:    {INSTALLER}")
    print(f"   Cooldown:     {COOLDOWN}s nach letzter Änderung")
    print(f"   Erweiterungen: {', '.join(VALID_EXTENSIONS)}")
    print(f"   Stop mit:     Strg+C oder --stop")
    print(f"   Status:       --status")
    print(f"{'='*60}\n")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Watcher gestoppt")
    finally:
        observer.stop()
        observer.join()
        remove_pid()

    return 0


if __name__ == "__main__":
    sys.exit(main())
