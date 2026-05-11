import requests
from bs4 import BeautifulSoup
from .config import save_session, load_session
from urllib.parse import urljoin

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class AuthError(Exception):
    pass

def authenticate(username, password):
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # 1. elogin authorize
    resp = session.get("https://elogin.put.poznan.pl/app/authorize?system=ekursy.esys.put.poznan.pl")
    soup = BeautifulSoup(resp.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'}).get('value')
    
    # 2. elogin login POST
    resp = session.post(resp.url, data={'login': username, 'password': password, 'csrf_token': csrf_token, 'send': ''}, headers={"Referer": resp.url})

    # 3. Follow all auto-submit forms
    # We loop up to 5 times to avoid infinite recursion
    for _ in range(5):
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Look for any form that is submitted via JS (common in SSO)
        # Form might have id 'redirectForm' or name 'frm' or just be the only form
        form = soup.find('form', {'id': 'redirectForm'}) or soup.find('form', {'name': 'frm'})
        
        if not form and "document.frm.submit()" in resp.text:
             form = soup.find('form')
             
        if form:
            action = form.get('action')
            if not action:
                break
            action_url = urljoin(resp.url, action)
            
            form_data = {inp.get('name'): inp.get('value', '') for inp in form.find_all('input', {'type': 'hidden'}) if inp.get('name')}
            
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
        raise AuthError(f"Authentication failed. MoodleSession not found. Final URL: {resp.url}")

def get_authenticated_session():
    cookies = load_session()
    if not cookies:
        return None
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.cookies.update(cookies)
    return session

def ensure_authenticated_session():
    """
    Ensures we have a valid session. If not, tries to log in using stored credentials.
    """
    from .config import load_credentials
    
    session = get_authenticated_session()
    
    # Check if session is valid by hitting the dashboard
    is_valid = False
    if session:
        try:
            resp = session.get("https://ekursy.put.poznan.pl/", timeout=10)
            if "Logowanie" not in resp.text and "login" not in resp.url:
                is_valid = True
        except:
            pass
            
    if is_valid:
        return session
        
    # Not valid, try to log in using stored credentials
    creds = load_credentials()
    if not creds:
        return None
        
    try:
        if authenticate(creds['username'], creds['password']):
            return get_authenticated_session()
    except:
        pass
        
    return None
