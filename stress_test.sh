#!/usr/bin/env bash
# =============================================================================
# AegisCLI — Full Test Suite
# Tests all modules, flags, edge cases, and log output accuracy
# Exists only for developers to stress test the suit
# =============================================================================

set -uo pipefail

# --- Config ------------------------------------------------------------------
TARGET_DOMAIN="httpbin.org"
TARGET_IP="93.184.216.34"       # example.com — static, predictable
INVALID_TARGET="thishostdoesnotexist.invalid"
LOG_DIR="$HOME/.aegiscli/logs"
PASS=0
FAIL=0
SKIP=0

# --- Colors ------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
DIM='\033[2m'
RESET='\033[0m'

# --- Helpers -----------------------------------------------------------------
header() {
    echo ""
    echo -e "${CYAN}══════════════════════════════════════════════${RESET}"
    echo -e "${CYAN}  $1${RESET}"
    echo -e "${CYAN}══════════════════════════════════════════════${RESET}"
}

pass() {
    echo -e "  ${GREEN}✓${RESET} $1"
    ((PASS++))
}

fail() {
    echo -e "  ${RED}✗${RESET} $1"
    ((FAIL++))
}

skip() {
    echo -e "  ${YELLOW}~${RESET} $1 ${DIM}(skipped)${RESET}"
    ((SKIP++))
}

# Run a command, expect it to exit 0
expect_success() {
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        pass "$desc"
    else
        fail "$desc — command exited non-zero"
    fi
}

# Run a command, expect it to exit non-zero
expect_failure() {
    local desc="$1"
    shift
    if ! "$@" > /dev/null 2>&1; then
        pass "$desc"
    else
        fail "$desc — expected failure but got success"
    fi
}

# Run command, check stdout contains a string
expect_output() {
    local desc="$1"
    local pattern="$2"
    shift 2
    output=$("$@" 2>&1 || true)
    if echo "$output" | grep -qi "$pattern"; then
        pass "$desc"
    else
        fail "$desc — expected '$pattern' in output"
        echo -e "    ${DIM}Got: $(echo "$output" | head -5)${RESET}"
    fi
}

# Get the most recently modified file in log dir matching a pattern
latest_log() {
    ls -t "$LOG_DIR"/$1 2>/dev/null | head -1
}

