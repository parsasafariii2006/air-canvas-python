"""OpenCV desktop renderer. No camera, model or window is opened here."""
from dataclasses import dataclass
import cv2
import numpy as np

from . import config as C

BG = (23, 21, 18)
CARD = (35, 32, 28)
LINE = (62, 57, 49)
TEXT = (242, 239, 231)
MUTED = (165, 156, 141)
ACCENT = (170, 235, 60)


@dataclass(frozen=True)
class Button:
    action: str
    label: str
    rect: tuple[int, int, int, int]
    color: tuple[int, int, int] | None = None

    def contains(self, point):
        x, y, w, h = self.rect
        return x <= point[0] < x+w and y <= point[1] < y+h


def toolbar_buttons():
    buttons = [Button(f"color:{i}", str(i+1), (14+46*i, 17, 36, 42), color)
               for i, (_, color) in enumerate(C.PALETTE)]
    for action, label, x, w in (
        ("pen", "PEN", 306, 54), ("eraser", "ERASE", 366, 68),
        ("smaller", "-", 444, 32), ("larger", "+", 482, 32),
        ("undo", "UNDO", 526, 64), ("redo", "REDO", 596, 64),
        ("save", "SAVE", 672, 68), ("clear", "CLEAR", 746, 68),
        ("background", "VIEW", 826, 118),
    ):
        buttons.append(Button(action, label, (x, 17, w, 42)))
    return buttons


BUTTONS = toolbar_buttons()


def button_at(point):
    return next((button.action for button in BUTTONS if button.contains(point)), None)


def text(image, value, xy, scale=0.48, color=TEXT, thickness=1):
    cv2.putText(image, str(value), xy, cv2.FONT_HERSHEY_SIMPLEX,
                scale, color, thickness, cv2.LINE_AA)


