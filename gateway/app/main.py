"""
HyperFileLens Gateway Service
Provides Kopia mount, file indexing, and AI query capabilities
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import settings
from .mount import kopia_mount
from .indexer import file_indexer
from .ai import ai_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting Gateway service...")
    
    # Initialize repository
    await kopia_mount.init_repository()
    
    # Mount repository
    mount_result = await kopia_mount.mount()
    logger.info(f"Mount result: {mount_result}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Gateway service...")
    await kopia_mount.unmount()


# Create FastAPI app
app = FastAPI(
    title="HyperFileLens Gateway",
    description="Kopia mount, file indexing, and AI query service",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Models ==============

class QueryRequest(BaseModel):
    """AI query request"""
    query: str
    extension: str = None


class SearchRequest(BaseModel):
    """File search request"""
    query: str
    extension: str = None
    limit: int = 100
    offset: int = 0


# ============== Mount Endpoints ==============

@app.get("/api/v1/mount/status")
async def get_mount_status():
    """Get Kopia mount status"""
    return await kopia_mount.get_status()


@app.post("/api/v1/mount/connect")
async def connect_repository():
    """Connect to Kopia repository"""
    return await kopia_mount.connect_repository()


@app.post("/api/v1/mount/mount")
async def mount_repository():
    """Mount Kopia repository"""
    return await kopia_mount.mount()


@app.post("/api/v1/mount/unmount")
async def unmount_repository():
    """Unmount Kopia repository"""
    return await kopia_mount.unmount()


# ============== Index Endpoints ==============

@app.get("/api/v1/index/stats")
async def get_index_stats():
    """Get file index statistics"""
    return file_indexer.get_stats()


@app.post("/api/v1/index/rebuild")
async def rebuild_index(background_tasks: BackgroundTasks):
    """Rebuild the file index"""
    background_tasks.add_task(file_indexer.scan_and_index)
    return {"status": "started", "message": "Index rebuild started in background"}


@app.post("/api/v1/index/search")
async def search_files(request: SearchRequest):
    """Search indexed files"""
    results = file_indexer.search(
        query=request.query,
        extension=request.extension,
        limit=request.limit,
        offset=request.offset
    )
    return {
        "results": results,
        "count": len(results),
        "query": request.query
    }


@app.delete("/api/v1/index")
async def clear_index():
    """Clear the file index"""
    return file_indexer.clear_index()


# ============== AI Endpoints ==============

@app.post("/api/v1/ai/query")
async def ai_query(request: QueryRequest):
    """Execute AI-powered file query"""
    # Get matching files
    files = file_indexer.search(
        query=request.query,
        extension=request.extension,
        limit=50
    )
    
    # Run AI query
    result = await ai_engine.query(request.query, files)
    
    return {
        **result,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/ai/suggest")
async def ai_suggest_restore(request: QueryRequest):
    """Get AI suggestions for file restoration"""
    files = file_indexer.search(
        query=request.query,
        extension=request.extension,
        limit=50
    )
    
    result = await ai_engine.suggest_restore(request.query, files)
    
    return {
        **result,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============== File Endpoints ==============

@app.get("/api/v1/files")
async def list_files(
    path: str = None,
    limit: int = 100,
    offset: int = 0
):
    """List files from mounted repository"""
    from pathlib import Path
    
    mount_path = Path(settings.KOPIA_MOUNT_PATH)
    if not mount_path.exists():
        raise HTTPException(status_code=503, detail="Repository not mounted")
    
    search_path = Path(path) if path else mount_path
    if not str(search_path).startswith(str(mount_path)):
        raise HTTPException(status_code=403, detail="Access denied")
    
    files = []
    directories = []
    
    try:
        if search_path.is_dir():
            for item in list(search_path.iterdir())[offset:offset+limit]:
                if item.is_file():
                    stat = item.stat()
                    files.append({
                        "name": item.name,
                        "path": str(item),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                elif item.is_dir():
                    directories.append({
                        "name": item.name,
                        "path": str(item)
                    })
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    return {
        "path": str(search_path),
        "files": files,
        "directories": directories
    }


# ============== Health ==============

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "gateway",
        "timestamp": datetime.utcnow().isoformat(),
        "mount_status": await kopia_mount.get_status()
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "HyperFileLens Gateway",
        "version": "1.0.0",
        "endpoints": {
            "mount": "/api/v1/mount",
            "index": "/api/v1/index",
            "ai": "/api/v1/ai",
            "files": "/api/v1/files"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
