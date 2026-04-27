import sys
import os

# To compile
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)

import tkinter as tk
from PIL import Image, ImageTk
import colorsys
import math
import shutil
import time
import ctypes
import random
import threading
import cv2

try:
    import pygame
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.mixer.init()
    _audio_ok = True
except Exception:
    _audio_ok = False

# Vars
ROWS = 4
COLS = 2
SIZE = 130
SPACING = 12
TITLEBAR_HEIGHT = 30

SWAP_DURATION = 0.45
CIRCLE_DURATION = 0.6
PAUSE_BETWEEN_SWAPS = 0.05
PAUSE_MIN = 0.4
PAUSE_MAX = 0.4

SWAPS_BEFORE_CIRCLE = 3
FLIPPED_SWAP_COUNT  = 10
PHASE_NORMAL_DURATION = 8.0

FLASH_HOLD       = 1400
FLASH_FADE_STEPS = 24
FLASH_FADE_MS    = 50
MUSIC_DELAY_MS   = 100
PRE_MOVE_DELAY   = 150

CIRCLE_RADIUS       = 220
CIRCLE_ROTATE_SPEED = 0.12
TRANSITION_DURATION = 1.4
COLORIZE_HUES       = [0, 30, 60, 120, 180, 210, 270, 300]

REVEAL_DURATION  = 1.4
REVEAL_STEPS     = 48
MEMORIZE_HOLD_MS = 3000

CORRECT_VIDEO = resource_path("Win.mp4")
WRONG_VIDEO   = resource_path("death.mp4")

CORRECT_KEY = random.randint(0, 7)

# TKinter
root = tk.Tk()
root.withdraw()

screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()

