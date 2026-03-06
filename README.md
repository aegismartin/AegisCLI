# ⚔️ AegisCLI — Modular Recon Framework

AegisCLI is a lightweight recon framework designed to eliminate tool-juggling hell. Native implementations with consistent CLI patterns across profiling, scanning, enumeration, and analysis - built for chaining, automation, and maintainability.

---

## 🚨 Current Version: **0.4.0 Alpha**

This release focuses on architectural hardening — structured JSON output, strict module contracts, consistent error handling, and clean separation of routing from tool logic.

---

## ✨ Features (v0.4.0 Alpha)

### Profiler Module

* **WHOIS / RDAP Lookup** with intelligent fallback to legacy whois protocol
* **DNS Resolver** supporting:
  * A / AAAA
  * MX
  * TXT
  * NS
  * CNAME
  * SOA
* **Reverse DNS (PTR) Lookups**
* **Web Fingerprinter** featuring:
  * Connection analysis (status code, response time, HTTP version, redirect chains)
  * SSL/TLS certificate inspection (subject, issuer, expiry date, Subject Alternative Names)
  * HTTP header profiling (Server, HSTS, cookies, security headers)
  * Cookie parsing with detailed attribute extraction
  * Smart output truncation for long data lists

### Framework Capabilities

* **Verbose Mode (`-v`)**
  Shows step-by-step internal execution for debugging and transparency.
* **Logging (`--log`)**
  Saves structured JSON output to:
  ```
  ~/.aegiscli/logs/
  ```
  JSON is the ground truth log format. Each tool run produces a timestamped `.json` file with a standard envelope (`tool`, `target`, `timestamp`, `data`).

  > **Note:** Pretty `.log` text file logging has been suspended as of `0.4.0a0` — terminal output contains ANSI escape codes that make plain text logs unreadable. The `.log` format may be revisited or removed in a future release.
* **Centralized Formatting**
  Consistent color-coded terminal output across all modules via `core/helpers/formatter.py`.
* **Strict modular architecture**
  Each tool enforces `fetch()`, `display()`, `export()`, `result()` via abstract base class.
* **Consistent CLI interface**
  All commands follow the pattern:
  ```
  aegiscli <module> <submodule> [flags] <target>
  ```
* **Packaged as a Python project**
  Installable with `pip install .` and exposes the `aegiscli` executable.

---

## 🚀 Quick Start

```bash
# WHOIS / RDAP lookup with verbose mode
aegiscli profiler whois -v example.com

# DNS records with JSON logging to ~/.aegiscli/logs
aegiscli profiler dns --log example.com

# DNS records verbose mode + logging
aegiscli profiler dns -v --log example.com

# Web fingerprinting
aegiscli profiler web --log httpbin.org

# Web fingerprinting with verbose mode and logging
aegiscli profiler web -v httpbin.org
```

---

## 🧩 Architecture Overview

AegisCLI follows a clean separation-of-concerns model:

```
aegiscli/
  cli.py              # Argument parsing, global flags, entry point
  core/
    utils/            # logger.py, flagger.py, exporter.py
    helpers/          # formatter.py (text formatting & visualization)
  tools/
    profiler/
      profiler.py     # Abstract base class — enforces tool contract
      selector.py     # Routes submodule selection
      submodules/     # whois.py, dns_module.py, web.py
    scanner/          # (planned)
    enumerator/       # (planned)
    analyser/         # (planned)
    injector/         # (planned)
```

Design principles:

* No global mutable state
* Tools never depend on each other's internals
* Uniform interfaces across all modules enforced at base class level
* Errors always visible — verbose mode is for diagnostics, not error reporting
* Nothing written to disk without explicit `--log`

---

## 📦 Roadmap

### Short-term

* Add security analysis flags for Web Fingerprinter (missing HSTS, insecure cookies, etc.)
* Additional OSINT sources for Profiler

### Medium-term

* Start Scanner module (ports, services, banners)
* Enumerator module with optional ffuf adapters
* Analyser module (using external APIs for reconnaissance)
* JSON configuration engine
* Tool chaining via orchestrator

### Long-term

* Plugin ecosystem
* Output profiles (Minimal / JSON / Extended)
* Unified workflow chaining and refinement
* Injector module (SQLi testing, payload logic)
* Log Analyser

---

## 📜 Changelog

Full history available in `CHANGELOG.md`.

Latest changes in **0.4.0 Alpha**:

* `exporter.py` added — structured JSON envelope output for all tools
* `selector.py` extracted — routing separated from base class
* `profiler.py` converted to ABC — strict contract enforced on all submodules
* `--log` now saves JSON only, nothing written to disk without the flag
* Consistent error handling across all profiler submodules
* whois, dns, web submodules brought to uniform structure

---

## ⚖️ License

Licensed under **AGPLv3** to ensure code transparency, enforce openness, and require attribution for derivative work.

---

## 🧠 Project Philosophy

AegisCLI is built intentionally as a **framework**. The priority is long-term stability, modular expansion, and real-world workflow integration.

Core principles:

* Architecture-first development
* Minimize complexity
* Strict readability standards
* Incremental refinement
* Predictable, consistent behavior

---