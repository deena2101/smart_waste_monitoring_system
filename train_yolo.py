from ultralytics import YOLO

def train():
    # Load a pre-trained YOLOv8 classification model
    model = YOLO('yolov8n-cls.pt')

    # Train the model
    # Note: For classification, YOLOv8 expects the root dataset directory containing 'train' and 'val' subfolders
    # where each contains folders for each class (e.g., train/biological, train/paper, train/plastic)
    results = model.train(
        data='c:/Users/bilja/Desktop/gotit/funzip_split',
        epochs=10, # Adjustable
        imgsz=224, # Standard classification size
        batch=16,
        project='c:/Users/bilja/Desktop/gotit/yolo_runs',
        name='funzip_classifier'
    )
    
    # Evaluate model on validation set
    metrics = model.val()
    
    print("\nTraining completed. Results saved in 'c:/Users/bilja/Desktop/gotit/yolo_runs/funzip_classifier'")

if __name__ == '__main__':
    train()
