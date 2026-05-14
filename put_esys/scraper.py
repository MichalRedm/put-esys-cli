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
            # Check if we are actually logged in (look for logout or profile links)
            in_dashboard = "Kokpit" in resp.text or "Dashboard" in resp.text
            if "login/logout.php" not in resp.text and not in_dashboard:
                 msg = "Could not find user session in eKursy (Dashboard). Try logging in again."
                 return None, msg
            msg = (
                "Could not identify User ID from dashboard. "
                "The page structure might have changed."
            )
            return None, msg
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
    # Strategy A: Look for any course links (Profile or Dashboard)
    # 1. Profile page style (user/view.php?id=USER_ID&course=COURSE_ID)
    profile_links = soup.find_all('a', href=re.compile(r'user/view\.php\?.*course=(\d+)'))
    for link in profile_links:
        href = link['href']
        cid_match = re.search(r'course=(\d+)', href)
        if cid_match:
            cid = cid_match.group(1)
            title = link.get_text(strip=True)
            existing_ids = [c['id'] for c in courses]
            is_valid_title = title and title not in ["Zobacz więcej", "View", "Kurs"]
            if is_valid_title and cid not in existing_ids:
                courses.append({
                    'id': cid,
                    'title': title,
                    'url': f"https://ekursy.put.poznan.pl/course/view.php?id={cid}"
                })

    # 2. Direct course links (course/view.php?id=COURSE_ID)
    direct_links = soup.find_all('a', href=re.compile(r'course/view\.php\?.*id=(\d+)'))
    for link in direct_links:
        href = link['href']
        # For course/view.php, the 'id' parameter IS the course ID
        cid_match = re.search(r'id=(\d+)', href)
        if cid_match:
            cid = cid_match.group(1)
            title = link.get_text(strip=True)
            existing_ids = [c['id'] for c in courses]
            is_valid_title = title and title not in ["Zobacz więcej", "View", "Kurs"]
            if is_valid_title and cid not in existing_ids:
                courses.append({
                    'id': cid,
                    'title': title,
                    'url': f"https://ekursy.put.poznan.pl/course/view.php?id={cid}"
                })
    
    # Strategy C: Look in the navigation menu (Dashboard) if Strategy A/B didn't find much
    if not courses:
        try:
            dashboard_resp = session.get("https://ekursy.put.poznan.pl/")
            dashboard_soup = BeautifulSoup(dashboard_resp.text, 'html.parser')
            # Look for any links to course/view.php
            nav_links = dashboard_soup.find_all('a', href=re.compile(r'course/view.php\?id=(\d+)'))
            for link in nav_links:
                href = link['href']
                cid_match = re.search(r'id=(\d+)', href)
                if cid_match:
                    cid = cid_match.group(1)
                    title = link.get_text(strip=True)
                    if title and len(title) > 3 and cid not in [c['id'] for c in courses]:
                        courses.append({
                            'id': cid,
                            'title': title,
                            'url': f"https://ekursy.put.poznan.pl/course/view.php?id={cid}"
                        })
        except Exception:
            pass
    
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

