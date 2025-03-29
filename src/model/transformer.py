from os import getenv, getcwd
from os.path import sep
from pathlib import Path
from sentence_transformers import SentenceTransformer

def get_model_path():
    
    pth = getenv("MODEL_PATH")
    if not pth:
        return Path(getcwd()).joinpath('models/kueater-model-27032025-onnx').resolve().__str__()
    
    if pth.startswith(sep):
        return pth
    
    return Path(getcwd()).joinpath(pth).resolve().__str__()

class Transformer:
    
    __instance = None
    
    __transformer: SentenceTransformer
    
    def __init__(self):
        raise RuntimeError("Call get() instead")
    
    @classmethod
    def get(cls) -> SentenceTransformer:
        if cls.__instance is None:
            print("Instantiating transformer...")
            cls.__instance = cls.__new__(cls)
            
            model_path = get_model_path()
    
            opts = {
                "device": "cpu",
                "backend": "onnx"
            }
            
            cls.__instance.__transformer = SentenceTransformer(model_path, **opts)
        return cls.__instance.__transformer
