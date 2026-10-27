"""Camera ownership and center-cropped frames with a fixed display geometry."""
import sys
import cv2

from .config import BOARD_WIDTH, BOARD_HEIGHT


def fit_frame(frame, width=BOARD_WIDTH, height=BOARD_HEIGHT):
    h, w = frame.shape[:2]
    if w <= 0 or h <= 0:
        raise ValueError("Empty camera frame.")
    scale = max(width/w, height/h)
    resized = cv2.resize(frame, (max(width, round(w*scale)), max(height, round(h*scale))))
    y = (resized.shape[0]-height)//2
    x = (resized.shape[1]-width)//2
    return resized[y:y+height, x:x+width].copy()


class Camera:
    def __init__(self, index=0):
        self.capture = None
        backends = (cv2.CAP_DSHOW, cv2.CAP_MSMF) if sys.platform == 'win32' else (cv2.CAP_ANY,)
        for backend in backends:
            candidate = cv2.VideoCapture(index, backend)
            if candidate.isOpened():
                candidate.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
                candidate.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
                candidate.set(cv2.CAP_PROP_FPS, 30)
                self.capture = candidate
                break
            candidate.release()
        if self.capture is None:
            raise RuntimeError(f"Camera {index} unavailable. Check Windows camera permissions or use mouse mode.")

    def read(self, mirror=True):
        ok, frame = self.capture.read()
        if not ok or frame is None or frame.size == 0:
            return None
        frame = fit_frame(frame)
        return cv2.flip(frame, 1) if mirror else frame

    def close(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None

