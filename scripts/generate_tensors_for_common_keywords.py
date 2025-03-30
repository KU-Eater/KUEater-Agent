import os
import sys
from pathlib import Path
from json import load, dump

root_dir = Path(os.path.abspath(__file__)).parents[1]
sys.path.append(str(root_dir))

from src.model.encoder import encode_sync_tensor

if __name__ == '__main__':

    common_words = [
        "Thai Food", "Egg", "Crispy Pork", "Fried Rice Chicken",
        "Iced Thai Tea", "Pad Thai", "Beef",
        "Thai Coconut Curry Noodle (Khao Soi)", "Noodles", "Crab", "Spicy Salad", "Sushi",
        "Hamburger", "Coffee", "Som Tam (Green Papaya Salad)",
        "Japanese Food", "Chicken", "Shrimp", "Smoothies", "Mango Sticky Rice", "Fish",
        "Japanese Curry Rice", "Stir-Fried Thai Basil (Pad Kra Pao)",
        "Thai Green Curry Chicken", "Stir-Fried Noodle (Pad See Ew)", "Spaghetti",
        "Thai Chicken Rice"
    ]

    generated_dir = root_dir.joinpath('generated/tensors')
    if not generated_dir.exists():
        generated_dir.mkdir(parents=True)

    common_words_tensors_file = generated_dir.joinpath('common_words.json')

    common_words_tensors = {}
    if common_words_tensors_file.exists():
        try:
            with open(common_words_tensors_file, mode="r") as f:
                common_words_tensors = load(f)
            if any(
                (w not in common_words_tensors.keys()) for w in common_words
            ):
                common_words_tensors = {}
                print("Word tensors file incomplete, regenerating...")
        except:
            print("Word tensors file cannot be read, regenerating...")
    else:
        print("Word tensors file not found, creating...")
    
    if not common_words_tensors:
        for word in common_words:
            common_words_tensors[word] = encode_sync_tensor(word).tolist()
        with open(common_words_tensors_file, mode="w") as f:
            dump(common_words_tensors, f)
        print("Word tensors file saved")