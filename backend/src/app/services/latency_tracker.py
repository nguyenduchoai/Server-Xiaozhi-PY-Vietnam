"""
Latency Tracker — In-memory ring buffer for AI pipeline metrics.

Collects ASR, LLM, TTS latency from each session and exposes
aggregated stats via API for the Admin Dashboard.
Thread-safe, zero external deps.
"""

import time
import threading
from collections import deque
from dataclasses import dataclass
from typing import Optional


@dataclass
class LatencyRecord:
    """Single pipeline execution record."""
    timestamp: float
    session_id: str
    user_id: str = ""
    agent_name: str = ""
    asr_ms: float = 0
    llm_first_token_ms: float = 0
    llm_total_ms: float = 0
    tts_first_chunk_ms: float = 0
    tts_total_ms: float = 0
    e2e_ms: float = 0  # End-to-end: voice_stop → first TTS audio
    text_preview: str = ""  # First 50 chars of recognized text


class LatencyTracker:
    """Thread-safe ring buffer for latency metrics.
    
    Keeps last N records (default 500) in memory.
    No database, no Redis — pure in-memory for speed.
    """

    def __init__(self, max_records: int = 500):
        self._records: deque[LatencyRecord] = deque(maxlen=max_records)
        self._lock = threading.Lock()
        self._active_sessions: dict[str, dict] = {}  # session_id -> start times
    
    def start_session(
        self,
        session_id: str,
        agent_name: str = "",
        user_id: Optional[str] = None,
        start_time: Optional[float] = None,
    ):
        """Mark session start (when voice_stop detected)."""
        with self._lock:
            if session_id in self._active_sessions:
                return
            self._active_sessions[session_id] = {
                "start": start_time or time.time(),
                "user_id": str(user_id or ""),
                "agent_name": agent_name,
                "asr_done": 0,
                "llm_first": 0,
                "llm_done": 0,
                "tts_first": 0,
                "tts_done": 0,
                "text": "",
            }

    def discard_session(self, session_id: str):
        """Drop an active session that did not become a real conversation."""
        with self._lock:
            self._active_sessions.pop(session_id, None)
    
    def mark_asr_done(self, session_id: str, text: str = ""):
        """Mark ASR completion."""
        with self._lock:
            if session_id in self._active_sessions:
                self._active_sessions[session_id]["asr_done"] = time.time()
                self._active_sessions[session_id]["text"] = text[:80]
    
    def mark_llm_first_token(self, session_id: str):
        """Mark first LLM token received."""
        with self._lock:
            if session_id in self._active_sessions:
                s = self._active_sessions[session_id]
                if not s["llm_first"]:
                    s["llm_first"] = time.time()
    
    def mark_llm_done(self, session_id: str):
        """Mark LLM streaming complete."""
        with self._lock:
            if session_id in self._active_sessions:
                self._active_sessions[session_id]["llm_done"] = time.time()
    
    def mark_tts_first_chunk(self, session_id: str):
        """Mark first TTS audio chunk ready."""
        with self._lock:
            if session_id in self._active_sessions:
                s = self._active_sessions[session_id]
                if not s["tts_first"]:
                    s["tts_first"] = time.time()
    
    def mark_tts_done(self, session_id: str):
        """Mark TTS complete — finalize record."""
        with self._lock:
            s = self._active_sessions.pop(session_id, None)
            if not s:
                return
            
            start = s["start"]
            record = LatencyRecord(
                timestamp=start,
                session_id=session_id,
                user_id=s.get("user_id", ""),
                agent_name=s["agent_name"],
                asr_ms=round((s["asr_done"] - start) * 1000) if s["asr_done"] else 0,
                llm_first_token_ms=round((s["llm_first"] - s["asr_done"]) * 1000) if s["llm_first"] and s["asr_done"] else 0,
                llm_total_ms=round((s["llm_done"] - s["asr_done"]) * 1000) if s["llm_done"] and s["asr_done"] else 0,
                tts_first_chunk_ms=round((s["tts_first"] - start) * 1000) if s["tts_first"] else 0,
                tts_total_ms=round((s["tts_done"] - start) * 1000) if s.get("tts_done") else round((time.time() - start) * 1000),
                e2e_ms=round((s["tts_first"] - start) * 1000) if s["tts_first"] else 0,
                text_preview=s["text"],
            )
            self._records.append(record)
    
    def get_stats(self, last_n: int = 50, user_id: Optional[str] = None) -> dict:
        """Get aggregated stats for dashboard."""
        user_id_str = str(user_id or "")
        with self._lock:
            records = list(self._records)
            if user_id_str:
                records = [r for r in records if r.user_id == user_id_str]
            records = records[-last_n:]
            active_sessions = [
                s for s in self._active_sessions.values()
                if not user_id_str or s.get("user_id") == user_id_str
            ]
        
        if not records:
            return {
                "count": 0,
                "avg_asr_ms": 0,
                "avg_llm_ms": 0,
                "avg_tts_ms": 0,
                "avg_e2e_ms": 0,
                "p95_e2e_ms": 0,
                "active_sessions": len(active_sessions),
                "recent": [],
            }
        
        asr_vals = [r.asr_ms for r in records if r.asr_ms > 0]
        llm_vals = [r.llm_first_token_ms for r in records if r.llm_first_token_ms > 0]
        tts_vals = [r.tts_first_chunk_ms for r in records if r.tts_first_chunk_ms > 0]
        e2e_vals = [r.e2e_ms for r in records if r.e2e_ms > 0]
        
        def avg(vals):
            return round(sum(vals) / len(vals)) if vals else 0
        
        def p95(vals):
            if not vals:
                return 0
            sorted_vals = sorted(vals)
            idx = int(len(sorted_vals) * 0.95)
            return round(sorted_vals[min(idx, len(sorted_vals) - 1)])
        
        # Recent 10 for live feed
        recent = [
            {
                "time": r.timestamp,
                "agent": r.agent_name,
                "text": r.text_preview,
                "asr_ms": r.asr_ms,
                "llm_ms": r.llm_first_token_ms,
                "tts_ms": r.tts_first_chunk_ms,
                "e2e_ms": r.e2e_ms,
            }
            for r in reversed(records[-10:])
        ]
        
        return {
            "count": len(records),
            "avg_asr_ms": avg(asr_vals),
            "avg_llm_ms": avg(llm_vals),
            "avg_tts_ms": avg(tts_vals),
            "avg_e2e_ms": avg(e2e_vals),
            "p95_e2e_ms": p95(e2e_vals),
            "active_sessions": len(active_sessions),
            "recent": recent,
        }


# Global singleton
latency_tracker = LatencyTracker()
