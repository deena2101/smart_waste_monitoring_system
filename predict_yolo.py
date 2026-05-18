from ultralytics import YOLO
import serial
import time

def predict_and_sort():
    # 1. Setup Arduino Connection (Based on your Device Manager: COM3)
    try:
        arduino = serial.Serial(port='COM3', baudrate=9600, timeout=.1)
        print("--- Connected to EcoSmart Hardware on COM3 ---")
        time.sleep(2) # Wait for connection to stabilize
    except Exception as e:
        print(f"--- Hardware Error: {e} ---")
        arduino = None

    # 2. Load the trained model
    model = YOLO('c:/Users/bilja/Desktop/gotit/yolo_runs/funzip_classifier/weights/best.pt')

    test_images = [
        'c:/Users/bilja/Desktop/gotit/funzip_split/val/biological/biological_101.jpg',
        'c:/Users/bilja/Desktop/gotit/funzip_split/val/paper/paper_10.jpg',
        'c:/Users/bilja/Desktop/gotit/funzip_split/val/plastic/plastic_10.jpg'
    ]

    # 3. Hardware Mapping (Characters match your Arduino code logic)
    # P = Plastic, O = Organic (Biological), A = Paper
    mapping = {'plastic': 'P', 'biological': 'O', 'paper': 'A'}

    for img_path in test_images:
        print(f"\n--- Processing: {img_path.split('/')[-1]} ---")
        results = model(img_path)
        
        # Get top prediction
        top_1_idx = results[0].probs.top1
        label = results[0].names[top_1_idx].lower() # Ensure lowercase for mapping
        confidence = results[0].probs.top1conf.item()
        
        print(f"Result: {label} ({confidence:.4f})")

        # 4. Physical Trigger: Move Servo if confidence is high
        if confidence > 0.75 and arduino:
            command = mapping.get(label)
            if command:
                arduino.write(bytes(command, 'utf-8'))
                print(f"Hardware Action: Moving flap to {label} bin ('{command}')")
                time.sleep(4) # Give the waste time to fall before next image
            else:
                print(f"Warning: No hardware mapping for {label}")

    if arduino:
        arduino.close()

if __name__ == '__main__':
    predict_and_sort()