def download_resource(url, session=None):
    """Download a resource (file) from a URL."""
    if not session:
        from .auth import get_authenticated_session
        session = get_authenticated_session()
        
    if not session:
        raise Exception("Not authenticated.")
        
    response = session.get(url, stream=True)
    response.raise_for_status()
    return response
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
    
    # Extract sesskey
    sesskey_match = re.search(r'"sesskey":"([^"]+)"', resp.text)
    sesskey = sesskey_match.group(1) if sesskey_match else None
    if not sesskey:
        # Fallback: look for sesskey in logout link or hidden inputs
        logout_link = soup.find('a', href=re.compile(r'sesskey=([^&]+)'))
        if logout_link:
            sesskey = re.search(r'sesskey=([^&]+)', logout_link['href']).group(1)

    title = soup.find('h1').get_text(strip=True) if soup.find('h1') else "Unknown Quiz"
    
    # Extract intro text
    intro_div = soup.find(id='intro') or soup.select_one('.quizdescription')
    intro = str(intro_div) if intro_div else ""
    
    # Extract all info paragraphs (Time limit, Grading method, etc.)
    info_paragraphs = [p.get_text(strip=True) for p in soup.select('.quizinfo p')]
    
    # Also check for availability info
    avail_info = soup.select_one('.availabilityinfo')
    if avail_info:
        info_paragraphs.append(avail_info.get_text(strip=True))

    grading_method = "Unknown"
    for p in info_paragraphs:
        if "Grading method" in p or "Metoda oceniania" in p:
            grading_method = p.split(":")[-1].strip()
            break
        
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
        'intro': intro,
        'info': info_paragraphs,
        'grading_method': grading_method,
        'attempts': attempts,
        'buttons': buttons,
        'sesskey': sesskey
    }, None

def start_quiz_attempt(quiz_id, session=None):
    if not session:
        session = get_authenticated_session()
    
    if not session:
        return None, "Not authenticated."

    # 1. Get the quiz page to find the sesskey and start button
    url = f"https://ekursy.put.poznan.pl/mod/quiz/view.php?id={quiz_id}"
    try:
        resp = session.get(url)
        resp.raise_for_status()
    except Exception as e:
        return None, f"Failed to access quiz page: {e}"

    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # 2. Extract sesskey
    sesskey_match = re.search(r'"sesskey":"([^"]+)"', resp.text)
    sesskey = sesskey_match.group(1) if sesskey_match else None
    if not sesskey:
        logout_link = soup.find('a', href=re.compile(r'sesskey=([^&]+)'))
        if logout_link:
            sesskey = re.search(r'sesskey=([^&]+)', logout_link['href']).group(1)
            
    if not sesskey:
        return None, "Could not find session key (sesskey). Page structure might have changed."

    # 3. Check if there's an active "Continue" button instead of "Start"
    # If so, we should just return the existing attempt ID
    continue_form = soup.select_one('.quizstartbuttondiv form')
    if continue_form:
        btn = continue_form.find('button')
        if btn and ("kontynuuj" in btn.get_text().lower() or "continue" in btn.get_text().lower()):
            # Extract attempt ID from the form if possible, or just follow it
            action = continue_form.get('action')
            data = {
                inp.get('name'): inp.get('value') 
                for inp in continue_form.find_all('input')
                if inp.get('name')
            }
            # Moodle often redirects to attempt.php?attempt=ID
            r = session.post(action, data=data, allow_redirects=True)
            match = re.search(r'attempt=(\d+)', r.url)
            if match:
                return match.group(1), None
    
    # 4. Start the attempt
    # Typically it's a POST to view.php?id=QUIZ_ID with startattempt=1 and sesskey
    data = {
        'cmid': quiz_id,
        'sesskey': sesskey,
        'startattempt': '1'
    }
    
    try:
        # Moodle uses a redirect after starting
        resp = session.post(url, data=data, allow_redirects=True)
        resp.raise_for_status()
        
        # The URL should now be something like .../mod/quiz/attempt.php?attempt=12345
        match = re.search(r'attempt=(\d+)', resp.url)
        if match:
            return match.group(1), None
        else:
            if "Password" in resp.text:
                return None, "This quiz requires a password. Please start it in the browser."
            return None, f"Started attempt but could not find attempt ID in URL: {resp.url}"
            
    except Exception as e:
        return None, f"Failed to start attempt: {e}"

