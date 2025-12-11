from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from llm_handler import process_user_query
from database import init_database, get_dataset_catalog

load_dotenv()

# Start the server and initialize database
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    print("Database initialized")
    print(f"API running at http://localhost:8000")
    print(f"API docs available at http://localhost:8000/docs")
    yield  # server runs here, handling requests
    print("Shutting down server")

app = FastAPI(
    title="GIS Chatbot API",
    description="This is the backend of a natural language chatbot application that answers GIS spatial queries!",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    message: str
    features_geojson: Optional[dict] = None
    buffer_geojson: Optional[dict] = None
    count: Optional[int] = None
    params: Optional[dict] = None

class DatasetInfo(BaseModel):
    name: str
    description: str
    geometry_type: str
    tokens: list[str]  
    aliases: list[str] 

class DatasetsResponse(BaseModel):
    datasets: dict[str, DatasetInfo]
    count: int

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "message": "GIS Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/api/chat",  # main API endpoint for interacting with LLM
            "datasets": "/api/datasets",  # look at all datasets in database
            "docs": "/docs"  # interactive API documentation
        }
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chatbot endpoint that takes in natural language query and outputs GIS results
    
    Example queries:
    - "How many schools are within 1 mile of pipelines?"
    - "Find hospitals within 2 kilometers of roads"
    - "Which schools are near pipelines?"
    """
    try:
        result = await process_user_query(request.query)
        
        return ChatResponse(
            message=result['message'],
            features_geojson=result.get('features_geojson'),
            buffer_geojson=result.get('buffer_geojson'),
            count=result.get('count'),
            params=result.get('params')
        )
    
    except ValueError as e:
        # User-facing errors (e.g., dataset not found)
        return ChatResponse(
            message=f"{str(e)}",
            features_geojson=None,
            buffer_geojson=None,
            count=None,
            params=None
        )
    
    except Exception as e:
        # System errors - log but return user-friendly message
        print(f"System error: {e}")
        return ChatResponse(
            message="An error occurred processing your query. Please try again or rephrase your question!",
            features_geojson=None,
            buffer_geojson=None,
            count=None,
            params=None
        )

@app.get("/api/datasets", response_model=DatasetsResponse)
async def get_datasets():
    """
    Get list of all available datasets in the database
    
    Returns dataset names, descriptions, and geometry types that can be used in spatial queries.
    """
    try:
        catalog = get_dataset_catalog()
        
        if not catalog:
            return DatasetsResponse(
                datasets={},
                count=0
            )
        
        return DatasetsResponse(
            datasets=catalog,
            count=len(catalog)
        )
    
    except Exception as e:
        print(f"Error fetching datasets: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve dataset catalog"
        )

# Run server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )