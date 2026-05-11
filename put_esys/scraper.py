import re
from bs4 import BeautifulSoup
from .auth import get_authenticated_session

def get_ekursy_courses(session=None):
    if not session:
        session = get_authenticated_session()
    
    if not session:
        return None, "Not authenticated. Please run 'login' or 'config set' first."
    
    # 1. Get dashboard to find user ID
    try:
        resp = session.get("https://ekursy.put.poznan.pl/")
        resp.raise_for_status()
    except Exception as e:
        return None, f"Failed to access eKursy dashboard: {e}"

    if "Logowanie" in resp.text and "login" in resp.url:
        return None, "Session expired. Please login again."

    # Look for userId in script tags or common locations
    user_id_match = re.search(r'"userId":(\d+)', resp.text)
    if not user_id_match:
        # Try to find user profile link in the menu
        soup = BeautifulSoup(resp.text, 'html.parser')
        profile_link = soup.find('a', href=re.compile(r'user/profile.php\?id=(\d+)'))
        if profile_link:
            user_id = re.search(r'id=(\d+)', profile_link['href']).group(1)
        else:
            # Check if we are actually logged in
            if "Michał Redmer" not in resp.text and "Kokpit" not in resp.text:
                 return None, "Could not find user session in eKursy (Dashboard)."
            return None, "Could not identify User ID from dashboard."
    else:
        user_id = user_id_match.group(1)
    
    # 2. Navigate to Profile page with all courses shown
    profile_url = f"https://ekursy.put.poznan.pl/user/profile.php?id={user_id}&showallcourses=1"
    try:
        resp = session.get(profile_url)
        resp.raise_for_status()
    except Exception as e:
        return None, f"Failed to access eKursy profile: {e}"

    soup = BeautifulSoup(resp.text, 'html.parser')
    
    courses = []
    
    # In the profile tree, courses are listed under "Szczegóły kursów" or "Course profiles"
    # Find the header first
    course_header = soup.find(lambda tag: tag.name in ['h3', 'dt'] and ('Profile w kursach' in tag.get_text() or 'Course profiles' in tag.get_text()))
    
    if not course_header:
        # Search all <li> elements for course links as fallback
        links = soup.find_all('a', href=re.compile(r'course/view.php\?id=(\d+)|course=(\d+)'))
        for link in links:
             href = link['href']
             course_id_match = re.search(r'id=(\d+)|course=(\d+)', href)
             if course_id_match:
                 cid = course_id_match.group(1) or course_id_match.group(2)
                 title = link.get_text(strip=True)
                 if title and title != "Zobacz więcej" and cid not in [c['id'] for c in courses]:
                     courses.append({
                         'id': cid,
                         'title': title,
                         'url': f"https://ekursy.put.poznan.pl/course/view.php?id={cid}"
                     })
    else:
        # Found the header, look for the list in the next sibling or parent's sibling
        dd = course_header.find_next('dd') or course_header.parent.find_next('dd')
        if dd:
            links = dd.find_all('a', href=True)
            for link in links:
                href = link['href']
                course_id_match = re.search(r'[&?]course=(\d+)', href)
                if course_id_match:
                    course_id = course_id_match.group(1)
                    title = link.get_text(strip=True)
                    if title and title != "Zobacz więcej":
                        courses.append({
                            'id': course_id,
                            'title': title,
                            'url': f"https://ekursy.put.poznan.pl/course/view.php?id={course_id}"
                        })
    
    return courses, None
