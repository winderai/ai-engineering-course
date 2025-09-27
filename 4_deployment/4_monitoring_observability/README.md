# Monitoring & Observability for LLM Applications

When deploying LLM applications to production, you need to understand what's happening inside your system. This covers the three pillars: metrics, logs, and traces.

User feedback is coming later.

---

## Logging != Monitoring != Tracing

- Log to capture exceptional states and useful information. Optionally parse this into a logging system.
- Monitor to track and alert on overall system performance and health.
- Trace to capture individual user flows.

Broader theme of "Observability" in which you might add even more features to expose the state of your system.

---

## OpenLit Demo

OpenLit provides automatic instrumentation for LLM applications using OpenTelemetry standards. It captures traces, metrics, and logs without requiring code changes.

### Setup

For local dashboard:

```bash
docker run -d --name openlit \
  -p 3000:3000 \
  -v ${PWD}/data:/app/data \
  ghcr.io/openlit/openlit:latest
```

---

### Demo Script

```bash
# Show the demo file
bat 4_deployment/4_monitoring_observability/openlit_demo.py

# Run the demo
uv run python 4_deployment/4_monitoring_observability/openlit_demo.py
```

This generates traces for:

- Simple LLM calls
- Multi-step RAG pipelines
- Batch processing
- Error handling

---

### Dashboard Navigation

Open <http://localhost:3000> and show:

1. **Traces View** - Individual request flows
2. **Metrics Dashboard** - Latency, throughput, costs
3. **LLM Analytics** - Token usage, model performance
4. **Error Tracking** - Failed requests and exceptions

Key metrics automatically captured:

- Request latency (P50, P95, P99)
- Token consumption and costs
- Model performance
- Error rates
- GPU utilization (if available)

---

## Key Observability Patterns

### What to Monitor

**Performance:**

- Response time (especially P95)
- Tokens per second
- Queue depth
- GPU/CPU utilization

**Quality:**

- Error rates
- User satisfaction (thumbs up/down)
- Content safety violations

**Cost:**

- Token consumption
- Model costs
- Infrastructure spend

---

## Resources

- [OpenLit Documentation](https://openlit.io/)
- [OpenTelemetry for LLMs](https://opentelemetry.io/blog/2024/llm-observability/)
- <https://winder.ai/logging-vs-tracing-vs-monitoring/> - wow that's old
- <https://winder.ai/user-feedback-llm-powered-applications/>
- <https://winder.ai/part-5-monitor-large-language-model/>
