# Optional accelerator GPU inference verification

This is **not needed** for the macOS Docker demonstration. Apple Silicon can use local Metal-accelerated inference, but it cannot execute CUDA GPU workloads.

To collect legitimate GPU-process evidence, use a compatible Linux accelerator machine that you control. Install its official driver and monitoring tools and run a locally hosted model. Confirm the model actually generates output and that its server process appears in local GPU utilization/process telemetry.

With the correct runtime configured on that machine:

```bash
export AQ_MODE=ollama
export AQ_OLLAMA_URL=http://127.0.0.1:11434
make verify-gpu
cat artifacts/gpu-residency-report.json
```

The check demands actual model participation with no deterministic fallback and requires GPU process-memory samples during inference. The result is **not** a per-request kernel trace. Preserve driver logs and model-server logs if you need stronger attribution. A hosted model responding to your Mac is not evidence of local GPU use.

When the GPU monitoring utility is absent, this integration correctly fails as unavailable instead of fabricating measurements.
