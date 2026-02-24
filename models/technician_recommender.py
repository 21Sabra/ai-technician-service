import logging
import pickle
import os
import numpy as np
from typing import Dict, List
from config import settings

logger = logging.getLogger(__name__)

# ── Technician Profiles ───────────────────────────────
TECH_PROFILES = {
    'tech-001': {'base_success': 0.88, 'base_rating': 4.7, 'experience': 8},
    'tech-002': {'base_success': 0.82, 'base_rating': 4.5, 'experience': 5},
    'tech-003': {'base_success': 0.78, 'base_rating': 4.3, 'experience': 4},
    'tech-004': {'base_success': 0.85, 'base_rating': 4.6, 'experience': 6},
    'tech-005': {'base_success': 0.74, 'base_rating': 4.2, 'experience': 3},
}


class TechnicianRecommender:
    """
    Technician Recommendation System
    يستخدم XGBoost Model لو موجود، وإلا Weighted Scoring
    """

    def __init__(self, db):
        self.db      = db
        self.model   = None
        self.features = None
        self.weights = {
            'specialization': settings.WEIGHT_SPECIALIZATION,
            'performance':    settings.WEIGHT_PERFORMANCE,
            'rating':         settings.WEIGHT_RATING,
            'availability':   settings.WEIGHT_AVAILABILITY
        }
        self._load_model()
        logger.info(f"Recommender initialized with weights: {self.weights}")

    def _load_model(self):
        model_path = os.path.join(
            os.path.dirname(__file__), 'ml', 'technician_model.pkl'
        )
        if os.path.exists(model_path):
            try:
                with open(model_path, 'rb') as f:
                    data = pickle.load(f)
                self.model    = data['model']
                self.features = data['features']
                logger.info(f"✅ ML Model loaded (v{data.get('version', '?')})")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load ML model: {e} — using Weighted Scoring")
        else:
            logger.info("ℹ️ No ML model found — using Weighted Scoring")

    # ──────────────────────────────────────────────────
    # Main Entry Point
    # ──────────────────────────────────────────────────

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

        if self.model:
            return self._recommend_ml(technicians, booking_data)
        else:
            return self._recommend_weighted(technicians, booking_data)

    # ──────────────────────────────────────────────────
    # ML Recommendation
    # ──────────────────────────────────────────────────

    def _recommend_ml(self, technicians: list, booking_data: dict) -> dict:
        logger.info("🤖 Using ML Model for recommendation")

        service_cats = [
            s.get('category', '').lower()
            for s in booking_data.get('services', [])
        ]

        scored = []
        for tech in technicians:
            try:
                features = self._build_features(tech, service_cats)
                feature_values = [[features[f] for f in self.features]]
                proba = self.model.predict_proba(feature_values)[0][1]

                scored.append({
                    'technician_id':   tech['TechnicianId'],
                    'technician_name': tech['DisplayName'],
                    'email':           tech['Email'],
                    'confidence':      round(float(proba), 3),
                    'features':        features
                })
            except Exception as e:
                logger.error(f"Error scoring tech {tech.get('TechnicianId')}: {e}")
                continue

        if not scored:
            logger.warning("ML scoring failed — falling back to Weighted Scoring")
            return self._recommend_weighted(technicians, booking_data)

        scored.sort(key=lambda x: x['confidence'], reverse=True)
        best = scored[0]

        logger.info(f"✅ ML recommended: {best['technician_id']} (confidence={best['confidence']})")

        return {
            'recommended_technician_id': best['technician_id'],
            'confidence': best['confidence'],
            'reason': self._generate_reason(best['features']),
            'alternatives': [
                {
                    'technician_id': t['technician_id'],
                    'confidence':    t['confidence'],
                    'reason':        self._generate_reason(t['features'])
                }
                for t in scored[1:3]
            ],
            'factors': {
                'specialization_match': round(best['features']['specialization_match'], 2),
                'location_proximity':   0.0,
                'rating':               round(best['features']['avg_rating'], 2),
                'workload':             self._workload_label(best['features']['workload_score'])
            }
        }

    def _build_features(self, tech: dict, service_cats: list) -> dict:
        tech_id = tech['TechnicianId']
        profile = TECH_PROFILES.get(tech_id, {
            'base_success': 0.75,
            'base_rating':  4.0,
            'experience':   3
        })

        spec_match     = self._calc_spec_match(tech.get('Specialization', ''), service_cats)
        avg_rating     = round(profile['base_rating'] / 5.0, 3)
        success_rate   = round(profile['base_success'], 3)
        workload_score = self._get_workload_score(tech_id)
        exp_score      = round(min(profile['experience'] / 10.0, 1.0), 3)

        return {
            'specialization_match': spec_match,
            'avg_rating':           avg_rating,
            'success_rate':         success_rate,
            'workload_score':       workload_score,
            'experience_score':     exp_score
        }

    def _calc_spec_match(self, tech_specs: str, service_cats: list) -> float:
        if not service_cats or not tech_specs:
            return 0.5
        specs   = [s.strip().lower() for s in tech_specs.split(',')]
        matches = sum(1 for c in service_cats if c in specs)
        return round(matches / len(service_cats), 3)

    def _get_workload_score(self, tech_id: str) -> float:
        try:
            workload = self.db.get_technician_current_workload(tech_id)
            if workload <= 2:   return 1.0
            elif workload <= 5: return 0.82
            elif workload <= 8: return 0.55
            else:               return 0.25
        except:
            return 0.82

    # ──────────────────────────────────────────────────
    # Weighted Scoring (Fallback)
    # ──────────────────────────────────────────────────

    def _recommend_weighted(self, technicians: list, booking_data: dict) -> dict:
        logger.info("⚖️ Using Weighted Scoring for recommendation")

        service_cats = [
            s.get('category', '').lower()
            for s in booking_data.get('services', [])
        ]

        scored = []
        for tech in technicians:
            try:
                scores = {
                    'specialization': self._calc_spec_match(
                        tech.get('Specialization', ''), service_cats
                    ),
                    'performance': self._calc_performance(tech['TechnicianId']),
                    'rating':      self._calc_rating(tech),
                    'availability': self._get_workload_score(tech['TechnicianId'])
                }
                total = sum(scores[k] * self.weights[k] for k in self.weights)

                scored.append({
                    'technician_id':   tech['TechnicianId'],
                    'technician_name': tech['DisplayName'],
                    'email':           tech['Email'],
                    'confidence':      round(min(total, 1.0), 3),
                    'features':        scores
                })
            except Exception as e:
                logger.error(f"Error scoring tech {tech.get('TechnicianId')}: {e}")
                continue

        if not scored:
            return {'error': 'Failed to score technicians', 'recommended_technician_id': None}

        scored.sort(key=lambda x: x['confidence'], reverse=True)
        best = scored[0]

        logger.info(f"✅ Weighted recommended: {best['technician_id']} (score={best['confidence']})")

        return {
            'recommended_technician_id': best['technician_id'],
            'confidence': best['confidence'],
            'reason': self._generate_reason(best['features']),
            'alternatives': [
                {
                    'technician_id': t['technician_id'],
                    'confidence':    t['confidence'],
                    'reason':        self._generate_reason(t['features'])
                }
                for t in scored[1:3]
            ],
            'factors': {
                'specialization_match': round(best['features']['specialization'], 2),
                'location_proximity':   0.0,
                'rating':               round(best['features']['rating'], 2),
                'workload':             self._workload_label(best['features']['availability'])
            }
        }

    def _calc_performance(self, tech_id: str) -> float:
        try:
            stats = self.db.get_technician_stats(tech_id)
            if not stats or stats.get('TotalBookings', 0) == 0:
                return 0.65
            sr = stats.get('SuccessRate') or 0.8
            wl = self.db.get_technician_current_workload(tech_id)
            return min((sr * 0.6) + (max(0.0, 1.0 - wl / 10.0) * 0.4), 1.0)
        except:
            return 0.65

    def _calc_rating(self, tech: dict) -> float:
        try:
            reviews_avg = self.db.get_technician_reviews_avg(tech['TechnicianId'])
            rating = reviews_avg if reviews_avg > 0 else tech.get('Rating', 0.0)
            return min(rating / 5.0, 1.0)
        except:
            return 0.5

    # ──────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────

    def _generate_reason(self, scores: dict) -> str:
        reasons = {
            'specialization_match': 'excellent specialization match',
            'specialization':       'excellent specialization match',
            'avg_rating':           'high customer ratings',
            'rating':               'high customer ratings',
            'success_rate':         'strong performance history',
            'performance':          'strong performance history',
            'workload_score':       'good availability',
            'availability':         'good availability',
            'experience_score':     'extensive experience',
        }
        top = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        parts = [reasons[k] for k, _ in top[:2] if k in reasons]
        return f"Best match based on {' and '.join(parts)}" if parts else "Best available match"

    def _workload_label(self, score: float) -> str:
        if score >= 0.8:   return 'light'
        elif score >= 0.5: return 'moderate'
        else:              return 'heavy'