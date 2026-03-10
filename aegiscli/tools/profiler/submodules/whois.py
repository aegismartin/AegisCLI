import whoisit
whoisit.bootstrap()
from colorama import Fore, Style
import subprocess
from aegiscli.core.utils.logger import log, logging, log_json
from aegiscli.core.utils.flagger import verbose
from aegiscli.core.utils import exporter
from aegiscli.tools.profiler.profiler import Profiler
from aegiscli.core.helpers.formatter import s
import time


# whois_shell is a subprocess fallback for registries that don't support RDAP
# some older TLDs (.ru, .cn, etc.) only respond to the legacy whois protocol
def whois_shell(domain):
    try:
        result = subprocess.run(
            ["whois", domain],
            capture_output=True,
            text=True,
            timeout=8
        )
        return result.stdout
    except:
        return None


class Whois(Profiler):
    def __init__(self, settings, submodule, target):
        super().__init__(settings, submodule, target)
        self.data = None   # holds whatever came back — RDAP dict or raw whois string
        self.mode = None   # "rdap" | "whois_raw" | "none" — determines how data is handled downstream
        self.info = {}     # structured RDAP fields, populated by rdap_lookup() only
        self.elapsed = None

    def fetch(self):
        # RDAP only — modern REST-based protocol that returns structured JSON
        # does not handle fallback, that's fallback()'s job
        verbose.write(f"Initializing WHOIS lookup for: {self.target}")
        verbose.space()

        verbose.step("Attempting RDAP query (modern protocol)")
        rdap_start = time.time()

        try:
            self.data = whoisit.domain(self.target)
            rdap_time = time.time() - rdap_start

            if isinstance(self.data, dict):
                self.mode = "rdap"
                verbose.ok(f"RDAP response received ({rdap_time:.3f}s)")
                verbose.write(f"Data structure validated: {len(self.data)} top-level keys")
            else:
                verbose.fail(f"RDAP returned invalid data type: {type(self.data).__name__}")
                self.data = None
                self.mode = None

        except ConnectionError:
            verbose.fail("RDAP connection refused or timed out")
            self.data = None
            self.mode = None
        except Exception as e:
            verbose.fail(f"RDAP query failed: {type(e).__name__}")
            self.data = None
            self.mode = None

        verbose.space()

    def fallback(self):
        # no-op if RDAP already succeeded — self.mode guards the whole method
        if self.mode == "rdap":
            return

        # raw WHOIS via system subprocess — unstructured text response
        # self.data becomes a plain string here, not a dict
        verbose.step("Falling back to legacy WHOIS protocol")
        whois_start = time.time()

        self.data = whois_shell(self.target)
        whois_time = time.time() - whois_start

        if self.data:
            self.mode = "whois_raw"
            verbose.ok(f"Raw WHOIS data retrieved ({whois_time:.3f}s)")
            verbose.write(f"Response size: {len(self.data)} bytes")
        else:
            self.mode = "none"
            verbose.fail("WHOIS command failed or returned no data")

        verbose.space()

    def display(self):
        # routes display based on self.mode — by this point fetch/fallback have
        # already set self.data and self.mode, this method just reacts to them
        if self.mode == "rdap":
            # rdap_lookup() parses self.data into self.info before display
            self.rdap_lookup()
            s.header("whois info")
            s.print_dict(self.info)
        elif self.mode == "whois_raw":
            s.header("whois info")
            # notice instead of error — raw whois is valid data, just unstructured
            log(f"{Fore.CYAN}[NOTICE]{Style.RESET_ALL} This registry does not support RDAP. This is all we could get\n")
            log(self.data)

        elif self.mode == "none":
            log(f"{Fore.RED}[ERROR]{Style.RESET_ALL} No WHOIS or RDAP data could be retrieved.")



    def rdap_lookup(self):
        # parses the raw RDAP response dict into self.info
        # only safe to call when self.mode == "rdap" and self.data is a dict
        verbose.step("Parsing RDAP response structure")

        entities = self.data.get("entities", {})
        verbose.write(f"Found {len(entities)} entity type(s) in response")

        verbose.indent()
        # entities is a dict of role -> list of contact objects
        # we only care about registrar and abuse contacts
        registrar = entities.get("registrar", [{}])
        if registrar and registrar[0]:
            verbose.write("Registrar entity present")
        else:
            verbose.write("⚠ Registrar entity missing")

        abuse = entities.get("abuse", [{}])
        if abuse and abuse[0]:
            verbose.write("Abuse contact present")
        else:
            verbose.write("⚠ Abuse contact missing")
        verbose.unindent()

        self.info = {
            "name": self.data.get("name"),
            "handle": self.data.get("handle"),
            "url": self.data.get("url"),
            "registration_date": self.data.get("registration_date"),
            "last_changed_date": self.data.get("last_changed_date"),
            "expiration_date": self.data.get("expiration_date"),
            "nameservers": self.data.get("nameservers"),
            "status": self.data.get("status"),
            "dnssec": self.data.get("dnssec"),
            "registrar": {
                "name": registrar[0].get("name") if registrar else None,
                "url": registrar[0].get("url") if registrar else None,
            },
            "abuse": {
                "email": abuse[0].get("email") if abuse else None,
                "tel": abuse[0].get("tel") if abuse else None,
            },
        }

        # verbose instrumentation — flattens nested dicts to count total populated fields
        # registrar.name, registrar.url etc. are counted as separate fields
        flat_fields = []
        for key, val in self.info.items():
            if isinstance(val, dict):
                flat_fields.extend([f"{key}.{k}" for k, v in val.items() if v is not None])
            elif val is not None:
                flat_fields.append(key)

        verbose.ok(f"Extracted {len(flat_fields)} populated fields from RDAP")
        verbose.space()

    def export(self):
        # nothing to export if both protocols failed
        if self.mode == "none":
            return

        # data payload differs by mode — raw whois is a string, rdap is self.info dict
        data_payload = {
            "mode": self.mode,
            "data": self.data if self.mode == "whois_raw" else self.info
        }

        envelope = exporter.dump(
            tool="profiler.whois",
            target=self.target,
            elapsed=self.elapsed,
            data=data_payload
        )
        # log_json only fires if --log flag was passed at CLI level
        if logging:
            path = log_json(envelope)
            verbose.ok(f"JSON log saved to {path}")

    def result(self):
        start = time.time()

        try:
            self.fetch()        # try RDAP, set self.data + self.mode
            self.fallback()     # try raw whois if RDAP failed, no-op otherwise

            self.elapsed = round(time.time() - start, 2)
            verbose.ok(f"WHOIS lookup completed in {self.elapsed:.3f}s total")
            verbose.space()

            self.display()  # display based on self.mode

            if self.mode == "none":
                # display already printed the error — raise so exit code is non-zero
                raise RuntimeError("No data retrieved from any source")

            self.export()       # serialize to JSON, log if --log

        except Exception as e:
            self.elapsed = time.time() - start
            log(f"{Fore.RED}[ERROR]{Style.RESET_ALL} WHOIS aborted after {self.elapsed:.3f}s — {type(e).__name__}")
            raise


if __name__ == "__main__":
    initializator = Whois(settings=None, submodule=None, target="httpbin.org")
    initializator.result()