import httpx
import pymssql
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

    def _get_db_connection(self):
        return pymssql.connect(
            server=settings.DB_SERVER,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            timeout=10
        )

    def get_available_technicians(self) -> List[Dict]:
        """جيب الفنيين من الـ DB مباشرة"""
        try:
            conn   = self._get_db_connection()
            cursor = conn.cursor(as_dict=True)
            cursor.execute("""
                SELECT 
                    t.Id           AS TechnicianId,
                    u.DisplayName,
                    u.Email,
                    t.Specialization,
                    t.Rating,
                    t.IsAvailable
                FROM Technicians t
                INNER JOIN AspNetUsers u ON t.UserId = u.Id
                WHERE t.IsAvailable = 1
            """)
            technicians = cursor.fetchall()
            cursor.close()
            conn.close()
            logger.info(f"Found {len(technicians)} available technicians")
            return technicians
        except Exception as e:
            logger.error(f"❌ Error fetching technicians: {e}")
            return []

    def get_technician_stats(self, technician_id: str) -> Optional[Dict]:
        try:
            conn   = self._get_db_connection()
            cursor = conn.cursor(as_dict=True)
            cursor.execute("""
                SELECT 
                    COUNT(*) as TotalBookings,
                    SUM(CASE WHEN Status = 2 THEN 1 ELSE 0 END) as CompletedBookings,
                    CAST(SUM(CASE WHEN Status = 2 THEN 1 ELSE 0 END) AS FLOAT) / 
                        NULLIF(COUNT(*), 0) as SuccessRate
                FROM Bookings
                WHERE TechnicianId = %s
            """, (technician_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row
        except Exception as e:
            logger.error(f"❌ Error fetching stats: {e}")
            return None

    def get_technician_current_workload(self, technician_id: str) -> int:
        try:
            conn   = self._get_db_connection()
            cursor = conn.cursor(as_dict=True)
            cursor.execute("""
                SELECT COUNT(*) as CurrentWorkload
                FROM Bookings
                WHERE TechnicianId = %s AND Status IN (0, 1)
            """, (technician_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return int(row['CurrentWorkload']) if row else 0
        except Exception as e:
            logger.error(f"❌ Error fetching workload: {e}")
            return 0

    def get_technician_reviews_avg(self, technician_id: str) -> float:
        try:
            conn   = self._get_db_connection()
            cursor = conn.cursor(as_dict=True)
            cursor.execute("""
                SELECT AVG(CAST(Rating AS FLOAT)) as AvgRating
                FROM Reviews
                WHERE TechnicianId = %s
            """, (technician_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return float(row['AvgRating']) if row and row['AvgRating'] else 0.0
        except Exception as e:
            logger.error(f"❌ Error fetching reviews: {e}")
            return 0.0

    def close(self):
        pass
