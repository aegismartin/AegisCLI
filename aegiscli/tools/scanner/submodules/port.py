import asyncio
import socket
from aegiscli.tools.scanner.scanner import Scanner
from aegiscli.core.helpers.formatter import s
from aegiscli.core.utils.logger import log, logging, log_json
from aegiscli.core.utils import exporter
from aegiscli.core.utils.flagger import verbose
from colorama import Fore, Style
import time


class Port(Scanner):
    def __init__(self, settings, submodule, target, ports):
        super().__init__(settings, submodule, target)
        self.ports = self.parse_ports(ports)
        # caps concurrent TCP connections — prevents OS file descriptor exhaustion
        self.semaphore = asyncio.Semaphore(400)
        self.data = None
        self.elapsed = None

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

    async def check_port(self, ip, port):
        # semaphore gate — only 400 coroutines active at once, rest queue here
        async with self.semaphore:
            try:
                # attempt TCP connect — wait_for enforces hard timeout per port
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port),
                    timeout=0.7
                )
                # connection succeeded — port is open, clean up and report
                writer.close()
                await writer.wait_closed()
                return port
            except:
                # timeout, refused, unreachable — port is closed or filtered
                return None

    async def run_scan(self):
        # resolve once here — not per port, avoids hammering DNS
        ip = socket.gethostbyname(self.target)
        # build full task list — coroutines don't run until gather fires them
        tasks = [self.check_port(ip, port) for port in self.ports]
        # fire all concurrently, collect results in original order
        results = await asyncio.gather(*tasks)
        # strip None (closed ports) — return only confirmed open port numbers
        return [p for p in results if p is not None]

    def fetch(self):
        # resolve target upfront — fail early before touching the network at scale
        verbose.step(f"Resolving target: {self.target}")
        try:
            ip = socket.gethostbyname(self.target)
            verbose.ok(f"Resolved to {ip}")
        except socket.gaierror:
            verbose.fail(f"DNS resolution failed for {self.target}")
            log(f"{Fore.RED}[ERROR]{Style.RESET_ALL} DNS resolution failed for {self.target}")
            raise

        port_count = len(list(self.ports))

        # surface scan parameters so user can reason about speed vs accuracy tradeoffs
        verbose.step(f"Building task queue — {port_count} coroutines")
        verbose.write(f"Concurrency cap: 400 simultaneous connections")
        verbose.write(f"Timeout per port: 0.7s")
        # theoretical = how long if every batch hits max timeout
        verbose.write(f"Expected scan duration: {round((port_count / 400) * 0.7 * 1.1, 2)}s")

        start = time.time()
        # asyncio.run() starts the event loop — bridges normal method into async world
        # blocks here until every coroutine in run_scan() completes or times out
        verbose.step("Handing off to event loop")
        self.data = asyncio.run(self.run_scan())
        self.elapsed = round(time.time() - start, 2)

        # closed/filtered = everything that returned None — useful for debugging false negatives
        verbose.ok(f"Event loop returned — {len(self.data)} open, {port_count - len(self.data)} closed/filtered in {self.elapsed}s")

    def display(self):
        def get_service(port):
            # getservbyport pulls from OS service database — no external dependency
            try:
                return socket.getservbyport(port)
            except OSError:
                return "unknown"

        rows = [{"port": p, "service": get_service(p)} for p in sorted(self.data)]
        s.header("Port Scanner")
        s.subheader("Open Ports")
        s.print_table(rows, columns=["port", "service"], summary_label="open port")
        s.message(f"Scan finished in {self.elapsed} seconds")

    def export(self):
        envelope = exporter.dump(
            tool="scanner.port",
            target=self.target,
            elapsed=self.elapsed,
            data={
                "open_ports": self.data,
            }
        )
        # log_json only fires if --log was passed at CLI level
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