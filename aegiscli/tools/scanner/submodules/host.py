import asyncio
import socket
import struct
import os
import ipaddress
from aegiscli.tools.scanner.scanner import Scanner
from aegiscli.core.helpers.formatter import s
from aegiscli.core.utils.logger import log, logging, log_json
from aegiscli.core.utils import exporter
from aegiscli.core.utils.flagger import verbose
from colorama import Fore, Style
import time


class Host(Scanner):
    def __init__(self, settings, submodule, target):
        super().__init__(settings, submodule, target)
        self.hosts = self.parse_target(target)   # flat list of IP strings to probe
        self.has_root = os.getuid() == 0         # ICMP needs raw sockets → needs root
        self.probe_ports = [22, 80, 443]         # ports used when falling back to TCP
        self.timeout = 1.5                       # per-host timeout for both ICMP and TCP
        self.semaphore = asyncio.Semaphore(100)  # max concurrent probes — lower than port.py because we're hitting more hosts
        self.data = None                         # populated by fetch() — list of result dicts
        self.elapsed = None                      # scan duration in seconds

    # ── target parsing ──────────────────────────────────────────────────────

    def parse_target(self, target: str) -> list[str]:
        try:
            # if it's a valid single IP, return it directly
            ipaddress.ip_address(target)
            return [target]
        except ValueError:
            try:
                # otherwise treat as CIDR — ip_network parses the range
                # strict=False normalises host bits (192.168.1.5/24 → 192.168.1.0/24)
                # .hosts() skips network address and broadcast — only usable IPs
                net = ipaddress.ip_network(target, strict=False)
                return [str(ip) for ip in net.hosts()]
            except ValueError:
                results = socket.getaddrinfo(target, None)
                return list(set(r[4][0] for r in results))

    # ── ICMP ────────────────────────────────────────────────────────────────

    def checksum(self, data: bytes) -> int:
        # standard one's complement checksum — required by the ICMP protocol
        # receiver runs the same algorithm on the received packet
        # if nothing was corrupted the result is 0xffff, otherwise packet is discarded
        s = 0
        for i in range(0, len(data), 2):
            # combine two bytes into one 16-bit number and add to running total
            # if packet length is odd, pad the last byte with 0
            w = (data[i] << 8) + (data[i+1] if i+1 < len(data) else 0)
            s += w
        # fold any overflow back into the lower 16 bits (one's complement)
        s = (s >> 16) + (s & 0xffff)
        s += (s >> 16)
        # bitwise NOT masked to 16 bits — makes the receiver's verification equation work
        return ~s & 0xffff

    def build_packet(self) -> bytes:
        # ICMP echo request packet structure (RFC 792):
        # byte 0   → type (8 = echo request)
        # byte 1   → code (always 0 for echo)
        # byte 2-3 → checksum
        # byte 4-5 → identifier (our PID — lets us match replies to our process)
        # byte 6-7 → sequence number
        # byte 8+  → payload (arbitrary, we use our tool name)

        pid = os.getpid() & 0xffff  # mask to 16 bits — PID can exceed unsigned short max
        payload = b"aegiscli"

        # pass 1 — build packet with checksum=0 (placeholder)
        # we can't compute the checksum before we have the packet bytes
        header = struct.pack("!BBHHH", 8, 0, 0, pid, 1)
        packet = header + payload

        # compute real checksum over the complete packet
        chk = self.checksum(packet)

        # pass 2 — rebuild with the real checksum inserted
        header = struct.pack("!BBHHH", 8, 0, chk, pid, 1)
        return header + payload

    def parse_reply(self, data: bytes) -> tuple[int, int]:
        # recvfrom() returns the full IP packet, not just ICMP
        # IP header is always exactly 20 bytes
        # TTL lives at byte 8 of the IP header — fixed position, defined by the IP protocol spec
        ttl = data[8]

        # slice off the IP header to get to the ICMP reply
        icmp = data[20:]

        # unpack the ICMP header — same format as what we sent
        # we only care about recv_id to verify the reply belongs to our process
        _, _, _, recv_id, _ = struct.unpack("!BBHHH", icmp[:8])

        return (ttl, recv_id)

    async def icmp_ping(self, ip: str) -> dict | None:
        try:
            # SOCK_RAW bypasses TCP/UDP — we're responsible for the protocol layer ourselves
            # IPPROTO_ICMP tells the OS which raw protocol we're speaking
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            sock.settimeout(self.timeout)

            packet = self.build_packet()
            sock.sendto(packet, (ip, 0))  # port is 0 — ICMP has no ports

            data, _ = sock.recvfrom(1024)

            ttl, recv_id = self.parse_reply(data)

            # verify this reply belongs to our ping and not another process's ICMP traffic
            pid = os.getpid() & 0xffff
            if recv_id != pid:
                return None

            return {
                "ip": ip,
                "alive": True,
                "method": "icmp",
                "ttl": ttl,
                "os_hint": self.os_hint(ttl)
            }

        except Exception:
            # timeout, permission error, anything — just return None
            # check_host will fall back to TCP
            return None

        finally:
            # always close the raw socket regardless of outcome
            sock.close()

    # ── TCP fallback ─────────────────────────────────────────────────────────

    async def tcp_probe(self, ip: str) -> dict:
        alive = False

        for port in self.probe_ports:
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port),
                    timeout=self.timeout
                )
                writer.close()
                await writer.wait_closed()
                # successful connection — host is definitely up
                alive = True
                break
            except ConnectionRefusedError:
                # host actively refused — it still responded, so it's alive
                # refused != unreachable
                alive = True
                break
            except Exception:
                # timeout or other error on this port — try the next one
                continue

        # no TTL available via TCP — OS fingerprinting only works with ICMP
        return {
            "ip": ip,
            "alive": alive,
            "method": "tcp",
            "ttl": None,
            "os_hint": None
        }

    # ── os hint ──────────────────────────────────────────────────────────────

    def os_hint(self, ttl: int) -> str:
        # default TTLs: Linux=64, Windows=128, Cisco=255
        # TTL decrements at each hop so we use thresholds not exact values
        # a Linux host 3 hops away might show TTL=61 — still >= 64 range
        if ttl >= 128:
            return "Windows"
        elif ttl >= 64:
            return "Linux/macOS"
        else:
            return "Network device / unknown"

    # ── per-host orchestration ───────────────────────────────────────────────

    async def check_host(self, ip: str) -> dict:
        async with self.semaphore:
            if self.has_root:
                # try ICMP first — faster, gives us TTL for OS fingerprinting
                result = await self.icmp_ping(ip)
                if result is None:
                    # ICMP failed or timed out — fall back to TCP
                    result = await self.tcp_probe(ip)
                return result
            else:
                # no root — can't create raw sockets, go straight to TCP
                return await self.tcp_probe(ip)

    # ── scan runner ──────────────────────────────────────────────────────────

    async def run_scan(self) -> list[dict]:
        # build all coroutines upfront — they don't execute until gather fires them
        tasks = [self.check_host(ip) for ip in self.hosts]
        # run all concurrently, semaphore controls actual parallelism
        results = await asyncio.gather(*tasks)
        # strip any None results (shouldn't happen but defensive)
        return [r for r in results if r is not None]

    # ── ABC interface ────────────────────────────────────────────────────────

    def fetch(self):
        verbose.step(f"Parsing target: {self.target}")
        verbose.write(f"Hosts to probe: {len(self.hosts)}")
        verbose.write(f"ICMP available: {self.has_root}")
        verbose.write(f"Concurrency cap: 100 simultaneous connections")

        start = time.time()
        verbose.step("Handing off to event loop")
        self.data = asyncio.run(self.run_scan())
        self.elapsed = round(time.time() - start, 2)

        alive_count = sum(1 for h in self.data if h["alive"])
        verbose.ok(f"Event loop returned — {alive_count} alive, {len(self.hosts) - alive_count} unreachable in {self.elapsed}s")

    def display(self):
        alive = [h for h in self.data if h["alive"]]

        rows = [
            {
                "ip": h["ip"],
                "method": h["method"],
                "ttl": h["ttl"] if h["ttl"] is not None else "-",
                "os_hint": h["os_hint"] if h["os_hint"] is not None else "-"
            }
            for h in alive
        ]

        s.header("Host Discovery")
        s.subheader("Live Hosts")
        s.print_table(rows, columns=["ip", "method", "ttl", "os_hint"], summary_label="live host")
        s.message(f"{len(alive)}/{len(self.data)} hosts alive — scan finished in {self.elapsed}s")

    def export(self):
        envelope = exporter.dump(
            tool="scanner.host",
            target=self.target,
            elapsed=self.elapsed,
            data={
                "alive_count": sum(1 for h in self.data if h["alive"]),
                "total_scanned": len(self.data),
                "hosts": [h for h in self.data if h["alive"]]
            }
        )
        if logging:
            path = log_json(envelope)
            verbose.ok(f"JSON log saved to {path}")

    def result(self):
        verbose.write(f"Starting host discovery: {self.target}")
        verbose.space()
        self.fetch()
        verbose.space()
        self.display()
        self.export()