import httpx
import logging
from typing import List, Dict, Optional
from config import settings

logger = logging.getLogger(__name__)


class DotNetClient:

    def __init__(self):
        self.base_url = settings.DOTNET_BACKEND_URL
        self.api_key  = settings.API_KEY
        self.headers  = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json"
        }

    def get_available_technicians(self) -> List[Dict]:
        """GET /api/Technicians/available"""
        try:
            url = f"{self.base_url}/api/Technicians/available"
            logger.info(f"Fetching available technicians from {url}")

            with httpx.Client(timeout=10) as client:
                response = client.get(url, headers=self.headers)

            if response.status_code != 200:
                logger.error(f"Failed: {response.status_code} - {response.text}")
                return self._get_fallback_technicians()

            data = response.json()
            logger.info(f"Found {len(data)} available technicians")

            return [
                {
                    'TechnicianId': t.get('id'),
                    'DisplayName':  t.get('displayName', ''),
                    'Email':        t.get('email', ''),
                    'Specialization': t.get('specialization', ''),
                    'Rating':       float(t.get('rating', 0)),
                    'IsAvailable':  t.get('isAvailable', True)
                }
                for t in data
            ]

        except Exception as e:
            logger.error(f"Error fetching technicians: {e} — using fallback")
            return self._get_fallback_technicians()

    def get_technician_stats(self, technician_id: str) -> Optional[Dict]:
        """GET /api/Technicians/{id}"""
        try:
            url = f"{self.base_url}/api/Technicians/{technician_id}"
            with httpx.Client(timeout=10) as client:
                response = client.get(url, headers=self.headers)

            if response.status_code != 200:
                return {'TotalBookings': 10, 'CompletedBookings': 8, 'SuccessRate': 0.80}

            data = response.json()
            return {
                'TotalBookings':     data.get('totalBookings', 10),
                'CompletedBookings': data.get('completedBookings', 8),
                'SuccessRate':       data.get('successRate', 0.80)
            }
        except Exception as e:
            logger.error(f"Error fetching stats for {technician_id}: {e}")
            return {'TotalBookings': 10, 'CompletedBookings': 8, 'SuccessRate': 0.80}

    def get_technician_current_workload(self, technician_id: str) -> int:
        try:
            url = f"{self.base_url}/api/Technicians/{technician_id}"
            with httpx.Client(timeout=10) as client:
                response = client.get(url, headers=self.headers)
            if response.status_code != 200:
                return 2
            return int(response.json().get('currentWorkload', 2))
        except Exception as e:
            logger.error(f"Error fetching workload for {technician_id}: {e}")
            return 2

    def get_technician_reviews_avg(self, technician_id: str) -> float:
        try:
            url = f"{self.base_url}/api/Technicians/{technician_id}"
            with httpx.Client(timeout=10) as client:
                response = client.get(url, headers=self.headers)
            if response.status_code != 200:
                return 4.0
            return float(response.json().get('rating', 4.0))
        except Exception as e:
            logger.error(f"Error fetching rating for {technician_id}: {e}")
            return 4.0

    def _get_fallback_technicians(self) -> List[Dict]:
        """Fallback لو الـ .NET مش متاح"""
        logger.warning("Using fallback technicians data")
        return [
            {'TechnicianId': 'tech-001', 'DisplayName': 'Ahmed Mohamed',
             'Email': 'ahmed@test.com', 'Specialization': 'maintenance,brakes,engine',
             'Rating': 4.8, 'IsAvailable': True},
            {'TechnicianId': 'tech-002', 'DisplayName': 'Mohamed Ali',
             'Email': 'mohamed@test.com', 'Specialization': 'engine,transmission',
             'Rating': 4.5, 'IsAvailable': True},
            {'TechnicianId': 'tech-003', 'DisplayName': 'Ali Hassan',
             'Email': 'ali@test.com', 'Specialization': 'brakes,suspension',
             'Rating': 4.2, 'IsAvailable': True},
            {'TechnicianId': 'tech-004', 'DisplayName': 'Khaled Omar',
             'Email': 'khaled@test.com', 'Specialization': 'maintenance,engine',
             'Rating': 4.6, 'IsAvailable': True},
            {'TechnicianId': 'tech-005', 'DisplayName': 'Omar Salem',
             'Email': 'omar@test.com', 'Specialization': 'transmission,suspension',
             'Rating': 4.0, 'IsAvailable': True},
        ]

    def close(self):
        pass