"""Application dimensions, paths and palette (OpenCV colors are BGR)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "hand_landmarker.task"
DRAWINGS_PATH = ROOT / "drawings"
WINDOW_NAME = "Air Canvas"
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 800
BOARD_X, BOARD_Y = 24, 108
BOARD_WIDTH, BOARD_HEIGHT = 960, 600
TOOLBAR_HEIGHT = 80
CANVAS_WIDTH, CANVAS_HEIGHT = BOARD_WIDTH, BOARD_HEIGHT - TOOLBAR_HEIGHT

PALETTE = (
    ("MINT", (170, 235, 60)),
    ("BLUE", (255, 145, 70)),
    ("CORAL", (105, 100, 255)),
    ("GOLD", (60, 205, 250)),
    ("VIOLET", (245, 135, 185)),
    ("INK", (44, 36, 29)),
)
BRUSH_MIN, BRUSH_MAX = 2, 48
HISTORY_LIMIT = 20

