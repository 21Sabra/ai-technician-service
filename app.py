from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import logging
from typing import Optional

from config import settings
from models.database import Database
from models.technician_recommender import TechnicianRecommender
from schemas.request import AITechnicianAssignmentRequest
from schemas.response import AITechnicianAssignmentResponse, ErrorResponse
from utils.logger import setup_logger

logger = setup_logger()

db: Optional[Database] = None
recommender: Optional[TechnicianRecommender] = None

# ✅ ده بيضيف 🔒 في الـ Swagger تلقائياً
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, recommender
    
    logger.info("="*60)
    logger.info("🚀 AI Technician Assignment Service Starting...")
    logger.info("="*60)
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database: {settings.DB_NAME}")
    logger.info(f"Port: {settings.API_PORT}")
    logger.info("="*60)
    
    db = Database()
    if db.connect():
        recommender = TechnicianRecommender(db)
        logger.info("✅ Service initialized successfully")
    else:
        logger.error("❌ Failed to initialize service")
    
    yield
    
    logger.info("🛑 Shutting down service...")
    if db:
        db.close()
    logger.info("✅ Shutdown complete")


app = FastAPI(
    title="AI Technician Assignment Service",
    description="Intelligent technician recommendation system for car maintenance bookings",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ✅ Authentication بـ HTTPBearer - بيظهر في Swagger صح
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != settings.API_KEY:
        logger.warning(f"❌ Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "AI Technician Assignment Service",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "database_connected": db is not None and db.connection is not None
    }


@app.post(
    "/api/assign-technician",
    response_model=AITechnicianAssignmentResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    tags=["Technician Assignment"],
    dependencies=[Depends(verify_api_key)]
)
async def assign_technician(request: AITechnicianAssignmentRequest):
    if not recommender:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )
    
    try:
        logger.info(f"📨 Received request for booking {request.booking_id}")
        
        booking_data = {
            'booking_id': request.booking_id,
            'services': [s.model_dump(by_alias=True) for s in request.services],
            'scheduled_date': request.scheduled_date.isoformat(),
            'location': request.location.model_dump() if request.location else None,
            'priority': request.priority
        }
        
        result = recommender.recommend(booking_data)
        
        if 'error' in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result['error']
            )
        
        logger.info(f"✅ Recommended technician {result['recommended_technician_id']} for booking {request.booking_id}")
        return AITechnicianAssignmentResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e) if settings.DEBUG else "Internal server error"
        )


@app.get(
    "/api/technicians/available",
    tags=["Technicians"],
    dependencies=[Depends(verify_api_key)]
)
async def get_available_technicians():
    if not db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not connected"
        )
    try:
        technicians = db.get_available_technicians()
        return {"count": len(technicians), "technicians": technicians}
    except Exception as e:
        logger.error(f"Error fetching technicians: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e) if settings.DEBUG else "Internal server error"
        )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
# ```

# ---

# دلوقتي في الـ Swagger:

# **1.** هتلاقي زرار **Authorize 🔒** فوق يمين الصفحة

# **2.** اضغطه وحط في الـ `Value` field:
# ```
# CarMaintenance_AI_2026_SecretKey!