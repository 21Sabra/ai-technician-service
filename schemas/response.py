from pydantic import BaseModel, Field
from typing import List, Optional


class AssignmentFactorsDto(BaseModel):
    specialization_match: float = Field(..., alias="specializationMatch")
    location_proximity: float = Field(..., alias="locationProximity")
    rating: float
    workload: str
    estimated_arrival_time: Optional[str] = Field(None, alias="estimatedArrivalTime")

    model_config = {"populate_by_name": True}


class AlternativeTechnicianDto(BaseModel):
    technician_id: str = Field(..., alias="technicianId")
    confidence: float
    reason: Optional[str] = None

    model_config = {"populate_by_name": True}


class AITechnicianAssignmentResponse(BaseModel):
    recommended_technician_id: str = Field(..., alias="recommendedTechnicianId")
    confidence: float
    reason: str
    alternatives: List[AlternativeTechnicianDto] = Field(default_factory=list)
    factors: Optional[AssignmentFactorsDto] = None

    model_config = {"populate_by_name": True}


class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None