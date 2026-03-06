import httpx
import aegiscli.tools.profiler.profiler as profiler
from aegiscli.core.utils.logger import log, logging, log_json
from aegiscli.core.utils.flagger import verbose
from aegiscli.core.utils import exporter
from colorama import Fore, Style
from aegiscli.core.helpers.formatter import s, parse_value, parse_cookie, flattener
import ssl
import socket
import time


class WebFinger(profiler.Profiler):
    def __init__(self, settings, submodule, advanced, target):
        super().__init__(settings, submodule, advanced, target)
        self.target = target

        # strip protocol to get bare domain for SSL socket connection
        self.domain = self.target.replace("http://", "") if self.target.startswith("http://") else self.target
        self.domain = self.target.replace("https://", "") if self.target.startswith("https://") else self.target

        self.tab = " " * 4

        # whitelist of headers worth extracting — everything else is noise
        # inline comments explain what each header leaks or reveals
        self.important_headers = [
            "Server",              # web server + version (nginx, Apache, Cloudflare…)
            "Date",                # response timestamp
            "Content-Type",        # MIME type
            "Content-Length",      # response size in bytes
            "Content-Encoding",    # gzip, br, deflate…
            "Transfer-Encoding",   # chunked, identity…
            "Connection",          # keep-alive / close
            "Set-Cookie",          # session hints, framework fingerprints, security flags
            "X-Powered-By",        # framework leak (PHP, Express, ASP.NET…)
            "X-AspNet-Version",    # ASP.NET version leak
            "X-AspNetMvc-Version", # ASP.NET MVC version leak
            "X-Drupal-Dynamic-Cache",
            "X-Generator",         # CMS fingerprint (Drupal, Joomla, Ghost…)
            "Via",                 # proxy/CDN hops
            "CF-RAY",              # confirms Cloudflare, unique request ID
            "CF-Cache-Status",     # Cloudflare cache behavior
            "X-Cache",             # Varnish or Nginx cache hit/miss
            "Strict-Transport-Security", # HSTS — is HTTPS enforced?
            "Access-Control-Allow-Origin", # CORS policy
        ]

        self.response = None       # raw httpx response object
        self.connection_data = {}  # populated by connection()
        self.headers = {}          # populated by headers_module() — filtered + parsed

        # only these cert fields are worth showing — the rest is boilerplate
        self.important_cert_data = [
            "issuer", "notAfter", "subject", "subjectAltName", "version"
        ]
        self.certs = {}  # populated by get_cert()

    def fetch(self):
        # normalize URL — prepend https:// if no protocol given
        verbose.step("Normalizing target URL")

        if not self.target.startswith("http://") and not self.target.startswith("https://"):
            verbose.write("No protocol detected, attempting HTTPS first")
            try:
                self.target = "https://" + self.target
            except Exception:
                verbose.write("HTTPS unavailable, falling back to HTTP")
                self.target = "http://" + self.target

        # follow_redirects=True — we want the final destination, not the redirect chain
        # timeout=5 — aggressive but necessary, slow targets aren't useful for recon
        verbose.step(f"Sending GET request with 5s timeout, redirects enabled")
        start_time = time.time()

        try:
            self.response = httpx.get(url=self.target, timeout=5, follow_redirects=True)
            elapsed = time.time() - start_time
            verbose.ok(f"Response received ({elapsed:.3f}s)")

            if self.response.history:
                verbose.indent()
                for i, resp in enumerate(self.response.history, 1):
                    verbose.write(f"Hop {i}: {resp.status_code} at {resp.url}")
                verbose.unindent()

        except httpx.TimeoutException:
            verbose.fail(f"Request timed out after 5s")
            log(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Request timed out — target unreachable or too slow")
            raise
        except httpx.ConnectError:
            verbose.fail(f"Connection refused or DNS failure")
            log(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Could not connect to {self.target} — check the target")
            raise
        except Exception as e:
            verbose.fail(f"Request failed: {type(e).__name__}")
            log(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Request failed: {type(e).__name__}")
            raise

    def connection(self):
        # extract high-level connection metadata from the final response
        verbose.step("Extracting connection metadata")

        self.connection_data["Status Code"] = self.response.status_code
        self.connection_data["Time Spent"] = self.response.elapsed.total_seconds()
        self.connection_data["HTTP Version"] = self.response.http_version

        # build full redirect chain including final URL
        chain = [str(r.url) for r in self.response.history] + [str(self.response.url)]
        self.connection_data["Redirects"] = " → ".join(chain)

        verbose.ok(f"Captured {len(self.connection_data)} connection properties")

    def headers_module(self):
        # filter response headers against the whitelist — ignore everything else
        verbose.step(f"Filtering {len(self.response.headers)} headers against {len(self.important_headers)} patterns")

        found_interesting = []
        found_tech = []
        found_security = []
        found_cdn = []
        skipped = 0

        verbose.indent()

        for h in self.important_headers:
            value = self.response.headers.get(h)
            if value and h != "Set-Cookie":
                # Set-Cookie handled separately below — get_list() needed for multiple cookies
                self.headers[h] = value
                found_interesting.append(h)

                if h in ["X-Powered-By", "Server", "X-AspNet-Version", "X-AspNetMvc-Version", "X-Generator"]:
                    found_tech.append(h)
                elif h in ["Strict-Transport-Security", "Access-Control-Allow-Origin"]:
                    found_security.append(h)
                elif h in ["CF-RAY", "CF-Cache-Status", "X-Cache", "Via"]:
                    found_cdn.append(h)
            else:
                skipped += 1

        verbose.unindent()

        if found_tech:
            verbose.write(f"Found {len(found_tech)} tech fingerprint header(s): {', '.join(found_tech)}")
        if found_security:
            verbose.write(f"Found {len(found_security)} security header(s): {', '.join(found_security)}")
        if found_cdn:
            verbose.write(f"Found {len(found_cdn)} CDN/proxy header(s): {', '.join(found_cdn)}")

        verbose.write(f"Skipped {skipped} absent headers")

        # get_list() is needed here — .get() only returns the first Set-Cookie value
        # servers can set multiple cookies in separate headers with the same name
        cookies = self.response.headers.get_list("Set-Cookie")
        if cookies:
            verbose.step(f"Parsing {len(cookies)} Set-Cookie header(s)")
            self.headers["Set-Cookie"] = [parse_cookie(c) for c in cookies]

            # flag missing security attributes — useful for quick security assessment
            cookies_with_httponly = sum(1 for c in self.headers["Set-Cookie"] if c.get("HttpOnly"))
            cookies_with_secure = sum(1 for c in self.headers["Set-Cookie"] if c.get("Secure"))
            cookies_with_samesite = sum(1 for c in self.headers["Set-Cookie"] if c.get("SameSite"))

            if cookies_with_httponly < len(cookies):
                verbose.write(f"⚠ {len(cookies) - cookies_with_httponly} cookie(s) missing HttpOnly flag")
            if cookies_with_secure < len(cookies):
                verbose.write(f"⚠ {len(cookies) - cookies_with_secure} cookie(s) missing Secure flag")
            if cookies_with_samesite < len(cookies):
                verbose.write(f"⚠ {len(cookies) - cookies_with_samesite} cookie(s) missing SameSite attribute")

        verbose.ok(f"Header extraction complete: {len(found_interesting)} captured")

    def get_cert(self):
        # raw SSL socket — httpx doesn't expose cert data directly so we open our own connection
        verbose.step(f"Opening SSL socket to {self.domain}:443")

        try:
            ctx = ssl.create_default_context()

            start_time = time.time()
            with ctx.wrap_socket(socket.socket(), server_hostname=self.domain) as sock:
                sock.connect((self.domain, 443))
                handshake_time = time.time() - start_time
                verbose.ok(f"TLS handshake completed ({handshake_time:.3f}s)")

                verbose.step("Retrieving peer certificate chain")
                raw = sock.getpeercert()  # returns nested tuple structure from ssl module

                if not raw:
                    verbose.fail("Server returned no certificate")
                    log(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} No certificate returned by server")
                    return

                verbose.write(f"Certificate contains {len(raw)} total fields")

                cert_fields_found = []
                for key, value in raw.items():
                    if key in self.important_cert_data:
                        self.certs[key] = value
                        cert_fields_found.append(key)

                # version 3 is standard X.509 — not interesting, just noise
                try:
                    if self.certs.get("version") == 3:
                        del self.certs["version"]
                        cert_fields_found.remove("version")
                        verbose.write("Filtered out X.509 v3 (standard)")
                except:
                    pass

                verbose.ok(f"Extracted {len(cert_fields_found)} relevant certificate fields")

        except ssl.SSLError as e:
            verbose.fail(f"SSL error: {type(e).__name__}")
            log(f"{Fore.RED}[ERROR]{Style.RESET_ALL} SSL error: {type(e).__name__}")
            raise
        except socket.gaierror:
            verbose.fail(f"DNS lookup failed for {self.domain}")
            log(f"{Fore.RED}[ERROR]{Style.RESET_ALL} DNS lookup failed for {self.domain}")
            raise
        except socket.timeout:
            verbose.fail("SSL handshake timed out")
            log(f"{Fore.RED}[ERROR]{Style.RESET_ALL} SSL handshake timed out")
            raise
        except ConnectionRefusedError:
            verbose.fail("Port 443 not accepting connections")
            log(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Port 443 refused connection on {self.domain}")
            raise
        except Exception as e:
            verbose.fail(f"Certificate retrieval failed: {type(e).__name__}")
            log(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Certificate retrieval failed: {type(e).__name__}")
            raise

    def display(self):
        # flattener() normalizes ssl.getpeercert()'s insane nested tuple structure
        # into a clean dict before passing to print_dict
        s.header("Web Fingerprint")
        s.subheader("Connection")
        s.print_dict(self.connection_data)
        s.subheader("Certificates")
        s.print_dict(flattener(self.certs))
        s.subheader("Headers")
        s.print_dict(self.headers)

    def export(self):
        # flattener called here to normalize certs for JSON
        # same reason as in display() — ssl.getpeercert() returns nested tuples
        envelope = exporter.dump(
            tool="profiler.web",
            target=self.target,
            data={
                "connection": self.connection_data,
                "headers": self.headers,
                "certs": flattener(self.certs)
            }
        )
        # log_json only fires if --log flag was passed at CLI level
        if logging:
            path = log_json(envelope)
            verbose.ok(f"JSON log saved to {path}")

    def result(self):
        verbose.write(f"Starting fingerprint: {self.target}")
        verbose.space()
        overall_start = time.time()

        try:
            self.fetch()           # HTTP GET, populate self.response
            verbose.space()

            self.connection()      # extract metadata from response into self.connection_data
            verbose.space()

            self.headers_module()  # filter + parse headers into self.headers
            verbose.space()

            self.get_cert()        # open raw SSL socket, populate self.certs
            verbose.space()

            overall_time = time.time() - overall_start
            verbose.ok(f"Scan completed in {overall_time:.3f}s total")
            verbose.space()

            self.display()
            self.export()

        except Exception as e:
            overall_time = time.time() - overall_start
            log(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Scan aborted after {overall_time:.3f}s — {type(e).__name__}")
            raise


if __name__ == "__main__":
    initializator = WebFinger(settings=None, submodule=None, advanced=False, target="httpbin.org")
    initializator.result()