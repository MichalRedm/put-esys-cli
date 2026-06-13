import requests
import urllib3
from rich.console import Console

# Disable SSL verification globally
orig_request = requests.Session.request


def patched_request(self, method, url, *args, **kwargs):
    kwargs["verify"] = False
    return orig_request(self, method, url, *args, **kwargs)


requests.Session.request = patched_request
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Patch rich Console.print to support 'err' parameter
orig_print = Console.print


def patched_print(self, *args, **kwargs):
    if "err" in kwargs:
        err = kwargs.pop("err")
        if err:
            if not getattr(self, "_is_stderr_console", False):
                if not hasattr(Console, "_stderr_console"):
                    Console._stderr_console = Console(stderr=True)
                    Console._stderr_console._is_stderr_console = True
                return Console._stderr_console.print(*args, **kwargs)
    return orig_print(self, *args, **kwargs)


Console.print = patched_print