def get_quiz_attempt(quiz_id, attempt_id, session=None):
    if not session:
        session = get_authenticated_session()
    
    if not session:
        return None, "Not authenticated."
    
    # If attempt_id is not provided, try to find the latest one
    if attempt_id is None:
        info, error = get_quiz_info(quiz_id, session)
        if error:
            return None, error
        
        # Priority 1: In progress attempt
        in_progress = [a for a in info['attempts'] if a.get('status') == 'In progress']
        if in_progress and in_progress[0].get('id'):
            attempt_id = in_progress[0]['id']
        # Priority 2: Latest finished attempt
        elif info['attempts'] and info['attempts'][0].get('id'):
            attempt_id = info['attempts'][0]['id']
        else:
            return None, "Could not find any quiz attempts. Start one in the browser first."
    
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

        # Extract attachments and check if they are allowed
        attachments = []
        allows_attachments = False
        att_div = que_div.select_one('.attachments')
        if att_div:
             # If att_div has children (like h4 label or ul), it means attachments are allowed
             # In finished reviews, an empty allowed attachments area has an h4 and an empty ul.
             # In in-progress attempts, it has a filemanager div.
             # A div with NO allowed attachments is just <div class="attachments"></div> (empty)
             if att_div.find(recursive=False) or att_div.get_text(strip=True):
                  allows_attachments = True
             
             for att_link in att_div.select('a'):
                  att_name = att_link.get_text(strip=True)
                  att_url = att_link.get('href')
                  if att_name and att_url and not att_url.startswith('#'):
                       attachments.append({
                            'name': att_name,
                            'url': att_url
                       })

        # Identify question type
        q_type = "unknown"
        for cls in que_div.get('class', []):
             is_qtype = cls.startswith('qtype_')
             is_known = cls in ['essay', 'multichoice', 'truefalse', 'shortanswer']
             if is_qtype or is_known:
                  q_type = cls.replace('qtype_', '')
                  break

        questions.append({
            'number': q_no,
            'state': q_state,
            'type': q_type,
            'allows_attachments': allows_attachments,
            'text': q_text_html,
            'answer': answer_html,
            'attachments': attachments
        })
        
    return {
        'quiz_id': quiz_id,
        'attempt_id': attempt_id,
        'questions': questions
    }, None

def save_quiz_answer(session, quiz_id, attempt_id, question_number, new_text):
    """Save an answer for a specific question in an in-progress attempt."""
    from bs4 import BeautifulSoup
    
    # 1. Fetch the attempt page to get current values and hidden fields
    url = f"https://ekursy.put.poznan.pl/mod/quiz/attempt.php?attempt={attempt_id}&cmid={quiz_id}"
    r = session.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # 2. Extract the form
    form = soup.select_one('#responseform')
    if not form:
        raise Exception("Could not find the quiz form. Is the attempt in progress?")
    
    data = {}
    
    # 3. Extract hidden fields and all inputs/textareas to maintain state
    # We want to replicate exactly what the browser would send
    for inp in form.find_all(['input', 'textarea']):
        name = inp.get('name')
        if not name:
            continue
            
        if inp.name == 'textarea':
            data[name] = inp.get_text()
        elif inp.get('type') == 'checkbox':
            if inp.has_attr('checked'):
                data[name] = inp.get('value', '1')
        elif inp.get('type') == 'radio':
            if inp.has_attr('checked'):
                data[name] = inp.get('value')
        else:
            data[name] = inp.get('value', '')

    # 4. Map question_number to its input name
    target_name = None
    for que_div in soup.select('.que'):
        q_no_el = que_div.select_one('.qno')
        if q_no_el and q_no_el.get_text(strip=True) == str(question_number):
            textarea = que_div.select_one('textarea')
            if textarea:
                target_name = textarea.get('name')
            break
            
    if not target_name:
        raise Exception(f"Could not find input for question {question_number}")
        
    # 5. Update the target answer
    data[target_name] = new_text
    
    # 6. Add 'next' to trigger save (Moodle saves on navigation)
    data['next'] = '1'
    
    # 7. Post to processattempt.php
    post_url = form.get('action')
    if not post_url.startswith('http'):
        from urllib.parse import urljoin
        post_url = urljoin(url, post_url)
        
    r = session.post(post_url, data=data)
    r.raise_for_status()
    return True
