# 👀 ObserverModel — Agent Runtime Governance for Autonomous Coding Agents

> Real-time FinOps, security guardrails, and behavioral governance for AI coding agents.

## Overview

Autonomous coding agents can execute hundreds of tool calls, read sensitive files, modify repositories, and consume significant API budgets without providing clear visibility into why those actions occurred.

Most observability platforms focus on collecting traces and displaying dashboards. They show what happened, but they rarely identify costly or risky behavioral patterns in a deterministic and reproducible way.

**ObserverModel** provides a governance layer for AI agents by:

* Monitoring runtime telemetry streams
* Detecting risky behavioral patterns using deterministic rules
* Estimating operational waste and cost attribution
* Flagging security and compliance violations
* Generating executive-ready audit reports automatically

The platform is designed around a simple principle:

> Same telemetry input → Same diagnosis → Same output.

No hallucinated findings. No black-box reasoning in the detection engine.

---

# Problem Statement

AI coding agents introduce two major operational risks:

### 💸 FinOps Risk

Agents frequently perform inefficient actions such as:

* Repeated repository scans
* Context reloading
* Failed retry loops
* Excessive file traversal

These behaviors increase token consumption, API spend, and execution latency.

### 🔒 Security & Compliance Risk

Agents may:

* Access credential files
* Modify protected configuration
* Traverse sensitive directories
* Operate outside intended workspace boundaries

Without runtime governance, organizations lack visibility into these actions.

---

# Solution

ObserverModel continuously monitors agent telemetry and transforms low-level tool activity into actionable governance insights.

```text
Agent Runtime
      │
      ▼
Telemetry Stream
      │
      ▼
Normalization Layer
      │
      ▼
Detection Engine
      │
      ▼
FinOps Attribution
      │
      ▼
AI Diagnostic Layer
      │
      ▼
Executive Audit Report
```

---

# Core Features

## 📡 Live Telemetry Monitoring

Streams runtime agent activity in real time.

Examples:

* File reads
* File writes
* Shell commands
* Tool failures
* Execution traces

---

## 🧠 Deterministic Detection Engine

Rule-based behavioral analysis with reproducible outputs.

### RapidFileEnumerationDetector

Detects excessive repository scanning behavior.

Example:

```text
main.py
models.py
routers/auth.py
```

accessed repeatedly within a constrained window.

---

### RetryLoopDetector

Detects repeated command failures indicating runaway execution loops.

Example:

```text
pytest
pytest
pytest
```

failing repeatedly without progress.

---

### RepeatedTargetReadDetector

Detects excessive re-reading of the same file, indicating memory inefficiency or context loss.

---

### SecretAccessDetector

Detects:

* Protected configuration modification
* Credential file access
* Sensitive configuration interactions

Examples:

```text
.env
id_rsa
credentials.json
secret.yaml
```

---

## 💰 FinOps Attribution

ObserverModel converts telemetry into operational cost intelligence.

Metrics include:

* Audited session cost
* Estimated waste footprint
* Efficiency score
* Cost attribution by behavioral anomaly
* Monthly waste projections

---

## 📄 Executive Audit Reporting

Automatically generates:

* Markdown reports
* PDF reports

Reports include:

* Behavioral findings
* Cost analysis
* Evidence trails
* Risk classification
* Recommended remediation actions

---

# Architecture

## Layer 1 — Ingestion & Normalization

Converts heterogeneous agent traces into a unified event schema.

Normalized event types:

```text
FILE_READ
FILE_WRITE
COMMAND_EXEC
```

---

## Layer 2 — Detection Engine

Processes normalized telemetry using deterministic rule evaluation.

Outputs:

```text
Finding
Severity
Target
Evidence
Cost Attribution
```

---

## Layer 3 — Intelligence Layer

Optional AI-powered diagnostic enrichment.

Responsibilities:

* Root-cause summaries
* Executive explanations
* Strategic remediation guidance

Detection remains fully deterministic.

The intelligence layer never participates in rule evaluation.

---

# Live Demonstration Workflow

```text
Telemetry Replay
       │
       ▼
Live Monitor
       │
       ▼
Alert Generation
       │
       ▼
FinOps Attribution
       │
       ▼
Audit Report
```

Example runtime:

```text
READ main.py
READ models.py
READ routers/auth.py

⚠ RapidFileEnumerationDetector

WRITE .env

⚠ SecretAccessDetector

Session Complete

Generating Audit Report...
```

---

# Project Structure

```text
observermodel/
│
├── parsers/
├── normalizers/
├── detectors/
├── intelligence/
├── reports/
├── data/
│
├── monitor.py
├── telemetry_replay.py
├── models.py
└── README.md
```

---

# Technology Stack

### Runtime

* Python 3.12+

### Validation

* Pydantic

### Telemetry Processing

* JSONL Streaming
* Stateful Event Correlation

### Intelligence Layer

* Google Gemini

### Reporting

* Markdown
* PDF Generation

---

# Running the Demo

## Install Dependencies

```bash
uv sync
```

## Configure Environment

Create a `.env` file:

```env
GEMINI_API_KEY=your_key_here
```

## Launch Live Monitor

```bash
uv run monitor.py
```

## Generated Artifacts

```text
AUDIT_REPORT.md
AUDIT_REPORT.pdf
```

---

# Future Roadmap

### Runtime Enforcement

* Policy-based process termination
* Execution guardrails
* Automated intervention

### Multi-Agent Support

* Claude Code
* OpenHands
* SWE-Agent
* Custom agent frameworks

### Enterprise Governance

* Cost budgets
* Compliance policies
* Risk scoring
* Audit retention

---

# Why ObserverModel?

Most agent platforms answer:

> "How much did the agent spend?"

ObserverModel answers:

> "Why did the agent spend it, what risks were introduced, and what should be done next?"

Built for the next generation of autonomous software engineering systems.
