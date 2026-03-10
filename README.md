# ⚔️ AegisCLI — Modular Recon Framework

AegisCLI is a lightweight recon framework designed to eliminate tool-juggling hell. Native implementations with consistent CLI patterns across profiling, scanning, enumeration, and analysis - built for chaining, automation, and maintainability.

---

## 🚨 Current Version: **0.5.0 Alpha**

This release introduces the **Scanner module** — async TCP port scanning with verbose diagnostics, and consistent JSON output that plugs directly into the existing envelope standard. Scanner is still green but it will grow more useful soon

---

## ✨ Features

### Profiler Module

* **WHOIS / RDAP Lookup** with intelligent fallback to legacy whois protocol
* **DNS Resolver** supporting A, AAAA, MX, TXT, NS, CNAME, SOA, and reverse PTR lookups
* **Web Fingerprinter** featuring:
  * Connection analysis (status code, response time, HTTP version, redirect chains)
  * SSL/TLS certificate inspection (subject, issuer, expiry date, SANs)
  * HTTP header profiling (Server, HSTS, cookies, CDN detection, security headers)
  * Cookie parsing with detailed attribute extraction

### Scanner Module

* **Port Scanner** featuring:
  * Async TCP connect scanning via `asyncio` — no external dependencies
  * Semaphore-controlled concurrency — 400 simultaneous connections cap, prevents OS file descriptor exhaustion
  * 0.7s timeout per port — tuned for balance between speed and accuracy on most networks
  * Flexible port targeting — default top 1024, range (`1-65535`), or list (`80,443,8080`)
  * Service name resolution from OS service database
  * Verbose diagnostics — resolved IP, task queue size, concurrency parameters, theoretical vs actual scan time, closed/filtered count

### Framework Capabilities

* **Verbose Mode (`-v`)**
  Step-by-step internal execution for debugging and transparency.
* **Logging (`--log`)**
  Saves structured JSON output to:
  ```
  ~/.aegiscli/logs/
  ```
  Each tool run produces a timestamped `.json` file with a standard envelope:
  ```json
  {
    "tool": "module.submodule",
    "target": "...",
    "timestamp": "...",
    "elapsed": 0.0,
    "data": {}
  }
  ```
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
# WHOIS / RDAP lookup
aegiscli profiler whois example.com

# DNS records with logging
aegiscli profiler dns --log example.com

# Web fingerprinting with verbose mode
aegiscli profiler web -v example.com

# Port scan — default top 1024 ports
aegiscli scanner port example.com

# Port scan — custom range
aegiscli scanner port --ports 1-65535 example.com

# Port scan — specific ports with logging
aegiscli scanner port --ports 80,443,8080 --log example.com

# Port scan — verbose mode
aegiscli scanner port -v --ports 1-1024 example.com
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
      profiler.py     # Abstract base class
      selector.py     # Routes submodule selection
      submodules/     # whois.py, dns_module.py, web.py
    scanner/
      scanner.py      # Abstract base class
      selector.py     # Routes submodule selection
      submodules/     # port.py
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

* Give banner grabbing ability to `port.py`
* Scanner `host.py` — host discovery, ICMP ping, TCP fallback, TTL-based OS hint
* Web Fingerprinter upgrade — deeper tech stack detection, framework fingerprinting
* Scanner `udp.py` — UDP port scanning

### Medium-term

* Add service discovery by banner grabbing
* Upgrade `dns` and `whois` submodules to actively interact with their discovery and dig deeper
* `settings.json` configuration engine — user-configurable defaults for concurrency, timeouts, output behavior, and module-specific parameters
* Enumerator module with ffuf or gobuster integration
* Analyser module (third-party API enrichment — Shodan, VirusTotal, Censys, and more.)

### Long-term

* Full blown tool chaining system
* Injector module (SQLi testing, payload logic)
* Log Analyser
* Plugin ecosystem

---

## 📜 Changelog

Full history available in `CHANGELOG.md`.

Latest changes in **0.5.0 Alpha**:

* Scanner module introduced — `scanner.py` ABC, `selector.py`, `port.py` submodule
* Async TCP port scanner with semaphore concurrency, flexible port targeting, service ID
* JSON envelope standardized across all modules — `elapsed` at envelope level, rounded to 2dp
* `advanced` dead parameter removed from Profiler selector
* Minor internal cleanup across Profiler submodules

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