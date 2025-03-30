import ast
from pandas import DataFrame

def extract_uuids(ingstr):
    ingredients_list = ast.literal_eval(ingstr)
    return [item['id'] for item in ingredients_list]

def dict_from(dict_like: str):
    try:
        return ast.literal_eval(dict_like)
    except:
        raise ValueError("Cannot turn dictstring to dict") 