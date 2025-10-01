import shutil
from pathlib import Path
import getpass
import os
import psutil

SOURCE_DIR = Path(__file__).parent
username = getpass.getuser()
PROGRAMS_DIR = Path(rf"C:\Users\{username}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs")

BLACKLIST_FILES = {"TERMS.txt", "LICENCE.txt", "NEWS.txt"}
BLACKLIST_EXTS = set()  # fixato
BLACKLIST_DIRS = {"OpenFile", "__pycache__"}

def kill_python_processes():
    try:
        current_pid = os.getpid()
        for proc in psutil.process_iter(attrs=['pid', 'name', 'exe']):
            try:
                if proc.info['name'] in ('python.exe', 'pythonw.exe') and proc.info['pid'] != current_pid:
                    if proc.info['exe'] and str(PROGRAMS_DIR) in proc.info['exe']:
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception:
        pass

def safe_remove_tree(src: Path, dst: Path):
    try:
        kill_python_processes()
        src = src.resolve()
        dst = dst.resolve()

        for root, dirs, files in os.walk(src):
            root_path = Path(root)
            rel = Path(os.path.relpath(root_path, src))
            target_root = dst / rel
            target_root.mkdir(parents=True, exist_ok=True)

            dirs[:] = [d for d in dirs if d not in BLACKLIST_DIRS]

            for fname in files:
                if fname in BLACKLIST_FILES:
                    continue
                if Path(fname).suffix.lower() in BLACKLIST_EXTS:
                    continue
                target_file = target_root / fname
                if target_file.exists():
                    try:
                        if target_file.is_file():
                            target_file.unlink()
                        elif target_file.is_dir():
                            shutil.rmtree(target_file)
                    except Exception as e:
                        print(f"Error removing {target_file}: {e}")

        # pulizia cartelle vuote
        for root, dirs, _ in os.walk(dst, topdown=False):
            for d in dirs:
                dir_path = Path(root) / d
                if not any(dir_path.iterdir()):
                    try:
                        dir_path.rmdir()
                    except Exception as e:
                        print(f"Error removing directory {dir_path}: {e}")

    except Exception as e:
        print(f"Error during removal: {e}")

if __name__ == "__main__":
    safe_remove_tree(SOURCE_DIR, PROGRAMS_DIR)
