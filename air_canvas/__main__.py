"""Run with python -m air_canvas (or run.py / START.bat)."""
import argparse
from pathlib import Path
import sys

from . import config as C


def main():
    parser = argparse.ArgumentParser(description='Air Canvas - draw with a webcam or mouse')
    parser.add_argument('--mouse', action='store_true', help='Start without a camera or model')
    parser.add_argument('--demo', action='store_true', help='Mouse mode with sample artwork')
    parser.add_argument('--camera', type=int, default=0, help='Webcam index (default: 0)')
    parser.add_argument('--output', type=Path, default=C.DRAWINGS_PATH, help='PNG output folder')
    parser.add_argument('--check', action='store_true', help='Check dependencies and real model inference; no camera')
    parser.add_argument('--max-frames', type=int, help='Close after N GUI frames (smoke test)')
    parser.add_argument('--screenshot', type=Path, help='Render a PNG without opening GUI or camera')
    args = parser.parse_args()
    if args.max_frames is not None and args.max_frames < 1:
        parser.error('--max-frames must be at least 1')
    try:
        import cv2
        import numpy as np
        from .app import AirCanvasApp
        if args.check:
            import mediapipe as mp
            from .tracking import HandTracker
            print(f'Python {sys.version.split()[0]} | OpenCV {cv2.__version__} | MediaPipe {mp.__version__} | NumPy {np.__version__}')
            tracker = HandTracker()
            try:
                result = tracker.detect(np.zeros((600, 960, 3), np.uint8))
                if result is not None:
                    raise RuntimeError('Unexpected hand detected on a blank frame.')
            finally:
                tracker.close()
            print('PASS: bundled model checksum, native runtime and blank-frame inference. No camera opened.')
            return 0
        app = AirCanvasApp(mouse=args.mouse or args.screenshot is not None,
                           camera_index=args.camera, output_dir=args.output, demo=args.demo)
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            ok, pixels = cv2.imencode('.png', app.render())
            if not ok:
                raise OSError('Screenshot encoding failed.')
            pixels.tofile(args.screenshot)
            print(f'Screenshot: {args.screenshot.resolve()}')
        else:
            app.run(max_frames=args.max_frames)
        return 0
    except ImportError as exc:
        print(f'Missing dependency: {exc}\nRun setup.bat, then START.bat.', file=sys.stderr)
        return 1
    except (RuntimeError, OSError, ValueError) as exc:
        print(f'Air Canvas error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

