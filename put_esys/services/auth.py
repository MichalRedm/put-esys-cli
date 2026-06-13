from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .config import load_credentials, load_session, save_session

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class SessionExpiredError(Exception):
    pass


class AuthError(Exception):
    pass


def authenticate(username, password) -> bool:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # 1. elogin authorize
    resp = session.get(
        "https://elogin.put.poznan.pl/app/authorize?system=ekursy.esys.put.poznan.pl"
    )
    soup = BeautifulSoup(resp.text, "html.parser")
    csrf_token = soup.find("input", {"name": "csrf_token"}).get("value")

    # 2. elogin login POST
    login_url = resp.url
    resp = session.post(
        login_url,
        data={"login": username, "password": password, "csrf_token": csrf_token, "send": ""},
        headers={"Referer": resp.url},
    )

    # 3. Follow all auto-submit forms
    for _ in range(5):
        soup = BeautifulSoup(resp.text, "html.parser")
        form = (
            soup.find("form", {"id": "redirectForm"})
            or soup.find("form", {"name": "frm"})
            or soup.find("form")
        )

        if form:
            action = form.get("action")
            if not action:
                break
            action_url = urljoin(resp.url, action)

            form_data = {
                inp.get("name"): inp.get("value", "")
                for inp in form.find_all("input", {"type": "hidden"})
                if inp.get("name")
            }

            if not form_data:
                form_data = {
                    inp.get("name"): inp.get("value", "")
                    for inp in form.find_all("input")
                    if inp.get("name")
                }

            # Post the form
            resp = session.post(action_url, data=form_data, headers={"Referer": resp.url})
        else:
            break

    # Final check
    all_cookies = {cookie.name: cookie.value for cookie in session.cookies}

    if "MoodleSession" in all_cookies or "ekursy.put.poznan.pl" in resp.url:
        save_session(all_cookies)
        return True
    else:
        # Check for error message in the final page if it failed
        soup = BeautifulSoup(resp.text, "html.parser")
        error_msg = soup.find(class_=lambda x: x and "alert" in x)
        error_text = error_msg.get_text(strip=True) if error_msg else "Unknown error"
        raise AuthError(f"Authentication failed: {error_text}. Final URL: {resp.url}")


def get_authenticated_session() -> Optional[requests.Session]:
    cookies = load_session()
    if not cookies:
        return None
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.cookies.update(cookies)

    def check_session_hook(response, *args, **kwargs):
        if "elogin.put.poznan.pl" in response.url or "login/index.php" in response.url:
            raise SessionExpiredError(
                "eKursy session expired. Please run 'put-esys login' to refresh your session."
            )
        content_type = response.headers.get("Content-Type", "")
        if "text/html" in content_type or "application/xhtml+xml" in content_type:
            if "Logowanie" in response.text and "login" in response.url:
                raise SessionExpiredError(
                    "eKursy session expired. Please run 'put-esys login' to refresh your session."
                )

    session.hooks["response"].append(check_session_hook)
    return session


def ensure_authenticated_session() -> Optional[requests.Session]:
    """
    Ensures we have a valid session. If not, tries to log in using stored credentials.
    """
    session = get_authenticated_session()

    # Check if session is valid by hitting the dashboard
    is_valid = False
    if session:
        try:
            resp = session.get("https://ekursy.put.poznan.pl/", timeout=10)
            if "Logowanie" not in resp.text and "login" not in resp.url:
                is_valid = True
        except Exception:
            pass

    if is_valid:
        return session

    # Not valid, try to log in using stored credentials
    creds = load_credentials()
    if not creds:
        return None

    try:
        if authenticate(creds["username"], creds["password"]):
            return get_authenticated_session()
    except Exception:
        pass

    return None
