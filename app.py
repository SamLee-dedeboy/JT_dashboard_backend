from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import mental_model, sunburst, linking, flow

app = FastAPI(title="JT Dashboard API", version="1.0.0")

# Configure CORS to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    mental_model.router, prefix="/api/mental-model", tags=["mental-model"]
)
app.include_router(sunburst.router, prefix="/api/sunburst", tags=["sunburst"])
app.include_router(linking.router, prefix="/api/linking", tags=["linking"])
app.include_router(flow.router, prefix="/api/flow", tags=["flow"])


@app.get("/")
async def root():
    return {"message": "JT Dashboard API", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "JT Dashboard API is running"}


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
