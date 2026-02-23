import pyodbc
import logging
from typing import List, Dict, Optional
from config import settings

logger = logging.getLogger(__name__)


class Database:
    """MS SQL Server database connection and queries"""
    
    def __init__(self):
        self.connection: Optional[pyodbc.Connection] = None
    
    def connect(self) -> bool:
        """Connect to MS SQL Server"""
        try:
            self.connection = pyodbc.connect(
                settings.database_url_pyodbc,
                timeout=10
            )
            
            logger.info(f"✅ Connected to MS SQL Server: {settings.DB_NAME}")
            return True
            
        except pyodbc.Error as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    def get_available_technicians(self) -> List[Dict]:
        """
        Get all available technicians
        
        Returns:
            List of technician dictionaries
        """
        if not self.connection:
            logger.error("No database connection")
            return []
        
        try:
            cursor = self.connection.cursor()
            
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
            
            # Convert rows to dictionaries
            columns = [column[0] for column in cursor.description]
            technicians = []
            
            for row in cursor.fetchall():
                tech_dict = dict(zip(columns, row))
                technicians.append(tech_dict)
            
            cursor.close()
            
            logger.info(f"Found {len(technicians)} available technicians")
            return technicians
            
        except pyodbc.Error as e:
            logger.error(f"❌ Error fetching technicians: {e}")
            return []
    
    def get_technician_stats(self, technician_id: str) -> Optional[Dict]:
        """
        Get technician performance statistics
        
        Args:
            technician_id: Technician ID
        
        Returns:
            Dictionary with stats or None
        """
        if not self.connection:
            return None
        
        try:
            cursor = self.connection.cursor()
            
            query = """
                SELECT 
                    COUNT(*) as TotalBookings,
                    SUM(CASE WHEN Status = 2 THEN 1 ELSE 0 END) as CompletedBookings,
                    CAST(SUM(CASE WHEN Status = 2 THEN 1 ELSE 0 END) AS FLOAT) / 
                        NULLIF(COUNT(*), 0) as SuccessRate
                FROM Bookings
                WHERE TechnicianId = ?
            """
            
            cursor.execute(query, (technician_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [column[0] for column in cursor.description]
                stats = dict(zip(columns, row))
                cursor.close()
                return stats
            
            cursor.close()
            return None
            
        except pyodbc.Error as e:
            logger.error(f"❌ Error fetching technician stats: {e}")
            return None
    
    def get_technician_current_workload(self, technician_id: str) -> int:
        """
        Get current number of pending/in-progress bookings
        
        Args:
            technician_id: Technician ID
        
        Returns:
            Number of active bookings
        """
        if not self.connection:
            return 0
        
        try:
            cursor = self.connection.cursor()
            
            query = """
                SELECT COUNT(*) as CurrentWorkload
                FROM Bookings
                WHERE TechnicianId = ?
                AND Status IN (0, 1)  -- Pending=0, InProgress=1
            """
            
            cursor.execute(query, (technician_id,))
            row = cursor.fetchone()
            
            workload = row[0] if row else 0
            cursor.close()
            
            return workload
            
        except pyodbc.Error as e:
            logger.error(f"❌ Error fetching workload: {e}")
            return 0
    
    def get_technician_reviews_avg(self, technician_id: str) -> float:
        """
        Get average rating from reviews
        
        Args:
            technician_id: Technician ID
        
        Returns:
            Average rating (0.0 to 5.0)
        """
        if not self.connection:
            return 0.0
        
        try:
            cursor = self.connection.cursor()
            
            query = """
                SELECT AVG(CAST(Rating AS FLOAT)) as AvgRating
                FROM Reviews
                WHERE TechnicianId = ?
            """
            
            cursor.execute(query, (technician_id,))
            row = cursor.fetchone()
            
            avg_rating = row[0] if row and row[0] else 0.0
            cursor.close()
            
            return float(avg_rating)
            
        except pyodbc.Error as e:
            logger.error(f"❌ Error fetching reviews: {e}")
            return 0.0
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("✅ Database connection closed")