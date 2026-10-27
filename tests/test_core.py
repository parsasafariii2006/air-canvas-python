"""Behavioral checks: no webcam, GUI or network required."""
import math
from pathlib import Path
import tempfile
import unittest

import cv2
import numpy as np

from air_canvas.canvas import Canvas
from air_canvas.gestures import Gesture, classify_hand, GestureGate, DwellSelector


class CanvasTests(unittest.TestCase):
    def test_ink_composites_over_white_and_camera(self):
        canvas = Canvas(120, 80)
        canvas.draw((20, 30), (0, 0, 255), 9)
        canvas.draw((80, 30), (0, 0, 255), 9)
        canvas.end_stroke()
        self.assertEqual(canvas.image[30, 50].tolist(), [0, 0, 255, 255])
        frame = np.full((80, 120, 3), 55, np.uint8)
        result = canvas.composite(frame)
        self.assertEqual(result[30, 50].tolist(), [0, 0, 255])
        self.assertEqual(result[60, 50].tolist(), [55, 55, 55])

    def test_eraser_removes_alpha_and_undo_restores_stroke(self):
        canvas = Canvas(120, 80)
        canvas.draw((30, 30), (100, 40, 255), 15)
        canvas.end_stroke()
        canvas.draw((30, 30), (0, 0, 0), 20, erase=True)
        canvas.end_stroke()
        self.assertEqual(int(canvas.image[30, 30, 3]), 0)
        canvas.undo()
        self.assertEqual(int(canvas.image[30, 30, 3]), 255)
        canvas.redo()
        self.assertEqual(int(canvas.image[30, 30, 3]), 0)

    def test_interruption_and_tracking_jump_do_not_join_strokes(self):
        canvas = Canvas(400, 200, max_jump=70)
        canvas.draw((20, 40), (0, 255, 0), 5)
        canvas.end_stroke()
        canvas.draw((100, 40), (0, 255, 0), 5)
        canvas.draw((300, 40), (0, 255, 0), 5)
        self.assertEqual(int(canvas.image[40, 60, 3]), 0)
        self.assertEqual(int(canvas.image[40, 200, 3]), 0)

    def test_clear_is_undoable_and_new_ink_invalidates_redo(self):
        canvas = Canvas(120, 80)
        canvas.draw((30, 30), (0, 0, 0), 9)
        canvas.end_stroke()
        canvas.clear()
        self.assertFalse(canvas.has_ink)
        canvas.undo()
        self.assertTrue(canvas.has_ink)
        canvas.undo()
        canvas.draw((70, 50), (0, 255, 0), 9)
        canvas.end_stroke()
        self.assertFalse(canvas.redo())

    def test_export_preserves_transparency_and_supports_unicode_paths(self):
        canvas = Canvas(120, 80)
        canvas.draw((30, 30), (0, 0, 255), 9)
        with tempfile.TemporaryDirectory(prefix='canvas_') as folder:
            target = Path(folder) / '\u0646\u0642\u0627\u0634\u06cc'
            white, transparent = canvas.save(target)
            opaque = cv2.imdecode(np.fromfile(white, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
            alpha = cv2.imdecode(np.fromfile(transparent, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
            self.assertEqual(opaque[0, 0].tolist(), [255, 255, 255])
            self.assertEqual(alpha.shape, (80, 120, 4))
            self.assertEqual(int(alpha[0, 0, 3]), 0)
            self.assertEqual(int(alpha[30, 30, 3]), 255)
            again = canvas.save(target)
            self.assertNotEqual(white, again[0])


def hand_fixture(extended, angle=0):
    """Independent schematic landmarks, before 2D rotation around the wrist."""
    points = [(0.0, 0.0, 0.0)] * 21
    for finger, base in enumerate((5, 9, 13, 17)):
        x = (finger - 1.5) * 0.10
        points[base] = (x, -0.25, 0)
        points[base + 1] = (x, -0.45, 0)
        points[base + 2] = (x, -0.60, 0) if extended[finger] else (x, -0.30, 0.03)
        points[base + 3] = (x, -0.75, 0) if extended[finger] else (x, -0.20, 0.05)
    c, s = math.cos(angle), math.sin(angle)
    return [(0.5 + c*x - s*y, 0.8 + s*x + c*y, z) for x, y, z in points]


class GestureTests(unittest.TestCase):
    def test_index_only_draws_even_when_hand_is_rotated(self):
        for angle in (0, math.pi/2, math.pi, -math.pi/3):
            with self.subTest(angle=angle):
                self.assertEqual(classify_hand(hand_fixture((True, False, False, False), angle)), Gesture.DRAW)

    def test_two_fingers_select_palm_fist_and_no_hand_pause(self):
        self.assertEqual(classify_hand(hand_fixture((True, True, False, False))), Gesture.SELECT)
        self.assertEqual(classify_hand(hand_fixture((True, True, True, True))), Gesture.PAUSE)
        self.assertEqual(classify_hand(hand_fixture((False, False, False, False))), Gesture.PAUSE)
        self.assertEqual(classify_hand(None), Gesture.NONE)

    def test_draw_requires_stability_but_tracking_loss_stops_immediately(self):
        gate = GestureGate(frames=3)
        self.assertEqual(gate.update(Gesture.DRAW), Gesture.PAUSE)
        self.assertEqual(gate.update(Gesture.DRAW), Gesture.PAUSE)
        self.assertEqual(gate.update(Gesture.DRAW), Gesture.DRAW)
        self.assertEqual(gate.update(Gesture.NONE), Gesture.NONE)
        self.assertEqual(gate.update(Gesture.DRAW), Gesture.PAUSE)

    def test_dwell_fires_once_until_cursor_leaves_button(self):
        dwell = DwellSelector(seconds=0.5)
        self.assertIsNone(dwell.update('undo', 10.0))
        self.assertEqual(dwell.update('undo', 10.51), 'undo')
        self.assertIsNone(dwell.update('undo', 12.0))
        dwell.update(None, 12.1)
        self.assertIsNone(dwell.update('undo', 12.2))
        self.assertEqual(dwell.update('undo', 12.71), 'undo')


if __name__ == '__main__':
    unittest.main()

