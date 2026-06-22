# Architecture Decisions Log

This document tracks the core architectural decisions made during the design of our security pipeline, prioritizing high data density, minimal operational complexity, and optimal computational efficiency for our threat detectors (*Retry Loop*, *Secret Access*, and *Repeated Reads*).

⚠️ **Contextual Scope Note:** The decisions documented below were established under rapid prototyping constraints for a fast-paced hackathon MVP. To minimize operational friction and maximize integration speed across multiple AI agent platforms, architectural choices heavily favor extreme minimalism over long-term enterprise scalability. These contracts are subject to iteration as system requirements evolve post-MVP.


---

## ADR 1: Ingestion Granularity Refinement (Tool-Use Isolation)

### Context
Defining the exact input unit of work for the `ClaudeNormalizer`. Initial assumptions implied passing the entire raw JSONL log line into the normalization layer, forcing the component to multi-task between structural filtering and schema mapping.

### Decision
We redefined the ingestion boundary: the input to the `ClaudeNormalizer` is strictly a single, pre-isolated `tool_use` object (e.g., `{ "type": "tool_use", "name": "Read", ... }`) rather than the comprehensive raw JSONL line.

### Rationale
* **Minimized Normalizer Footprint:** Shifting the responsibility of parsing and filtering text blocks upstream ensures the normalizer functions as a pure mapper. It acts on structured, predictable tool shapes rather than scanning chaotic, multi-line agent outputs.
* **Granular Validation Failures:** If a log line contains multiple tool invocations, processing them as isolated units allows the pipeline to drop or isolate a single malformed `tool_use` block while successfully normalizing neighboring valid blocks within the same session.

### Consequence
* **Upstream Extraction Dependency:** The ingestion pipeline orchestrator must implement an extraction step to unpack raw JSONL logs and yield individual `tool_use` nodes directly to the normalizer.
---

## ADR 2: Minimal Normalized Event Schema

### Context
We needed a universal data structure capable of representing distinct system activities (file reads, file writes, command executions, and execution errors) using a single, unified model.

### Decision
We established a strict, minimal 5-field schema:
* `timestamp`
* `event_type`
* `target`
* `status`
* `payload`

### Rationale
* **Abstraction over Specialization:** Avoided narrow, hyper-specific fields like `file_path`, `file_name`, or `command_string`. By utilizing a single generic `target` field, the schema effortlessly handles file pathways or terminal execution strings without changing structural shape.
* **Exclusion of Session Metadata:** Intentionally stripped out identity tracking fields like `user_id` and infrastructure variables (`ip_address`, `database_name`, `computer_model`). Because the current benchmark system evaluates a single-agent session, tracking identity at the individual event level introduces strict data redundancy; metadata belongs at the session level.
* **Separation of Concerns:** Split the execution outcome concept into two distinct fields: a clean categorical state (`status` for rapid `success` or `failure` checking) and a raw text bucket (`payload`) for verbose data, context strings, or standard error logs.

---

## ADR 3: Event Vocabulary Minimization

### Context
To ensure low computational overhead, the system requires a lean, predictable menu of action labels (`event_type`) rather than creating a unique category name for every edge case.

### Decision
We established a baseline, two-verb vocabulary for the initial MVP scope:
1. `COMMAND_EXECUTION`
2. `FILE_READ`

### Rationale
* **Detector Alignment:** `COMMAND_EXECUTION` acts as the explicit telemetry stream for the *Retry Loop* detector. `FILE_READ` isolates data-access vectors required to feed both the *Secret Access* and *Repeated Reads* engines.
* **Pruning Inactive Paths:** We intentionally evaluated and excluded `FILE_WRITE` from the MVP vocabulary. Analysis of our target benchmarks indicates that current threat behaviors isolate vulnerabilities entirely to unauthorized file inspection and environmental data exfiltration (e.g., reading `.env`, `.env.backup`, `config/production.py`). Logging system modifications would generate dead telemetry that our current detectors do not evaluate.

---

## ADR 4: Atomic Lifecycle Logging (Single-Event Architecture)

### Context
Determining how to represent the completion or sudden failure of an operation—such as a terminal command running `pytest tests/test_auth.py` and resulting in an asynchronous `ImportError: cannot import User`.

### Decision
We chose a **Single-Event Architecture** over a split-event model. A terminal run, its concluding state, and its output string live within a singular, atomic `COMMAND_EXECUTION` log entry. We rejected the multi-event alternative (`COMMAND_EXECUTION` + `COMMAND_RESULT`).

### Rationale
1. **Data Lifecycle Simplicity:** Preserves a strict 1:1 relationship between a log entry and the underlying physical system action. This keeps our ledger footprint light and guarantees that telemetry scales linearly with actual agent events, rather than doubling due to arbitrary lifecycle state tracking (start/stop entries).
2. **Computational Efficiency for Detectors:** Avoids building complex stateful tracking inside the evaluation engines. With an atomic model, the *Retry Loop* detector can confirm a failure pattern in a single lookup pass by checking `target` and `status` simultaneously. A split-event model would force the detector to perform high-overhead windowing operations: tracking a command entry, scanning ahead in time, and programmatically stitching an isolated result back to its parent transaction across concurrent processes.

---

## ADR 5: Unstructured Payload Pipeline (Single Text Field)

### Context
Determining the structural schema for the `payload` field to prevent it from turning into an unstructured "junk drawer" while integrating multiple disparate agent platforms (Claude Code, OpenHands, SWE-agent). We evaluated splitting payload into a dictionary of standardized keys (`text`, `size`, `diff`, `tokens`) versus collapsing it into a singular data type.

### Decision
We selected **Option A (Single Text Field)**. The entire `payload` field is strictly defined as a single string containing raw console stdout, error dumps, or file contents. We explicitly rejected using a dictionary format with standardized keys.

### Rationale
* **Zero Enforcement Overhead (Advantage):** Eliminates the friction of cross-platform normalization. Because every AI agent names its outputs differently (e.g., `observation`, `system_response`, `output`), a multi-key dictionary would require writing complex validation rules to ensure external developers map data to the correct keys. A single text field allows normalizers to simply dump whatever string output they capture into a single slot.
* **Elimination of Speculative Features:** Stripped out speculative payload tracking keys like `size`, `tokens`, and `diff`. Chronological tracking via `timestamp`, `event_type`, and `target` provides sufficient data for the *Repeated Reads* detector, making explicit size metrics redundant for the MVP scope.

### Consequence
* **Loss of Granular Data Clarity (Disadvantage):** By collapsing all event metadata into a single string, we sacrifice structural clarity. If future analytical features or detectors require specific metrics (such as explicit LLM token counts or exact byte deltas), the system cannot query a clean key and will be forced to perform high-overhead string parsing or regex extraction on the raw text block.

---

## ADR 6: Constrained Event Type Vocabulary (Enum Architecture)

### Context
Determining how to strictly enforce the structural types of our log entries (`event_type`) to ensure consistent parsing and downstream detector compatibility. We evaluated using plain strings versus a constrained enum-style vocabulary.

### Decision
We selected **Option B (Constrained Vocabulary / Enum-style concept)**. Only pre-approved, uppercase values (`COMMAND_EXECUTION`, `FILE_READ`) are valid. Raw or arbitrary strings are strictly rejected by the normalizer.

### Rationale
* **Immediate Runtime Safety (Technical Reason):** Utilizing a constrained vocabulary allows static type checkers or validation layers to catch typos (e.g., `"FILE_READD"`) instantly. This ensures structural errors fail loudly during validation rather than quietly passing through the system as raw strings and breaking detector pattern matching.
* **Centralized Configuration Contract (Maintenance Reason):** Acts as a single source of truth for the codebase. If the system's event capabilities expand post-MVP, developers can modify or append definitions in a single centralized configuration file instead of digging deep into individual components to refactor scattered raw strings.

---

## ADR 7: Stateless Record-Level Ingestion (Atomic Normalization Boundary)

### Context
Refining the public interface boundary for `normalizer.py`. We previously assumed the component should ingest monolithic session files. However, because target agent traces span completely mismatched ingestion signatures (Claude Code uses JSONL, SWE-agent uses standard JSON, and LangSmith uses nested tree graphs), a session-level batch normalizer creates tight structural coupling. We evaluated record-by-record processing versus full-session array processing.

### Decision
We selected **Option A (Normalizing one record at a time)**. The normalizer interface contract is defined as a pure, stateless data transformation function: `record -> normalized_event`. It is completely blind to session boundaries, files, or streams.

### Rationale
* **Universal Decoupling (Advantage):** Maximum architectural reusability. By forcing upstream parsers to handle file-type extraction (JSON, JSONL, streams) and pass a single raw record, the normalizer acts as a pure translation layer. It works identically for single historical data points or real-time streaming pipelines with zero configuration changes.
* **Separation of Concerns:** Isolates the transformation engine from timeline assembly. The normalizer's singular responsibility is translation, keeping the codebase clean and modular.

### Consequence
* **Timeline Aggregation Displacement (Disadvantage):** Strips out all session macro-context during the translation step. Because the normalizer processes elements in complete isolation, it cannot verify chronological ordering or session grouping internally. This completely shifts the operational burden of historical timeline assembly and state tracking to the outer orchestration layer before threat detectors can execute.

---

## ADR 8: Platform-Isolated Normalizer Polymorphism (Polymorphic Translation)

### Context
Determining the code organization and class hierarchy for `normalizers/normalizer.py` to handle the wildly disparate raw event signatures across agent platforms (e.g., Claude's `tool_use`/`assistant` loops versus SWE-agent's `thought`/`action`/`observation` traces). We evaluated using a single generic `Normalizer` class with conditional routing versus isolated, platform-specific normalizer classes behind a shared interface.

### Decision
We selected **Option B (One normalizer per source)**. The implementation enforces dedicated subclasses (e.g., `ClaudeNormalizer`, `OpenHandsNormalizer`) utilizing a shared interface strategy.

### Rationale
* **Incremental Hackathon Execution (Hackathon Advantage):** Enables rapid, modular development. We can build and thoroughly test a single platform engine (e.g., `ClaudeNormalizer`) to achieve an immediate end-to-end MVP pipeline without spending time architecting speculative routing logic or stubbing out empty handlers for other platforms.
* **Blast Radius Isolation (Scalability Advantage):** Because raw agent schemas share zero structural overlap, encapsulating translation rules within source-specific classes ensures that modifying, adding, or deprecating a specific agent's translation logic has zero regression risk or impact on the data paths of independent platforms.

### Consequence
* **Scaffolding Overhead:** Requires creating and maintaining a clean interface definition and separate class instantiations from day one, slightly increasing the initial file/class footprint compared to an ad-hoc conditional script.

---

## ADR 9: Concrete Single-Source Execution (YAGNI Normalization)

### Context
Determining the code organization and class hierarchy for `normalizers/normalizer.py` to handle raw event signatures for the MVP. We initially evaluated using a polymorphic Abstract Base Class (ABC) interface to handle multiple platform extensions (Claude, OpenHands, SWE-agent). 

### Decision
We rejected the abstract base class paradigm for the initial implementation. The file `normalizers/normalizer.py` will contain exactly one concrete object: `ClaudeNormalizer`, with no abstract inheritance layer or speculative interface definitions.

### Rationale
* **Zero Extension Points Before Extensions Exist:** Designing for hypothetical future normalizers introduces redundant inheritance, extra imports, and structural complexity that does not contribute to shipping the immediate MVP demo. 
* **Incremental Velocity:** Building a direct, concrete `ClaudeNormalizer` allows us to verify the end-to-end ingestion pipeline immediately without spending time managing or maintaining a speculative polymorphic wrapper.

### Consequence
* **Absence of Shared Interface Constraints:** The caller must interact directly with `ClaudeNormalizer.normalize_record`. Standardizing signatures across future normalizers will be deferred as a refactoring task only when a second concrete implementation is explicitly introduced.

---

## ADR 10: Decoupling Data Contracts from Operational Subsystems (Core Model Isolation)

### Context
Determining the architectural placement of global system data structures, specifically the `NormalizedEvent` data model. We evaluated embedding the data model directly within the `normalizers/normalizer.py` transformation domain versus isolating it within a dedicated schema-only boundary.

### Decision
We rejected placing core data structures inside operational files. The `NormalizedEvent` structure will reside exclusively in an independent, top-level data layer (e.g., `models.py`). 

### Rationale
* **Prevention of Circular Dependencies:** Because high-level execution blocks (orchestrators) and independent analytical layers (threat detectors) must read and manipulate `NormalizedEvent` instances, housing the definition inside a low-level leaf component like a platform normalizer creates an immediate circular import risk.
* **Architectural Inversion Control:** High-level policy (detectors, timelines) should never depend directly on detailed, source-specific translation code (normalizers). Separating the model enforces a clean dependency graph where all components depend inward on a stable, shared data contract.

