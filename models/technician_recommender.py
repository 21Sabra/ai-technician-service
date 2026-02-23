import math
import logging
from typing import List, Dict, Optional
from datetime import datetime
from config import settings

logger = logging.getLogger(__name__)


class TechnicianRecommender:
    """
    Technician Recommendation System using Weighted Scoring
    
    Scoring Formula:
    Total Score = (Specialization × 0.40) + (Performance × 0.30) + 
                  (Rating × 0.20) + (Availability × 0.10)
    """
    
    def __init__(self, db):
        self.db = db
        
        # Weights from config
        self.weights = {
            'specialization': settings.WEIGHT_SPECIALIZATION,
            'performance': settings.WEIGHT_PERFORMANCE,
            'rating': settings.WEIGHT_RATING,
            'availability': settings.WEIGHT_AVAILABILITY
        }
        
        logger.info(f"Recommender initialized with weights: {self.weights}")
    
    def recommend(self, booking_data: dict) -> dict:
        """
        Main recommendation function
        
        Args:
            booking_data: {
                'booking_id': int,
                'services': [{'category': str, ...}],
                'scheduled_date': str,
                'location': {'latitude': float, 'longitude': float},
                'priority': str
            }
        
        Returns:
            Recommendation response
        """
        logger.info(f"🔍 Starting recommendation for booking {booking_data.get('booking_id')}")
        
        # 1. Get available technicians
        technicians = self.db.get_available_technicians()
        
        if not technicians:
            logger.warning("⚠️ No available technicians found")
            return {
                'error': 'No available technicians found',
                'recommended_technician_id': None
            }
        
        logger.info(f"Found {len(technicians)} available technicians")
        
        # 2. Calculate scores for each technician
        scored_technicians = []
        
        for tech in technicians:
            try:
                scores = self._calculate_scores(tech, booking_data)
                total_score = self._calculate_total_score(scores)
                
                scored_technicians.append({
                    'technician_id': tech['TechnicianId'],
                    'technician_name': tech['DisplayName'],
                    'email': tech['Email'],
                    'total_score': total_score,
                    'confidence': total_score,
                    'scores': scores
                })
                
                logger.debug(
                    f"Technician {tech['TechnicianId']}: "
                    f"Score={total_score:.3f}, "
                    f"Spec={scores['specialization']:.2f}, "
                    f"Perf={scores['performance']:.2f}, "
                    f"Rating={scores['rating']:.2f}, "
                    f"Avail={scores['availability']:.2f}"
                )
                
            except Exception as e:
                logger.error(f"Error scoring technician {tech.get('TechnicianId')}: {e}")
                continue
        
        if not scored_technicians:
            return {
                'error': 'Failed to score technicians',
                'recommended_technician_id': None
            }
        
        # 3. Sort by total score (highest first)
        scored_technicians.sort(key=lambda x: x['total_score'], reverse=True)
        
        # 4. Get best technician
        best = scored_technicians[0]
        
        logger.info(
            f"✅ Best technician: {best['technician_id']} "
            f"({best['technician_name']}) with score {best['total_score']:.3f}"
        )
        
        # 5. Prepare response
        return {
            'recommended_technician_id': best['technician_id'],
            'confidence': round(best['confidence'], 2),
            'reason': self._generate_reason(best['scores']),
            'alternatives': [
                {
                    'technician_id': t['technician_id'],
                    'confidence': round(t['confidence'], 2),
                    'reason': self._generate_reason(t['scores'])
                }
                for t in scored_technicians[1:3]  # Top 2 alternatives
            ],
            'factors': {
                'specialization_match': round(best['scores']['specialization'], 2),
                'location_proximity': round(best['scores']['availability'], 2),
                'rating': round(best['scores']['rating'], 2),
                'workload': self._get_workload_label(best['scores']['performance'])
            }
        }
    
    def _calculate_scores(self, technician: dict, booking_data: dict) -> dict:
        """Calculate individual scores for a technician"""
        
        return {
            'specialization': self._calculate_specialization_score(
                technician, 
                booking_data.get('services', [])
            ),
            'performance': self._calculate_performance_score(
                technician['TechnicianId']
            ),
            'rating': self._calculate_rating_score(
                technician
            ),
            'availability': self._calculate_availability_score(
                technician['TechnicianId'],
                booking_data.get('location')
            )
        }
    
    def _calculate_specialization_score(
        self, 
        technician: dict, 
        services: list
    ) -> float:
        """
        Calculate specialization match score
        
        Logic:
        - Extract service categories from booking
        - Match against technician's specializations
        - Return percentage match (0.0 to 1.0)
        
        Args:
            technician: Technician data
            services: List of services in booking
        
        Returns:
            Score between 0.0 and 1.0
        """
        if not services:
            return 0.5  # Neutral score
        
        # Get requested categories (lowercase for comparison)
        requested_categories = [
            s.get('category', '').lower().strip() 
            for s in services
        ]
        requested_categories = [c for c in requested_categories if c]
        
        if not requested_categories:
            return 0.5
        
        # Get technician specializations (comma-separated in DB)
        tech_specs = technician.get('Specialization', '').lower()
        tech_specs_list = [s.strip() for s in tech_specs.split(',') if s.strip()]
        
        if not tech_specs_list:
            return 0.3  # Low score if no specialization
        
        # Calculate matches
        matches = 0
        for category in requested_categories:
            # Check if category matches any specialization
            if any(category in spec or spec in category for spec in tech_specs_list):
                matches += 1
        
        # Calculate match percentage
        match_percentage = matches / len(requested_categories)
        
        # Boost score slightly if perfect match
        if match_percentage == 1.0:
            return 0.95
        elif match_percentage >= 0.5:
            return 0.70 + (match_percentage * 0.20)  # 0.70 to 0.90
        else:
            return 0.50 + (match_percentage * 0.20)  # 0.50 to 0.70
    
    def _calculate_performance_score(self, technician_id: str) -> float:
        """
        Calculate performance score based on:
        1. Success rate (completed bookings)
        2. Current workload
        
        Args:
            technician_id: Technician ID
        
        Returns:
            Score between 0.0 and 1.0
        """
        # Get technician stats
        stats = self.db.get_technician_stats(technician_id)
        
        if not stats or stats.get('TotalBookings', 0) == 0:
            # New technician - give moderate score
            return 0.65
        
        # 1. Success rate (60% weight)
        success_rate = stats.get('SuccessRate', 0.0)
        if success_rate is None:
            success_rate = 0.8  # Default
        
        # 2. Current workload (40% weight)
        current_workload = self.db.get_technician_current_workload(technician_id)
        
        # Convert workload to score (lower workload = better)
        # 0 bookings = 1.0, 10+ bookings = 0.0
        workload_score = max(0.0, 1.0 - (current_workload / 10.0))
        
        # Combine
        performance_score = (success_rate * 0.6) + (workload_score * 0.4)
        
        return min(performance_score, 1.0)
    
    def _calculate_rating_score(self, technician: dict) -> float:
        """
        Calculate rating score
        
        Uses:
        1. Technician.Rating from DB (primary)
        2. Average from Reviews table (if available)
        
        Args:
            technician: Technician data
        
        Returns:
            Score between 0.0 and 1.0
        """
        # Get rating from Technician table
        tech_rating = technician.get('Rating', 0.0)
        
        # Also get average from Reviews table
        reviews_avg = self.db.get_technician_reviews_avg(
            technician['TechnicianId']
        )
        
        # Use reviews average if available, otherwise use tech rating
        final_rating = reviews_avg if reviews_avg > 0 else tech_rating
        
        # Convert 0-5 rating to 0-1 score
        score = final_rating / 5.0
        
        return min(score, 1.0)
    
    def _calculate_availability_score(
        self, 
        technician_id: str,
        location: Optional[dict] = None
    ) -> float:
        """
        Calculate availability score
        
        Note: Since Technician table doesn't have Location in your schema,
        this focuses on workload and availability status.
        
        Args:
            technician_id: Technician ID
            location: Customer location (optional)
        
        Returns:
            Score between 0.0 and 1.0
        """
        # Get current workload
        workload = self.db.get_technician_current_workload(technician_id)
        
        # Convert to availability score
        # 0-2 bookings = excellent (1.0)
        # 3-5 bookings = good (0.7-0.9)
        # 6-10 bookings = moderate (0.4-0.6)
        # 10+ bookings = low (0.0-0.3)
        
        if workload <= 2:
            return 1.0
        elif workload <= 5:
            return 0.9 - ((workload - 2) * 0.06)  # 0.9 to 0.72
        elif workload <= 10:
            return 0.6 - ((workload - 5) * 0.04)  # 0.6 to 0.4
        else:
            return max(0.2, 0.4 - ((workload - 10) * 0.02))
    
    def _calculate_total_score(self, scores: dict) -> float:
        """Calculate weighted total score"""
        total = sum(
            scores[key] * self.weights[key]
            for key in self.weights.keys()
        )
        return min(total, 1.0)
    
    def _generate_reason(self, scores: dict) -> str:
        """Generate human-readable reason"""
        # Find top 2 factors
        sorted_scores = sorted(
            scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        top_factor = sorted_scores[0][0]
        second_factor = sorted_scores[1][0] if len(sorted_scores) > 1 else None
        
        reasons = {
            'specialization': 'excellent specialization match',
            'performance': 'strong performance history',
            'rating': 'high customer ratings',
            'availability': 'good availability'
        }
        
        reason_parts = [reasons.get(top_factor, 'best match')]
        if second_factor and scores[second_factor] > 0.7:
            reason_parts.append(reasons.get(second_factor, ''))
        
        return f"Best match based on {' and '.join(reason_parts)}"
    
    def _get_workload_label(self, performance_score: float) -> str:
        """Convert performance score to workload label"""
        if performance_score >= 0.8:
            return 'light'
        elif performance_score >= 0.6:
            return 'moderate'
        else:
            return 'heavy'