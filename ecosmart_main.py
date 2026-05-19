import cv2
import numpy as np
import urllib.request
try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except Exception:
    YOLO = None
    ULTRALYTICS_AVAILABLE = False
import time
import threading
import sqlite3
import datetime
import argparse
import random
import io
import math
try:
    import serial
    SERIAL_AVAILABLE = True
except Exception:
    serial = None
    SERIAL_AVAILABLE = False
from flask import Flask, Response, jsonify, request

# ─── Global State ─────────────────────────────────────────────────────────────
latest_frame_jpg = None
frame_lock = threading.Lock()

# Ultrasonic distance readings from Arduino
sensor_data = {
    'D1': 30.0, # Plastic
    'D2': 30.0, # Paper
    'D3': 30.0, # Organic
    'D4': 30.0  # Platform/Extra
}

# Simulation flag (set at startup)
SIMULATE = False

# Database (SQLite) connection and lock
db_conn = None
db_lock = threading.Lock()

# ─── Flask App & Dashboard ────────────────────────────────────────────────────
stream_app = Flask(__name__)

@stream_app.route('/')
def index():
    # Provide a beautiful dashboard with progress bars for the 4 sensors
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>EcoSmart Dashboard</title>
        <style>
            body { background: #111; color: white; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; margin: 0; padding: 20px; }
            h1 { color: #4ade80; margin-bottom: 10px; }
            .container { display: flex; gap: 30px; margin-top: 20px; flex-wrap: wrap; justify-content: center; }
            .video-box { border: 3px solid #4ade80; border-radius: 8px; overflow: hidden; max-width: 90vw; }
            .video-box img { display: block; width: 100%; max-width: 600px; }
            .stats-box { background: #222; padding: 20px; border-radius: 8px; width: 300px; }
            .history-box { background: #161616; padding: 14px; border-radius: 8px; margin-top: 18px; width: 640px; }
            .history-list { list-style: none; padding: 0; margin: 0; display: flex; gap: 8px; flex-wrap: wrap; }
            .history-list li { background: #1f1f1f; padding: 8px 10px; border-radius: 6px; font-size: 0.9em; }
            
            .bin-section { margin-bottom: 15px; }
            .bin-label { display: flex; justify-content: space-between; font-weight: bold; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px; font-size: 0.9em; }
            
            .bar-bg { background: #444; border-radius: 10px; height: 20px; width: 100%; overflow: hidden; position: relative; }
            .bar-fill { height: 100%; transition: width 0.5s ease; border-radius: 10px; }
            .bar-text { position: absolute; right: 10px; top: 2px; font-size: 0.8em; font-weight: bold; color: #fff; text-shadow: 1px 1px 2px #000; }
            
            .color-plastic { background: #f97316; } /* Orange */
            .color-paper { background: #eab308; }   /* Yellow */
            .color-organic { background: #22c55e; } /* Green */
            .color-unknown { background: #9ca3af; } /* Gray */
        </style>
    </head>
    <body>
        <h1>🌿 EcoSmart Dashboard</h1>
        <div class="container">
            <div class="video-box">
                <img src="/stream" alt="Live Camera Feed">
            </div>
            
            <div class="stats-box">
                <h2 style="margin-top: 0; color: #aaa;">Bin Fill Levels</h2>
                
                <div class="bin-section">
                    <div class="bin-label"><span style="color:#f97316">Plastic (D1)</span> <span id="val-d1">-- cm</span></div>
                    <div class="bar-bg"><div id="bar-d1" class="bar-fill color-plastic" style="width: 0%;"></div></div>
                </div>
                
                <div class="bin-section">
                    <div class="bin-label"><span style="color:#eab308">Paper (D2)</span> <span id="val-d2">-- cm</span></div>
                    <div class="bar-bg"><div id="bar-d2" class="bar-fill color-paper" style="width: 0%;"></div></div>
                </div>
                
                <div class="bin-section">
                    <div class="bin-label"><span style="color:#22c55e">Organic (D3)</span> <span id="val-d3">-- cm</span></div>
                    <div class="bar-bg"><div id="bar-d3" class="bar-fill color-organic" style="width: 0%;"></div></div>
                </div>
                
                <div class="bin-section">
                    <div class="bin-label"><span style="color:#9ca3af">Unknown Waste (D4)</span> <span id="val-d4">-- cm</span></div>
                    <div class="bar-bg"><div id="bar-d4" class="bar-fill color-unknown" style="width: 0%;"></div></div>
                </div>
                
            </div>
        </div>

        <div class="history-box">
            <h2 style="margin:6px 0 10px 0; color:#bbb;">Recent Sensor Readings (latest first)</h2>
            <ul id="history-list" class="history-list">
                <li>Loading...</li>
            </ul>
        </div>

        <script>
            // Assume 30cm is completely empty, 5cm is 100% full
            const EMPTY_CM = 30.0;
            const FULL_CM = 5.0;

            function cmToPercent(cm) {
                if(cm > EMPTY_CM) return 0;
                if(cm < FULL_CM) return 100;
                let percent = ((EMPTY_CM - cm) / (EMPTY_CM - FULL_CM)) * 100;
                return Math.round(percent);
            }

            function updateSensors() {
                fetch('/status')
                    .then(r => r.json())
                    .then(data => {
                        ['D1', 'D2', 'D3', 'D4'].forEach(id => {
                            let cm = data[id] || 0.0;
                            let pct = cmToPercent(cm);
                            
                            document.getElementById('val-' + id.toLowerCase()).innerText = cm.toFixed(1) + ' cm (' + pct + '%)';
                            document.getElementById('bar-' + id.toLowerCase()).style.width = pct + '%';
                        });
                    })
                    .catch(e => console.error(e));
            }

            function updateHistory() {
                fetch('/history?n=8')
                    .then(r => r.json())
                    .then(data => {
                        const list = document.getElementById('history-list');
                        list.innerHTML = '';
                        if(!data || data.length === 0) {
                            list.innerHTML = '<li>No readings yet</li>';
                            return;
                        }
                        data.forEach(item => {
                            const li = document.createElement('li');
                            const shortTs = new Date(item.ts).toLocaleTimeString();
                            li.textContent = `${item.sensor}: ${item.value.toFixed(1)} cm @ ${shortTs}`;
                            list.appendChild(li);
                        });
                    })
                    .catch(e => console.error(e));
            }

            // Fetch every 1 second
            setInterval(() => { updateSensors(); updateHistory(); }, 1000);
            updateSensors();
            updateHistory();
        </script>
    </body>
    </html>
    '''

@stream_app.route('/stream')
def stream():
    def generate():
        while True:
            with frame_lock:
                jpg = latest_frame_jpg
            if jpg is not None:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n')
            time.sleep(0.05)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@stream_app.route('/status')
def status():
    # Return the latest ultrasonic readings as JSON
    return jsonify(sensor_data)


@stream_app.route('/history')
def history():
    # Return recent sensor readings from the DB (most recent first)
    try:
        n = int(request.args.get('n', 50))
    except Exception:
        n = 50
    rows = get_recent_readings(limit=n)
    # rows are tuples of (sensor, value, ts)
    out = [{'sensor': r[0], 'value': r[1], 'ts': r[2]} for r in rows]
    return jsonify(out)

def run_stream_server():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR) # hide trivial web requests from console
    stream_app.run(host='0.0.0.0', port=5002, debug=False, use_reloader=False)


def simulate_hardware_thread():
    """When running without real hardware, simulate sensor readings and a camera feed."""
    global sensor_data, latest_frame_jpg
    t0 = time.time()
    while True:
        # generate some wave-like values for each sensor
        elapsed = time.time() - t0
        vals = {
            'D1': 10 + 20 * (0.5 + 0.5 * math.sin(elapsed * 0.3 + 0)),
            'D2': 8  + 18 * (0.5 + 0.5 * math.sin(elapsed * 0.25 + 1)),
            'D3': 6  + 12 * (0.5 + 0.5 * math.sin(elapsed * 0.4 + 2)),
            'D4': 20 + 6  * (0.5 + 0.5 * math.sin(elapsed * 0.2 + 3)),
        }
        for k, v in vals.items():
            sensor_data[k] = float(v)
            try:
                save_sensor_reading(k, sensor_data[k])
            except Exception:
                pass

        # create a synthetic frame showing current values
        try:
            frame = np.zeros((360, 640, 3), dtype=np.uint8)
            frame[:] = (30, 30, 30)
            cv2.putText(frame, 'SIMULATED ESP32-CAM', (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200,200,200), 2)
            y = 70
            for k in ['D1','D2','D3','D4']:
                txt = f"{k}: {sensor_data[k]:.1f} cm"
                cv2.putText(frame, txt, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (240,240,240), 2)
                y += 40
            _, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            with frame_lock:
                latest_frame_jpg = jpg.tobytes()
        except Exception:
            pass

        time.sleep(1.0)


def init_db(path='sensors.db'):
    """Initialize SQLite DB and return connection."""
    global db_conn
    try:
        conn = sqlite3.connect(path, check_same_thread=False)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor TEXT,
                value REAL,
                ts TEXT
            )
        ''')
        conn.commit()
        db_conn = conn
        print(f"--- DB initialized at {path} ---")
    except Exception as e:
        print(f"--- DB init error: {e} ---")


def save_sensor_reading(sensor, value):
    """Persist a single sensor reading to DB (non-blocking guarded)."""
    global db_conn
    if db_conn is None:
        return
    try:
        ts = datetime.datetime.utcnow().isoformat()
        with db_lock:
            db_conn.execute('INSERT INTO sensor_readings(sensor, value, ts) VALUES(?,?,?)', (sensor, float(value), ts))
            db_conn.commit()
    except Exception:
        pass


def get_recent_readings(limit=50):
    global db_conn
    if db_conn is None:
        return []
    try:
        with db_lock:
            cur = db_conn.execute('SELECT sensor, value, ts FROM sensor_readings ORDER BY id DESC LIMIT ?', (limit,))
            rows = cur.fetchall()
        return rows
    except Exception:
        return []

# ─── Arduino Setup & Serial Reader ────────────────────────────────────────────
serial_lock = threading.Lock()  # Prevents simultaneous read/write on COM3
arduino = None

def serial_reader_thread():
    """Continuously parse ultrasonic readings coming from the Arduino."""
    while True:
        if arduino and arduino.is_open:
            try:
                with serial_lock:
                    line = arduino.readline().decode('utf-8', errors='ignore').strip()

                if line.startswith("D1:"):
                    # DEBUG: print raw line so we can verify D2/D3/D4
                    print(f"[SENSOR] {line}")
                    parts = line.split()
                    for p in parts:
                        if ':' in p:
                            kv = p.split(':', 1)
                            if len(kv) == 2:
                                key, val = kv
                                key = key.strip()
                                if key in sensor_data:
                                    try:
                                        v = float(val)
                                        if 1.0 <= v <= 100.0:
                                                    sensor_data[key] = v
                                                    # persist reading
                                                    try:
                                                        save_sensor_reading(key, sensor_data[key])
                                                    except Exception:
                                                        pass
                                        elif v == 0.0:
                                                    sensor_data[key] = 30.0
                                                    try:
                                                        save_sensor_reading(key, sensor_data[key])
                                                    except Exception:
                                                        pass
                                    except ValueError:
                                        pass
            except Exception:
                pass
        time.sleep(0.05)

# ─── YOLO Model ───────────────────────────────────────────────────────────────
model_path = 'yolo_runs/funzip_classifier/weights/best.pt'
model = None
if ULTRALYTICS_AVAILABLE:
    try:
        model = YOLO(model_path, task='classify') # strict mode
        print(f"--- Model Loaded: {model_path} ---")
    except Exception as e:
        print(f"--- Model Error: {e} ---")
        model = None
else:
    print('--- ultralytics not available; running without model (inference disabled) ---')

# ─── Hardware Mapping ─────────────────────────────────────────────────────────
mapping = {
    'plastic':    'plastic\n',
    'paper':      'paper\n',
    'biological': 'organic\n'
}

LABEL_COLORS = {
    'plastic':    (0, 140, 255),   # Orange
    'paper':      (255, 255, 0),   # Yellow
    'biological': (0, 200, 80),    # Green
}

# ─── Main Program ─────────────────────────────────────────────────────────────
def run_system(simulate=False):
    global latest_frame_jpg

    ESP32_CAM_URL = "http://192.168.255.1/capture"
    print(f"Connecting to ESP32-CAM at {ESP32_CAM_URL}...")
    print("Live View + Dashboard → http://localhost:5002")
    print("System Live. Press Ctrl+C to exit.\n")

    REQUIRED_STABLE_FRAMES = 4
    CONFIDENCE_THRESHOLD   = 0.88
    MARGIN_THRESHOLD       = 0.15

    stable_label = None
    stable_count = 0

    try:
        while True:
            # 1. Fetch image
            if simulate:
                # Read the synthetic frame produced by the simulator thread
                with frame_lock:
                    jpg = latest_frame_jpg
                if jpg is None:
                    time.sleep(0.2)
                    continue
                try:
                    arr = np.frombuffer(jpg, dtype=np.uint8)
                    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                except Exception:
                    frame = None
                if frame is None:
                    stable_label = None; stable_count = 0
                    time.sleep(0.5); continue
            else:
                try:
                    img_resp = urllib.request.urlopen(ESP32_CAM_URL, timeout=5)
                    img_array = np.array(bytearray(img_resp.read()), dtype=np.uint8)
                    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    if frame is None:
                        stable_label = None; stable_count = 0
                        time.sleep(1); continue
                except Exception as e:
                    print(f"--- Network Error: {e} ---")
                    stable_label = None; stable_count = 0
                    time.sleep(2); continue

            # 2. Run Inference (skip if no model available)
            if model is not None:
                results = model(frame, verbose=False)
            else:
                results = []

            detected_label = None
            top_conf = 0.0
            display_label = "No waste detected"
            display_color = (100, 100, 100)

            for r in results:
                if r.probs:
                    probs = r.probs.data.cpu().numpy()
                    top1_idx = int(r.probs.top1)
                    top1_conf = float(r.probs.top1conf)

                    sorted_probs = np.sort(probs)[::-1]
                    second_conf = sorted_probs[1] if len(sorted_probs) > 1 else 0.0
                    margin = top1_conf - second_conf

                    label = r.names[top1_idx].lower()
                    top_conf = top1_conf

                    display_label = f"{label} {top1_conf:.0%}"
                    display_color = LABEL_COLORS.get(label, (200, 200, 200))

                    if top1_conf >= CONFIDENCE_THRESHOLD and margin >= MARGIN_THRESHOLD:
                        detected_label = label

            # 3. GUI Overlay
            h, w = frame.shape[:2]
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, 70), (30, 30, 30), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
            cv2.putText(frame, display_label, (15, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.4, display_color, 3, cv2.LINE_AA)

            bar_w = int((stable_count / REQUIRED_STABLE_FRAMES) * (w - 30))
            cv2.rectangle(frame, (15, h - 25), (w - 15, h - 10), (60, 60, 60), -1)
            if bar_w > 0:
                cv2.rectangle(frame, (15, h - 25), (15 + bar_w, h - 10), display_color, -1)
            cv2.putText(frame, f"Stability: {stable_count}/{REQUIRED_STABLE_FRAMES}", (15, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

            _, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            with frame_lock:
                latest_frame_jpg = jpg.tobytes()

            # 4. Action Logic
            if detected_label and detected_label == stable_label:
                stable_count += 1
                if stable_count == 1:
                    print()
                print(f"Targeting: {detected_label} ({top_conf:.2f}) [{stable_count}/{REQUIRED_STABLE_FRAMES}]")
            else:
                stable_label = detected_label
                stable_count = 1 if detected_label else 0

            # Execute Arduino Command
            if stable_count >= REQUIRED_STABLE_FRAMES and detected_label:
                command = mapping.get(detected_label)
                if command and arduino:
                    print(f">>> STABLE WASTE: {detected_label} — Triggering Motors <<<")

                    # Acquire lock so reader thread doesn't read mid-write
                    with serial_lock:
                        arduino.write(command.encode('utf-8'))

                    print("PROCESSING... (waiting 7s for bin mechanism)")
                    time.sleep(7)
                    print("Ready for next item.\n")

                stable_label = None
                stable_count = 0

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n--- Stopped by user ---")

    if arduino:
        arduino.close()
        print("--- Serial Connection Closed ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='EcoSmart System')
    parser.add_argument('--simulate', action='store_true', help='Run in simulation mode without hardware')
    args = parser.parse_args()
    SIMULATE = bool(args.simulate)

    # Initialize DB then start background services
    init_db('sensors.db')

    t_web = threading.Thread(target=run_stream_server, daemon=True)
    t_web.start()

    if SIMULATE:
        print('--- Running in SIMULATION mode (no Arduino / ESP32 required) ---')
        t_sim = threading.Thread(target=simulate_hardware_thread, daemon=True)
        t_sim.start()
    else:
        # try to open the serial port for real hardware
        try:
            arduino = serial.Serial('COM3', 9600, timeout=0.5)
            time.sleep(2)
            print('--- Connected to EcoSmart Hardware on COM3 ---')
        except Exception as e:
            print(f'--- Serial Error: {e} ---')
            arduino = None

        t_serial = threading.Thread(target=serial_reader_thread, daemon=True)
        t_serial.start()

    run_system(simulate=SIMULATE)