import os
import sys
from pathlib import Path
from json import load, dump

root_dir = Path(os.path.abspath(__file__)).parents[1]
sys.path.append(str(root_dir))

from src.model.encoder import encode_sync_tensor

if __name__ == '__main__':

    common_words = [
        "Thai Food", "Crispy Pork", "Fried Chicken", "Iced Thai Tea", "Pad Thai",
        "Vietnamese Noodle (Pho)", "Noodles", "Crab", "Spicy Salad", "Sushi",
        "Dim Sum", "Smoothies", "Thai Coconut Curry Noodle (Khao Soi)", "Hamburger",
        "Coffee", "Clean Food", "Som Tam (Papaya Salad)", "Fish Steak",
        "Japanese Foods", "Chicken", "Pork", "Shrimp", "Teriyaki Chicken Rice",
        "Thai Style Suki", "Boat Noodles", "Mango Sticky Rice", "Chicken Nuggets",
        "Japanese Curry Rice", "Biryani", "Har Gow (Shrimp Dumplings)", "Yen Ta Fo (Pink Noodles)",
        "Seafood", "Thai Curry with Rice (Kao Kang)", "Tom Yum Noodles", "Beef Stewed",
        "Stir-Fried Thai Basil (Pad Kra Pao)", "Thai Green Curry Chicken", "Stir-Fried Noodle (Pad See Ew)",
        "Spaghetti", "Thai Chicken Rice", "Fried Rice", "Stir-Fried Dish", "Grilled Meat",
        "Soup Dish", "Sandwich", "Salmon", "Fruit", "Vegetarian Meal", "Boiled Rice",
        "Omelette", "Crispy Fried Dish", "Instant Noodles", "Milk Tea", "Yakisoba",
        "Curry Udon", "Coke", "Coconut Milkshake", "Lime Soda", "Sticky Rice with Grilled Pork",
        "Pepsi", "Garlic Pork with Rice", "Meat Dish", "Spicy Mango Salad", "Bento Box",
        "Stir-Fried Basil with Crispy Pork", "Honey Lime Tea", "Panaeng Curry",
        "Spicy Glass Noodle (Yum Woon Sen)", "Grilled Pork Skewers (Moo Ping)",
        "Pork Leg Stew (Kha Moo)", "Strawberry Milkshake", "Macaroni",
        "Chicken with Cashew Nuts", "Rice with Holy Basil Pork", "Pizza",
        "Deep-Fried Pork Belly with Fish Sauce", "Pork with Ginger Stir-Fry",
        "Japanese Pork Cutlet (Tonkatsu) Rice", "Steamed Fish with Soy Sauce",
        "Vegan Protein Dish", "Cheese Sausage", "Tom Yum Goong (Spicy Shrimp Soup)",
        "Tom Kha Gai (Chicken in Coconut Soup)", "French Fries", "Boiled Rice with Pork",
        "Stir-Fried Morning Glory", "Coconut", "Spicy Chicken Salad Rice", "Wonton",
        "Boneless Chicken Bites", "Herbal", "Red BBQ Pork with Rice", "Meatballs",
        "Stir-Fried Basil with Chicken", "Fried Rice with Crab", "Cheese",
        "Clear Soup Kuay Jap", "Ice Cream", "Rice Omelette with Minced Pork",
        "Pork Congee", "American Fried Rice", "Stir-Fried Basil with Seafood",
        "Fried Bread with Minced Pork", "Iced Americano", "Cocoa Milk",
        "Stewed Egg with Rice", "Sea Bass", "Spicy Salmon Salad", "Pink Milk",
        "Healthy Smoothie", "Salad", "Steamed Bun with Minced Pork",
        "Stir-Fried Noodles in Gravy (Rad Na)", "Shrimp Paste Fried Rice", "Kaphrao",
        "Stir-Fried Red Curry Pork (Pad Ped)", "Spaghetti Drunken Noodles (Pad Kee Mao)",
        "Iced Black Tea", "Taiwanese Milk Tea", "Spicy Minced Pork Salad (Larb Moo)",
        "Bananas", "Rice with Vegetarian Curry", "River Prawns", "Century Egg",
        "Instant Noodle Salad (Yum Mama)", "Stir-Fried Red Curry Pork",
        "Fried Egg with Minced Shrimp", "Clear Soup with Tofu and Minced Pork",
        "Ramen with Pork Chashu", "Stir-Fried Wild Boar", "Cheese Balls",
        "Watermelon Smoothie", "Boba Tea", "Stir-Fried Basil with Pork", "Grilled Pork with Rice",
        "Boiled Egg","Vegetarian Stir-Fry", "Konjac", "Steamed Chicken Breast", "Fried Egg", 
        "Stir-Fry Crispy Pork Chili Salt", "Fried Red Sausage", "Bear Brand Milk"
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