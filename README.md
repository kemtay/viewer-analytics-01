# E-learning Viewer Analytics - Render Package

This package converts the desktop `video_emb.py` idea into a Render-friendly web app.

## What it does

- Browser plays `static/lesson.mp4`
- Browser asks permission for the viewer webcam
- Browser sends webcam snapshots to the Python backend
- Python backend uses MediaPipe FaceMesh to detect:
  - Eyes closed
  - Sleeping
  - Looking extreme left
  - Looking extreme right
  - Looking extreme up
  - Looking extreme down
  - Viewer invisible

## Local test

```powershell
cd render_viewer_analytics_package
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Render settings

Build command:

```text
pip install -r requirements.txt
```

Start command:

```text
gunicorn app:app -k uvicorn.workers.UvicornWorker
```

## Files

```text
app.py
requirements.txt
.python-version
static/index.html
static/app.js
static/lesson.mp4
```

## Privacy note

This demo sends webcam snapshots to the server. For production, consider doing analytics inside the browser and sending only analytics labels to the server.
