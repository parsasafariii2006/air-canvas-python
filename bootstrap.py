"""One-time setup using only the Python standard library."""
import argparse
import hashlib
from pathlib import Path
import struct
import subprocess
import sys
import urllib.request
import venv

ROOT = Path(__file__).resolve().parent
MODEL_URL = 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'
MODEL_HASH = 'fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1'


def main():
    parser = argparse.ArgumentParser(description='Install Air Canvas in its own .venv')
    parser.add_argument('--repair-model', action='store_true', help='Re-download and verify the official model')
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 14) or struct.calcsize('P') != 8:
        raise RuntimeError('Please run setup.bat with 64-bit Python 3.14 (tested runtime).')
    environment = ROOT / '.venv'
    executable = environment / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    if not executable.is_file():
        print('Creating an isolated Python environment...', flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    subprocess.run([str(executable), '-m', 'pip', 'install', '-r', str(ROOT/'requirements.txt')], check=True)
    subprocess.run([str(executable), '-m', 'pip', 'check'], check=True)
    model = ROOT / 'models' / 'hand_landmarker.task'
    if args.repair_model or not model.is_file():
        model.parent.mkdir(parents=True, exist_ok=True)
        print('Downloading the official hand model (about 8 MB)...', flush=True)
        request = urllib.request.Request(MODEL_URL, headers={'User-Agent': 'AirCanvas-Setup/1.0'})
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = response.read(20_000_000)
        if hashlib.sha256(payload).hexdigest() != MODEL_HASH:
            raise RuntimeError('Downloaded model checksum mismatch; existing model was preserved.')
        temporary = model.with_suffix('.download')
        temporary.write_bytes(payload)
        temporary.replace(model)
    if hashlib.sha256(model.read_bytes()).hexdigest() != MODEL_HASH:
        raise RuntimeError('Model checksum failed. Run setup.bat --repair-model.')
    subprocess.run([str(executable), '-m', 'air_canvas', '--check'], cwd=ROOT, check=True)
    print('\nSetup complete. Double-click START.bat or START_MOUSE.bat.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(f'\nSetup failed: {exc}', file=sys.stderr)
        raise SystemExit(1)

