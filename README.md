# ⚔️ AegisCLI — Modular Recon Framework

AegisCLI is a lightweight recon framework designed to eliminate tool-juggling hell. Native implementations with consistent CLI patterns across profiling, scanning, enumeration, and analysis - built for chaining, automation, and maintainability.

---

## 🚨 Current Version: **0.6.1 Alpha**

This release adds **service discovery** to the port scanner — banner strings are now parsed into structured identity (protocol, software, version) and included in JSON log output alongside the raw banner.

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

* **Host Discovery** featuring:
  * ICMP echo with raw sockets when root is available — faster, provides TTL
  * TCP fallback on ports 22, 80, 443 when no root — connected or refused both confirm alive
  * CIDR range support — sweep entire subnets (e.g. `192.168.1.0/24`)
  * Hostname resolution via `getaddrinfo` — returns all A records, not just one
  * TTL-based OS fingerprinting — Windows / Linux/macOS / network device hint
  * Semaphore-controlled concurrency — 100 simultaneous probes
  * Verbose diagnostics — host count, ICMP availability, per-host method and result

* **Port Scanner** featuring:
  * Async TCP connect scanning via `asyncio` — no external dependencies
  * Semaphore-controlled concurrency — 400 simultaneous connections cap, prevents OS file descriptor exhaustion
  * 0.7s timeout per port — tuned for balance between speed and accuracy on most networks
  * Flexible port targeting — default top 1024, range (`1-65535`), or list (`80,443,8080`)
  * Service name resolution from OS service database
  * **Banner grabbing** — passive read for known service ports (SSH, FTP, SMTP, MySQL, Redis, etc.), HTTP GET probe for web ports, SSL/TLS upgrade with SNI for HTTPS ports
  * Two-step port detection — plain TCP confirms open status first, banner grab is a separate step that never affects port reporting
  * Verbose diagnostics — resolved IP, task queue size, concurrency parameters, theoretical vs actual scan time, per-port banner grab status and result preview

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

# Host discovery — single IP
aegiscli scanner host 192.168.1.1

# Host discovery — subnet sweep
aegiscli scanner host 192.168.1.0/24

# Host discovery — verbose with logging
aegiscli scanner host -v --log 192.168.1.0/24

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
      submodules/     # port.py, host.py
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

* Web Fingerprinter upgrade — deeper tech stack detection, framework fingerprinting

### Medium-term

* Scanner `udp.py` — UDP port scanning
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

Latest changes in **0.6.1 Alpha**:

* `service.py` added — internal banner parsing helper shared across scanner submodules
* Service discovery wired into port scanner — each result now carries a structured `service` field in JSON output
* Raw banner preserved alongside parsed service — parser never blocks port reporting
* `service` is `null` when banner is empty or unrecognised

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