import asyncio
import os
import time
from enum import Enum
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient

load_dotenv()

app = FastAPI(title="Sovereign AI Gateway (Phase 2 - RAG Ready)", version="2.0")

class DataClassification(str, Enum):
    CONFIDENTIAL = "CONFIDENTIAL"
    PUBLIC = "PUBLIC"

class RouterRequest(BaseModel):
    query: str = Field(..., description="The user prompt or system query.")
    classification: DataClassification = Field(
        default=DataClassification.CONFIDENTIAL
    )

class HybridModelRouter:
    def __init__(self):
        self.routing_policy = os.getenv("ROUTING_POLICY", "STRICT_LOCAL").upper()
        
        # 1. Initialize Sovereign LLM
        self.local_llm = ChatOllama(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://192.168.0.121:11434"),
            model=os.getenv("OLLAMA_MODEL", "llama3"),
            temperature=0.1 
        )
        
        # 2. Initialize Cloud LLM
        self.cloud_llm = ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o",
            temperature=0.3
        )

        # 3. Initialize CPU-Forced Embeddings (all-MiniLM-L6-v2)
        print("\n[INIT] Loading HuggingFace Embeddings (Strictly CPU)...", flush=True)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}, # GUARANTEES NO GPU CALLS
            encode_kwargs={'normalize_embeddings': True}
        )
        print("[INIT] Embeddings loaded successfully.", flush=True)

        # 4. Initialize Qdrant Vector DB Connection
        qdrant_url = os.getenv("QDRANT_URL", "http://192.168.0.122:6333")
        print(f"[INIT] Connecting to Qdrant Vector DB at {qdrant_url}...", flush=True)
        try:
            self.qdrant = QdrantClient(url=qdrant_url)
            # Test connection by listing collections
            collections = self.qdrant.get_collections()
            print(f"[INIT] Qdrant connected. Existing collections: {collections.collections}", flush=True)
        except Exception as e:
            print(f"[INIT ERROR] Failed to connect to Qdrant: {e}", flush=True)

    async def process_query(self, request: RouterRequest) -> dict:
        messages = [HumanMessage(content=request.query)]
        start_time = time.time()
        
        print(f"\n[GATEWAY] Received query: '{request.query}'", flush=True)

        route_to_cloud = False
        if self.routing_policy == "LOCAL_FIRST" or self.routing_policy == "HYBRID":
            if request.classification == DataClassification.PUBLIC:
                route_to_cloud = True

        if route_to_cloud:
            print("[ROUTING] Action: Sending to Cloud (GPT-4o)...", flush=True)
            response = await self.cloud_llm.ainvoke(messages)
            source = "Cloud Endpoint (GPT-4o)"
        else:
            print("[ROUTING] Action: Sending to Sovereign Edge (LXC 121)...", flush=True)
            response = await self.local_llm.ainvoke(messages)
            source = f"Sovereign Edge (Llama 3 @ 192.168.0.121)"

        execution_time = round(time.time() - start_time, 2)
        print(f"[GATEWAY] Execution Complete: {execution_time}s", flush=True)
        
        return {
            "source": source,
            "applied_policy": self.routing_policy,
            "execution_time_seconds": execution_time,
            "response": response.content
        }

router_instance = HybridModelRouter()

@app.post("/v1/query")
async def process_query_endpoint(request: RouterRequest):
    try:
        return await router_instance.process_query(request)
    except Exception as e:
        print(f"[ERROR] {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))
