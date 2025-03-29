import asyncio
from torch import Tensor
from .transformer import Transformer

async def encode(text: str) -> str:
    transformer = Transformer.get()
    tensors: Tensor = await asyncio.to_thread(transformer.encode, text)
    return str(tensors.tolist())

def encode_sync(text: str) -> str:
    transformer = Transformer.get()
    tensors: Tensor = transformer.encode(text)
    return str(tensors.tolist())