def rounded(image, rect, color, radius=12):
    x, y, w, h = rect
    r = min(radius, w//2, h//2)
    cv2.rectangle(image, (x+r, y), (x+w-r-1, y+h-1), color, -1)
    cv2.rectangle(image, (x, y+r), (x+w-1, y+h-r-1), color, -1)
    for cx, cy in ((x+r, y+r), (x+w-r-1, y+r), (x+r, y+h-r-1), (x+w-r-1, y+h-r-1)):
        cv2.circle(image, (cx, cy), r, color, -1, cv2.LINE_AA)


CONNECTIONS = ((0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
               (5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),
               (15,16),(13,17),(0,17),(17,18),(18,19),(19,20))


def draw_skeleton(frame, landmarks):
    if landmarks is None:
        return
    h, w = frame.shape[:2]
    points = [(int(x*w), int(y*h)) for x, y, _ in landmarks]
    for a, b in CONNECTIONS:
        cv2.line(frame, points[a], points[b], ACCENT, 2, cv2.LINE_AA)
    for point in points:
        cv2.circle(frame, point, 3, TEXT, -1, cv2.LINE_AA)


def render(app):
    screen = np.full((C.WINDOW_HEIGHT, C.WINDOW_WIDTH, 3), BG, np.uint8)
    rounded(screen, (24, 24, 40, 40), ACCENT, 10)
    cv2.line(screen, (35, 52), (44, 34), BG, 3, cv2.LINE_AA)
    cv2.line(screen, (44, 34), (53, 52), BG, 3, cv2.LINE_AA)
    cv2.line(screen, (39, 46), (49, 46), BG, 2, cv2.LINE_AA)
    text(screen, "AIR CANVAS", (78, 48), 0.86, TEXT, 2)
    text(screen, "YOUR HAND. YOUR IDEAS.", (79, 72), 0.37, MUTED)
    badge = "PAUSED" if app.paused else ("MOUSE MODE" if app.mouse_mode else "HAND MODE")
    rounded(screen, (1050, 30, 206, 36), CARD, 10)
    cv2.circle(screen, (1068, 48), 4, MUTED if app.paused else ACCENT, -1)
    text(screen, badge, (1082, 54), 0.43)

    board = np.full((C.BOARD_HEIGHT, C.BOARD_WIDTH, 3), 255, np.uint8)
    background = None if app.white_background or app.frame is None else app.frame[C.TOOLBAR_HEIGHT:]
    board[C.TOOLBAR_HEIGHT:] = app.canvas.composite(background)
    board[:C.TOOLBAR_HEIGHT] = CARD
    cv2.line(board, (0, 77), (959, 77), LINE, 1)
    for button in BUTTONS:
        x, y, w, h = button.rect
        active = (button.action == f"color:{app.color_index}" and not app.eraser) or (
            button.action == "eraser" and app.eraser) or (button.action == "pen" and not app.eraser)
        if button.color is not None:
            if active:
                rounded(board, (x-3, y-3, w+6, h+6), TEXT, 10)
            rounded(board, button.rect, button.color, 8)
            text(board, button.label, (x+14, y+27), 0.40, TEXT if button.action == 'color:5' else BG)
        else:
            rounded(board, button.rect, ACCENT if active else (51, 47, 41), 8)
            label = ("WHITE" if app.white_background else "CAMERA") if button.action == "background" else button.label
            size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)[0]
            text(board, label, (x+(w-size[0])//2, y+26), 0.40, BG if active else TEXT)
        if app.dwell.target == button.action and app.dwell.progress > 0:
            cv2.line(board, (x, y+h+6), (x+int(w*app.dwell.progress), y+h+6), ACCENT, 3)

    if app.cursor is not None:
        x, y = app.cursor
        if 0 <= x < C.BOARD_WIDTH and 0 <= y < C.BOARD_HEIGHT:
            color = MUTED if app.paused else (TEXT if app.eraser else C.PALETTE[app.color_index][1])
            radius = max(6, (app.brush * (3 if app.eraser else 1))//2)
            cv2.circle(board, (x, y), radius+2, BG, 2, cv2.LINE_AA)
            cv2.circle(board, (x, y), radius, color, 2, cv2.LINE_AA)
            cv2.circle(board, (x, y), 2, color, -1, cv2.LINE_AA)
    screen[C.BOARD_Y:C.BOARD_Y+C.BOARD_HEIGHT, C.BOARD_X:C.BOARD_X+C.BOARD_WIDTH] = board

    sx = 1012
    rounded(screen, (sx, 108, 244, 156), CARD)
    if app.frame is not None:
        preview = app.frame.copy()
        draw_skeleton(preview, app.landmarks)
        screen[116:256, sx+8:sx+236] = cv2.resize(preview, (228, 140))
    else:
        cv2.circle(screen, (sx+122, 164), 22, LINE, 1, cv2.LINE_AA)
        cv2.circle(screen, (sx+122, 164), 9, ACCENT, -1, cv2.LINE_AA)
        text(screen, "NO CAMERA NEEDED", (sx+35, 214), 0.43)
        text(screen, "Click and drag to draw", (sx+33, 240), 0.37, MUTED)

    text(screen, "GESTURE", (sx, 298), 0.35, MUTED)
    state = "PAUSED" if app.paused else ("CLICK + DRAG" if app.mouse_mode else app.gesture.value)
    text(screen, state, (sx, 329), 0.66, ACCENT, 2)
    cv2.line(screen, (sx, 350), (1256, 350), LINE, 1)
    text(screen, "HOW IT WORKS", (sx, 381), 0.39, MUTED)
    for y, number, title, detail in (
        (413, "01", "INDEX FINGER", "Only index extended: draw"),
        (474, "02", "TWO FINGERS", "Hover on a tool for 0.65s"),
        (535, "03", "RELAX YOUR HAND", "Other poses lift the pen"),
    ):
        text(screen, number, (sx, y), 0.43, ACCENT)
        text(screen, title, (sx+32, y), 0.40)
        text(screen, detail, (sx, y+22), 0.34, MUTED)

    rounded(screen, (sx, 583, 244, 125), CARD)
    text(screen, "BRUSH", (sx+16, 610), 0.35, MUTED)
    text(screen, f"{app.brush} px", (sx+152, 611), 0.49)
    cv2.line(screen, (sx+17, 632), (sx+225, 632), LINE, 4)
    amount = int((app.brush-C.BRUSH_MIN)/(C.BRUSH_MAX-C.BRUSH_MIN)*208)
    cv2.line(screen, (sx+17, 632), (sx+17+amount, 632), ACCENT, 4)
    cv2.circle(screen, (sx+17+amount, 632), 5, TEXT, -1)
    text(screen, "E  Eraser    P  Pen", (sx+16, 664), 0.37, MUTED)
    text(screen, "+ / -  Brush size", (sx+16, 688), 0.37, MUTED)

    text(screen, "S  SAVE     Z / Y  UNDO / REDO     C  CLEAR     SPACE  PAUSE", (24, 744), 0.41)
    text(screen, "1-6  COLOR     B  VIEW     M  HAND / MOUSE     F  MIRROR     ESC  EXIT", (24, 772), 0.35, MUTED)
    text(screen, f"{app.fps:02.0f} FPS", (1180, 744), 0.40, MUTED)
    if app.notice and app.clock() < app.notice_until:
        rounded(screen, (230, 654, 550, 38), BG, 8)
        text(screen, app.notice[:64], (245, 679), 0.43, ACCENT)
    return screen

