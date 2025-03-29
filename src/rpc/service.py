from abc import abstractmethod, ABC

from grpc import aio
from generated.agent.main_pb2_grpc import KUEaterEmbeddingAgentServicer
from generated.agent.main_pb2 import (
    GetEmbeddingRequest, GetEmbeddingResponse,
    NewRecommendationsRequest, NewRecommendationsResponse
)


class AgentService(ABC, KUEaterEmbeddingAgentServicer):

    @abstractmethod
    async def GetEmbedding(
        self,
        request: GetEmbeddingRequest,
        context: aio.ServicerContext
    ) -> GetEmbeddingResponse:
        pass
    
    @abstractmethod
    async def NewRecommendations(
        self,
        request: NewRecommendationsRequest,
        context: aio.ServicerContext
    ) -> NewRecommendationsResponse:
        pass
