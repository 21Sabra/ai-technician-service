import pymssql
import logging
from typing import List, Dict, Optional
from config import settings

logger = logging.getLogger(__name__)


class Database:
    
    def __init__(self):
        self.connection: Optional[pymssql.Connection] = None
    
    def connect(self) -> bool:
        try:
            self.connection = pymssql.connect(
                server=settings.DB_SERVER,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                timeout=10
            )
            logger.info(f"✅ Connected to MS SQL Server: {settings.DB_NAME}")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    def get_available_technicians(self) -> List[Dict]:
        if not self.connection:
            return []
        try:
            cursor = self.connection.cursor(as_dict=True)
            query = """
                SELECT 
                    t.Id as TechnicianId,
                    u.DisplayName,
                    u.Email,
                    t.Specialization,
                    t.Rating,
                    t.IsAvailable
                FROM Technicians t
                INNER JOIN AspNetUsers u ON t.UserId = u.Id
                WHERE t.IsAvailable = 1
            """
            cursor.execute(query)
            technicians = cursor.fetchall()
            cursor.close()
            logger.info(f"Found {len(technicians)} available technicians")
            return technicians
        except Exception as e:
            logger.error(f"❌ Error fetching technicians: {e}")
            return []
    
    def get_technician_stats(self, technician_id: str) -> Optional[Dict]:
        if not self.connection:
            return None
        try:
            cursor = self.connection.cursor(as_dict=True)
            query = """
                SELECT 
                    COUNT(*) as TotalBookings,
                    SUM(CASE WHEN Status = 2 THEN 1 ELSE 0 END) as CompletedBookings,
                    CAST(SUM(CASE WHEN Status = 2 THEN 1 ELSE 0 END) AS FLOAT) / 
                        NULLIF(COUNT(*), 0) as SuccessRate
                FROM Bookings
                WHERE TechnicianId = %s
            """
            cursor.execute(query, (technician_id,))
            row = cursor.fetchone()
            cursor.close()
            return row
        except Exception as e:
            logger.error(f"❌ Error fetching technician stats: {e}")
            return None
    
    def get_technician_current_workload(self, technician_id: str) -> int:
        if not self.connection:
            return 0
        try:
            cursor = self.connection.cursor(as_dict=True)
            query = """
                SELECT COUNT(*) as CurrentWorkload
                FROM Bookings
                WHERE TechnicianId = %s
                AND Status IN (0, 1)
            """
            cursor.execute(query, (technician_id,))
            row = cursor.fetchone()
            cursor.close()
            return int(row['CurrentWorkload']) if row else 0
        except Exception as e:
            logger.error(f"❌ Error fetching workload: {e}")
            return 0
    
    def get_technician_reviews_avg(self, technician_id: str) -> float:
        if not self.connection:
            return 0.0
        try:
            cursor = self.connection.cursor(as_dict=True)
            query = """
                SELECT AVG(CAST(Rating AS FLOAT)) as AvgRating
                FROM Reviews
                WHERE TechnicianId = %s
            """
            cursor.execute(query, (technician_id,))
            row = cursor.fetchone()
            cursor.close()
            return float(row['AvgRating']) if row and row['AvgRating'] else 0.0
        except Exception as e:
            logger.error(f"❌ Error fetching reviews: {e}")
            return 0.0
    
    def close(self):
        if self.connection:
            self.connection.close()
            logger.info("✅ Database connection closed")