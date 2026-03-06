import dns.resolver
import dns.reversename
import aegiscli.tools.profiler.profiler as profiler
from aegiscli.core.utils.logger import log, logging, log_json
from aegiscli.core.utils.flagger import verbose
from aegiscli.core.utils import exporter
from colorama import Style, Fore
from aegiscli.core.helpers.formatter import s
import time


class DNS(profiler.Profiler):
    def __init__(self, settings, submodule, advanced, target):
        super().__init__(settings, submodule, advanced, target)
        self.target = target
        self.rtype = ["A", "AAAA", "MX", "TXT", "NS", "CNAME", "SOA"]  # record types to query
        self.dns_records = {}     # populated by resolve_record() — only types that returned data
        self.reverse_results = {} # populated by reverse_all() — only IPs that have PTR records

    def fetch(self):
        # satisfies ABC contract — wraps both data collection steps
        # resolve_record and reverse_all stay separate for clarity and testability
        self.resolve_record()
        verbose.space()
        self.reverse_all()

    def resolve_record(self):
        # Cloudflare + Google as resolvers — avoids ISP DNS that might lie or filter results
        verbose.step(f"Initializing DNS resolver with Cloudflare (1.1.1.1) and Google (8.8.8.8)")
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ["1.1.1.1", "8.8.8.8"]

        verbose.step(f"Querying {len(self.rtype)} record types for {self.target}")
        verbose.indent()

        raw = {}  # unfiltered results including empty record types
        queries_succeeded = 0
        queries_failed = 0
        total_records = 0

        for rtype in self.rtype:
            query_start = time.time()
            try:
                answers = resolver.resolve(self.target, rtype)
                query_time = time.time() - query_start
                records = [record.to_text() for record in answers]
                raw[rtype] = records
                queries_succeeded += 1
                total_records += len(records)
                verbose.write(f"{rtype}: {len(records)} record(s) found ({query_time:.3f}s)")

            except dns.resolver.NoAnswer:
                # NOERROR with no records — domain exists but no record of this type
                queries_failed += 1
                verbose.write(f"{rtype}: No records (NOERROR)")
            except dns.resolver.NXDOMAIN:
                # domain doesn't exist at all — show this always, not just in verbose
                queries_failed += 1
                verbose.fail(f"{rtype}: Domain does not exist (NXDOMAIN)")
                log(f"{Fore.RED}[ERROR]{Style.RESET_ALL} Domain does not exist: {self.target}")
                return
            except dns.exception.Timeout:
                queries_failed += 1
                verbose.fail(f"{rtype}: Query timed out")
                log(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} {rtype} query timed out")
            except Exception as e:
                queries_failed += 1
                verbose.fail(f"{rtype}: {type(e).__name__}")
                log(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} {rtype} query failed: {type(e).__name__}")

        verbose.unindent()
        verbose.ok(f"DNS queries complete: {queries_succeeded} succeeded, {queries_failed} failed, {total_records} total records")

        # drop empty record types — no point storing or displaying them
        self.dns_records = {k: v for k, v in raw.items() if v}
        verbose.step(f"Filtering results: {len(self.dns_records)}/{len(raw)} record types have data")

    def reverse_dns(self, ip):
        # single IP reverse lookup — converts IP to in-addr.arpa format and queries PTR
        # returns empty list on any failure, caller handles the absence
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ["1.1.1.1", "8.8.8.8"]
        try:
            rev = dns.reversename.from_address(ip)  # e.g. 8.8.8.8 → 8.8.8.8.in-addr.arpa
            answers = resolver.resolve(rev, "PTR")
            return [record.to_text() for record in answers]
        except:
            return []

    def reverse_all(self):
        # PTR records exist for both A (IPv4) and AAAA (IPv6), so we check both
        ips = []
        ips.extend(self.dns_records.get("A", []))
        ips.extend(self.dns_records.get("AAAA", []))

        if not ips:
            verbose.write("No A or AAAA records to perform reverse DNS on")
            return

        verbose.step(f"Performing reverse DNS lookups on {len(ips)} IP address(es)")
        verbose.indent()

        raw = {}  # unfiltered — includes IPs with no PTR
        ptrs_found = 0

        for ip in ips:
            lookup_start = time.time()
            ptrs = self.reverse_dns(ip)
            lookup_time = time.time() - lookup_start
            raw[ip] = ptrs

            if ptrs:
                verbose.write(f"{ip}: {len(ptrs)} PTR record(s) ({lookup_time:.3f}s)")
                ptrs_found += len(ptrs)
            else:
                verbose.write(f"{ip}: No PTR records ({lookup_time:.3f}s)")

        verbose.unindent()
        verbose.ok(f"Reverse DNS complete: {ptrs_found} PTR record(s) found")

        # drop IPs with no PTR — empty entries add noise to output and JSON
        self.reverse_results = {ip: ptrs for ip, ptrs in raw.items() if ptrs}

    def display(self):
        # " RECORD" suffix is purely cosmetic — makes output easier to read at a glance
        display_records = {f"{k} RECORD": v for k, v in self.dns_records.items()}

        s.header("DNS Info")
        s.subheader("DNS Records")
        if display_records:
            s.print_dict(display_records)
        else:
            log(f"{Fore.YELLOW}No DNS records found{Style.RESET_ALL}")

        s.subheader("Reverse DNS")
        if self.reverse_results:
            s.print_dict(self.reverse_results)
        else:
            log(f"{Fore.YELLOW}No PTR records found{Style.RESET_ALL}")

    def export(self):
        # dns_records stored without " RECORD" suffix — cleaner for tooling to query
        envelope = exporter.dump(
            tool="profiler.dns",
            target=self.target,
            data={
                "dns_records": self.dns_records,
                "reverse_dns": self.reverse_results
            }
        )
        # log_json only fires if --log flag was passed at CLI level
        if logging:
            path = log_json(envelope)
            verbose.ok(f"JSON log saved to {path}")

    def result(self):
        verbose.write(f"Starting DNS enumeration for: {self.target}")
        verbose.space()
        overall_start = time.time()

        try:
            self.fetch()           # resolve_record + reverse_all
            verbose.space()

            overall_time = time.time() - overall_start
            verbose.ok(f"DNS enumeration completed in {overall_time:.3f}s total")
            verbose.space()

            self.display()  # formatted terminal output
            self.export()   # JSON envelope + optional log

        except Exception as e:
            overall_time = time.time() - overall_start
            log(f"{Fore.RED}[ERROR]{Style.RESET_ALL} DNS aborted after {overall_time:.3f}s — {type(e).__name__}")
            raise


if __name__ == "__main__":
    initializator = DNS(settings=None, submodule=None, advanced=False, target="httpbin.org")
    initializator.result()