"""
EcoSentinel - Ocean Background Ingestion Scheduler
Periodically triggers automated ingestion from Global Fishing Watch API / Ocean Adapter to Person 3.
Guarantees worker singleton status (no duplicate workers on reload), configurable polling interval,
and structured health/status reporting.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from adapters.ocean_ingest import ingest_ocean_events

logger = logging.getLogger("ecosentinel.ocean_scheduler")


class OceanScheduler:
    """
    Background worker manager for periodic Ocean GFW ingestion.
    """

    def __init__(self) -> None:
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._mode: str = os.environ.get("OCEAN_POLL_MODE", "auto")
        self._poll_interval: int = int(os.environ.get("OCEAN_POLL_INTERVAL_SECONDS", "300"))
        
        # Status tracking metrics
        self._last_run_at: Optional[str] = None
        self._last_success_at: Optional[str] = None
        self._last_fetched_count: int = 0
        self._last_processed_count: int = 0
        self._last_duplicate_count: int = 0
        self._last_failed_count: int = 0
        self._last_error: Optional[str] = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """
        Start the background polling worker loop if not already running.
        Guarantees duplicate workers are NOT created on application reload.
        """
        if self._running or (self._task and not self._task.done()):
            logger.info("OceanScheduler background worker is already active. Skipping duplicate start.")
            return

        self._running = True
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._worker_loop())
            logger.info(
                f"Started OceanScheduler background worker (mode={self._mode}, interval={self._poll_interval}s)"
            )
        except RuntimeError:
            # If no running event loop is active (e.g. during synchronous startup), log warning
            logger.warning("No active asyncio event loop found to attach OceanScheduler worker task.")

    def stop(self) -> None:
        """Stop the background polling worker cleanly."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("Stopped OceanScheduler background worker.")

    async def _worker_loop(self) -> None:
        """Continuous background polling loop."""
        while self._running:
            try:
                await self.poll_once()
            except Exception as exc:
                logger.error(f"Error during scheduled ocean polling: {str(exc)}", exc_info=True)
                self._last_error = str(exc)

            try:
                await asyncio.sleep(self._poll_interval)
            except asyncio.CancelledError:
                break

    async def poll_once(self) -> Dict[str, Any]:
        """
        Execute a single ingestion poll cycle asynchronously.
        Updates status metrics and returns result dictionary.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        self._last_run_at = now_iso

        try:
            # Run ingestion in executor thread to prevent blocking asyncio event loop
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(
                None,
                lambda: ingest_ocean_events(mode=self._mode, limit=10),
            )

            self._last_fetched_count = res.get("fetched_count", 0)
            self._last_processed_count = res.get("newly_processed_count", 0)
            self._last_duplicate_count = res.get("duplicate_count", 0)
            self._last_failed_count = res.get("failed_count", 0)

            errors = res.get("errors") or []
            if errors:
                self._last_error = errors[0]
            else:
                self._last_error = None
                self._last_success_at = datetime.now(timezone.utc).isoformat()

            logger.info(
                f"Ocean poll completed: fetched={self._last_fetched_count}, "
                f"processed={self._last_processed_count}, duplicate={self._last_duplicate_count}, "
                f"failed={self._last_failed_count}"
            )
            return res

        except Exception as exc:
            self._last_failed_count = 1
            self._last_error = str(exc)
            logger.error(f"Ocean poll execution failed: {str(exc)}")
            raise

    def get_status(self) -> Dict[str, Any]:
        """
        Return structured status JSON dictionary for GET /ingest/ocean/status.
        Never exposes API tokens or credentials.
        """
        return {
            "running": self._running,
            "mode": self._mode,
            "poll_interval_seconds": self._poll_interval,
            "last_run_at": self._last_run_at,
            "last_success_at": self._last_success_at,
            "last_fetched_count": self._last_fetched_count,
            "last_processed_count": self._last_processed_count,
            "last_duplicate_count": self._last_duplicate_count,
            "last_failed_count": self._last_failed_count,
            "last_error": self._last_error,
        }


# Singleton scheduler instance
ocean_scheduler = OceanScheduler()
