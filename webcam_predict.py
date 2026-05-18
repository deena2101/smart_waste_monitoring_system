from flask import Flask, request, jsonify
from flask_cors import CORS
from ultralytics import YOLO
import cv2
import numpy as np
import base64
import serial
import urllib.request

app = Flask(__name__)
CORS(app)

# 1. Setup Arduino Connection
# IMPORTANT: Change 'COM3' to the port shown in your Arduino IDE
try:
    arduino = serial.Serial(port='COM3', baudrate=9600, timeout=.1)
    print("--- Connected to Arduino Bin Hardware ---")
except Exception as e:
    print(f"--- Arduino NOT Found: {e} ---")
    arduino = None

# 2. ESP32-CAM Configuration
ESP32_CAM_URL = "http://192.168.96.1/capture"

# 3. Load your YOLOv8 model
MODEL_PATH = 'c:/Users/bilja/Desktop/gotit/yolo_runs/funzip_classifier/weights/best.pt'
model = YOLO(MODEL_PATH)

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Fetch image directly from ESP32-CAM
        img_resp = urllib.request.urlopen(ESP32_CAM_URL)
        img_array = np.array(bytearray(img_resp.read()), dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"error": "Failed to capture image from ESP32-CAM"}), 500

        # Run AI Prediction
        results = model(img)
        probs = results[0].probs
        label = results[0].names[probs.top1]
        confidence = float(probs.top1conf)

        # 4. Trigger Hardware if confidence is high (> 75%)
        if confidence > 0.75 and arduino:
            # Matches Arduino expectations exactly
            mapping = {'plastic': 'plastic\n', 'biological': 'organic\n', 'paper': 'paper\n'}
            cmd = mapping.get(label.lower())
            
            if cmd:
                arduino.write(bytes(cmd, 'utf-8'))
                print(f"Action: Opening {label} bin (Conf: {confidence:.2f})")

        return jsonify({"label": label, "confidence": confidence})

    except Exception as e:
        print(f"Error during prediction: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Running on port 5001 to match your index.html fetch call
    app.run(port=5001, debug=False)
