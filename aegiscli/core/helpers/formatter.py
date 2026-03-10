from aegiscli.core.utils.logger import log
from colorama import Fore, Style
import sys
USE_GLYPHS = sys.stdout.encoding.lower() == "utf-8"
arrow = "❯❯" if USE_GLYPHS else ">>"

def parse_cookie(cookie_str):
    parts = [p.strip() for p in cookie_str.split(";")]
    result = {}
    result["name"] = parts[0].split("=")[0]
    for part in parts[1:]:
        if "=" in part:
            k, v = part.split("=", 1)
            result[k.strip()] = v.strip()
        else:
            result[part.strip()] = True
    return result

def flattener(obj, _parent_key=None):
    """
    Recursively flattens SSL cert data and other nested structures.
    Handles the insane ((('key','value'),),) pattern from ssl.getpeercert()
    """
    
    if not isinstance(obj, (tuple, list, dict)):
        return obj
    
    if isinstance(obj, dict):
        flat = {k: flattener(v, _parent_key=k) for k, v in obj.items()}
        return flat
    
    if isinstance(obj, (tuple, list)):
        flat_list = [flattener(x, _parent_key=_parent_key) for x in obj]
        
        if _parent_key == "subjectAltName":
            return flat_list

        if all(isinstance(item, list) and len(item) == 2 and 
               isinstance(item[0], str) and isinstance(item[1], str) 
               for item in flat_list):
            result = {}
            for k, v in flat_list:
                if k in result:
                    if not isinstance(result[k], list):
                        result[k] = [result[k]]
                    result[k].append(v)
                else:
                    result[k] = v
            return result
        
        return flat_list


def parse_value(value):
    if "; " in value and ", " in value:
        chunks = value.split(", ")
        if all("=" in c and ";" in c for c in chunks):
            return chunks  
    return value


class Special_Text:
    def __init__(self):
        self.tab = " " * 4
    
    def header(self, text):
        log(f"{Fore.MAGENTA}{'═' * 75}\n  {arrow}  {Fore.WHITE}{Style.BRIGHT}{text.upper()}{Style.RESET_ALL}\n{Fore.MAGENTA}{'═' * 75}{Style.RESET_ALL}")

    def subheader(self, text): 
        log(f"{Fore.CYAN}{'═' * 75}{Style.RESET_ALL}\n{Style.DIM}{Fore.CYAN}▸{Style.RESET_ALL} {Fore.WHITE}{text.upper()}{Style.RESET_ALL}\n{Fore.CYAN}{'═' * 75}{Style.RESET_ALL}")

    def print_dict(self, d, indent=0):
        tab = " " * 4 * indent
        for key, value in d.items():
            if isinstance(value, list):
                # Check if it's a list of cookie dicts (has 'name' key)
                if value and isinstance(value[0], dict) and 'name' in value[0]:
                    log(f"{tab}{Fore.CYAN}{key}:{Style.RESET_ALL}")
                    for cookie in value:
                        self.print_cookie(cookie, indent + 1)
                else:
                    # Regular list - truncate if longer than 4 items
                    log(f"{tab}{Fore.CYAN}{key}:{Style.RESET_ALL}")
                    display_items = value[:4] if len(value) > 4 else value
                    for item in display_items:
                        if isinstance(item, dict):
                            self.print_dict(item, indent + 1)
                        elif isinstance(item, list) and len(item) == 2:
                            # Handle [type, value] pairs like SAN entries
                            log(f"{tab}{self.tab}{Fore.CYAN}{item[0]}:{Style.RESET_ALL} {item[1]}")
                        else:
                            log(f"{tab}{self.tab}{item}")
                    if len(value) > 4:
                        log(f"{tab}{self.tab}{Style.DIM}... and {len(value) - 4} more{Style.RESET_ALL}")
            elif isinstance(value, dict):
                log(f"{tab}{Fore.CYAN}{key}:{Style.RESET_ALL}")
                self.print_dict(value, indent + 1)
            else:
                log(f"{tab}{Fore.CYAN}{key}:{Style.RESET_ALL} {value}")

    def print_cookie(self, cookie, indent=0):
        tab = " " * 4 * indent
        log(f"{tab}{Fore.YELLOW}{cookie.get('name', '?')}{Style.RESET_ALL}")
        for k, v in cookie.items():
            if k != "name":
                log(f"{tab}{self.tab}{Fore.CYAN}{k}:{Style.RESET_ALL} {v}")

    def print_table(self, rows, columns, summary_label, col_widths=None):
        """
        Renders tabular data cleanly.
        rows:      list of dicts e.g. [{"port": 80, "service": "http"}, ...]
        columns:   ordered list of keys to display e.g. ["port", "service"]
        col_widths: optional list of fixed widths, auto-calculated if None
        """
        if not rows:
            log(f"{Fore.YELLOW}  No results.{Style.RESET_ALL}")
            return

        if col_widths is None:
            col_widths = []
            for col in columns:
                max_val = max(len(str(row.get(col, ""))) for row in rows)
                col_widths.append(max(len(col), max_val) + 2)

        # Header
        header = ""
        for col, width in zip(columns, col_widths):
            header += f"{Fore.CYAN}{col.upper():<{width}}{Style.RESET_ALL}"
        log(header)

        # Divider
        log(f"{Fore.CYAN}{'─' * 75}{Style.RESET_ALL}")

        # Rows
        for row in rows:
            line = ""
            for col, width in zip(columns, col_widths):
                val = str(row.get(col, ""))
                line += f"{Fore.WHITE}{val:<{width}}{Style.RESET_ALL}"
            log(line)

        # Summary
        log(f"\n{Style.DIM}{len(rows)} {summary_label}(s){Style.RESET_ALL}")
    
    def message(self, text):
        log(f"{Style.DIM}{text}{Style.RESET_ALL}")


s = Special_Text()