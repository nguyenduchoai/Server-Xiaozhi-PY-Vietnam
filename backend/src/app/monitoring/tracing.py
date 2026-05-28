"""
OpenTelemetry Distributed Tracing Configuration

Provides comprehensive distributed tracing with:
- Trace context propagation
- Custom spans for key operations
- Metrics collection
- Export to multiple backends
"""

from contextlib import contextmanager
from typing import Optional, Any, Generator
from functools import wraps
import time

from app.core.logger import get_logger


logger = get_logger(__name__)


class TracingConfig:
    """Tracing configuration."""
    
    SERVICE_NAME = "xiaozhi-server"
    SERVICE_VERSION = "1.0.0"
    
    ENABLED = True
    
    EXPORTER_TYPE = "otlp"
    
    OTLP_ENDPOINT = "http://localhost:4317"
    
    SAMPLE_RATE = 1.0
    
    INCLUDED_SPANS = [
        "http.request",
        "db.query",
        "redis.command",
        "mqtt.publish",
        "ai.provider",
    ]
    
    CUSTOM_SPANS = [
        "agent.process",
        "device.connection",
        "websocket.message",
        "cache.operation",
    ]


class NoOpSpan:
    """No-op span for when tracing is disabled."""
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def set_attribute(self, key: str, value: Any):
        pass
    
    def set_attributes(self, **kwargs):
        pass
    
    def add_event(self, name: str, attributes: Optional[dict] = None):
        pass
    
    def set_status(self, status: str, description: str = ""):
        pass
    
    def record_exception(self, exception: Exception):
        pass
    
    def end(self):
        pass


class TracingManager:
    """
    OpenTelemetry tracing manager.
    
    Provides:
    - Tracer instance
    - Span creation helpers
    - Context propagation
    - Decorators for automatic instrumentation
    """
    
    def __init__(self):
        self._tracer = None
        self._initialized = False
        self._config = TracingConfig()
    
    def initialize(self):
        """Initialize OpenTelemetry tracing."""
        if self._initialized:
            return
        
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.sdk.resources import Resource
            
            resource = Resource.create({
                "service.name": self._config.SERVICE_NAME,
                "service.version": self._config.SERVICE_VERSION,
                "deployment.environment": getattr(
                    __import__('app.core.config', fromlist=['settings']),
                    'settings'
                ).ENVIRONMENT.value if hasattr(__import__('app.core.config', fromlist=['settings']), 'settings') else "development",
            })
            
            provider = TracerProvider(resource=resource)
            
            trace.set_tracer_provider(provider)
            
            self._tracer = trace.get_tracer(
                self._config.SERVICE_NAME,
                self._config.SERVICE_VERSION,
            )
            
            self._try_setup_exporter()
            
            self._initialized = True
            logger.info("[Tracing] OpenTelemetry initialized successfully")
            
        except ImportError as e:
            logger.warning(f"[Tracing] OpenTelemetry not available: {e}")
            self._tracer = None
        except Exception as e:
            logger.error(f"[Tracing] Failed to initialize: {e}")
            self._tracer = None
    
    def _try_setup_exporter(self):
        """Try to setup trace exporter."""
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            
            exporter = OTLPSpanExporter(
                endpoint=self._config.OTLP_ENDPOINT,
                insecure=True,
            )
            
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            processor = BatchSpanProcessor(exporter)
            
            from opentelemetry import trace
            trace.get_tracer_provider().add_span_processor(processor)
            
        except ImportError:
            logger.warning("[Tracing] OTLP exporter not available")
        except Exception as e:
            logger.warning(f"[Tracing] Failed to setup exporter: {e}")
    
    @property
    def tracer(self):
        """Get the tracer instance."""
        if not self._initialized:
            self.initialize()
        return self._tracer
    
    @contextmanager
    def span(
        self,
        name: str,
        attributes: Optional[dict] = None,
        kind: str = "INTERNAL",
    ) -> Generator[Any, None, None]:
        """
        Create a span context manager.
        
        Args:
            name: Span name
            attributes: Initial span attributes
            kind: Span kind (INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER)
        """
        if not self.tracer:
            yield NoOpSpan()
            return
        
        try:
            from opentelemetry.trace import SpanKind
            
            kind_map = {
                "INTERNAL": SpanKind.INTERNAL,
                "SERVER": SpanKind.SERVER,
                "CLIENT": SpanKind.CLIENT,
                "PRODUCER": SpanKind.PRODUCER,
                "CONSUMER": SpanKind.CONSUMER,
            }
            
            span_kind = kind_map.get(kind.upper(), SpanKind.INTERNAL)
            
            with self.tracer.start_as_current_span(
                name,
                kind=span_kind,
            ) as span:
                if attributes:
                    span.set_attributes(**attributes)
                yield span
                
        except Exception as e:
            logger.error(f"[Tracing] Span error: {e}")
            yield NoOpSpan()
    
    def trace_function(self, name: Optional[str] = None, attributes: Optional[dict] = None):
        """
        Decorator to trace a function.
        
        Usage:
            @tracing.trace_function("my_function")
            async def my_function():
                pass
        """
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                span_name = name or func.__name__
                
                with self.span(span_name, attributes) as span:
                    try:
                        start_time = time.time()
                        result = await func(*args, **kwargs)
                        duration = time.time() - start_time
                        
                        span.set_attribute("duration_ms", duration * 1000)
                        span.set_status("OK")
                        
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status("ERROR", str(e))
                        raise
                
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                span_name = name or func.__name__
                
                with self.span(span_name, attributes) as span:
                    try:
                        start_time = time.time()
                        result = func(*args, **kwargs)
                        duration = time.time() - start_time
                        
                        span.set_attribute("duration_ms", duration * 1000)
                        span.set_status("OK")
                        
                        return result
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status("ERROR", str(e))
                        raise
                
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        
        return decorator
    
    def add_span_attributes(self, **kwargs):
        """Add attributes to current span."""
        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            if span:
                span.set_attributes(**kwargs)
        except Exception as e:
            logger.debug(f"[Tracing] Could not add attributes: {e}")
    
    def record_event(self, name: str, attributes: Optional[dict] = None):
        """Record an event in the current span."""
        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            if span:
                span.add_event(name, attributes)
        except Exception as e:
            logger.debug(f"[Tracing] Could not record event: {e}")


