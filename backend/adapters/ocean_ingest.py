"""
EcoSentinel - Ocean Automated Ingestion Layer
Bridges Person 2 Ocean/AIS GFW Adapter and Person 3 Reasoning Pipeline with identity-based deduplication.
"""

from typing import Any, Dict, List, Optional, Set

from adapters.ocean_gfw import fetch_ocean_events
from database.firestore import db_client
from orchestrator.pipeline import process_event
from schemas.event import NormalizedEvent, PipelineResult


class OceanIngestionEngine:
    """
    Automated ingestion manager for Ocean/AIS events.
    Handles event fetching, identity-based deduplication, Person 3 pipeline execution,
    and structured batch reporting.
    """

    def __init__(self, store: Optional[Any] = None) -> None:
        self.store = store if store is not None else db_client
        self._seen_dedup_keys: Set[str] = set()

    def _get_dedup_key(self, event: NormalizedEvent) -> str:
        """Derive stable deduplication key for live GFW and simulated events."""
        metadata = event.metadata or {}
        source = metadata.get("source", "unknown")
        gfw_id = metadata.get("gfw_event_id")

        if gfw_id:
            return f"{source}:{gfw_id}"
        return f"{source}:{event.id}"

    def is_duplicate(self, event: NormalizedEvent) -> bool:
        """
        Check if event is a duplicate by examining:
        1. Local in-memory deduplication set
        2. Persistent incident store (by event.id or gfw_event_id)
        """
        dedup_key = self._get_dedup_key(event)
        if dedup_key in self._seen_dedup_keys:
            return True

        # Check existing store for event.id
        if self.store and hasattr(self.store, "get_incident"):
            existing = self.store.get_incident(event.id)
            if existing:
                self._seen_dedup_keys.add(dedup_key)
                return True

        # Check existing store for matching source + gfw_event_id in metadata
        metadata = event.metadata or {}
        gfw_id = metadata.get("gfw_event_id")
        source = metadata.get("source")

        if gfw_id and self.store and hasattr(self.store, "list_incidents"):
            incidents = self.store.list_incidents(limit=500, domain="ocean")
            for inc in incidents:
                inc_meta = inc.get("event", {}).get("metadata", {})
                if inc_meta.get("gfw_event_id") == gfw_id and inc_meta.get("source") == source:
                    self._seen_dedup_keys.add(dedup_key)
                    return True

        return False

    def ingest_events(
        self,
        mode: str = "auto",
        limit: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch, deduplicate, and process ocean events through Person 3 pipeline.
        Returns structured batch ingestion report.
        """
        try:
            fetched_events = fetch_ocean_events(
                start_date=start_date,
                end_date=end_date,
                token=token,
                limit=limit,
                mode=mode,
            )
        except Exception as exc:
            # GFW API failure in live mode fails loudly
            if mode == "live":
                raise
            return {
                "fetched_count": 0,
                "duplicate_count": 0,
                "newly_processed_count": 0,
                "failed_count": 1,
                "processed_results": [],
                "errors": [f"GFW API fetch error: {str(exc)}"],
            }

        fetched_count = len(fetched_events)
        duplicate_count = 0
        newly_processed_count = 0
        failed_count = 0
        processed_results: List[PipelineResult] = []
        errors: List[str] = []

        for event in fetched_events:
            if self.is_duplicate(event):
                duplicate_count += 1
                continue

            dedup_key = self._get_dedup_key(event)

            try:
                result = process_event(event)
                self._seen_dedup_keys.add(dedup_key)
                processed_results.append(result)
                newly_processed_count += 1
            except Exception as exc:
                failed_count += 1
                errors.append(f"Failed processing event {event.id}: {str(exc)}")

        return {
            "fetched_count": fetched_count,
            "duplicate_count": duplicate_count,
            "newly_processed_count": newly_processed_count,
            "failed_count": failed_count,
            "processed_results": processed_results,
            "errors": errors,
        }


# Singleton engine instance
ingestion_engine = OceanIngestionEngine()


def ingest_ocean_events(
    mode: str = "auto",
    limit: int = 10,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    token: Optional[str] = None,
    store: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Convenience function for automated ocean event ingestion.
    """
    engine = OceanIngestionEngine(store=store) if store is not None else ingestion_engine
    return engine.ingest_events(
        mode=mode,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        token=token,
    )
