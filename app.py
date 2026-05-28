import base64
import time
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.responses import RedirectResponse
from fastapi.responses import FileResponse


app = FastAPI(title="E-learning Viewer Analytics")

# Serve static/index.html, static/app.js, and static/lesson.mp4
@app.get("/")
def home():
    return FileResponse("static/index.html")
    #return RedirectResponse(url="/static/index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

app.mount("/static", StaticFiles(directory="static"), name="static")


# -----------------------------
# Settings
# -----------------------------
EAR_THRESHOLD = 0.23
SLEEP_WARNING_SECONDS = 3.0

EXTREME_LEFT_RIGHT_THRESHOLD = 0.035
EXTREME_UP_THRESHOLD = 0.030
EXTREME_DOWN_THRESHOLD = 0.045


# -----------------------------
# MediaPipe FaceMesh setup
# -----------------------------
mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

LEFT_EYE_LANDMARKS = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_LANDMARKS = [362, 385, 387, 263, 380, 373]


# -----------------------------
# Simple global state
# For many users, use per-session state instead.
# -----------------------------
sleep_start_time: Optional[float] = None
sleeping_state = False


class FramePayload(BaseModel):
    image: str


def normalized_to_pixel(landmark, frame_width, frame_height):
    return np.array(
        [int(landmark.x * frame_width), int(landmark.y * frame_height)],
        dtype=np.float32,
    )


def calculate_ear(landmarks, frame_width, frame_height, indices):
    points = [
        normalized_to_pixel(landmarks[i], frame_width, frame_height)
        for i in indices
    ]

    horizontal = np.linalg.norm(points[0] - points[3])
    vertical1 = np.linalg.norm(points[1] - points[5])
    vertical2 = np.linalg.norm(points[2] - points[4])

    if horizontal < 1e-6:
        return 0.0

    return (vertical1 + vertical2) / (2.0 * horizontal)


def detect_sleep_ear(landmarks, frame):
    frame_h, frame_w = frame.shape[:2]

    left_ear = calculate_ear(landmarks, frame_w, frame_h, LEFT_EYE_LANDMARKS)
    right_ear = calculate_ear(landmarks, frame_w, frame_h, RIGHT_EYE_LANDMARKS)

    return float((left_ear + right_ear) / 2.0)


def detect_extreme_head_direction(landmarks):
    nose = landmarks[1]
    left_face = landmarks[234]
    right_face = landmarks[454]
    forehead = landmarks[10]
    chin = landmarks[152]

    face_center_x = (left_face.x + right_face.x) / 2
    face_center_y = (forehead.y + chin.y) / 2

    x_offset = nose.x - face_center_x
    y_offset = nose.y - face_center_y

    messages = []

    if x_offset > EXTREME_LEFT_RIGHT_THRESHOLD:
        messages.append("Looking extreme right")
    elif x_offset < -EXTREME_LEFT_RIGHT_THRESHOLD:
        messages.append("Looking extreme left")

    if y_offset < -EXTREME_UP_THRESHOLD:
        messages.append("Looking extreme up")
    elif y_offset > EXTREME_DOWN_THRESHOLD:
        messages.append("Looking extreme down")

    return messages, {
        "head_x": round(x_offset, 3),
        "head_y": round(y_offset, 3),
    }


def decode_base64_image(data_url):
    """
    Browser sends image as:
    data:image/jpeg;base64,xxxxx
    """
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]

    image_bytes = base64.b64decode(data_url)
    np_arr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    return frame


@app.post("/analyze")
def analyze_frame(payload: FramePayload):
    global sleep_start_time, sleeping_state

    frame = decode_base64_image(payload.image)

    if frame is None:
        return {
            "messages": ["Invalid frame"],
            "ear": None,
            "head": None,
        }

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = mp_face_mesh.process(rgb_frame)

    if not results.multi_face_landmarks:
        sleep_start_time = None
        sleeping_state = False

        return {
            "messages": ["Viewer invisible"],
            "ear": None,
            "head": None,
        }

    landmarks = results.multi_face_landmarks[0].landmark

    messages = []

    # -----------------------------
    # Sleep detection
    # -----------------------------
    ear = detect_sleep_ear(landmarks, frame)
    now = time.time()

    if ear < EAR_THRESHOLD:
        if sleep_start_time is None:
            sleep_start_time = now

        closed_duration = now - sleep_start_time

        if closed_duration > SLEEP_WARNING_SECONDS:
            sleeping_state = True
            messages.append("Sleeping")
        elif closed_duration > 0.5:
            messages.append("Eyes closed")
    else:
        if sleeping_state:
            messages.append("Viewer woke up")

        sleep_start_time = None
        sleeping_state = False

    # -----------------------------
    # Head direction detection
    # -----------------------------
    direction_messages, head_debug = detect_extreme_head_direction(landmarks)
    messages.extend(direction_messages)

    if not messages:
        messages.append("Viewer visible / stable")

    return {
        "messages": messages,
        "ear": round(ear, 3),
        "head": head_debug,
    }

@app.get("/packages")
def packages():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        capture_output=True,
        text=True,
    )

    return {
        "packages": result.stdout.splitlines()
    }

@app.get("/debug")
def debug():
    import mediapipe as mp
    import numpy as np
    import cv2

    return {
        "mediapipe_version": getattr(mp, "__version__", "unknown"),
        "mediapipe_has_solutions": hasattr(mp, "solutions"),
        "numpy_version": np.__version__,
        "opencv_version": cv2.__version__,
    }