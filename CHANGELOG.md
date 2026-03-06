# Changelog
All notable changes to **AegisCLI** will be documented in this file.

The format is based on [Semantic Versioning](https://semver.org/).

---

## [0.4.0a0] - 2026-03-06

### Added
- `exporter.py` added to `core/utils/` — builds structured JSON envelopes for all tool output
- `selector.py` added to `tools/profiler/` — routing logic extracted out of `profiler.py` into its own class
- `log_json()` added to `logger.py` — handles JSON disk writes, only fires when `--log` is active

### Changed
- `profiler.py` converted to ABC — enforces `fetch()`, `display()`, `export()`, `result()` on all submodules, adds target validation in `__init__`
- `cli.py` now routes through `Profiler_Selector` instead of instantiating `Profiler` directly, `mode` parameter removed
- `--log` now saves a `.json` file to `~/.aegiscli/logs/` instead of a plain `.log` file — JSON is the ground truth for logging going forward. Pretty `.log` file still gets created but is ANSI-polluted and reserved for future use
- JSON is never written to disk without `--log` — previously `exporter.dump()` wrote unconditionally
- Error messages now always visible regardless of `-v` — previously all errors were silently swallowed unless verbose mode was active
- whois submodule refactored: `fetch()` handles RDAP only, `fallback()` handles legacy whois only, `self.raw_whois` removed in favor of unified `self.data`, `mode_handler()` renamed to `display()`
- DNS submodule: `fetch()` wrapper added to satisfy ABC contract, wraps `resolve_record()` and `reverse_all()`
- Web submodule: `pretty()` renamed to `display()`, export logic extracted into `export()` method
- All three profiler submodules now follow consistent structure — `fetch()`, `display()`, `export()`, `result()` with uniform error handling and timing output

---

## [0.3.1a0] - 2026-02-17

### Changed

- Verbose mode now is much more usefull and consistent across all the tool (Change was made faster than initially planned)
- DNS and WHOIS submodules of the Profiler module are now showing consistent output with Web Fingerprinter submodule

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

### Known Issues
- WHOIS and DNS submodules still use legacy formatting (migration to formatter.py planned for v0.3.1a0)
- Verbose mode is not in Web Fingerprinter as the flag will be meeting improvements (planned in v0.3.2a0)

---

## [0.2.0a0] - 2026-02-05
### Added
- New Profiler submodule was added - DNS Resolver.
- Reverse DNS lookup integration.
- Verbose mode (`-v`) with step-by-step logging.
- Added `dnspython` as a dependency.

### Changed
- Structure changed for better maintance
- Commands structure changed

### Fixed
- Minor consistency changes

---

## [0.1.0a0] - 2026-01-29
### Added
- Initial project structure.
- WHOIS submodule for **Profiler** module.
- CLI entry point `aegiscli`.
- Logging was added