# Changelog
All notable changes to **AegisCLI** will be documented in this file.

The format is based on [Semantic Versioning](https://semver.org/).

---
## [0.7.0a0] - 2026-04-20

### Added
- `web.py` — `BodyParser` class using stdlib `html.parser` — no new dependencies
- `web.py` — `body_analysis()` method — parses response body for CMS/framework signals; populates `self.body_signs`
- Body signal extraction: meta tags (`generator`, `application-name`, `powered-by`), framework path signatures in script/link src attributes, Angular/React HTML root attribute detection
- Path signatures cover WordPress (`/wp-content/`, `/wp-includes/`), Drupal (`/sites/default/`), Next.js (`/_next/`, `/static/chunks/`), Nuxt (`/__nuxt/`), Rails (`/assets/application-`)
- `body_signals` included in JSON envelope output and terminal display

### Architecture
- `BodyParser` lives at module level in `web.py` — internal helper, no external consumers anticipated

---

## [0.6.2a0] - 2026-04-13

### Fixed
- `web.py` — `self.domain` stripping logic was broken; second assignment always overwrote the first regardless of protocol
- `web.py` — dead `try/except` around string assignment in `fetch()` removed; HTTP fallback was unreachable
- `web.py` — `ConnectionRefusedError` in `get_cert()` now soft-fails with a warning instead of aborting the scan; HTTP-only targets no longer crash
- `web.py` — `get_cert()` call in `result()` isolated in its own `try/except` — cert failure no longer kills the full pipeline
- `exporter.py` — `elapsed` type hint corrected from `int` to `float`; dead `LOG_DIR` definition removed
- `logger.py` — `stop_log()` now resets `file` to `None` after closing to prevent double-close `ValueError`
- `flagger.py` — `USE_GLYPHS` check now guards against `None` encoding when stdout is redirected
- `cli.py` — `[ERROR]` in exception handler now uses consistent color formatting
- `selector.py` — unknown submodule no longer silently no-ops; raises `ValueError` instead

---

## [0.6.1a0] - 2026-04-02

### Added
- `service.py` — internal banner parsing helper for scanner submodules; parses raw banner strings into structured dicts (protocol, software, version, os_hint)
- Service discovery wired into `port.py` — each open port result now carries a parsed `service` field alongside the raw banner

### Architecture
- `service.py` lives in `submodules/` as a shared internal helper — justified by `udp.py` being a planned consumer of the same logic
- Raw banner preserved in all cases — `service` is a parsed layer on top, never a replacement
- `service` is `null` in JSON output when banner is empty or unrecognised — parser never blocks port reporting

---

## [0.6.0a0] - 2026-03-17

### Added
- `host.py` — host discovery submodule with ICMP echo and TCP fallback
- ICMP ping via raw sockets — requires root, provides TTL for OS fingerprinting
- TCP fallback on ports 22, 80, 443 — `ConnectionRefusedError` treated as alive, no root required
- TTL-based OS hint — Windows (≥128), Linux/macOS (≥64), network device (<64)
- CIDR range support — sweep entire subnets (e.g. `192.168.1.0/24`)
- Hostname resolution via `getaddrinfo` — returns all A records, not just one

### Architecture
- Dead hosts excluded from JSON log output — alive-only export keeps logs clean
- Semaphore cap set to 100 — lower than `port.py` to account for broader host ranges


## [0.5.1a0] - 2026-03-12

### Added
- `port.py` — banner grabbing with three strategies: passive read (SSH, FTP, SMTP, Redis, etc.), HTTP GET probe (port 80 family), HTTPS probe with SSL/SNI (port 443 family)
- `_grab_http_banner()` — shared async helper used by both HTTP and HTTPS paths
- Verbose output for banner grabbing — probe type, TLS handshake confirmation, result preview, failure reason

### Changed
- `check_port()` split into two decoupled steps — plain TCP confirms open status, banner grab is separate; banner failure never hides an open port
- `display()` shows `None` for ports with no banner instead of empty cell
- DNS resolution bug fixed in `fetch()` — `gethostbyname()` moved inside `try` block so `socket.gaierror` is actually catchable
- `stress_test.sh` updated for the new checks.

### Architecture
- SSL context is now a local variable per coroutine — eliminates the `self.ctx` race condition from concurrent coroutines sharing state

---

## [0.5.0a0] - 2026-03-10

### Added
- **Scanner module** introduced — `scanner.py` (ABC), `selector.py` (routing), `port.py` (first submodule)
- `port.py` — async TCP connect port scanner built on `asyncio.gather()` with semaphore-controlled concurrency (400 cap, 0.7s timeout per port)
- Port range parsing — supports default (1–1024), range (`--ports 1-65535`), and list (`--ports 80,443,8080`) formats
- Service name resolution via OS service database (`socket.getservbyport`)
- Verbose mode for Scanner — surfaces resolved IP, task queue size, concurrency parameters, theoretical scan time, and closed/filtered port count
- `Scanner_Selector` added — routes submodule selection, passes submodule-specific flags via `**kwargs` without polluting the selector signature
- JSON log output for Scanner consistent with Profiler envelope structure
- `stress_test.sh` was added to the repository for testing the tool in production. Does not affect the tool's capabilities and user experience

### Changed
- JSON envelope now includes `elapsed` field at envelope level across all modules — previously missing from Profiler submodules, previously nested inside `data` in Scanner
- `elapsed` is now rounded to 2 decimal places consistently across all modules
- `open_ports` key used in Scanner JSON output (replacing `ports`)
- Minor internal cleanup across Profiler submodules — no user-facing changes
- `advanced` parameter removed from `Profiler_Selector` — was dead code, never wired up

### Architecture
- Scanner follows identical ABC contract to Profiler — `fetch()`, `display()`, `export()`, `result()`
- Selector pattern consistent across both modules — CLI stays thin, routing owned by module
- Submodule-exclusive flags handled via `**kwargs` in Selector — no selector signature changes needed as new submodules are added

---

## [0.4.0a0] - 2026-03-06

### Added
- `exporter.py` added to `core/utils/` — builds structured JSON envelopes for all tool output
- `selector.py` added to `tools/profiler/` — routing logic extracted out of `profiler.py` into its own class
- `log_json()` added to `logger.py` — handles JSON disk writes, only fires when `--log` is active

### Changed
- `profiler.py` converted to ABC — enforces `fetch()`, `display()`, `export()`, `result()` on all submodules, adds target validation in `__init__`
- `cli.py` now routes through `Profiler_Selector` instead of instantiating `Profiler` directly, `mode` parameter removed
- `--log` now saves a `.json` file to `~/.aegiscli/logs/` instead of a plain `.log` file — JSON is the ground truth for logging going forward
- Error messages now always visible regardless of `-v` — previously all errors were silently swallowed unless verbose mode was active
- whois submodule refactored: `fetch()` handles RDAP only, `fallback()` handles legacy whois only, `self.raw_whois` removed in favor of unified `self.data`, `mode_handler()` renamed to `display()`
- DNS submodule: `fetch()` wrapper added to satisfy ABC contract, wraps `resolve_record()` and `reverse_all()`
- Web submodule: `pretty()` renamed to `display()`, export logic extracted into `export()` method
- All three profiler submodules now follow consistent structure — `fetch()`, `display()`, `export()`, `result()` with uniform error handling and timing output

---

## [0.3.1a0] - 2026-02-17

### Changed
- Verbose mode now is much more useful and consistent across all tools
- DNS and WHOIS submodules of the Profiler module are now showing consistent output with Web Fingerprinter submodule

---

## [0.3.0a0] - 2026-02-15

### Added
- New Profiler submodule: **Web Fingerprinter**
  - Connection analysis (status code, timing, HTTP version, redirect chains)
  - SSL/TLS certificate inspection (subject, issuer, expiry, SANs with smart truncation)
  - HTTP header profiling with security-focused analysis
  - Cookie parsing with detailed attribute extraction
- Centralized text formatting system via `core/helpers/formatter.py`
  - Consistent color-coded terminal output across modules
  - Smart truncation for long data lists (certificates, DNS records, etc.)

### Changed
- Restructured project layout: moved `logger.py` and `flagger.py` to `core/utils/`
- Improved output readability with unified formatting utilities

---

## [0.2.0a0] - 2026-02-05

### Added
- New Profiler submodule: DNS Resolver
- Reverse DNS lookup integration
- Verbose mode (`-v`) with step-by-step logging
- Added `dnspython` as a dependency

### Changed
- Structure changed for better maintainability
- Commands structure changed

### Fixed
- Minor consistency changes

---

## [0.1.0a0] - 2026-01-29

### Added
- Initial project structure
- WHOIS submodule for Profiler module
- CLI entry point `aegiscli`
- Logging added