### Consequence
* **Cross-Module Import Ingestion:** Requires explicit imports of the shared data model from the central schema file across all layers of the ingestion and detection pipeline, eliminating hidden or implicit code coupling.

---

## ADR 11: Immutable Primitive Data Contracts (String-Based Temporal Isolation)

### Context
Determining the primitive type mapping for temporal data tracking inside the `NormalizedEvent` data model. We evaluated transitioning the `timestamp` field from a raw `str` to a native Pydantic `datetime` object to handle downstream analytical sequencing.

### Decision
We rejected using the native `datetime` type for the MVP layer and froze the field definition strictly as a primitive `str` representing an ISO-8601 compliant sequence.

### Rationale
* **Zero Parsing Overhead:** Forcing a strict `datetime` type signature inside the core validation entry point introduces a massive operational risk, as any variation or malformation in raw upstream logs would trigger fatal Pydantic validation failures.
* **Native Chronological String Evaluation:** Because the ingestion pipeline normalizes log times into standardized ISO-8601 formats, the sequence natively supports exact chronological sorting using standard string comparison operators (`<`, `>`). This achieves analytical sorting for free with zero structural conversion overhead.

### Consequence
* **Deferred Object Coercion:** All threat tracking layers (such as loop and read detectors) will manipulate timestamps as strings, deferring complex object parsing until an explicit delta calculation absolutely mandates it.
* **String-Enum Coercion Mixin:** The `EventType` enumeration must explicitly inherit from `(str, Enum)`. This allows Pydantic to cleanly coerce incoming raw JSON log strings into valid enum choices automatically, without requiring manual object conversion during the parsing or normalization phases.
* **Stringified Payload Boundary:** The optional `payload` field is strictly typed as a primitive `str` (defaulting to `""`), intentionally blocking structured dictionaries at the validation gate to enforce a completely flat, single-text footprint for the MVP's log metadata.

---

## ADR 12: Decoupled Multi-Vendor Classification and Resilient Ingestion Orchestration

### Context
Determining the structural strategy for classifying heterogeneous, raw vendor logs (specifically Claude records) and transforming them into the frozen `NormalizedEvent` schema. We evaluated how to manage the translation of external telemetry into internal event definitions while maintaining a minimized operational footprint and ensuring absolute pipeline crash-resilience.

### Decision
We rejected inline conditional logic (`if/elif`) for log transformation and isolated structural validation until after a dedicated classification phase. The architecture is split into two distinct structural boundaries: translating data via static lookup tables and offloading operational crash-resilience entirely to an outer pipeline ingestion orchestrator.

### Rationale
* **Classification Before Validation:** Raw vendor logs do not natively adhere to our internal schemas or feature explicit security classifications. We must first classify the incoming record based on its tool invocation to understand what systemic behavior it represents. Only after classification do we know which fields are structurally expected and can safely execute target metadata extraction.
* **Translation vs. Decision Framework:** Conditionals are reserved for complex algorithmic logic, whereas mapping external tool names (such as `view_file` or `bash`) to internal security events (`FILE_READ` or `COMMAND_EXECUTION`) is fundamentally a value-translation problem. A lookup table functions as a single source of truth, yielding a smaller syntax footprint during prototyping and eliminating logic modifications when adding future telemetry sources.
* **Separation of Functional Contract from Operational Resilience:** Forcing the normalizer to silently catch errors or emit generic fallback events breaks the integrity of the frozen domain model. Raising a strict exception keeps the component predictable and pure. Operational resilience is achieved by wrapping the normalizer inside a try/except execution block within the outer ingestion loop, safely routing malformed records to a Dead Letter Queue (DLQ) without halting the stream.

### Consequence
* **Immutable Core Processing Loop:** Adding new tools or third-party logs requires updating only the static dictionary lookup configurations; the core processing code of the normalizer remains entirely untouched.
* **Mandatory Orchestration Wrapper:** The normalizer cannot be safely invoked nakedly in production. It must always be executed inside an orchestrator framework that provides the required exception handling boundaries and telemetry DLQ routing.
* **Sequential Five-Step Ingestion Flow:** The operational pipeline transforms raw telemetry into the target schema by adhering to a strict five-step sequence:
  1. Identify the tool name from the record.
  2. Map the tool name to the internal corresponding event type.
  3. Extract the required metadata from the record based on the event type's structure.
  4. Format and sanitize the extracted fields to match the flat string constraints.
  5. Assemble the finalized, structured event object.