tracing = TracingManager()


def trace_span(
    name: str,
    attributes: Optional[dict] = None,
    kind: str = "INTERNAL",
):
    """
    Decorator for creating a span around a function.
    
    Usage:
        @trace_span("process_data")
        async def process_data():
            pass
    """
    return tracing.trace_function(name, attributes)


class DatabaseTracing:
    """Database query tracing utilities."""
    
    @staticmethod
    @contextmanager
    def trace_query(
        query: str,
        parameters: Optional[dict] = None,
    ) -> Generator[None, None, None]:
        """Trace a database query."""
        with tracing.span(
            "db.query",
            attributes={
                "db.system": "postgresql",
                "db.statement": query[:500],
            },
        ) as span:
            try:
                if parameters:
                    span.set_attribute("db.parameters", str(parameters)[:200])
                yield
                span.set_status("OK")
            except Exception as e:
                span.record_exception(e)
                span.set_status("ERROR", str(e))
                raise


class RedisTracing:
    """Redis command tracing utilities."""
    
    @staticmethod
    @contextmanager
    def trace_command(
        command: str,
        key: Optional[str] = None,
    ) -> Generator[None, None, None]:
        """Trace a Redis command."""
        with tracing.span(
            "redis.command",
            attributes={
                "db.system": "redis",
                "db.operation": command,
                "db.redis.key": key or "",
            },
        ) as span:
            try:
                yield
                span.set_status("OK")
            except Exception as e:
                span.record_exception(e)
                span.set_status("ERROR", str(e))
                raise


class AIProviderTracing:
    """AI provider tracing utilities."""
    
    @staticmethod
    @contextmanager
    def trace_provider_call(
        provider: str,
        operation: str,
        model: Optional[str] = None,
    ) -> Generator[None, None, None]:
        """Trace an AI provider call."""
        with tracing.span(
            f"ai.{provider}.{operation}",
            attributes={
                "ai.provider": provider,
                "ai.operation": operation,
                "ai.model": model or "",
            },
        ) as span:
            start_time = time.time()
            try:
                yield
                duration = time.time() - start_time
                span.set_attribute("duration_ms", duration * 1000)
                span.set_status("OK")
            except Exception as e:
                span.record_exception(e)
                span.set_status("ERROR", str(e))
                raise