# Check a JSON field exists and is not null/empty
json_field_exists() {
    local file="$1"
    local field="$2"
    local value
    value=$(python3 -c "
import json, sys
with open('$file') as f:
    d = json.load(f)
keys = '$field'.split('.')
for k in keys:
    if isinstance(d, list): d = d[int(k)]
    else: d = d.get(k)
print(d if d is not None else '')
" 2>/dev/null)
    if [[ -n "$value" && "$value" != "None" && "$value" != "[]" ]]; then
        pass "JSON: $field exists and is populated"
    else
        fail "JSON: $field is missing or empty in $file"
    fi
}

json_field_value() {
    local file="$1"
    local field="$2"
    local expected="$3"
    local value
    value=$(python3 -c "
import json
with open('$file') as f:
    d = json.load(f)
keys = '$field'.split('.')
for k in keys:
    if isinstance(d, list): d = d[int(k)]
    else: d = d.get(k)
print(d)
" 2>/dev/null)
    if [[ "$value" == "$expected" ]]; then
        pass "JSON: $field == '$expected'"
    else
        fail "JSON: $field expected '$expected', got '$value'"
    fi
}

json_field_type() {
    local file="$1"
    local field="$2"
    local expected_type="$3"
    local actual_type
    actual_type=$(python3 -c "
import json
with open('$file') as f:
    d = json.load(f)
keys = '$field'.split('.')
for k in keys:
    if isinstance(d, list): d = d[int(k)]
    else: d = d.get(k)
print(type(d).__name__)
" 2>/dev/null)
    if [[ "$actual_type" == "$expected_type" ]]; then
        pass "JSON: $field is type $expected_type"
    else
        fail "JSON: $field expected type $expected_type, got $actual_type"
    fi
}


# =============================================================================
# INSTALL
# =============================================================================
header "Installing AegisCLI"

if pip install . -q; then
    pass "pip install . succeeded"
else
    echo -e "${RED}FATAL: Installation failed. Aborting tests.${RESET}"
    exit 1
fi

if command -v aegiscli &> /dev/null; then
    pass "aegiscli binary is available in PATH"
else
    fail "aegiscli binary not found after install"
    exit 1
fi


# =============================================================================
# CLI ROUTING
# =============================================================================
header "CLI — Routing & Global Flags"

expect_failure "No args → exits non-zero" \
    aegiscli

expect_failure "Unknown module → exits non-zero" \
    aegiscli invalidmodule target

expect_failure "Profiler with no submodule → exits non-zero" \
    aegiscli profiler

expect_failure "Scanner with no submodule → exits non-zero" \
    aegiscli scanner

expect_failure "Profiler with invalid submodule → exits non-zero" \
    aegiscli profiler invalidsubmodule "$TARGET_DOMAIN"

expect_failure "Scanner with invalid submodule → exits non-zero" \
    aegiscli scanner invalidsubmodule "$TARGET_DOMAIN"


# =============================================================================
# PROFILER — WHOIS
# =============================================================================
header "Profiler — WHOIS (basic)"

expect_success "whois: runs against $TARGET_DOMAIN" \
    aegiscli profiler whois "$TARGET_DOMAIN"

expect_success "whois: verbose flag accepted" \
    aegiscli profiler whois -v "$TARGET_DOMAIN"

expect_output "whois: output contains registrar info" "registrar" \
    aegiscli profiler whois "$TARGET_DOMAIN"

expect_output "whois: verbose shows steps" "rdap\|whois\|resolv\|fetch" \
    aegiscli profiler whois -v "$TARGET_DOMAIN"


# =============================================================================
# PROFILER — WHOIS LOGGING
# =============================================================================
header "Profiler — WHOIS (logging)"

aegiscli profiler whois --log "$TARGET_DOMAIN" > /dev/null 2>&1
WHOIS_LOG=$(latest_log "aegiscli_profiler_whois_*.json")

if [[ -n "$WHOIS_LOG" ]]; then
    pass "whois: log file created at $WHOIS_LOG"
    json_field_value "$WHOIS_LOG" "tool" "profiler.whois"
    json_field_exists "$WHOIS_LOG" "target"
    json_field_exists "$WHOIS_LOG" "timestamp"
    json_field_exists "$WHOIS_LOG" "elapsed"
    json_field_type   "$WHOIS_LOG" "elapsed" "float"
    json_field_exists "$WHOIS_LOG" "data"
else
    fail "whois: no log file found in $LOG_DIR"
    skip "whois: JSON field checks (no log to check)"
fi


# =============================================================================
# PROFILER — DNS
# =============================================================================
header "Profiler — DNS (basic)"

expect_success "dns: runs against $TARGET_DOMAIN" \
    aegiscli profiler dns "$TARGET_DOMAIN"

expect_success "dns: verbose flag accepted" \
    aegiscli profiler dns -v "$TARGET_DOMAIN"

expect_output "dns: output contains A record" "A\|address\|record" \
    aegiscli profiler dns "$TARGET_DOMAIN"

expect_output "dns: verbose shows resolution steps" "resolv\|record\|dns\|query" \
    aegiscli profiler dns -v "$TARGET_DOMAIN"


# =============================================================================
# PROFILER — DNS LOGGING
# =============================================================================
header "Profiler — DNS (logging)"

aegiscli profiler dns --log "$TARGET_DOMAIN" > /dev/null 2>&1
DNS_LOG=$(latest_log "aegiscli_profiler_dns_*.json")

if [[ -n "$DNS_LOG" ]]; then
    pass "dns: log file created"
    json_field_value "$DNS_LOG" "tool" "profiler.dns"
    json_field_exists "$DNS_LOG" "target"
    json_field_exists "$DNS_LOG" "timestamp"
    json_field_exists "$DNS_LOG" "elapsed"
    json_field_type   "$DNS_LOG" "elapsed" "float"
    json_field_exists "$DNS_LOG" "data.dns_records"
else
    fail "dns: no log file found"
    skip "dns: JSON field checks"
fi


# =============================================================================
# PROFILER — WEB
# =============================================================================
header "Profiler — Web Fingerprinter (basic)"

expect_success "web: runs against $TARGET_DOMAIN" \
    aegiscli profiler web "$TARGET_DOMAIN"

expect_success "web: verbose flag accepted" \
    aegiscli profiler web -v "$TARGET_DOMAIN"

expect_output "web: output contains status code" "200\|301\|302\|403\|404" \
    aegiscli profiler web "$TARGET_DOMAIN"

expect_output "web: output contains server header" "server\|nginx\|apache\|cloudflare\|gunicorn" \
    aegiscli profiler web "$TARGET_DOMAIN"

expect_output "web: verbose shows SSL steps" "ssl\|tls\|cert\|handshake" \
    aegiscli profiler web -v "$TARGET_DOMAIN"


# =============================================================================
# PROFILER — WEB LOGGING
# =============================================================================
header "Profiler — Web (logging)"

aegiscli profiler web --log "$TARGET_DOMAIN" > /dev/null 2>&1
WEB_LOG=$(latest_log "aegiscli_profiler_web_*.json")

if [[ -n "$WEB_LOG" ]]; then
    pass "web: log file created"
    json_field_value "$WEB_LOG" "tool" "profiler.web"
    json_field_exists "$WEB_LOG" "target"
    json_field_exists "$WEB_LOG" "timestamp"
    json_field_exists "$WEB_LOG" "elapsed"
    json_field_type   "$WEB_LOG" "elapsed" "float"
    json_field_exists "$WEB_LOG" "data.connection"
    json_field_exists "$WEB_LOG" "data.headers"
    json_field_exists "$WEB_LOG" "data.certs"
else
    fail "web: no log file found"
    skip "web: JSON field checks"
fi


# =============================================================================
# SCANNER — PORT (basic)
# =============================================================================
header "Scanner — Port (basic)"

expect_success "port: runs with default range against $TARGET_DOMAIN" \
    aegiscli scanner port "$TARGET_DOMAIN"

expect_success "port: verbose flag accepted" \
    aegiscli scanner port -v "$TARGET_DOMAIN"

expect_success "port: --ports range flag accepted" \
    aegiscli scanner port --ports 80-443 "$TARGET_DOMAIN"

expect_success "port: --ports list flag accepted" \
    aegiscli scanner port --ports 80,443 "$TARGET_DOMAIN"

expect_output "port: finds port 80 on $TARGET_DOMAIN" "80" \
    aegiscli scanner port --ports 80,443 "$TARGET_DOMAIN"

expect_output "port: finds port 443 on $TARGET_DOMAIN" "443" \
    aegiscli scanner port --ports 80,443 "$TARGET_DOMAIN"

expect_output "port: banner shown for port 80" "HTTP\|200\|nginx\|apache\|server" \
    aegiscli scanner port --ports 80,443 "$TARGET_DOMAIN"

expect_output "port: banner shown for port 443" "HTTP\|200\|nginx\|cloudflare\|server" \
    aegiscli scanner port --ports 80,443 "$TARGET_DOMAIN"


expect_output "port: verbose shows resolution" "resolv\|resolved\|ip" \
    aegiscli scanner port -v --ports 80,443 "$TARGET_DOMAIN"

expect_output "port: verbose shows scan parameters" "400\|semaphore\|timeout\|coroutine" \
    aegiscli scanner port -v --ports 80,443 "$TARGET_DOMAIN"

expect_output "port: verbose shows event loop result" "open\|closed\|filtered" \
    aegiscli scanner port -v --ports 80,443 "$TARGET_DOMAIN"

expect_output "port: scan time shown in output" "second\|scan finished" \
    aegiscli scanner port --ports 80,443 "$TARGET_DOMAIN"


# =============================================================================
# SCANNER — PORT (edge cases)
# =============================================================================
header "Scanner — Port (edge cases)"

expect_success "port: single port via list syntax" \
    aegiscli scanner port --ports 80 "$TARGET_DOMAIN"

expect_success "port: scan against raw IP" \
    aegiscli scanner port --ports 80,443 "$TARGET_IP"

expect_success "port: known closed port range returns cleanly" \
    aegiscli scanner port --ports 10-15 "$TARGET_DOMAIN"

expect_output "port: no open ports found message on dead range" "0\|no\|open" \
    aegiscli scanner port --ports 10-15 "$TARGET_DOMAIN"


# =============================================================================
# SCANNER — PORT LOGGING
# =============================================================================
header "Scanner — Port (logging)"

aegiscli scanner port --log --ports 80,443 "$TARGET_DOMAIN" > /dev/null 2>&1
PORT_LOG=$(latest_log "aegiscli_scanner_port_*.json")

if [[ -n "$PORT_LOG" ]]; then
    pass "port: log file created"
    json_field_value "$PORT_LOG" "tool" "scanner.port"
    json_field_exists "$PORT_LOG" "target"
    json_field_exists "$PORT_LOG" "timestamp"
    json_field_exists "$PORT_LOG" "elapsed"
    json_field_type   "$PORT_LOG" "elapsed" "float"
    json_field_exists "$PORT_LOG" "data.open_ports"
    json_field_type   "$PORT_LOG" "data.open_ports" "list"

    # verify elapsed is rounded to 2 decimal places
    python3 -c "
import json
with open('$PORT_LOG') as f:
    d = json.load(f)
e = d.get('elapsed', 0)
assert e == round(e, 2), f'elapsed not rounded: {e}'
print('ok')
" > /dev/null 2>&1 && pass "port: elapsed rounded to 2dp" || fail "port: elapsed not rounded to 2dp"

    # verify open_ports is a list of dicts with port and banner keys
    python3 -c "
import json
with open('$PORT_LOG') as f:
    d = json.load(f)
ports = d['data']['open_ports']
assert all(isinstance(p, dict) for p in ports), 'open_ports entries are not dicts'
assert all('port' in p for p in ports), 'open_ports entries missing port key'
assert all('banner' in p for p in ports), 'open_ports entries missing banner key'
print('ok')
" > /dev/null 2>&1 && pass "port: open_ports entries are dicts with port and banner keys" || fail "port: open_ports structure malformed"

    # verify port values are integers
    python3 -c "
import json
with open('$PORT_LOG') as f:
    d = json.load(f)
ports = d['data']['open_ports']
assert all(isinstance(p['port'], int) for p in ports), 'port values contain non-int'
print('ok')
" > /dev/null 2>&1 && pass "port: port values are integers" || fail "port: port values are not integers"

    # verify 80 and 443 are in the results
    python3 -c "
import json
with open('$PORT_LOG') as f:
    d = json.load(f)
port_numbers = [p['port'] for p in d['data']['open_ports']]
assert 80 in port_numbers, '80 missing'
assert 443 in port_numbers, '443 missing'
print('ok')
" > /dev/null 2>&1 && pass "port: 80 and 443 confirmed open in JSON" || fail "port: 80 or 443 missing from open_ports"

    # verify at least one banner was grabbed
    python3 -c "
import json
with open('$PORT_LOG') as f:
    d = json.load(f)
ports = d['data']['open_ports']
banners = [p['banner'] for p in ports if p['banner'] is not None]
assert len(banners) > 0, 'no banners grabbed'
print('ok')
" > /dev/null 2>&1 && pass "port: at least one banner grabbed" || fail "port: no banners found in JSON"

else
    fail "port: no log file found"
    skip "port: all JSON field checks"
fi


# =============================================================================
# ENVELOPE CONSISTENCY — cross module check
# =============================================================================
header "Envelope Consistency — all modules"

echo -e "  ${DIM}Checking all recent logs share consistent envelope structure...${RESET}"

for log_file in "$WHOIS_LOG" "$DNS_LOG" "$WEB_LOG" "$PORT_LOG"; do
    if [[ -z "$log_file" ]]; then
        continue
    fi
    name=$(basename "$log_file")

    # every envelope must have these 5 fields
    for field in tool target timestamp elapsed data; do
        python3 -c "
import json
with open('$log_file') as f:
    d = json.load(f)
assert '$field' in d, '$field missing'
" > /dev/null 2>&1 && pass "$name: has '$field' field" || fail "$name: missing '$field' field"
    done

    # elapsed must always be float rounded to 2dp
    python3 -c "
import json
with open('$log_file') as f:
    d = json.load(f)
e = d['elapsed']
assert isinstance(e, float), f'elapsed is not float: {type(e)}'
assert e == round(e, 2), f'elapsed not rounded to 2dp: {e}'
" > /dev/null 2>&1 && pass "$name: elapsed is float, rounded to 2dp" || fail "$name: elapsed format issue"

    # tool field must follow module.submodule format
    python3 -c "
import json
with open('$log_file') as f:
    d = json.load(f)
tool = d['tool']
assert '.' in tool, f'tool field missing dot notation: {tool}'
" > /dev/null 2>&1 && pass "$name: tool follows module.submodule format" || fail "$name: tool field format wrong"
done


# =============================================================================
# SUMMARY
# =============================================================================
echo ""
echo -e "${CYAN}══════════════════════════════════════════════${RESET}"
echo -e "${CYAN}  TEST SUMMARY${RESET}"
echo -e "${CYAN}══════════════════════════════════════════════${RESET}"
echo -e "  ${GREEN}Passed:  $PASS${RESET}"
echo -e "  ${RED}Failed:  $FAIL${RESET}"
echo -e "  ${YELLOW}Skipped: $SKIP${RESET}"
TOTAL=$((PASS + FAIL + SKIP))
echo -e "  ${DIM}Total:   $TOTAL${RESET}"
echo ""

if [[ $FAIL -eq 0 ]]; then
    echo -e "${GREEN}  All tests passed.${RESET}"
    exit 0
else
    echo -e "${RED}  $FAIL test(s) failed.${RESET}"
    exit 1
fi