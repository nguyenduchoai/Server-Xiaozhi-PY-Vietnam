from enum import Enum


class InterfaceType(Enum):
    # Interface type
    STREAM = "STREAM"  # Streaming interface
    NON_STREAM = "NON_STREAM"  # Non-streaming interface
    LOCAL = "LOCAL"  # Local service
