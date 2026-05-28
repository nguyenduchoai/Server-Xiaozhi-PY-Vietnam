"""
2-Stage Intent Detection Provider

Optimized intent detection that separates category classification
from function call detection to reduce latency by ~60-80%.
"""

from .intent_2stage import IntentProvider

__all__ = ["IntentProvider"]
