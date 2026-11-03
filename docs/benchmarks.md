# Benchmarks

This project has a pytest-based benchmark suite under `tests/benchmarks/`.

Run:

```bash
make benchmark
```

Benchmarks carry the `benchmark` marker and the default `addopts` deselects it, so `make test-python`, `make test`, and a bare `pytest` skip them. The marker is applied to every test under `tests/benchmarks/` automatically, so new benchmark files need no decorator.

To run them without make:

```bash
uv run pytest tests/benchmarks/ -m benchmark
```

This writes local output to:

```text
benchmark-results/latency.json
benchmark-results/token_usage.json
benchmark-results/index.html
```

`benchmark-results/` is generated output. It should be overwritten on each run and should not be committed unless otherwise noted.

## Current Scope

The benchmark suite measures latency and token usage. Latency uses `pytest-benchmark` for warmup, repeated rounds, and timing collection. The project writes a small normalized JSON file so the HTML report can use the same format when future benchmark suites are added.

Covered latency cases:

- server init in `full` mode
- server init in `progressive` mode
- server init in `semantic` mode
- dynamic tool registry init
- dynamic discovery tools:
  - `list_tools`
  - `describe_tools`
  - `find_tools`
- trainer schema and metadata scan
- preview tool paths:
  - `fine_tune`
  - `run_custom_training`
  - `run_container_training`
- security validation:
  - `validate_k8s_name`
  - `validate_resource_limits`
  - `is_safe_python_code`

Preview benchmarks use `confirmed=False`, so they do not submit jobs to Kubernetes.

`fine_tune` GPU pre-check is patched inside the benchmark so the benchmark can run without a cluster.

Token usage measures the context a client receives before any tool runs: the server instructions plus the `tools/list` payload (name, description, input and output schema of each tool). It runs with the `platform-admin` persona so every mode is compared on the full tool set. Tokens are estimated as `ceil(characters / 4)` with no extra dependencies, so the numbers compare modes and tools rather than predict a specific model's count.

Covered token usage cases:

- static surface for each mode (`full`, `progressive`, `semantic`) × instruction tier (`full`, `compact`, `minimal`)
- `full` mode tool schemas grouped by tool category (`planning`, `discovery`, `training`, …)
- a check that `progressive` and `semantic` tool schemas stay smaller than `full`

## Output Format

Latency results use this shape:

```json
{
  "suite": "latency",
  "iterations": 100,
  "warmup": 5,
  "results": [
    {
      "name": "server_init_full",
      "unit": "ms",
      "p50": 18.1,
      "p95": 24.5,
      "p99": 31.2,
      "min": 15.9,
      "max": 40.8
    }
  ]
}
```

Token usage results use this shape:

```json
{
  "suite": "token_usage",
  "estimator": "ceil(characters / 4)",
  "results": [
    {
      "name": "surface_semantic_full",
      "unit": "tokens",
      "tool_count": 2,
      "instructions_tokens": 1526,
      "tools_tokens": 334,
      "total_tokens": 1860
    }
  ]
}
```

## Report

The HTML report is generated from benchmark JSON files.

Current report includes:

- P50
- P95
- P99
- min
- max
- P99/P50 tail ratio
- visual spread bars
- summary cards
- token usage per mode, tier and tool category, with relative size bars

Open:

```text
benchmark-results/index.html
```

## Future Suites

Planned benchmark files:

```text
tests/benchmarks/test_cpu_profile.py
tests/benchmarks/test_memory.py
```

Planned output files:

```text
benchmark-results/cpu_profile.json
benchmark-results/memory.json
```

Recommended tools:

- CPU profile: Python `cProfile`
- memory profile: Python `tracemalloc`

Keep dependencies minimal. Add external profiling dependencies only if stdlib tools are not enough.
