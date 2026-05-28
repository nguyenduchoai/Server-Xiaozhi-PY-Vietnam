"""
gRPC Module

Provides gRPC support for internal service communication.
"""

from .services import GRPCServer, grpc_server

__all__ = [
    "GRPCServer",
    "grpc_server",
]
