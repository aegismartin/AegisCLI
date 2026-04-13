from colorama import Fore, Style
from aegiscli.core.utils.logger import log
import sys

USE_GLYPHS = (sys.stdout.encoding or "").lower() == "utf-8"

class Verbose:
    def __init__(self):
        self.enabled = False
        self.level = 0
        
        # Symbols - with fallbacks for non-UTF8 terminals
        self.sym_info = "◆" if USE_GLYPHS else "*"
        self.sym_step = "▸" if USE_GLYPHS else ">"
        self.sym_ok = "✓" if USE_GLYPHS else "+"
        self.sym_fail = "✗" if USE_GLYPHS else "-"
        
    def enable(self):
        self.enabled = True
        
    def _indent(self):
        return " " * (self.level * 4)
    
    def write(self, text):
        if self.enabled:
            log(f"{self._indent()}{Fore.WHITE}{self.sym_info}{Style.RESET_ALL} {text}")
    
    def step(self, text):
        if self.enabled:
            log(f"{self._indent()}{Fore.CYAN}{self.sym_step}{Style.RESET_ALL} {Style.DIM}{text}{Style.RESET_ALL}")
    
    def ok(self, text):
        if self.enabled:
            log(f"{self._indent()}{Fore.GREEN}{self.sym_ok}{Style.RESET_ALL} {text}")
    
    def fail(self, text):
        if self.enabled:
            log(f"{self._indent()}{Fore.RED}{self.sym_fail}{Style.RESET_ALL} {text}")
    
    def space(self):
        if self.enabled:
            log("")
    
    def indent(self):
        self.level += 1
    
    def unindent(self):
        if self.level > 0:
            self.level -= 1

verbose = Verbose()