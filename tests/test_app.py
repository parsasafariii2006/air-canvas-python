import tempfile
import unittest
from pathlib import Path
import numpy as np

from air_canvas.app import AirCanvasApp
from air_canvas.config import BOARD_X, BOARD_Y, TOOLBAR_HEIGHT
from air_canvas.gestures import Gesture


class AppTests(unittest.TestCase):
    def test_pause_then_resume_does_not_bridge_separate_marks(self):
        app = AirCanvasApp(mouse=True)
        app.process_pointer((50, 180), Gesture.DRAW, 1)
        app.handle_key(ord(' '))
        app.process_pointer((150, 180), Gesture.DRAW, 2)
        app.handle_key(ord(' '))
        app.process_pointer((200, 180), Gesture.DRAW, 3)
        self.assertEqual(int(app.canvas.image[100, 120, 3]), 0)
        self.assertEqual(int(app.canvas.image[100, 200, 3]), 255)

    def test_toolbar_dwell_selects_color_without_drawing(self):
        app = AirCanvasApp(mouse=True)
        point = (120, 32)  # Third swatch, coral.
        app.process_pointer(point, Gesture.SELECT, 1.0)
        app.process_pointer(point, Gesture.SELECT, 1.7)
        self.assertEqual(app.color_index, 2)
        self.assertFalse(app.canvas.has_ink)

    def test_mouse_stroke_and_clear_can_be_undone(self):
        import cv2
        app = AirCanvasApp(mouse=True)
        x, y = BOARD_X + 70, BOARD_Y + TOOLBAR_HEIGHT + 80
        app.on_mouse(cv2.EVENT_LBUTTONDOWN, x, y, 0, None)
        app.on_mouse(cv2.EVENT_MOUSEMOVE, x + 40, y, cv2.EVENT_FLAG_LBUTTON, None)
        app.on_mouse(cv2.EVENT_LBUTTONUP, x + 40, y, 0, None)
        self.assertEqual(int(app.canvas.image[80, 90, 3]), 255)
        app.handle_key(ord('c'))
        self.assertFalse(app.canvas.has_ink)
        app.handle_key(ord('z'))
        self.assertTrue(app.canvas.has_ink)

    def test_save_creates_two_files_in_configured_output(self):
        with tempfile.TemporaryDirectory() as folder:
            app = AirCanvasApp(mouse=True, output_dir=Path(folder))
            app.process_pointer((50, 180), Gesture.DRAW, 1)
            app.handle_key(ord('s'))
            self.assertEqual(len(list(Path(folder).glob('*.png'))), 2)
            self.assertEqual(app.saved_version, app.canvas.version)

    def test_renderer_has_expected_dimensions_without_camera(self):
        app = AirCanvasApp(mouse=True)
        screen = app.render()
        self.assertEqual(screen.shape, (800, 1280, 3))
        self.assertEqual(screen.dtype, np.uint8)

    def test_invalid_landmarks_are_tracking_loss_not_render_or_round_errors(self):
        for index, value in ((8, float('nan')), (5, float('nan')), (8, float('inf'))):
            with self.subTest(index=index, value=value):
                app = AirCanvasApp(mouse=True)
                app.frame = np.zeros((600, 960, 3), np.uint8)
                app.process_pointer((40, 180), Gesture.DRAW, 0)
                landmarks = [(0.5, 0.5, 0.0)] * 21
                landmarks[index] = (value, 0.5, 0.0)
                app.process_hand(landmarks, 1)
                self.assertEqual(app.gesture, Gesture.NONE)
                self.assertIsNone(app.landmarks)
                self.assertIsNone(app.cursor)
                self.assertEqual(app.render().shape, (800, 1280, 3))


if __name__ == '__main__':
    unittest.main()

