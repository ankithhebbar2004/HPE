from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from datetime import datetime
from dotenv import load_dotenv
from typing import Any, Dict

# Load environment variables
load_dotenv()

# Configuration
SPRING_BACKEND_URL = os.getenv("SPRING_BACKEND_URL", "http://localhost:8080")
API_KEY = os.getenv("API_KEY", "")
PORT = int(os.getenv("PORT", 5000))

# Initialize FastAPI
app = FastAPI(
    title="Python Backend Service",
    description="Simple Python backend that connects to a Spring Boot backend",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a reusable HTTP client
http_client = httpx.AsyncClient(timeout=30.0)

@app.on_event("shutdown")
async def shutdown_event():
    """Close the HTTP client on shutdown"""
    await http_client.aclose()

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "service": "python-backend"}

@app.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_to_spring(request: Request, path: str):
    """Dynamic proxy to Spring Boot backend for any endpoint"""
    url = f"{SPRING_BACKEND_URL}/{path}"
    
    # Get request content
    body = await request.body()
    
    # Prepare headers
    headers = dict(request.headers)
    headers.pop("host", None)
    
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    
    try:
        # Forward the request to Spring Boot
        response = await http_client.request(
            method=request.method,
            url=url,
            headers=headers,
            params=dict(request.query_params),
            content=body,
        )
        
        # Return the Spring Boot response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error communicating with backend: {str(e)}")

@app.post("/api/process")
async def process_data(data: Dict[str, Any]):
    """Process data and forward to Spring Boot"""
    try:
        # Example processing
        processed_data = {
            "processed": True,
            "original": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # Forward to Spring Boot
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SPRING_BACKEND_URL}/api/processed-data",
                json=processed_data,
                headers={"Content-Type": "application/json"}
            )
            
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print(f"Starting FastAPI backend service on port {PORT}")
    print(f"Connecting to Spring Boot backend at {SPRING_BACKEND_URL}")
    print(f"API documentation available at http://localhost:{PORT}/docs")
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)