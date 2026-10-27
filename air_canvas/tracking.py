"""MediaPipe Tasks adapter; imports the model runtime only in hand mode."""
import hashlib
from pathlib import Path
import time

import cv2
import numpy as np

from .config import MODEL_PATH

MODEL_SHA256 = "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1"


class HandTracker:
    def __init__(self, model_path: Path = MODEL_PATH):
        import mediapipe as mp
        self.mp = mp
        model_path = Path(model_path)
        if not model_path.is_file():
            raise FileNotFoundError(f"Hand model missing: {model_path}. Run setup.bat --repair-model.")
        model_bytes = model_path.read_bytes()
        if hashlib.sha256(model_bytes).hexdigest() != MODEL_SHA256:
            raise ValueError("The bundled hand model failed its SHA-256 check. Run setup.bat --repair-model.")
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_buffer=model_bytes),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        self._model = mp.tasks.vision.HandLandmarker.create_from_options(options)
        self._timestamp = -1

    def detect(self, bgr_frame):
        rgb = np.ascontiguousarray(cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB))
        image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
        self._timestamp = max(self._timestamp + 1, time.monotonic_ns() // 1_000_000)
        result = self._model.detect_for_video(image, self._timestamp)
        if not result.hand_landmarks:
            return None
        return [(p.x, p.y, p.z) for p in result.hand_landmarks[0]]

    def close(self):
        self._model.close()

