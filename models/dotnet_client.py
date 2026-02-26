import logging
from typing import List, Dict, Optional
from config import settings

logger = logging.getLogger(__name__)


class DotNetClient:

    def __init__(self):
        self.base_url = settings.DOTNET_BACKEND_URL
        self.api_key  = settings.API_KEY

    def get_available_technicians(self) -> List[Dict]:
        """
        Hardcoded technicians - DB not accessible from Railway
        هيتحدث لما الـ .NET يضيف الـ endpoint
        """
        return [
            {
                'TechnicianId': 'tech-001',
                'DisplayName': 'Ahmed Mohamed',
                'Email': 'ahmed@test.com',
                'Specialization': 'maintenance,brakes,engine',
                'Rating': 4.8,
                'IsAvailable': True
            },
            {
                'TechnicianId': 'tech-002',
                'DisplayName': 'Mohamed Ali',
                'Email': 'mohamed@test.com',
                'Specialization': 'engine,transmission',
                'Rating': 4.5,
                'IsAvailable': True
            },
            {
                'TechnicianId': 'tech-003',
                'DisplayName': 'Ali Hassan',
                'Email': 'ali@test.com',
                'Specialization': 'brakes,suspension',
                'Rating': 4.2,
                'IsAvailable': True
            },
            {
                'TechnicianId': 'tech-004',
                'DisplayName': 'Khaled Omar',
                'Email': 'khaled@test.com',
                'Specialization': 'maintenance,engine',
                'Rating': 4.6,
                'IsAvailable': True
            },
            {
                'TechnicianId': 'tech-005',
                'DisplayName': 'Omar Salem',
                'Email': 'omar@test.com',
                'Specialization': 'transmission,suspension',
                'Rating': 4.0,
                'IsAvailable': True
            },
        ]

    def get_technician_stats(self, technician_id: str) -> Optional[Dict]:
        return {
            'TotalBookings': 10,
            'CompletedBookings': 8,
            'SuccessRate': 0.80
        }

    def get_technician_current_workload(self, technician_id: str) -> int:
        return 2

    def get_technician_reviews_avg(self, technician_id: str) -> float:
        ratings = {
            'tech-001': 4.8,
            'tech-002': 4.5,
            'tech-003': 4.2,
            'tech-004': 4.6,
            'tech-005': 4.0,
        }
        return ratings.get(technician_id, 4.0)

    def close(self):
        pass