import requests
from bs4 import BeautifulSoup
from put_esys.auth import get_authenticated_session

def find_in_progress_attempt(quiz_id):
    session = get_authenticated_session()
    url = f"https://ekursy.put.poznan.pl/mod/quiz/view.php?id={quiz_id}"
    resp = session.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Find the startattempt form
    form = soup.select_one('.quizstartbuttondiv form')
    if not form:
        print("No start/continue form found.")
        return
        
    action = form.get('action')
    data = {inp.get('name'): inp.get('value') for inp in form.find_all('input')}
    
    # Post and don't allow redirect to see where it goes
    resp = session.post(action, data=data, allow_redirects=False)
    print(f"Status: {resp.status_code}")
    print(f"Location: {resp.headers.get('Location')}")

if __name__ == "__main__":
    find_in_progress_attempt(2129129)
