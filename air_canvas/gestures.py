"""Small deterministic gesture recognizer, hysteresis and dwell selection."""
from enum import Enum
import math


class Gesture(str, Enum):
    NONE = "NO HAND"
    DRAW = "DRAW"
    SELECT = "SELECT"
    PAUSE = "HOVER"


def _distance(a, b):
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))


def _angle(a, b, c):
    u = tuple(x-y for x, y in zip(a, b))
    v = tuple(x-y for x, y in zip(c, b))
    denominator = math.sqrt(sum(x*x for x in u) * sum(x*x for x in v))
    if denominator < 1e-10:
        return 0.0
    cosine = sum(x*y for x, y in zip(u, v)) / denominator
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def classify_hand(landmarks, aspect: float = 1.0) -> Gesture:
    """Accept 21 (x,y,z) tuples; thumb is ignored for left/right-hand symmetry.

    Joint angles and wrist distances avoid a simple y-axis 'finger up' test.
    aspect = video width / height; MediaPipe z uses the normalized x scale.
    """
    if landmarks is None or len(landmarks) != 21:
        return Gesture.NONE
    points = [(float(x), float(y)/aspect, float(z)) for x, y, z in landmarks]
    if not all(math.isfinite(value) for point in points for value in point):
        return Gesture.NONE
    extended = []
    for base in (5, 9, 13, 17):
        mcp, pip, dip, tip = (points[base+i] for i in range(4))
        straight = _angle(mcp, pip, dip) > 155 and _angle(pip, dip, tip) > 150
        away = _distance(tip, points[0]) > 1.10 * _distance(pip, points[0])
        extended.append(straight and away)
    if extended == [True, False, False, False]:
        return Gesture.DRAW
    if extended == [True, True, False, False]:
        return Gesture.SELECT
    return Gesture.PAUSE


class GestureGate:
    """Require stable DRAW entry; exits and no-hand never wait for debounce."""
    def __init__(self, frames: int = 3):
        self.frames = max(1, frames)
        self._last = Gesture.NONE
        self._count = 0

    def update(self, gesture: Gesture) -> Gesture:
        self._count = self._count + 1 if gesture == self._last else 1
        self._last = gesture
        if gesture == Gesture.DRAW and self._count < self.frames:
            return Gesture.PAUSE
        return gesture

    def reset(self):
        self._last, self._count = Gesture.NONE, 0


class DwellSelector:
    """One activation per button entry; monotonic seconds are supplied by caller."""
    def __init__(self, seconds: float = 0.65):
        self.seconds = seconds
        self.target = None
        self.started = 0.0
        self.fired = False
        self.progress = 0.0

    def update(self, target: str | None, now: float) -> str | None:
        if target != self.target:
            self.target, self.started, self.fired = target, now, False
        self.progress = 0.0 if target is None else min(1.0, max(0.0, (now-self.started)/self.seconds))
        if target is not None and self.progress >= 1.0 and not self.fired:
            self.fired = True
            return target
        return None

