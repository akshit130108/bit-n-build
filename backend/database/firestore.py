import math
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the Earth in kilometers."""
    r = 6371.0  # Earth radius in kilometers
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def parse_iso_datetime(ts_str: str) -> datetime:
    """Parse ISO 8601 string to timezone-aware UTC datetime."""
    try:
        # Replace trailing 'Z' if present
        clean_ts = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


class InMemoryStore:
    """High-performance in-memory incident store used for local development and offline mode."""

    def __init__(self) -> None:
        self._incidents: Dict[str, Dict[str, Any]] = {}

    def save_incident(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        incident_id = incident.get("event", {}).get("id") or incident.get("id")
        if not incident_id:
            raise ValueError("Incident missing valid event id")
        self._incidents[incident_id] = incident
        return incident

    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        return self._incidents.get(incident_id)

    def update_incident(self, incident_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if incident_id not in self._incidents:
            return None
        self._incidents[incident_id].update(updates)
        return self._incidents[incident_id]

    def list_incidents(
        self,
        limit: int = 50,
        domain: Optional[str] = None,
        risk_level: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for inc in self._incidents.values():
            event_obj = inc.get("event", {})
            risk_obj = inc.get("risk", {})
            gate_obj = inc.get("human_gate", {})

            if domain and event_obj.get("domain") != domain.lower():
                continue
            if risk_level and risk_obj.get("level") != risk_level.upper():
                continue
            if status and gate_obj.get("status") != status.upper():
                continue
            results.append(inc)

        # Sort newest first by created_at or event timestamp
        results.sort(
            key=lambda x: x.get("created_at") or x.get("event", {}).get("timestamp", ""),
            reverse=True,
        )
        return results[:limit]

    def query_nearby_incidents(
        self,
        lat: float,
        lon: float,
        max_distance_km: float = 15.0,
        hours_window: float = 48.0,
        domain: Optional[str] = None,
        event_type: Optional[str] = None,
        exclude_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)

        for inc_id, inc in self._incidents.items():
            if exclude_id and inc_id == exclude_id:
                continue

            event_obj = inc.get("event", {})
            loc_obj = event_obj.get("location") or inc.get("localization")
            if not loc_obj:
                continue

            inc_lat = loc_obj.get("lat")
            inc_lon = loc_obj.get("lon")
            if inc_lat is None or inc_lon is None:
                continue

            # Domain check
            if domain and event_obj.get("domain") != domain.lower():
                continue

            # Event type check (allow matching chainsaw to possible_logging or vice-versa)
            if event_type:
                inc_type = event_obj.get("event_type", "").lower()
                refined_type = inc.get("classification", {}).get("refined_type", "").lower()
                req_type = event_type.lower()
                if (req_type not in inc_type) and (req_type not in refined_type):
                    continue

            # Spatial distance check
            dist = haversine_distance_km(lat, lon, float(inc_lat), float(inc_lon))
            if dist > max_distance_km:
                continue

            # Temporal window check
            ts_str = event_obj.get("timestamp") or inc.get("created_at")
            if ts_str:
                dt = parse_iso_datetime(ts_str)
                age_hours = (now - dt).total_seconds() / 3600.0
                if age_hours > hours_window:
                    continue

            # Enrich copy with computed proximity
            matched_inc = dict(inc)
            matched_inc["distance_km"] = round(dist, 2)
            matches.append(matched_inc)

        matches.sort(key=lambda x: x.get("distance_km", 0.0))
        return matches

    def clear(self) -> None:
        self._incidents.clear()


class DatabaseClient:
    """
    Unified database client that connects to Firebase Firestore if configured,
    or falls back transparently to InMemoryStore for rapid hackathon iteration.
    """

    def __init__(self) -> None:
        self.backend_type = "in_memory"
        self._memory = InMemoryStore()
        self._firestore_db = None
        self._init_firestore()

    def _init_firestore(self) -> None:
        # Check for service account key file
        key_path = os.environ.get("FIREBASE_KEY_PATH") or os.path.join(
            os.path.dirname(__file__), "..", "firebase-key.json"
        )
        has_env_creds = bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

        if not (os.path.exists(key_path) or has_env_creds):
            return

        try:
            import firebase_admin
            from firebase_admin import credentials, firestore

            if not firebase_admin._apps:
                if os.path.exists(key_path):
                    cred = credentials.Certificate(key_path)
                    firebase_admin.initialize_app(cred)
                else:
                    firebase_admin.initialize_app()

            self._firestore_db = firestore.client()
            self.backend_type = "firestore"
        except Exception:
            # Graceful fallback to memory store
            self.backend_type = "in_memory"
            self._firestore_db = None

    def save_incident(self, incident_dict: Dict[str, Any]) -> Dict[str, Any]:
        # Always mirror to memory for fast spatial queries
        self._memory.save_incident(incident_dict)

        if self._firestore_db:
            try:
                incident_id = incident_dict.get("event", {}).get("id") or incident_dict.get("id")
                doc_ref = self._firestore_db.collection("incidents").document(incident_id)
                doc_ref.set(incident_dict)
            except Exception:
                pass
        return incident_dict

    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        if self._firestore_db:
            try:
                doc = self._firestore_db.collection("incidents").document(incident_id).get()
                if doc.exists:
                    return doc.to_dict()
            except Exception:
                pass
        return self._memory.get_incident(incident_id)

    def update_incident(self, incident_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        updated = self._memory.update_incident(incident_id, updates)
        if self._firestore_db:
            try:
                doc_ref = self._firestore_db.collection("incidents").document(incident_id)
                doc_ref.update(updates)
            except Exception:
                pass
        return updated

    def list_incidents(
        self,
        limit: int = 50,
        domain: Optional[str] = None,
        risk_level: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self._memory.list_incidents(limit=limit, domain=domain, risk_level=risk_level, status=status)

    def query_nearby_incidents(
        self,
        lat: float,
        lon: float,
        max_distance_km: float = 15.0,
        hours_window: float = 48.0,
        domain: Optional[str] = None,
        event_type: Optional[str] = None,
        exclude_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self._memory.query_nearby_incidents(
            lat=lat,
            lon=lon,
            max_distance_km=max_distance_km,
            hours_window=hours_window,
            domain=domain,
            event_type=event_type,
            exclude_id=exclude_id,
        )

    def clear(self) -> None:
        self._memory.clear()


# Singleton database instance
db_client = DatabaseClient()
