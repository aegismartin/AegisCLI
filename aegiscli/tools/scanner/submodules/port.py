import asyncio
import socket
from aegiscli.tools.scanner.scanner import Scanner
from aegiscli.core.helpers.formatter import s
from aegiscli.core.utils.logger import log, logging, log_json
from aegiscli.core.utils import exporter
from aegiscli.core.utils.flagger import verbose
from colorama import Fore, Style
import time
import ssl


class Port(Scanner):
    def __init__(self, settings, submodule, target, ports):
        super().__init__(settings, submodule, target)
        self.ports = self.parse_ports(ports)
        # caps concurrent TCP connections — prevents OS file descriptor exhaustion
        self.semaphore = asyncio.Semaphore(400)
        self.data = None       # list of (port, banner) tuples after fetch()
        self.elapsed = None
        self.passive_ports = {21, 22, 23, 25, 110, 143, 587, 3306, 5432, 6379, 27017, 9200, 11211}
        self.http_probe = {80, 8080, 8000, 8008, 8888, 3000, 5000}
        self.https_probe = {443, 8443, 9443}
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"

    def parse_ports(self, ports_arg):
        # no flag passed — use default top 1024
        if ports_arg is None:
            return range(1, 1025)
        # range format: "1-1024"
        if "-" in ports_arg:
            start, end = ports_arg.split("-")
            return range(int(start), int(end) + 1)
        # list format: "80,443,8080"
        if "," in ports_arg:
            return [int(p) for p in ports_arg.split(",")]

    async def _grab_http_banner(self, reader, writer) -> str | None:
        writer.write(
            f"GET / HTTP/1.0\r\n"
            f"Host: {self.target}\r\n"
            f"User-Agent: {self.user_agent}\r\n"
            f"\r\n"
            .encode()
        )
        await writer.drain()
        raw = await asyncio.wait_for(reader.read(1024), timeout=0.4)
        decoded = raw.decode("utf-8", errors="replace")
        server_header = next(
            (line.split(":", 1)[1].strip()
            for line in decoded.split("\r\n")
            if line.lower().startswith("server:")),
            None
        )
        status_line = decoded.split("\r\n")[0].strip()
        return f"{status_line} | Server: {server_header}" if server_header else status_line

    async def check_port(self, ip, port):
        async with self.semaphore:

            # ── step 1: plain TCP connect — sole purpose is confirming port is open ──
            # if this fails, port is closed/filtered, we're done
            try:
                _, tcp_writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port),
                    timeout=0.7
                )
                tcp_writer.close()
                await tcp_writer.wait_closed()
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                return None

            # ── port confirmed open — step 2 is banner only ──
            # nothing below can change the port's open status
            verbose.ok(f"Port {port} open — attempting banner grab")
            banner = None

            try:
                if port in self.passive_ports:
                    verbose.step(f"Port {port} — passive read (service speaks first)")
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(ip, port),
                        timeout=0.7
                    )
                    raw = await asyncio.wait_for(reader.read(1024), timeout=0.4)
                    banner = raw.decode("utf-8", errors="replace").strip()
                    if banner:
                        verbose.ok(f"Port {port} — banner: {banner[:60]}{'...' if len(banner) > 60 else ''}")
                    else:
                        verbose.fail(f"Port {port} — passive read returned empty")

                elif port in self.http_probe:
                    verbose.step(f"Port {port} — HTTP probe (GET /)")
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(ip, port),
                        timeout=0.7
                    )
                    banner = await self._grab_http_banner(reader, writer)
                    if banner:
                        verbose.ok(f"Port {port} — {banner[:60]}{'...' if len(banner) > 60 else ''}")
                    else:
                        verbose.fail(f"Port {port} — HTTP probe got no response")

                elif port in self.https_probe:
                    verbose.step(f"Port {port} — SSL handshake + HTTPS probe")
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(ip, port, ssl=ctx, server_hostname=self.target),
                        timeout=2.5
                    )
                    verbose.write(f"Port {port} — TLS handshake complete, sending GET /")
                    banner = await self._grab_http_banner(reader, writer)
                    if banner:
                        verbose.ok(f"Port {port} — {banner[:60]}{'...' if len(banner) > 60 else ''}")
                    else:
                        verbose.fail(f"Port {port} — HTTPS probe got no response")

                else:
                    verbose.write(f"Port {port} — not in probe lists, skipping banner")

                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

            except Exception as e:
                # banner grab failed — port still open, just no banner
                verbose.fail(f"Port {port} — banner grab failed ({type(e).__name__})")
                banner = None

            return (port, banner)

    def fetch(self):
        # resolve target upfront — fail early before touching the network at scale
        verbose.step(f"Resolving target: {self.target}")
        try:
            self.ip = socket.gethostbyname(self.target)
            verbose.ok(f"Resolved to {self.ip}")
        except socket.gaierror:
            verbose.fail(f"DNS resolution failed for {self.target}")
            log(f"{Fore.RED}[ERROR]{Style.RESET_ALL} DNS resolution failed for {self.target}")
            raise

        port_count = len(list(self.ports))

        # surface scan parameters so user can reason about speed vs accuracy tradeoffs
        verbose.step(f"Building task queue — {port_count} coroutines")
        verbose.write(f"Concurrency cap: 400 simultaneous connections")
        verbose.write(f"Timeout per port: 0.7s TCP + 2.5s SSL + 0.4s banner read")
        # theoretical = how long if every batch hits max timeout
        verbose.write(f"Expected scan duration: {round((port_count / 400) * 0.7 * 1.1, 2)}s")

        start = time.time()
        verbose.step("Handing off to event loop")
        self.data = asyncio.run(self.run_scan())
        self.elapsed = round(time.time() - start, 2)

        banner_count = sum(1 for _, b in self.data if b)
        verbose.ok(f"Event loop returned — {len(self.data)} open ({banner_count} banners grabbed), {port_count - len(self.data)} closed/filtered in {self.elapsed}s")

    async def run_scan(self):
        # build full task list — coroutines don't run until gather fires them
        tasks = [self.check_port(self.ip, port) for port in self.ports]
        # fire all concurrently, collect results in original order
        results = await asyncio.gather(*tasks)
        # strip None (closed ports) — return only confirmed open (port, banner) tuples
        return [r for r in results if r is not None]

    def display(self):
        def get_service(port):
            try:
                return socket.getservbyport(port)
            except OSError:
                return "unknown"

        rows = [
            {
                "port": port,
                "service": get_service(port),
                "banner": banner if banner else "None"
            }
            for port, banner in sorted(self.data, key=lambda x: x[0])
        ]

        s.header("Port Scanner")
        s.subheader("Open Ports")
        s.print_table(rows, columns=["port", "service", "banner"], summary_label="open port")
        s.message(f"Scan finished in {self.elapsed} seconds")

    def export(self):
        envelope = exporter.dump(
            tool="scanner.port",
            target=self.target,
            elapsed=self.elapsed,
            data={
                "open_ports": [
                    {"port": port, "banner": banner}
                    for port, banner in self.data
                ]
            }
        )
        if logging:
            path = log_json(envelope)
            verbose.ok(f"JSON log saved to {path}")

    def result(self):
        verbose.write(f"Starting port scan: {self.target}")
        verbose.space()
        self.fetch()
        verbose.space()
        self.display()
        self.export()