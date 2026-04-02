import re


# ── per-protocol regex patterns ────────────────────────────────────────────────
# each entry: (protocol_name, compiled_regex, group_mapping)
# group_mapping maps named regex groups → output dict keys

_PATTERNS = [
    (
        "SSH",
        re.compile(r"^SSH-(?P<version>\d+\.\d+)-(?P<software>\S+?)(?:[ _](?P<os_hint>.+))?$"),
        # software field often looks like "OpenSSH_9.3p1" — split on _ to separate name from version
    ),
    (
        "FTP",
        re.compile(r"^220[\s-](?P<hostname>\S+)?\s*(?P<software>[A-Za-z]+(?:\s[A-Za-z]+)?)\s+(?P<software_version>[\d.]+)?"),
    ),
    (
        "SMTP",
        re.compile(r"^220\s+(?P<hostname>\S+)\s+(?:ESMTP\s+)?(?P<software>\S+)"),
    ),
    (
        "POP3",
        re.compile(r"^\+OK\s+(?P<software>.+?)\s+(?P<software_version>[\d.]+)"),
    ),
    (
        "IMAP",
        re.compile(r"^\* OK\s+(?P<software>.+?)\s+(?P<software_version>[\d.v]+)"),
    ),
    (
        "MySQL",
        re.compile(r"^(?P<software_version>[\d.]+)(?:-(?P<os_hint>[A-Za-z]+))?"),
    ),
    (
        "Redis",
        re.compile(r"^(?:\+PONG|-ERR)"),
    ),
    (
        "HTTP",
        re.compile(r"^HTTP/(?P<http_version>[\d.]+)\s+(?P<status_code>\d+).*\|\s*Server:\s*(?P<software>[^\s/]+)(?:/(?P<software_version>[\d.]+))?"),
    ),
]


def _parse_ssh(match: re.Match) -> dict:
    """SSH banner has compound software field: OpenSSH_9.3p1 — needs splitting."""
    result = {
        "protocol": "SSH",
        "version": match.group("version"),
        "software": None,
        "software_version": None,
        "os_hint": match.group("os_hint"),
    }
    raw_software = match.group("software") or ""
    if "_" in raw_software:
        name, ver = raw_software.split("_", 1)
        result["software"] = name
        result["software_version"] = ver
    else:
        result["software"] = raw_software
    return result


def _parse_generic(protocol: str, match: re.Match, keys: list[str]) -> dict:
    """Builds a dict from named groups for protocols with no special handling."""
    result = {"protocol": protocol}
    for key in keys:
        try:
            result[key] = match.group(key)
        except IndexError:
            result[key] = None
    return result


def parse(banner: str | None, port: int) -> dict | None:
    """
    Parses a raw banner string into structured service identity.

    Returns a dict on success, None if banner is empty or unrecognised.
    Raw banner is never modified — this is a read-only parse layer.

    port is accepted for future use (disambiguating identical banner formats
    across protocols) but not currently used in routing logic.
    """
    if not banner or not banner.strip():
        return None

    banner = banner.strip()

    # ── SSH ───────────────────────────────────────────────────────────────────
    m = _PATTERNS[0][1].match(banner)
    if m:
        return _parse_ssh(m)

    # ── FTP ───────────────────────────────────────────────────────────────────
    m = _PATTERNS[1][1].match(banner)
    if m:
        return _parse_generic("FTP", m, ["hostname", "software", "software_version"])

    # ── SMTP ──────────────────────────────────────────────────────────────────
    m = _PATTERNS[2][1].match(banner)
    if m:
        return _parse_generic("SMTP", m, ["hostname", "software"])

    # ── POP3 ──────────────────────────────────────────────────────────────────
    m = _PATTERNS[3][1].match(banner)
    if m:
        return _parse_generic("POP3", m, ["software", "software_version"])

    # ── IMAP ──────────────────────────────────────────────────────────────────
    m = _PATTERNS[4][1].match(banner)
    if m:
        return _parse_generic("IMAP", m, ["software", "software_version"])

    # ── MySQL ─────────────────────────────────────────────────────────────────
    # MySQL banners start with a version string — only match on known MySQL ports
    # to avoid false positives on arbitrary numeric-looking banners
    if port in {3306}:
        m = _PATTERNS[5][1].match(banner)
        if m:
            return _parse_generic("MySQL", m, ["software_version", "os_hint"])

    # ── Redis ─────────────────────────────────────────────────────────────────
    m = _PATTERNS[6][1].match(banner)
    if m:
        return {"protocol": "Redis", "software": "Redis", "software_version": None}

    # ── HTTP / HTTPS ──────────────────────────────────────────────────────────
    m = _PATTERNS[7][1].match(banner)
    if m:
        return _parse_generic("HTTP", m, ["http_version", "status_code", "software", "software_version"])

    return None