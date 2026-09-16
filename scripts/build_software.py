import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.resolve()
FRONTEND_DIR = ROOT_DIR / "frontend"
DIST_DIR = ROOT_DIR / "dist"
INSTALLER_DIR = ROOT_DIR / "installer"
ISCC_PATH = Path(r"C:\Users\asus\AppData\Local\Programs\Inno Setup 6\ISCC.exe")


def run_command(cmd, cwd=ROOT_DIR):
    print(f"\n[BUILD] Running: {cmd} (in {cwd})")
    res = subprocess.run(cmd, shell=True, cwd=cwd)
    if res.returncode != 0:
        print(f"[ERROR] Command failed with exit code {res.returncode}")
        sys.exit(res.returncode)


def step1_build_frontend():
    print("\n" + "=" * 60)
    print("STEP 1: BUILDING FRONTEND ASSETS")
    print("=" * 60)
    dist_index = FRONTEND_DIR / "dist" / "index.html"
    if not dist_index.exists():
        run_command("npm run build", cwd=FRONTEND_DIR)
    else:
        print("Frontend assets already built in frontend/dist.")


def step2_bundle_pyinstaller():
    print("\n" + "=" * 60)
    print("STEP 2: PACKAGING DESKTOP SOFTWARE WITH PYINSTALLER")
    print("=" * 60)

    py_exe = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
    pyinstaller_exe = ROOT_DIR / ".venv" / "Scripts" / "pyinstaller.exe"

    if not pyinstaller_exe.exists():
        pyinstaller_exe = "pyinstaller"

    # PyInstaller command: package desktop_app.py
    # Add data directories: backend, agent, frontend/dist
    add_data_args = [
        f'--add-data "{ROOT_DIR / "backend"};backend"',
        f'--add-data "{ROOT_DIR / "agent"};agent"',
        f'--add-data "{FRONTEND_DIR / "dist"};frontend/dist"',
        f'--add-data "{ROOT_DIR / "database"};database"',
    ]

    cmd = (
        f'"{pyinstaller_exe}" '
        f'--noconfirm --onedir --windowed '
        f'--name YTAutomationStudio '
        f'{" ".join(add_data_args)} '
        f'"{ROOT_DIR / "desktop_app.py"}"'
    )

    run_command(cmd, cwd=ROOT_DIR)
    print("\n[SUCCESS] PyInstaller bundled desktop software into dist/YTAutomationStudio")


def step3_compile_inno_setup():
    print("\n" + "=" * 60)
    print("STEP 3: COMPILING INNO SETUP INSTALLER")
    print("=" * 60)

    iss_file = INSTALLER_DIR / "yt_automation_studio.iss"
    if not ISCC_PATH.exists():
        print(f"[WARNING] Inno Setup compiler not found at {ISCC_PATH}. Checking PATH...")
        iscc = "iscc"
    else:
        iscc = str(ISCC_PATH)

    # Ensure output directory exists
    (INSTALLER_DIR / "output").mkdir(parents=True, exist_ok=True)

    cmd = f'"{iscc}" "{iss_file}"'
    run_command(cmd, cwd=INSTALLER_DIR)

    setup_exe = INSTALLER_DIR / "output" / "YT-Automation-Studio-Setup.exe"
    if setup_exe.exists():
        print("\n" + "=" * 60)
        print("[SUCCESS] INSTALLER CREATED SUCCESSFULLY:")
        print(f"Path: {setup_exe}")
        print(f"Size: {setup_exe.stat().st_size / (1024 * 1024):.2f} MB")
        print("=" * 60)
    else:
        print("[ERROR] Installer was not generated.")


def main():
    print("================================================================")
    print("YT AUTOMATION STUDIO — COMPLETE SOFTWARE & INSTALLER BUILD PIPELINE")
    print("================================================================")
    step1_build_frontend()
    step2_bundle_pyinstaller()
    step3_compile_inno_setup()


if __name__ == "__main__":
    main()