offset_x = screen_w - (COLS * (SIZE + SPACING)) - 50
offset_y = (screen_h // 2) - (ROWS * (SIZE + SPACING + TITLEBAR_HEIGHT)) // 2

screen_center_x = screen_w / 2 - SIZE / 2
screen_center_y = screen_h / 2 - SIZE / 2

positions = []
for r in range(ROWS):
    for c in range(COLS):
        x = offset_x + c * (SIZE + SPACING)
        y = offset_y + r * (SIZE + SPACING + TITLEBAR_HEIGHT)
        positions.append((x, y))

def load_and_scale(path, size):
    img = Image.open(path).convert("RGBA")
    img = img.resize((size, size), Image.LANCZOS)
    return img

def tint_image(pil_img, hue_deg, saturation=0.85):
    img = pil_img.convert("RGB")
    pixels = list(img.getdata())
    new_pixels = []
    for r, g, b in pixels:
        h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
        h = hue_deg / 360.0
        s = saturation
        nr, ng, nb = colorsys.hls_to_rgb(h, l, s)
        new_pixels.append((int(nr*255), int(ng*255), int(nb*255)))
    result = Image.new("RGB", pil_img.size)
    result.putdata(new_pixels)
    return result

base_img = load_and_scale(resource_path("key.png"), SIZE)

NORMAL_HUE  = 15
CORRECT_HUE = 120

normal_photo  = ImageTk.PhotoImage(tint_image(base_img, NORMAL_HUE))
correct_photo = ImageTk.PhotoImage(tint_image(base_img, CORRECT_HUE))

SPIN_STEPS = 60
spin_frames_normal = []
for step in range(SPIN_STEPS + 1):
    angle = 180.0 * step / SPIN_STEPS
    spin_frames_normal.append(
        ImageTk.PhotoImage(tint_image(base_img, NORMAL_HUE).rotate(angle, resample=Image.BICUBIC))
    )

normal_photo_flipped = spin_frames_normal[SPIN_STEPS]

fade_frames = []
for step in range(FLASH_FADE_STEPS + 1):
    t_f = step / FLASH_FADE_STEPS
    hue = CORRECT_HUE + (NORMAL_HUE - CORRECT_HUE) * t_f
    fade_frames.append(ImageTk.PhotoImage(tint_image(base_img, hue)))

shuffled_hues = COLORIZE_HUES[:]
random.shuffle(shuffled_hues)

color_photos_upright = [ImageTk.PhotoImage(tint_image(base_img, h)) for h in shuffled_hues]

#Render hue shift
reveal_frames = []
print("Rendering Hue shift to use later")
for key_idx in range(8):
    target_hue = shuffled_hues[key_idx]
    frames = []
    for step in range(REVEAL_STEPS + 1):
        t   = step / REVEAL_STEPS
        t_e = 1.0 - (1.0 - t) ** 3
        hue   = NORMAL_HUE + (target_hue - NORMAL_HUE) * t_e
        angle = 180.0 * (1.0 - t_e)
        tinted = tint_image(base_img, hue)
        if angle > 0.5:
            tinted = tinted.rotate(angle, resample=Image.BICUBIC)
        frames.append(ImageTk.PhotoImage(tinted))
    reveal_frames.append(frames)
print("Done.")

is_flipped      = False
movement_active = False

def start_movement():
    global movement_active
    movement_active = True
    swap_queue.extend(generate_shuffle())
    start_next_swap()

def do_flash_fade(step=0):
    w = windows[CORRECT_KEY]
    if step > FLASH_FADE_STEPS:
        w["canvas"].itemconfig(w["canvas_img"], image=normal_photo)
        root.after(PRE_MOVE_DELAY, start_movement)
        return
    w["canvas"].itemconfig(w["canvas_img"], image=fade_frames[step])
    root.after(FLASH_FADE_MS, lambda s=step+1: do_flash_fade(s))

def begin_flash():
    windows[CORRECT_KEY]["canvas"].itemconfig(windows[CORRECT_KEY]["canvas_img"], image=correct_photo)
    root.after(FLASH_HOLD, lambda: do_flash_fade(0))
    if _audio_ok:
        def play_music():
            try:
                pygame.mixer.music.load(resource_path("Limbo.mp3"))
                pygame.mixer.music.set_volume(0.4)
                pygame.mixer.music.play(1)
            except Exception:
                pass
        root.after(MUSIC_DELAY_MS, play_music)

root.after(300, begin_flash)

#Winows
windows = []
for i in range(8):
    win = tk.Toplevel()
    win.title(f"Key {i+1}")
    win.resizable(False, False)
    win.attributes("-topmost", True)
    win.deiconify()

    canvas = tk.Canvas(win, width=SIZE, height=SIZE, bg="black", highlightthickness=0)
    canvas.pack()

    canvas_img = canvas.create_image(SIZE // 2, SIZE // 2, image=normal_photo)

    x, y = positions[i]
    win.geometry(f"{SIZE}x{SIZE}+{int(x)}+{int(y)}")
    win.lift()

    windows.append({
        "win":        win,
        "canvas":     canvas,
        "canvas_img": canvas_img,
        "pos":        i,
        "is_correct": (i == CORRECT_KEY),
    })

win_x = [float(positions[i][0]) for i in range(8)]
win_y = [float(positions[i][1]) for i in range(8)]
arc_paths = [None] * 8

def ease_quintic(t):
    if t < 0.5:
        return 16 * t**5
    else:
        return 1 - (-2*t + 2)**5 / 2

def ease_out_cubic(t):
    return 1 - (1 - t)**3

swap_queue         = []
state              = "still"
timer              = 0.0
pause_time         = random.uniform(PAUSE_MIN, PAUSE_MAX)
swaps_done         = 0
normal_phase_swaps = 0
flipped_swaps_done = 0
circle_t           = 0.0
phase_clock        = 0.0
game_phase         = "normal"
_flip_triggered    = False

reveal_t              = 0.0
circle_angle          = 0.0
transition_t          = 0.0
transition_start_pos  = []
clickable             = False
result_shown          = False

def generate_shuffle():
    num_swaps = random.randint(4, 7)
    return [tuple(random.sample(range(8), 2)) for _ in range(num_swaps)]

def start_next_swap():
    global state, timer, pause_time, swaps_done, normal_phase_swaps, flipped_swaps_done

    if not movement_active or game_phase == "still":
        return

    if swap_queue:
        i, j = swap_queue.pop(0)
        swaps_done += 1

        if game_phase == "normal":
            normal_phase_swaps += 1
        elif game_phase == "flipped":
            flipped_swaps_done += 1
            limit = FLIPPED_SWAP_COUNT if FLIPPED_SWAP_COUNT > 0 else normal_phase_swaps
            if flipped_swaps_done >= limit:
                swap_queue.clear()

        pi = windows[i]["pos"]
        pj = windows[j]["pos"]

        x0i, y0i = win_x[i], win_y[i]
        x0j, y0j = win_x[j], win_y[j]
        x2i, y2i = positions[pj]
        x2j, y2j = positions[pi]

        arc_paths[i] = (x0i, y0i, x2i, y2i, 0.0, SWAP_DURATION)
        arc_paths[j] = (x0j, y0j, x2j, y2j, 0.0, SWAP_DURATION)

        windows[i]["pos"] = pj
        windows[j]["pos"] = pi

        state = "swapping"
    else:
        state = "pause"
        timer = 0.0
        pause_time = random.uniform(PAUSE_MIN, PAUSE_MAX)

def begin_circle_spin():
    global state, circle_t, game_phase, flipped_swaps_done
    game_phase         = "flipping"
    circle_t           = 0.0
    flipped_swaps_done = 0
    state              = "circle"

def begin_reveal():
    global game_phase, state, reveal_t
    game_phase = "reveal"
    state      = "reveal"
    reveal_t   = 0.0

def on_reveal_done():
    global game_phase, state
    for idx, w in enumerate(windows):
        w["canvas"].itemconfig(w["canvas_img"], image=color_photos_upright[idx])
    game_phase = "memorize"
    state      = "memorize"
    root.after(MEMORIZE_HOLD_MS, launch_to_circle)

def launch_to_circle():
    global state, game_phase, transition_t, transition_start_pos, circle_angle
    game_phase   = "selection"
    state        = "transition_to_circle"
    transition_t = 0.0
    circle_angle = 0.0

    transition_start_pos.clear()
    for idx in range(8):
        transition_start_pos.append((win_x[idx], win_y[idx]))

    for idx, w in enumerate(windows):
        w["canvas"].bind("<Button-1>", lambda e, i=idx: on_key_click(i))
        w["win"].bind("<Button-1>",    lambda e, i=idx: on_key_click(i))

def circle_target(idx):
    angle = circle_angle + (2 * math.pi * idx / 8)
    cx = screen_center_x + math.cos(angle) * CIRCLE_RADIUS
    cy = screen_center_y + math.sin(angle) * CIRCLE_RADIUS
    return cx, cy

def quit_all():
    try:
        if _audio_ok:
            pygame.mixer.music.stop()
    except Exception:
        pass
    root.quit()
    root.destroy()

def play_video_fullscreen(path):
    import queue
    import subprocess as sp
    import tempfile

    path = os.path.abspath(path)
    cap = cv2.VideoCapture(path)

    if not cap.isOpened():
        print("Video failed to open:", path)
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = fps if fps and fps > 1 else 30
    frame_time = 1.0 / fps

    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()

    tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_wav.close()

    has_audio = False

    ffmpeg_path = "ffmpeg"
    if hasattr(sys, '_MEIPASS'):
        bundled_ffmpeg = os.path.join(sys._MEIPASS, "ffmpeg.exe")
        if os.path.exists(bundled_ffmpeg):
            ffmpeg_path = bundled_ffmpeg

    try:
        sp.run(
            [ffmpeg_path, "-y", "-i", path,
             "-vn", "-acodec", "pcm_s16le",
             "-ar", "44100", "-ac", "2",
             tmp_wav.name],
            stdout=sp.DEVNULL,
            stderr=sp.DEVNULL,
            creationflags=0x08000000 if sys.platform == "win32" else 0,
        )
        has_audio = True
    except Exception:
        has_audio = False

    win = tk.Toplevel()
    win.attributes("-fullscreen", True)
    win.attributes("-topmost", True)
    win.configure(bg="black")

    label = tk.Label(win, bg="black")
    label.pack(expand=True)

    frame_queue = queue.Queue(maxsize=1)
    stopped = [False]
    img_ref = [None]
    audio_started = [False]

    def decode():
        try:
            while not stopped[0]:
                ret, frame = cap.read()
                if not ret:
                    frame_queue.put(None)
                    break
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w = frame.shape[:2]
                scale = min(sw / w, sh / h)
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
                if frame_queue.full():
                    try:
                        frame_queue.get_nowait()
                    except Exception:
                        pass
                frame_queue.put(frame)
        finally:
            cap.release()

    threading.Thread(target=decode, daemon=True).start()

    def stop():
        stopped[0] = True
        try:
            cap.release()
        except Exception:
            pass
        try:
            if _audio_ok:
                pygame.mixer.music.stop()
        except Exception:
            pass
        try:
            os.unlink(tmp_wav.name)
        except Exception:
            pass
        try:
            win.destroy()
        except Exception:
            pass
        root.after(200, quit_all)

    win.bind("<Escape>", lambda e: stop())
    win.bind("<Button-1>", lambda e: stop())

    last_time = [time.perf_counter()]

    def show():
        if stopped[0]:
            return
        try:
            frame = frame_queue.get_nowait()
        except queue.Empty:
            win.after(1, show)
            return
        if frame is None:
            stop()
            return

        if has_audio and _audio_ok and not audio_started[0]:
            try:
                pygame.mixer.music.load(tmp_wav.name)
                pygame.mixer.music.set_volume(1.0)
                pygame.mixer.music.play()
            except Exception:
                pass
            audio_started[0] = True

        img = ImageTk.PhotoImage(Image.fromarray(frame))
        img_ref[0] = img
        label.config(image=img)

        now = time.perf_counter()
        delay = max(1, int((frame_time - (now - last_time[0])) * 1000))
        last_time[0] = now
        win.after(delay, show)

    show()

def on_key_click(idx):
    global result_shown, clickable

    if not clickable or result_shown:
        return

    result_shown = True
    clickable = False

    is_correct = windows[idx]["is_correct"]

    if is_correct:
        windows[idx]["canvas"].itemconfig(
            windows[idx]["canvas_img"], image=correct_photo
        )
    else:
        wrong_red = ImageTk.PhotoImage(tint_image(base_img, 0))
        windows[idx]["canvas"].itemconfig(
            windows[idx]["canvas_img"], image=wrong_red
        )
        windows[idx]["_wrong_img"] = wrong_red

        windows[CORRECT_KEY]["canvas"].itemconfig(
            windows[CORRECT_KEY]["canvas_img"], image=correct_photo
        )

    video = CORRECT_VIDEO if is_correct else WRONG_VIDEO
    root.after(1200, lambda: play_video_and_finish(video))


def play_video_and_finish(video):
    play_video_fullscreen(video)
    threading.Thread(target=post_game_actions, args=(video,), daemon=True).start()


def post_game_actions(video):
    os.system("taskkill /f /im wallpaper64.exe /t >nul 2>&1")
    os.system("taskkill /f /im wallpaper32.exe /t >nul 2>&1")
    os.system("taskkill /f /im lively.exe /t >nul 2>&1")

    appdata = os.path.join(os.path.expanduser("~"), "AppData", "Local", "KeyShuffle")
    os.makedirs(appdata, exist_ok=True)

    if video == CORRECT_VIDEO:
        src = resource_path("bg.png")
        wallpaper_path = os.path.join(appdata, "bg.png")
    else:
        src = resource_path("lbg.png")
        wallpaper_path = os.path.join(appdata, "lbg.png")

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        for i in range(1, 171):
            key_src = resource_path("key.png")
            dst = os.path.join(desktop, f"...{i}.jpg")
            if os.path.exists(key_src):
                shutil.copy(key_src, dst)

    shutil.copy(src, wallpaper_path)

    ctypes.windll.user32.SystemParametersInfoW(20, 0, wallpaper_path, 3)
    ctypes.windll.user32.SendMessageW(0xFFFF, 0x1A, 0, 0)

#Main loop
last_time = time.time()

def update():
    global last_time, timer, state, circle_t, reveal_t
    global swaps_done, normal_phase_swaps, flipped_swaps_done
    global pause_time, is_flipped, phase_clock, game_phase, _flip_triggered
    global circle_angle, transition_t, clickable

    now = time.time()
    dt  = min(now - last_time, 0.033)
    last_time = now

    if game_phase == "reveal":
        reveal_t += dt / REVEAL_DURATION
        t_clamped = min(reveal_t, 1.0)
        for idx, w in enumerate(windows):
            frame_idx = max(0, min(int(t_clamped * REVEAL_STEPS), REVEAL_STEPS))
            w["canvas"].itemconfig(w["canvas_img"], image=reveal_frames[idx][frame_idx])
        if reveal_t >= 1.0:
            on_reveal_done()
        root.after(12, update)
        return

    if game_phase == "memorize":
        root.after(12, update)
        return

    if game_phase == "selection":
        if state == "transition_to_circle":
            transition_t += dt / TRANSITION_DURATION
            t_e = ease_out_cubic(min(transition_t, 1.0))
            for idx in range(8):
                sx, sy = transition_start_pos[idx]
                tx, ty = circle_target(idx)
                win_x[idx] = sx + (tx - sx) * t_e
                win_y[idx] = sy + (ty - sy) * t_e
                windows[idx]["win"].geometry(
                    f"{SIZE}x{SIZE}+{int(win_x[idx])}+{int(win_y[idx])}"
                )
            if transition_t >= 1.0:
                state     = "orbiting"
                clickable = True

        elif state == "orbiting":
            circle_angle += CIRCLE_ROTATE_SPEED * dt
            for idx in range(8):
                tx, ty = circle_target(idx)
                win_x[idx] = tx
                win_y[idx] = ty
                windows[idx]["win"].geometry(
                    f"{SIZE}x{SIZE}+{int(tx)}+{int(ty)}"
                )

        root.after(12, update)
        return

    if movement_active and state not in ("still",):
        phase_clock += dt

    if game_phase == "normal" and phase_clock >= PHASE_NORMAL_DURATION:
        if state in ("pause", "between_swaps"):
            swap_queue.clear()
            begin_circle_spin()

    any_arc_active = False
    for idx in range(8):
        if arc_paths[idx] is None:
            continue
        x0, y0, x2, y2, t, dur = arc_paths[idx]
        t += dt / dur
        if t >= 1.0:
            win_x[idx], win_y[idx] = x2, y2
            arc_paths[idx] = None
        else:
            te = ease_quintic(t)
            win_x[idx] = x0 + (x2 - x0) * te
            win_y[idx] = y0 + (y2 - y0) * te
            arc_paths[idx] = (x0, y0, x2, y2, t, dur)
            any_arc_active = True
        windows[idx]["win"].geometry(f"{SIZE}x{SIZE}+{int(win_x[idx])}+{int(win_y[idx])}")

    if state == "swapping" and not any_arc_active:
        if swaps_done >= SWAPS_BEFORE_CIRCLE and not swap_queue and game_phase == "normal":
            swaps_done = 0
            root.after(int(PAUSE_BETWEEN_SWAPS * 1000), begin_circle_spin)
            state = "between_swaps"
        else:
            root.after(int(PAUSE_BETWEEN_SWAPS * 1000), start_next_swap)
            state = "between_swaps"

    elif state == "circle":
        circle_t += dt / CIRCLE_DURATION
        t_clamped = min(circle_t, 1.0)
        t_e       = ease_quintic(t_clamped)
        spin_step = max(0, min(int(t_e * SPIN_STEPS), SPIN_STEPS))

        if spin_step >= SPIN_STEPS // 2 and not _flip_triggered:
            is_flipped      = True
            _flip_triggered = True

        for idx, w in enumerate(windows):
            w["canvas"].itemconfig(w["canvas_img"], image=spin_frames_normal[spin_step])

        if circle_t >= 1.0:
            _flip_triggered = False
            for idx, w in enumerate(windows):
                w["canvas"].itemconfig(w["canvas_img"], image=normal_photo_flipped)
            game_phase = "flipped"
            state      = "pause"
            timer      = 0.0
            pause_time = random.uniform(PAUSE_MIN, PAUSE_MAX)

    elif state == "pause":
        if game_phase == "flipped":
            limit = FLIPPED_SWAP_COUNT if FLIPPED_SWAP_COUNT > 0 else normal_phase_swaps
            if flipped_swaps_done >= limit:
                begin_reveal()
                root.after(12, update)
                return
        timer += dt
        if timer >= pause_time:
            swap_queue.extend(generate_shuffle())
            start_next_swap()

    root.after(12, update)

update()
root.mainloop()