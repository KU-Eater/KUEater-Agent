import asyncio
import sys

from os import getenv
from grpc import StatusCode
from grpc import aio
from generated.agent.main_pb2_grpc import add_KUEaterEmbeddingAgentServicer_to_server
from generated.agent.main_pb2 import (
    GetEmbeddingRequest, GetEmbeddingResponse,
    NewRecommendationsRequest, NewRecommendationsResponse
)
from rpc import AgentService
from model import encode

class AgentServiceImpl(AgentService):

    async def GetEmbedding(self, request: GetEmbeddingRequest, context: aio.ServicerContext) -> GetEmbeddingResponse:
        text = request.text
        if not text:
            _e = "Text is empty, nothing to encode"
            context.set_code(StatusCode.INVALID_ARGUMENT)
            context.set_details(_e)
            raise ValueError(_e)
        try:
            result = await encode(text)
            return GetEmbeddingResponse(
                vectors=result
            )
        except:
            _e = "Unexpected exception while encoding: {}".format(text)
            context.set_code(StatusCode.INTERNAL)
            context.set_details(_e)
            raise RuntimeError(_e)
    
    async def NewRecommendations(self, request: NewRecommendationsRequest, context: aio.ServicerContext) -> NewRecommendationsResponse:
        return await super().NewRecommendations(request, context)

async def serve(port: int=50052) -> None:
    server = aio.server()
    add_KUEaterEmbeddingAgentServicer_to_server(AgentServiceImpl(), server=server)
    listen_addr = "[::]:{}".format(port)
    server.add_insecure_port(listen_addr)
    print("Starting server on {}".format(listen_addr))
    await server.start()
    await server.wait_for_termination()

if __name__ == "__main__":
    
    import dotenv
    
    dotenv.load_dotenv()
    
    port = getenv("PORT")

    if not port:
        asyncio.run(serve())
    else:
        try:
            asyncio.run(serve(int(port)))
        except ValueError:
            print("Port is not an integer")
            sys.exit(1)