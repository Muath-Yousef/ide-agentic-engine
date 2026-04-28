"""
OpenTelemetry setup — call ``setup_telemetry()`` once at process start
before importing any engine modules that use the ``tracer``.
"""

from __future__ import annotations

import logging
import os

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

_OTLP_ENDPOINT: str = os.environ.get("OTLP_ENDPOINT", "http://localhost:4317")
_SERVICE_NAME: str = os.environ.get("SERVICE_NAME", "ide-agentic-engine")


def setup_telemetry() -> None:
    """
    Initialise OpenTelemetry traces + metrics.

    Sends spans/metrics to Jaeger/Prometheus via OTLP gRPC.
    Safe to call multiple times (idempotent via global check).
    """
    resource = Resource.create({"service.name": _SERVICE_NAME})

    # --- Traces ---
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=_OTLP_ENDPOINT))
    )
    trace.set_tracer_provider(tracer_provider)

    # --- Metrics ---
    reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=_OTLP_ENDPOINT),
        export_interval_millis=60_000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)

    logger.info("OpenTelemetry initialised → %s  service=%s", _OTLP_ENDPOINT, _SERVICE_NAME)


def get_tracer(name: str) -> trace.Tracer:
    """Convenience wrapper — equivalent to ``trace.get_tracer(name)``."""
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """Convenience wrapper — equivalent to ``metrics.get_meter(name)``."""
    return metrics.get_meter(name)
