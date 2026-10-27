"""Application controller and desktop loop; hardware starts only in run()."""
from pathlib import Path
import math
import time

import cv2

from . import config as C
from .canvas import Canvas
from .gestures import Gesture, GestureGate, DwellSelector, classify_hand
from . import ui


class AirCanvasApp:
    def __init__(self, mouse=False, camera_index=0, output_dir=C.DRAWINGS_PATH,
                 demo=False, clock=time.monotonic):
        self.canvas = Canvas(C.CANVAS_WIDTH, C.CANVAS_HEIGHT)
        self.mouse_mode = mouse or demo
        self.camera_index = camera_index
        self.output_dir = Path(output_dir)
        self.clock = clock
        self.color_index, self.brush = 0, 8
        self.eraser, self.paused = False, False
        self.white_background, self.mirror = True, True
        self.gesture, self.cursor = Gesture.NONE, None
        self.landmarks, self.frame = None, None
        self.fps = 0.0
        self.notice, self.notice_until = "", 0.0
        self.dwell = DwellSelector()
        self.gate = GestureGate()
        self.camera, self.tracker = None, None
        self._smoothed, self._raw_previous = None, None
        self._mouse_down = False
        self.saved_version = 0
        if demo:
            self._seed_demo()

    def notify(self, message, duration=4):
        self.notice = message
        self.notice_until = self.clock() + duration
        print(message)

    def reset_pointer(self):
        self.canvas.end_stroke()
        self._smoothed, self._raw_previous = None, None
        self._mouse_down = False
        self.dwell.update(None, self.clock())
        self.gate.reset()

    def process_pointer(self, point, gesture, now):
        self.cursor, self.gesture = point, gesture
        target = ui.button_at(point) if point is not None and gesture == Gesture.SELECT else None
        action = self.dwell.update(target, now)
        if action is not None:
            self.handle_action(action)
        if self.paused or point is None or gesture != Gesture.DRAW:
            self.canvas.end_stroke()
            return
        x, y = point
        if y < C.TOOLBAR_HEIGHT:
            self.canvas.end_stroke()
            return
        self.canvas.draw((x, y-C.TOOLBAR_HEIGHT), C.PALETTE[self.color_index][1],
                         self.brush * (3 if self.eraser else 1), erase=self.eraser)

    def process_hand(self, landmarks, now):
        # Both gesture logic and skeleton rendering consume these coordinates.
        # Reject bad observations at their shared boundary, before int/round.
        if landmarks is not None:
            try:
                valid = len(landmarks) == 21 and all(
                    len(point) == 3 and all(math.isfinite(v) and abs(v) <= 10 for v in point)
                    for point in landmarks)
            except (TypeError, ValueError):
                valid = False
            if not valid:
                landmarks = None
        self.landmarks = landmarks
        gesture = self.gate.update(classify_hand(landmarks, C.BOARD_WIDTH/C.BOARD_HEIGHT))
        if landmarks is None:
            self._smoothed, self._raw_previous = None, None
            self.process_pointer(None, gesture, now)
            return
        x, y, _ = landmarks[8]
        raw = (round(x*C.BOARD_WIDTH), round(y*C.BOARD_HEIGHT))
        if gesture == Gesture.DRAW and not self.paused and raw[1] >= C.TOOLBAR_HEIGHT:
            if self._raw_previous is not None and math.dist(raw, self._raw_previous) > 180:
                self.canvas.end_stroke()
                self._smoothed = None
            self._smoothed = raw if self._smoothed is None else tuple(
                previous + 0.45*(current-previous) for previous, current in zip(self._smoothed, raw))
            point = tuple(round(v) for v in self._smoothed)
            self._raw_previous = raw
        else:
            self._smoothed, self._raw_previous = None, None
            point = raw
        self.process_pointer(point, gesture, now)

    def handle_action(self, action):
        self.canvas.end_stroke()
        self._smoothed, self._raw_previous = None, None
        if action.startswith('color:'):
            self.color_index = int(action.split(':')[1])
            self.eraser = False
        elif action == 'pen':
            self.eraser = False
        elif action == 'eraser':
            self.eraser = True
        elif action in ('smaller', 'larger'):
            self.brush = max(C.BRUSH_MIN, min(C.BRUSH_MAX, self.brush + (2 if action == 'larger' else -2)))
        elif action == 'undo':
            self.notify('Undo' if self.canvas.undo() else 'Nothing to undo')
        elif action == 'redo':
            self.notify('Redo' if self.canvas.redo() else 'Nothing to redo')
        elif action == 'clear':
            self.canvas.clear()
            self.notify('Canvas cleared. Press Z to restore.')
        elif action == 'background':
            self.white_background = not self.white_background
        elif action == 'save':
            self.save()

    def save(self):
        try:
            white, transparent = self.canvas.save(self.output_dir)
            self.saved_version = self.canvas.version
            self.notify('Saved: white PNG + transparent PNG')
            print(f'  {white}\n  {transparent}')
            return white, transparent
        except (OSError, cv2.error) as exc:
            self.notify('Save failed. Check the output folder permissions.', 8)
            print(f'Save error: {exc}')
            return None

    def handle_key(self, key):
        if key in (27, ord('q'), ord('Q')):
            return False
        if 65 <= key <= 90:
            key += 32
        actions = {
            ord('s'): 'save', ord('e'): 'eraser', ord('p'): 'pen',
            ord('z'): 'undo', ord('y'): 'redo', ord('c'): 'clear',
            ord('b'): 'background', ord('+'): 'larger', ord('='): 'larger',
            ord('-'): 'smaller', ord('_'): 'smaller',
        }
        if key in actions:
            self.handle_action(actions[key])
        elif ord('1') <= key <= ord('6'):
            self.handle_action(f'color:{key-ord("1")}')
        elif key == ord(' '):
            self.paused = not self.paused
            self.reset_pointer()
        elif key == ord('f'):
            self.mirror = not self.mirror
            self.reset_pointer()
        elif key == ord('m'):
            self.reset_pointer()
            if self.mouse_mode:
                self.start_hand_mode()
            else:
                self.stop_hand_mode()
                self.notify('Mouse mode: click and drag to draw.')
        return True

    def on_mouse(self, event, x, y, flags, _param):
        point = (x-C.BOARD_X, y-C.BOARD_Y)
        inside = 0 <= point[0] < C.BOARD_WIDTH and 0 <= point[1] < C.BOARD_HEIGHT
        if event == cv2.EVENT_LBUTTONDOWN and inside and point[1] < C.TOOLBAR_HEIGHT:
            self.reset_pointer()
            action = ui.button_at(point)
            if action:
                self.handle_action(action)
            return
        if not self.mouse_mode:
            return
        if event == cv2.EVENT_LBUTTONDOWN and inside:
            self._mouse_down = True
        elif event == cv2.EVENT_LBUTTONUP:
            self._mouse_down = False
            self.canvas.end_stroke()
        elif event == cv2.EVENT_MOUSEMOVE and not flags & cv2.EVENT_FLAG_LBUTTON:
            self._mouse_down = False
        self.process_pointer(point if inside else None,
                             Gesture.DRAW if self._mouse_down else Gesture.PAUSE, self.clock())

    def start_hand_mode(self):
        from .camera import Camera
        from .tracking import HandTracker
        self.stop_hand_mode()
        try:
            self.camera = Camera(self.camera_index)
            self.tracker = HandTracker()
            self.mouse_mode = False
            self.notify('Hand mode: index to draw; two fingers to choose tools.')
        except Exception as exc:
            self.stop_hand_mode()
            self.notify('Camera or tracker unavailable. Mouse mode is ready.', 10)
            print(f'Hand mode error: {exc}')

    def stop_hand_mode(self):
        if self.tracker is not None:
            self.tracker.close()
            self.tracker = None
        if self.camera is not None:
            self.camera.close()
            self.camera = None
        self.mouse_mode = True
        self.frame, self.landmarks, self.cursor = None, None, None
        self.reset_pointer()

    def render(self):
        return ui.render(self)

    def run(self, max_frames=None):
        if not self.mouse_mode:
            self.start_hand_mode()
        failures, count = 0, 0
        previous = self.clock()
        try:
            cv2.namedWindow(C.WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
            cv2.setMouseCallback(C.WINDOW_NAME, self.on_mouse)
            while True:
                now = self.clock()
                if not self.mouse_mode:
                    try:
                        self.frame = self.camera.read(self.mirror)
                        if self.frame is None:
                            failures += 1
                            self.process_hand(None, now)
                            if failures >= 8:
                                raise RuntimeError('Camera stopped returning frames.')
                        else:
                            failures = 0
                            self.process_hand(self.tracker.detect(self.frame), now)
                    except Exception as exc:
                        self.stop_hand_mode()
                        self.notify('Camera disconnected. Switched to mouse mode.', 8)
                        print(f'Camera/tracking error: {exc}')
                elapsed = max(1e-4, now-previous)
                self.fps = 0.9*self.fps + 0.1/elapsed
                previous = now
                cv2.imshow(C.WINDOW_NAME, self.render())
                key = cv2.waitKey(12)
                count += 1
                if not self.handle_key(key) or (max_frames is not None and count >= max_frames):
                    break
                if cv2.getWindowProperty(C.WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                    break
        finally:
            self.stop_hand_mode()
            if self.canvas.has_ink and self.canvas.version != self.saved_version:
                self.save()
            cv2.destroyAllWindows()

    def _seed_demo(self):
        # A deterministic sample artwork, not a claim of live hand input.
        for index, (cx, cy, radius) in enumerate(((220, 245, 130), (415, 245, 130), (610, 245, 130))):
            for t in range(181):
                angle = math.radians(t*2)
                point = (round(cx+radius*math.cos(angle)), round(cy+radius*math.sin(angle)))
                self.canvas.draw(point, C.PALETTE[index][1], 12)
            self.canvas.end_stroke()
        self.saved_version = self.canvas.version

