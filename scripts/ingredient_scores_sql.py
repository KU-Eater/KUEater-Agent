import os
import sys
import numpy as np
from pathlib import Path
from json import load, dump, loads
from typing import Callable
from psycopg_pool import ConnectionPool
from torch import tensor


root_dir = Path(os.path.abspath(__file__)).parents[1]
sys.path.append(str(root_dir))

from src.model.encoder import similarity_sync, encode_sync_tensor

# Query all embeddings that are ingredient

query = "SELECT id, name FROM kueater.ingredient;"

def new_transaction(fn: Callable[..., str]):
    def wrapper(*args):
        result = fn(*args)
        return f"""BEGIN TRANSACTION;
            
        {result}
        
        COMMIT;"""
    return wrapper

@new_transaction
def generate_diet_sql(conn_pool: ConnectionPool, diet_tensors: dict[str, list[float]]) -> str:
    
    print("== GENERATING DIET SCORES... ==")
    
    _header = """/*
    DIET SECTION
    */"""
    
    statements = [
        _header,
        "INSERT INTO kueater.ingredient_diet_score (ingredient_id, diet, score) VALUES"
    ]
    exec_rows = []
    
    print("== FETCHING INGREDIENTS FROM DATABASE... ==")
    
    with conn_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            exec_rows = cur.fetchall()
            
    print("== SCORING, THIS MIGHT TAKE A WHILE... ==")

    for idx, row in enumerate(exec_rows):    # for each ingredient
        (uid, name) = row

        # for each diet
        for d, t in diet_tensors.items():
            tensors = tensor(t)
            sim = similarity_sync(encode_sync_tensor(f"{name} compatible with"), tensors)
            if idx >= len(exec_rows) - 1:
                statements.append(f"('{uid}', '{d}', {sim});")
            else:
                statements.append(f"('{uid}', '{d}', {sim}),")
    
    return "\n".join(statements)


@new_transaction
def generate_allergen_sql(conn_pool: ConnectionPool, allergen_tensors: dict[str, list[float]]) -> str:
    
    print("== GENERATING ALLERGEN SCORES... ==")
    
    _header = """/*
    ALLERGEN SECTION
    */"""
    
    statements = [
        _header,
        "INSERT INTO kueater.ingredient_allergen_score (ingredient_id, allergen, score) VALUES"
    ]
    exec_rows = []
    
    print("== FETCHING INGREDIENTS FROM DATABASE... ==")
        
    with conn_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            exec_rows = cur.fetchall()
            
    print("== SCORING, THIS MIGHT TAKE A WHILE... ==")

    for idx, row in enumerate(exec_rows):    # for each ingredient
        (uid, name) = row

        # for each diet
        for a, t in allergen_tensors.items():
            tensors = tensor(t)
            sim = similarity_sync(encode_sync_tensor(f"{name} has allergen"), tensors)
            if idx >= len(exec_rows) - 1:
                statements.append(f"('{uid}', '{a}', {sim});")
            else:
                statements.append(f"('{uid}', '{a}', {sim}),")
    
    return "\n".join(statements)

if __name__ == '__main__':
    
    import dotenv
    
    dotenv.load_dotenv()
    
    db = os.getenv("DATABASE_URL")
    if not db:
        print("DATABASE_URL is not specified in environment")
        sys.exit(1)
        
    conn_pool: ConnectionPool = ConnectionPool(db, min_size=2, max_size=2)

    diets = [
        "Halal", "Vegetarian", "Vegan","Pescatarian", 
        "Pollotarian", "Low-Carb","Keto", "Low-Fat", "High-Protein"
    ]

    allergens = [
        "Lactose", "Eggs", "Shellfish", "Fishes", "Seafood",
        "Peanuts", "Gluten", "Sesame", "Nuts", "Soy", "Rice",
        "Red Meat", "Corn", "Wheat", "Fructose", "Chocolate", 
        "Msg"
    ]
    
    generated_dir = root_dir.joinpath('generated/tensors')
    if not generated_dir.exists():
        generated_dir.mkdir(parents=True)
    
    diets_tensors_file = generated_dir.joinpath('diets.json')
    allergens_tensors_file = generated_dir.joinpath('allergen.json')
    
    # Diets tensors loading
    diets_tensors = {}
    if diets_tensors_file.exists():
        try:
            with open(diets_tensors_file, mode="r") as f:
                diets_tensors = load(f)
            if any(
                (d not in diets_tensors.keys()) for d in diets
            ):
                diets_tensors = {}
                print("Diet tensors file incomplete, regenerating...")
        except:
            print("Diet tensors file cannot be read, regenerating...")
    else:
        print("Diet tensors file not found, creating...")
    
    if not diets_tensors:
        for diet in diets:
            diets_tensors[diet] = encode_sync_tensor(diet).tolist()
        with open(diets_tensors_file, mode="w") as f:
            dump(diets_tensors, f)
        print("Diet tensors file saved")
        
    # Allergen tensors loading
    allergens_tensors = {}
    if allergens_tensors_file.exists():
        try:
            with open(allergens_tensors_file, mode="r") as f:
                allergens_tensors = load(f)
            if any(
                (a not in allergens_tensors.keys()) for a in allergens
            ):
                allergens_tensors = {}
                print("Allergen tensors file incomplete, regenerating...")
        except:
            print("Allergen tensors file cannot be read, regenerating...")
    else:
        print("Allergen tensors file not found, creating...")
    
    if not allergens_tensors:
        for allergen in allergens:
            allergens_tensors[allergen] = encode_sync_tensor(allergen).tolist()
        with open(allergens_tensors_file, mode="w") as f:
            dump(allergens_tensors, f)
        print("Allergen tensors file saved")

    generated_dir = root_dir.joinpath('generated/sql')
    if not generated_dir.exists():
        generated_dir.mkdir(parents=True)

    _header = """/*
    KU Eater Ingredient Scoring for Diet and Allergen
    */"""
    
    parts = [
        _header,
        generate_diet_sql(conn_pool, diets_tensors),
        generate_allergen_sql(conn_pool, allergens_tensors)
    ]
    
    print("== FINISHING UP ==")
    
    with open(
        generated_dir.joinpath("ingredient_scoring.sql"),
        mode="w", encoding="utf-8"
    ) as f:
        f.write("\n".join(parts))
