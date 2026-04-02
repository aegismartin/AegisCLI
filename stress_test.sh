#!/usr/bin/env bash
# =============================================================================
# AegisCLI — Full Test Suite
# Tests structure, exit codes, and JSON envelope consistency
# Never asserts specific output content — host behaviour is not our problem
# =============================================================================

set -uo pipefail

# --- Config ------------------------------------------------------------------
TARGET_DOMAIN="httpbin.org"
TARGET_IP="93.184.216.34"       # example.com — static, predictable
TARGET_CIDR="192.168.15.27/30"  # small subnet — fast, local
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

pass() { echo -e "  ${GREEN}✓${RESET} $1"; ((PASS++)); }
fail() { echo -e "  ${RED}✗${RESET} $1"; ((FAIL++)); }
skip() { echo -e "  ${YELLOW}~${RESET} $1 ${DIM}(skipped)${RESET}"; ((SKIP++)); }

expect_success() {
    local desc="$1"; shift
    if "$@" > /dev/null 2>&1; then pass "$desc"
    else fail "$desc — command exited non-zero"; fi
}

expect_failure() {
    local desc="$1"; shift
    if ! "$@" > /dev/null 2>&1; then pass "$desc"
    else fail "$desc — expected failure but got success"; fi
}

latest_log() {
    ls -t "$LOG_DIR"/$1 2>/dev/null | head -1
}

