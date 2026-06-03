import requests
import urllib3

# Disable SSL verification globally
orig_request = requests.Session.request

def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return orig_request(self, method, url, *args, **kwargs)

requests.Session.request = patched_request
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
