import logging
from typing import Dict, Optional
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
        self.weights = {
            'specialization': settings.WEIGHT_SPECIALIZATION,
            'performance': settings.WEIGHT_PERFORMANCE,
            'rating': settings.WEIGHT_RATING,
            'availability': settings.WEIGHT_AVAILABILITY
        }
        logger.info(f"Recommender initialized with weights: {self.weights}")
    
    def recommend(self, booking_data: dict) -> dict:
        logger.info(f"🔍 Starting recommendation for booking {booking_data.get('booking_id')}")
        
        technicians = self.db.get_available_technicians()
        
        if not technicians:
            logger.warning("⚠️ No available technicians found")
            return {
                'error': 'No available technicians found',
                'recommended_technician_id': None
            }
        
        logger.info(f"Found {len(technicians)} available technicians")
        
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
        
        scored_technicians.sort(key=lambda x: x['total_score'], reverse=True)
        best = scored_technicians[0]
        
        logger.info(
            f"✅ Best technician: {best['technician_id']} "
            f"({best['technician_name']}) with score {best['total_score']:.3f}"
        )
        
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
                for t in scored_technicians[1:3]
            ],
            'factors': {
                'specialization_match': round(best['scores']['specialization'], 2),
                'location_proximity': 0.0,
                'rating': round(best['scores']['rating'], 2),
                'workload': self._get_workload_label(best['scores']['performance'])
            }
        }
    
    def _calculate_scores(self, technician: dict, booking_data: dict) -> dict:
        return {
            'specialization': self._calculate_specialization_score(
                technician,
                booking_data.get('services', [])
            ),
            'performance': self._calculate_performance_score(
                technician['TechnicianId']
            ),
            'rating': self._calculate_rating_score(technician),
            'availability': self._calculate_availability_score(
                technician['TechnicianId']
            )
        }
    
    def _calculate_specialization_score(self, technician: dict, services: list) -> float:
        if not services:
            return 0.5

        requested_categories = [
            s.get('category', '').lower().strip()
            for s in services
        ]
        requested_categories = [c for c in requested_categories if c]
        
        if not requested_categories:
            return 0.5
        
        tech_specs = technician.get('Specialization', '').lower()
        tech_specs_list = [s.strip() for s in tech_specs.split(',') if s.strip()]
        
        if not tech_specs_list:
            return 0.3
        
        matches = 0
        for category in requested_categories:
            if any(category in spec or spec in category for spec in tech_specs_list):
                matches += 1
        
        match_percentage = matches / len(requested_categories)
        
        if match_percentage == 1.0:
            return 0.95
        elif match_percentage >= 0.5:
            return 0.70 + (match_percentage * 0.20)
        else:
            return 0.50 + (match_percentage * 0.20)
    
    def _calculate_performance_score(self, technician_id: str) -> float:
        stats = self.db.get_technician_stats(technician_id)
        
        if not stats or stats.get('TotalBookings', 0) == 0:
            return 0.65
        
        success_rate = stats.get('SuccessRate', 0.0)
        if success_rate is None:
            success_rate = 0.8
        
        current_workload = self.db.get_technician_current_workload(technician_id)
        workload_score = max(0.0, 1.0 - (current_workload / 10.0))
        performance_score = (success_rate * 0.6) + (workload_score * 0.4)
        
        return min(performance_score, 1.0)
    
    def _calculate_rating_score(self, technician: dict) -> float:
        tech_rating = technician.get('Rating', 0.0)
        reviews_avg = self.db.get_technician_reviews_avg(technician['TechnicianId'])
        final_rating = reviews_avg if reviews_avg > 0 else tech_rating
        score = final_rating / 5.0
        return min(score, 1.0)
    
    def _calculate_availability_score(self, technician_id: str) -> float:
        workload = self.db.get_technician_current_workload(technician_id)
        
        if workload <= 2:
            return 1.0
        elif workload <= 5:
            return 0.9 - ((workload - 2) * 0.06)
        elif workload <= 10:
            return 0.6 - ((workload - 5) * 0.04)
        else:
            return max(0.2, 0.4 - ((workload - 10) * 0.02))
    
    def _calculate_total_score(self, scores: dict) -> float:
        total = sum(
            scores[key] * self.weights[key]
            for key in self.weights.keys()
        )
        return min(total, 1.0)
    
    def _generate_reason(self, scores: dict) -> str:
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
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
        if performance_score >= 0.8:
            return 'light'
        elif performance_score >= 0.6:
            return 'moderate'
        else:
            return 'heavy'