json_field_exists() {
    local file="$1" field="$2" value
    value=$(python3 -c "
import json
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
        fail "JSON: $field is missing or empty"
    fi
}

json_field_value() {
    local file="$1" field="$2" expected="$3" value
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
    if [[ "$value" == "$expected" ]]; then pass "JSON: $field == '$expected'"
    else fail "JSON: $field expected '$expected', got '$value'"; fi
}

json_field_type() {
    local file="$1" field="$2" expected_type="$3" actual_type
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
    if [[ "$actual_type" == "$expected_type" ]]; then pass "JSON: $field is type $expected_type"
    else fail "JSON: $field expected type $expected_type, got $actual_type"; fi
}

json_assert() {
    local file="$1" desc="$2" code="$3"
    python3 -c "
import json
with open('$file') as f:
    d = json.load(f)
$code
print('ok')
" > /dev/null 2>&1 && pass "$desc" || fail "$desc"
}

check_envelope() {
    local file="$1" name
    name=$(basename "$file")

    for field in tool target timestamp elapsed data; do
        python3 -c "
import json
with open('$file') as f:
    d = json.load(f)
assert '$field' in d
" > /dev/null 2>&1 && pass "$name: has '$field'" || fail "$name: missing '$field'"
    done

    python3 -c "
import json
with open('$file') as f:
    d = json.load(f)
e = d['elapsed']
assert isinstance(e, float)
assert e == round(e, 2)
" > /dev/null 2>&1 && pass "$name: elapsed is float rounded to 2dp" || fail "$name: elapsed format wrong"

    python3 -c "
import json
with open('$file') as f:
    d = json.load(f)
assert '.' in d['tool']
" > /dev/null 2>&1 && pass "$name: tool follows module.submodule format" || fail "$name: tool field format wrong"
}


# =============================================================================
# INSTALL
# =============================================================================
header "Installing AegisCLI"

if pip install . -q; then pass "pip install . succeeded"
else echo -e "${RED}FATAL: Installation failed.${RESET}"; exit 1; fi

if command -v aegiscli &> /dev/null; then pass "aegiscli binary available in PATH"
else fail "aegiscli binary not found"; exit 1; fi


# =============================================================================
# CLI ROUTING
# =============================================================================
header "CLI — Routing & Exit Codes"

expect_failure "no args → exits non-zero"                          aegiscli
expect_failure "unknown module → exits non-zero"                   aegiscli invalidmodule target
expect_failure "profiler with no submodule → exits non-zero"       aegiscli profiler
expect_failure "scanner with no submodule → exits non-zero"        aegiscli scanner
expect_failure "profiler with invalid submodule → exits non-zero"  aegiscli profiler bad "$TARGET_DOMAIN"
expect_failure "scanner with invalid submodule → exits non-zero"   aegiscli scanner bad "$TARGET_DOMAIN"
expect_failure "empty target → exits non-zero"                     aegiscli profiler whois ""


# =============================================================================
# PROFILER — WHOIS
# =============================================================================
header "Profiler — WHOIS"

expect_success "whois: runs and exits 0"     aegiscli profiler whois "$TARGET_DOMAIN"
expect_success "whois: -v flag accepted"     aegiscli profiler whois -v "$TARGET_DOMAIN"
expect_success "whois: --log flag accepted"  aegiscli profiler whois --log "$TARGET_DOMAIN"
expect_success "whois: invalid target handled" aegiscli profiler whois "$INVALID_TARGET"

header "Profiler — WHOIS (logging)"

aegiscli profiler whois --log "$TARGET_DOMAIN" > /dev/null 2>&1
WHOIS_LOG=$(latest_log "aegiscli_profiler_whois_*.json")

if [[ -n "$WHOIS_LOG" ]]; then
    pass "whois: log file created"
    json_field_value "$WHOIS_LOG" "tool" "profiler.whois"
    json_field_exists "$WHOIS_LOG" "target"
    json_field_exists "$WHOIS_LOG" "timestamp"
    json_field_exists "$WHOIS_LOG" "elapsed"
    json_field_type   "$WHOIS_LOG" "elapsed" "float"
    json_field_exists "$WHOIS_LOG" "data"
else
    fail "whois: no log file found"
    skip "whois: JSON checks skipped"
fi


# =============================================================================
# PROFILER — DNS
# =============================================================================
header "Profiler — DNS"

expect_success "dns: runs and exits 0"     aegiscli profiler dns "$TARGET_DOMAIN"
expect_success "dns: -v flag accepted"     aegiscli profiler dns -v "$TARGET_DOMAIN"
expect_success "dns: --log flag accepted"  aegiscli profiler dns --log "$TARGET_DOMAIN"

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
    json_field_exists "$DNS_LOG" "data"
else
    fail "dns: no log file found"
    skip "dns: JSON checks skipped"
fi


# =============================================================================
# PROFILER — WEB
# =============================================================================
header "Profiler — Web Fingerprinter"

expect_success "web: runs and exits 0"     aegiscli profiler web "$TARGET_DOMAIN"
expect_success "web: -v flag accepted"     aegiscli profiler web -v "$TARGET_DOMAIN"
expect_success "web: --log flag accepted"  aegiscli profiler web --log "$TARGET_DOMAIN"

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
    skip "web: JSON checks skipped"
fi


# =============================================================================
# SCANNER — HOST
# =============================================================================
header "Scanner — Host"

expect_success "host: runs against single IP"        aegiscli scanner host "$TARGET_IP"
expect_success "host: runs against domain"           aegiscli scanner host "$TARGET_DOMAIN"
expect_success "host: runs against CIDR"             aegiscli scanner host "$TARGET_CIDR"
expect_success "host: -v flag accepted"              aegiscli scanner host -v "$TARGET_IP"
expect_success "host: --log flag accepted"           aegiscli scanner host --log "$TARGET_IP"
expect_failure "host: invalid target exits non-zero" aegiscli scanner host "$INVALID_TARGET"

header "Scanner — Host (logging)"

aegiscli scanner host --log "$TARGET_IP" > /dev/null 2>&1
HOST_LOG=$(latest_log "aegiscli_scanner_host_*.json")

if [[ -n "$HOST_LOG" ]]; then
    pass "host: log file created"
    json_field_value "$HOST_LOG" "tool" "scanner.host"
    json_field_exists "$HOST_LOG" "target"
    json_field_exists "$HOST_LOG" "timestamp"
    json_field_exists "$HOST_LOG" "elapsed"
    json_field_type   "$HOST_LOG" "elapsed" "float"
    json_field_type   "$HOST_LOG" "data.alive_count" "int"
    json_field_type   "$HOST_LOG" "data.total_scanned" "int"
    json_field_type   "$HOST_LOG" "data.hosts" "list"

    json_assert "$HOST_LOG" "host: elapsed rounded to 2dp" \
        "e = d['elapsed']; assert e == round(e, 2)"

    json_assert "$HOST_LOG" "host: alive_count <= total_scanned" \
        "assert d['data']['alive_count'] <= d['data']['total_scanned']"

    json_assert "$HOST_LOG" "host: hosts list contains only alive entries" \
        "assert all(h['alive'] for h in d['data']['hosts'])"

    json_assert "$HOST_LOG" "host: host entries have correct keys" \
        "assert all(all(k in h for k in ['ip','alive','method','ttl','os_hint']) for h in d['data']['hosts'])"

    json_assert "$HOST_LOG" "host: method values are tcp or icmp only" \
        "assert all(h['method'] in {'tcp','icmp'} for h in d['data']['hosts'])"
else
    fail "host: no log file found"
    skip "host: all JSON checks skipped"
fi


# =============================================================================
# SCANNER — PORT
# =============================================================================
header "Scanner — Port"

expect_success "port: runs with default range"   aegiscli scanner port "$TARGET_DOMAIN"
expect_success "port: -v flag accepted"          aegiscli scanner port -v --ports 80,443 "$TARGET_DOMAIN"
expect_success "port: --ports range accepted"    aegiscli scanner port --ports 80-443 "$TARGET_DOMAIN"
expect_success "port: --ports list accepted"     aegiscli scanner port --ports 80,443 "$TARGET_DOMAIN"
expect_success "port: single port accepted"      aegiscli scanner port --ports 80 "$TARGET_DOMAIN"
expect_success "port: raw IP accepted"           aegiscli scanner port --ports 80,443 "$TARGET_IP"
expect_success "port: dead range exits cleanly"  aegiscli scanner port --ports 10-15 "$TARGET_DOMAIN"

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
    json_field_type   "$PORT_LOG" "data.open_ports" "list"

    json_assert "$PORT_LOG" "port: elapsed rounded to 2dp" \
        "e = d['elapsed']; assert e == round(e, 2)"

    json_assert "$PORT_LOG" "port: open_ports entries have port, banner, and service keys" \
        "assert all('port' in p and 'banner' in p and 'service' in p for p in d['data']['open_ports'])"

    json_assert "$PORT_LOG" "port: port values are integers" \
        "assert all(isinstance(p['port'], int) for p in d['data']['open_ports'])"

    json_assert "$PORT_LOG" "port: service is dict or null — no other types" \
        "assert all(p['service'] is None or isinstance(p['service'], dict) for p in d['data']['open_ports'])"

    json_assert "$PORT_LOG" "port: non-null service entries have protocol field" \
        "assert all('protocol' in p['service'] for p in d['data']['open_ports'] if p['service'] is not None)"
else
    fail "port: no log file found"
    skip "port: all JSON checks skipped"
fi


# =============================================================================
# ENVELOPE CONSISTENCY — cross module
# =============================================================================
header "Envelope Consistency — all modules"

for log_file in "$WHOIS_LOG" "$DNS_LOG" "$WEB_LOG" "$HOST_LOG" "$PORT_LOG"; do
    if [[ -n "$log_file" && -f "$log_file" ]]; then
        check_envelope "$log_file"
    fi
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
