import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# LangChain & AI Imports
from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

# Configure Enterprise Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load Environment Variables (.env)
load_dotenv()

app = FastAPI(title="Sovereign Hybrid AI Gateway", version="1.4.0")

# --- Infrastructure & Governance Configurations ---
# FinOps: Centralized external model selection defaulting to low-cost tier
EXTERNAL_MODEL = os.getenv("EXTERNAL_MODEL", "gpt-4o-mini") 
# Server-Side Governance: Enforce Zero-Trust by default
ROUTING_POLICY = os.getenv("ROUTING_POLICY", "STRICT_LOCAL") 

QDRANT_URL = "http://192.168.0.122:6333"
OLLAMA_URL = "http://192.168.0.121:11434"
COLLECTION_NAME = "mainframe_logic"

# --- Phase 2 & 4: Local Memory (RAG) Initialization ---
logger.info("Initializing CPU-bound embeddings for RAG...")
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'} # CRITICAL: Forces execution to CPU, preventing GPU/CUDA crashes
)

logger.info(f"Connecting to Qdrant Vector DB at {QDRANT_URL}...")
qdrant_client = QdrantClient(url=QDRANT_URL)
vector_store = QdrantVectorStore(
    client=qdrant_client, 
    collection_name=COLLECTION_NAME, 
    embedding=embeddings
)

# --- LLM Client Instantiation ---
local_llm = ChatOllama(base_url=OLLAMA_URL, model="llama3", temperature=0.1)
public_llm = ChatOpenAI(model=EXTERNAL_MODEL, temperature=0.7)

# --- Prompt Engineering (Phase 4) ---
# We force the LLM to answer STRICTLY based on the retrieved COBOL context
SOVEREIGN_PROMPT_TEMPLATE = """
You are an Enterprise AI Architect assisting with Mainframe modernization.
You have been provided with the following highly confidential legacy COBOL code snippets.

Context:
{context}

Question: {question}

Instructions:
1. Answer the question using ONLY the context provided above.
2. If the answer is not contained within the context, state "I do not have enough sovereign context to answer this."
3. Do not use outside knowledge. Do not hallucinate.
"""
sovereign_prompt = PromptTemplate(template=SOVEREIGN_PROMPT_TEMPLATE, input_variables=["context", "question"])

# --- API Payloads ---
class QueryPayload(BaseModel):
    prompt: str
    classification: str # "CONFIDENTIAL" or "PUBLIC"

# --- Centralized Policy Router ---
@app.post("/v1/query")
async def route_query(payload: QueryPayload):
    logger.info(f"Incoming query. User classification: {payload.classification}. Policy: {ROUTING_POLICY}")

    # Zero-Trust Enforcement: If STRICT_LOCAL is on, force all traffic internally regardless of user payload
    is_confidential = payload.classification.upper() == "CONFIDENTIAL" or ROUTING_POLICY == "STRICT_LOCAL"

    if is_confidential:
        logger.info("Routing -> CONFIDENTIAL (LXC 121: Llama 3 via RAG)")
        try:
            # 1. Asynchronously Retrieve Top-3 relevant COBOL chunks
            logger.info("Querying Qdrant for semantic context...")
            docs = await vector_store.asimilarity_search(payload.prompt, k=3)
            
            # 2. Format the context
            retrieved_context = "\n\n".join([doc.page_content for doc in docs])
            logger.info(f"Retrieved {len(docs)} chunks from Vector DB.")

            # 3. Inject context into the prompt template
            final_prompt = sovereign_prompt.format(context=retrieved_context, question=payload.prompt)
            
            # 4. Generate Sovereign Answer
            response = await local_llm.ainvoke(final_prompt)
            return {
                "route": "INTERNAL_SOVEREIGN",
                "model": "llama3",
                "response": response.content,
                "chunks_retrieved": len(docs)
            }
        except Exception as e:
            logger.error(f"Internal generation failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Sovereign AI Node Unavailable.")
    
    else:
        # FinOps & External Routing
        logger.info(f"Routing -> PUBLIC (Cloud API: {EXTERNAL_MODEL})")
        try:
            response = await public_llm.ainvoke(payload.prompt)
            return {
                "route": "EXTERNAL_PUBLIC",
                "model": EXTERNAL_MODEL,
                "response": response.content
            }
        except Exception as e:
            logger.error(f"Public API call failed: {str(e)}")
            raise HTTPException(status_code=502, detail="External Cloud API Unavailable.")