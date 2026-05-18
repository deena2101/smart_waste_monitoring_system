import os
import shutil
import random
from pathlib import Path

def split_dataset(source_dir, dest_dir, split_ratio=(0.8, 0.2)):
    source_dir = Path(source_dir)
    dest_dir = Path(dest_dir)
    
    # Create train and val directories
    train_dir = dest_dir / 'train'
    val_dir = dest_dir / 'val'
    
    for class_dir in source_dir.iterdir():
        if not class_dir.is_dir():
            continue
            
        class_name = class_dir.name
        images = list(class_dir.glob('*.jpg')) + list(class_dir.glob('*.png')) + list(class_dir.glob('*.jpeg'))
        
        # Shuffle images randomly
        random.seed(42)
        random.shuffle(images)
        
        # Calculate split index
        train_count = int(len(images) * split_ratio[0])
        
        train_images = images[:train_count]
        val_images = images[train_count:]
        
        print(f"Class '{class_name}': {len(train_images)} train, {len(val_images)} val")
        
        # Create output directories for this class
        (train_dir / class_name).mkdir(parents=True, exist_ok=True)
        (val_dir / class_name).mkdir(parents=True, exist_ok=True)
        
        # Copy images
        for img_path in train_images:
            shutil.copy2(img_path, train_dir / class_name / img_path.name)
            
        for img_path in val_images:
            shutil.copy2(img_path, val_dir / class_name / img_path.name)
            
    print("Dataset split completed successfully.")

if __name__ == "__main__":
    SOURCE = "c:/Users/bilja/Desktop/gotit/funzip"
    DEST = "c:/Users/bilja/Desktop/gotit/funzip_split"
    
    print(f"Splitting dataset from {SOURCE} to {DEST}")
    split_dataset(SOURCE, DEST)
