# Changelog
All notable changes to **AegisCLI** will be documented in this file.

The format is based on [Semantic Versioning](https://semver.org/).

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