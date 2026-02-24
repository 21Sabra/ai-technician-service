from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime


class BookingServiceInfoDto(BaseModel):
    service_id: int = Field(..., alias="serviceId")
    service_name: str = Field(..., alias="serviceName")
    category: str

    model_config = {"populate_by_name": True}


class AITechnicianAssignmentRequest(BaseModel):
    booking_id: int = Field(..., alias="bookingId")
    services: List[BookingServiceInfoDto] = Field(..., min_length=1)
    scheduled_date: datetime = Field(..., alias="scheduledDate")
    priority: str = Field(default="normal")

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        if v.lower() not in ['urgent', 'normal', 'low']:
            raise ValueError('Priority must be urgent, normal, or low')
        return v.lower()

    model_config = {"populate_by_name": True}