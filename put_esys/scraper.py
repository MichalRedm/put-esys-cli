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
    def is_course_profile(tag):
        return (
            tag.name in ['div', 'dt'] and
            ('Profile w kursach' in tag.get_text() or 'Course profiles' in tag.get_text())
        )

    course_header = soup.find(is_course_profile)
    
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

def get_course_content(course_id, session=None):
    if not session:
        session = get_authenticated_session()
    
    if not session:
        return None, "Not authenticated."
    
    url = f"https://ekursy.put.poznan.pl/course/view.php?id={course_id}"
    try:
        resp = session.get(url)
        resp.raise_for_status()
    except Exception as e:
        return None, f"Failed to access course page: {e}"

    soup = BeautifulSoup(resp.text, 'html.parser')
    
    course_title = soup.find('h1').get_text(strip=True) if soup.find('h1') else "Unknown Course"
    
    sections = []
    # eKursy uses several formats, but sections are usually li.section
    for section_li in soup.select('li.section'):
        # Section name can be in various places depending on format
        name_tag = section_li.select_one('h3.sectionname')
        if not name_tag:
             # Try fallback for "General" or other structures
             name_tag = section_li.select_one('.section-title')
             
        if name_tag:
            section_name = name_tag.get_text(strip=True)
        else:
            section_id = section_li.get('id', '?')
            section_name = f"Section {section_id}"
        
        activities = []
        for activity_li in section_li.select('li.activity'):
             # Activity name and link
             a_tag = activity_li.select_one('div.activityname a')
             if a_tag:
                 # Clean up lambda2 specific hidden spans
                 for span in a_tag.find_all('span', class_='accesshide'):
                     span.decompose()
                 
                 name = a_tag.get_text(strip=True)
                 link = a_tag['href']
                 
                 # Try to identify type from classes (modtype_...)
                 activity_type = "unknown"
                 for cls in activity_li.get('class', []):
                     if cls.startswith('modtype_'):
                         activity_type = cls.replace('modtype_', '')
                         break
                 
                 activities.append({
                     'name': name,
                     'url': link,
                     'type': activity_type
                 })
        
        if activities or (name_tag and section_name):
            sections.append({
                'name': section_name,
                'activities': activities
            })
            
    return {
        'title': course_title,
        'sections': sections
    }, None
def get_quiz_info(quiz_id, session=None):
    if not session:
        session = get_authenticated_session()
    
    if not session:
        return None, "Not authenticated."
    
    url = f"https://ekursy.put.poznan.pl/mod/quiz/view.php?id={quiz_id}"
    try:
        resp = session.get(url)
        resp.raise_for_status()
    except Exception as e:
        return None, f"Failed to access quiz page: {e}"

    soup = BeautifulSoup(resp.text, 'html.parser')
    
    title = soup.find('h1').get_text(strip=True) if soup.find('h1') else "Unknown Quiz"
    
    grading_info = soup.select_one('.quizinfo p')
    grading_method = grading_info.get_text(strip=True) if grading_info else "Unknown"
    
    attempts = []
    # Attempts can be in a table or a list of cards in newer Moodle/Lambda themes
    # Check for cards first (as seen in the retrieved HTML)
    attempt_cards = soup.select('.quizreviewsummary')
    for card in attempt_cards:
        attempt_data = {}
        for row in card.select('tr'):
            th = row.find('th')
            td = row.find('td')
            if th and td:
                key = th.get_text(strip=True).lower()
                val = td.get_text(strip=True)
                attempt_data[key] = val
        
        # Look for attempt number in the heading above the table
        header = card.find_previous('h4', class_='card-title')
        if header:
            attempt_data['number'] = header.get_text(strip=True)
        
        attempts.append(attempt_data)
        
    # Check for buttons
    buttons = []
    for form in soup.select('.quizstartbuttondiv form'):
        btn = form.find('button')
        if btn:
            buttons.append({
                'text': btn.get_text(strip=True),
                'url': form.get('action')
            })

    return {
        'title': title,
        'grading_method': grading_method,
        'attempts': attempts,
        'buttons': buttons
    }, None
