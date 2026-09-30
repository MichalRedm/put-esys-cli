# Scraping & Authentication Standards

> [!IMPORTANT]
> **Trigger Paths**: `put_esys/services/**`
> **When to Read**: MUST be read before implementing or updating authentication routines, HTTP scrapers, Moodle forms, or mail clients.

This document establishes standards and guardrails for scraping PUT electronic systems, handling SSO redirects, managing session state, and interacting with Moodle endpoints.

---

## 1. Core Principles & Stack

- **HTTP Client**: Use `requests.Session()` with persistent headers, standard browser `User-Agent`, and automatic redirect following.
- **SSO Traversal**: Authentication against `elogin.put.poznan.pl` requires extracting hidden `csrf_token` fields and iteratively following auto-submitting POST forms (`redirectForm`, `frm`).
- **Session Caching**: Never re-authenticate on every request. Persist valid session cookies (`MoodleSession`) in local user config directories (`appdirs.user_config_dir("put-esys")`).
- **Resilient Parsing**: Parse HTML using `BeautifulSoup(html, "html.parser")`. Rely on semantic attributes (e.g. `form[action*="assign"]`, `input[name]`) rather than deeply nested CSS selectors that break across Moodle updates.
- **Moodle Upload Protocol**: Assignment and quiz file uploads in Moodle require obtaining a `draftitemid`, uploading files to the Moodle file repository (`repository/repository_ajax.php` or `draftfiles.php`), and submitting the final form with the draft ID.

---

## 2. Declarative Code Standards (Golden Patterns)

### SSO Redirect Auto-Submit Loop
```python
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Follow all intermediate auto-submit forms until target system session is established
for _ in range(5):
    soup = BeautifulSoup(resp.text, "html.parser")
    form = (
        soup.find("form", {"id": "redirectForm"})
        or soup.find("form", {"name": "frm"})
        or soup.find("form")
    )
    if not form or not form.get("action"):
        break

    action_url = urljoin(resp.url, form.get("action"))
    form_data = {
        inp.get("name"): inp.get("value", "")
        for inp in form.find_all("input")
        if inp.get("name")
    }
    resp = session.post(action_url, data=form_data, headers={"Referer": resp.url})
```

### Checking for Expired Session and Graceful Re-authentication
```python
def check_session_valid(resp: requests.Response) -> bool:
    if "elogin.put.poznan.pl" in resp.url:
        return False
    return True
```

---

## 3. Anti-Pattern & Pitfall Traps

| Anti-Pattern Trap | Why It Fails | Golden Pattern |
| :--- | :--- | :--- |
| **Assuming single redirect for SSO login** | PUT eLogin bounces through multiple SAML/POST auto-submitting forms before setting Moodle session cookies. | Iterate up to 5 times extracting and submitting hidden form fields until landing on the target domain. |
| **Re-authenticating on every CLI invocation** | Triggers rate limiting on PUT SSO servers and adds unnecessary network latency. | Save session cookies locally and reuse them until a redirect to eLogin is detected. |
| **Brittle class-based CSS selectors** | Moodle class names change between major versions or themes, breaking scrapers. | Select elements by input names, action URLs, IDs, or stable ARIA/semantic attributes. |
| **Direct POST of files without Moodle draft ID** | Moodle ignores uploaded files if they are not staged in an active user draft area. | Retrieve the Moodle draft item ID from the edit submission form, upload to draft area, then submit. |
| **Omitting timeout on network requests** | Network disruptions or hung connections can freeze background AI tasks indefinitely. | Always specify explicit timeouts on `session.get()` and `session.post()` (e.g. `timeout=30`). |
| **Storing credentials in repository files** | Commits sensitive passwords and tokens into version control. | Store credentials strictly in the OS user config directory via `appdirs` or retrieve via environment variables. |
