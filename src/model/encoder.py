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

def encode_sync_tensor(text: str) -> Tensor:
    transformer = Transformer.get()
    return transformer.encode(text)

def similarity_sync(lhs: Tensor, rhs: Tensor) -> float:
    transformer = Transformer.get()
    return float(transformer.similarity(lhs, rhs)[0][0])