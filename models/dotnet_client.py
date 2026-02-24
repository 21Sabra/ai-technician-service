import httpx
import logging
from typing import List, Dict, Optional
from config import settings

logger = logging.getLogger(__name__)


class DotNetClient:
    """بيجيب البيانات من الـ .NET بدل DB مباشرة"""
    
    def __init__(self):
        self.base_url = settings.DOTNET_BACKEND_URL
        self.api_key = settings.API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def get_available_technicians(self) -> List[Dict]:
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(
                    f"{self.base_url}/api/ai/technicians/available",
                    headers=self.headers
                )
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Found {len(data)} available technicians")
                    return data
                logger.error(f"Failed to get technicians: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"❌ Error calling .NET: {e}")
            return []
    
    def get_technician_stats(self, technician_id: str) -> Optional[Dict]:
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(
                    f"{self.base_url}/api/ai/technicians/{technician_id}/stats",
                    headers=self.headers
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.error(f"❌ Error getting stats: {e}")
            return None
    
    def get_technician_current_workload(self, technician_id: str) -> int:
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(
                    f"{self.base_url}/api/ai/technicians/{technician_id}/workload",
                    headers=self.headers
                )
                if response.status_code == 200:
                    data = response.json()
                    return int(data.get("currentWorkload", 0))
                return 0
        except Exception as e:
            logger.error(f"❌ Error getting workload: {e}")
            return 0
    
    def get_technician_reviews_avg(self, technician_id: str) -> float:
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(
                    f"{self.base_url}/api/ai/technicians/{technician_id}/rating",
                    headers=self.headers
                )
                if response.status_code == 200:
                    data = response.json()
                    return float(data.get("averageRating", 0.0))
                return 0.0
        except Exception as e:
            logger.error(f"❌ Error getting rating: {e}")
            return 0.0
    
    def close(self):
        pass