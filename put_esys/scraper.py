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
    # Attempts can be in a table or a list of cards
    attempt_cards = soup.select('.generaltable.quizreviewsummary')
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
            
        # Look for Review link
        review_link = (
            card.find_parent('div', class_='card').find('a', string='Review') 
            if card.find_parent('div', class_='card') 
            else None
        )
        if not review_link:
             # Try finding in the next div
             review_link = card.find_next('a', string='Review')
             
        if review_link:
            href = review_link.get('href')
            attempt_data['review_url'] = href
            import re
            match = re.search(r'attempt=(\d+)', href)
            if match:
                attempt_data['id'] = match.group(1)
        
        # If in progress and no ID found, try to find it in the "Continue" button
        if attempt_data.get('status') == 'In progress' and not attempt_data.get('id'):
            continue_form = soup.select_one('.quizstartbuttondiv form')
            if continue_form:
                # We might need to follow the redirect to get the attempt ID
                action = continue_form.get('action')
                if action:
                    data = {
                        inp.get('name'): inp.get('value') 
                        for inp in continue_form.find_all('input')
                    }
                    try:
                        # Use allow_redirects=False to see the Location header
                        # without actually loading the whole page
                        r = session.post(action, data=data, allow_redirects=False)
                        loc = r.headers.get('Location', '')
                        import re
                        match = re.search(r'attempt=(\d+)', loc)
                        if match:
                            attempt_data['id'] = match.group(1)
                    except Exception:
                        pass

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

def get_quiz_attempt(quiz_id, attempt_id, session=None):
    if not session:
        session = get_authenticated_session()
    
    if not session:
        return None, "Not authenticated."
    
    # Try review.php first (for finished attempts)
    url = f"https://ekursy.put.poznan.pl/mod/quiz/review.php?attempt={attempt_id}&cmid={quiz_id}"
    try:
        resp = session.get(url)
        resp.raise_for_status()
        
        # If review.php redirects back to view.php, it might be in progress
        # or we might need attempt.php
        if 'mod/quiz/view.php' in resp.url:
             url = (
                 f"https://ekursy.put.poznan.pl/mod/quiz/attempt.php"
                 f"?attempt={attempt_id}&cmid={quiz_id}"
             )
             resp = session.get(url)
             resp.raise_for_status()
             
    except Exception as e:
        return None, f"Failed to access attempt page: {e}"

    soup = BeautifulSoup(resp.text, 'html.parser')
    
    questions = []
    for que_div in soup.select('.que'):
        q_no_el = que_div.select_one('.qno')
        q_no = q_no_el.get_text(strip=True) if q_no_el else "?"
        
        q_state_el = que_div.select_one('.state')
        q_state = q_state_el.get_text(strip=True) if q_state_el else ""
        
        q_text_el = que_div.select_one('.qtext')
        q_text_html = str(q_text_el) if q_text_el else ""
        
        # Extract answer
        # Essay
        answer_div = (
            que_div.select_one('.qtype_essay_response') or 
            que_div.select_one('.answer')
        )
        
        # For in-progress attempts, it might be in a textarea
        textarea = que_div.find('textarea')
        if textarea:
             # If it's a textarea, it's already "plain" text but usually with HTML 
             # entities or formatting.
             answer_html = textarea.get_text(strip=True)
        else:
             answer_html = str(answer_div) if answer_div else "No answer found"
        
        # Multiple choice / true-false
        # If it's a list of options
        options = []
        for option_div in que_div.select('.answer > div'):
             label = option_div.find('label')
             if label:
                  is_selected = (
                      'checked' in str(option_div) or 
                      'selected' in str(option_div)
                  )
                  options.append({
                       'text': label.get_text(strip=True),
                       'selected': is_selected
                  })
        
        if options:
             # Convert options to a simple HTML list for markdownify to handle
             opt_list = []
             for opt in options:
                  marker = "<b>[x]</b>" if opt['selected'] else "[ ]"
                  opt_list.append(f"<li>{marker} {opt['text']}</li>")
             answer_html = f"<ul>{''.join(opt_list)}</ul>"

        questions.append({
            'number': q_no,
            'state': q_state,
            'text': q_text_html,
            'answer': answer_html
        })
        
    return {
        'quiz_id': quiz_id,
        'attempt_id': attempt_id,
        'questions': questions
    }, None
