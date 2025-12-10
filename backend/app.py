from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from llm_handler import process_user_query
from database import init_database

load_dotenv()

app = FastAPI(title="GIS Chatbot API")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    message: str
    geojson: dict = None
    metadata: dict = None

@app.on_event("startup")
async def startup_event():
    """Initialize database once when server starts"""
    init_database()
    print("✅ Database initialized")

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main endpoint: natural language query → GIS results
    Example: "How many schools are within 1 mile of pipelines?"
    """
    try:
        result = await process_user_query(request.query)
        
        return ChatResponse(
            message=result['message'],
            geojson=result.get('geojson'),
            metadata=result.get('metadata')
        )
    
    except ValueError as e:
        # User-facing errors (e.g., dataset not found)
        return ChatResponse(
            message=f"❌ {str(e)}",
            geojson=None
        )
    
    except Exception as e:
        # System errors
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)