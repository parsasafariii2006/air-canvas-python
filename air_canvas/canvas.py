"""Transparent canvas, bounded snapshot history and Unicode-safe PNG export."""
from collections import deque
from datetime import datetime
from pathlib import Path
import math
import uuid

import cv2
import numpy as np

from .config import HISTORY_LIMIT


class Canvas:
    def __init__(self, width: int, height: int, max_jump: float = 180,
                 history_limit: int = HISTORY_LIMIT):
        if width <= 0 or height <= 0 or max_jump <= 0 or history_limit < 1:
            raise ValueError("Canvas dimensions, jump limit and history must be positive.")
        self.width, self.height = width, height
        self.image = np.zeros((height, width, 4), dtype=np.uint8)
        self.max_jump = max_jump
        self._undo = deque(maxlen=history_limit)
        self._redo = deque(maxlen=history_limit)
        self._previous = None
        self._editing = False
        self.version = 0

    @property
    def has_ink(self) -> bool:
        return bool(np.any(self.image[:, :, 3]))

    def end_stroke(self):
        self._previous = None
        self._editing = False

    def _checkpoint(self):
        self._undo.append(self.image.copy())
        self._redo.clear()

    def draw(self, point: tuple[int, int], color: tuple[int, int, int],
             thickness: int, erase: bool = False):
        x, y = point
        if not (0 <= x < self.width and 0 <= y < self.height):
            self.end_stroke()
            return
        if thickness < 1:
            raise ValueError("Brush thickness must be positive.")
        if self._previous is not None and math.dist(self._previous, point) > self.max_jump:
            self.end_stroke()
        if not self._editing:
            self._checkpoint()
            self._editing = True
        ink = (0, 0, 0, 0) if erase else (*color, 255)
        # LINE_8 keeps unpremultiplied color and alpha consistent on the raster.
        if self._previous is not None:
            cv2.line(self.image, self._previous, point, ink, thickness, cv2.LINE_8)
        cv2.circle(self.image, point, max(1, thickness // 2), ink, -1, cv2.LINE_8)
        self._previous = point
        self.version += 1

    def clear(self) -> bool:
        self.end_stroke()
        if not self.has_ink:
            return False
        self._checkpoint()
        self.image.fill(0)
        self.version += 1
        return True

    def undo(self) -> bool:
        self.end_stroke()
        if not self._undo:
            return False
        self._redo.append(self.image.copy())
        self.image = self._undo.pop()
        self.version += 1
        return True

    def redo(self) -> bool:
        self.end_stroke()
        if not self._redo:
            return False
        self._undo.append(self.image.copy())
        self.image = self._redo.pop()
        self.version += 1
        return True

    def composite(self, background=None) -> np.ndarray:
        if background is None:
            background = np.full((self.height, self.width, 3), 255, np.uint8)
        if background.shape != (self.height, self.width, 3):
            raise ValueError("Background must match canvas height, width and BGR channels.")
        # Ink is fully opaque; the alpha mask also preserves black drawing pixels.
        result = background.copy()
        mask = self.image[:, :, 3] != 0
        result[mask] = self.image[:, :, :3][mask]
        return result

    def save(self, directory: Path) -> tuple[Path, Path]:
        self.end_stroke()
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        name = datetime.now().strftime("canvas_%Y%m%d_%H%M%S_%f") + "_" + uuid.uuid4().hex[:6]
        white = directory / (name + ".png")
        transparent = directory / (name + "_transparent.png")
        for path, pixels in ((white, self.composite()), (transparent, self.image)):
            ok, encoded = cv2.imencode(".png", pixels)
            if not ok:
                raise OSError(f"PNG encoding failed: {path}")
            # imwrite is not reliable for Unicode Windows paths in all builds.
            encoded.tofile(path)
        return white, transparent

