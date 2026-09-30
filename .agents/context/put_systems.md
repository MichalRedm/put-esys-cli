# PUT Electronic Systems Specification

This document details the external electronic systems of Poznań University of Technology (PUT) supported by `put-esys-cli`, including endpoints, authentication flows, session handling, and data structures.

---

## 1. Central SSO Authentication (`elogin.put.poznan.pl`)

PUT uses a centralized Single Sign-On (SSO) gateway.

### SSO Flow
```
1. Client requests protected system (e.g. eKursy)
2. Redirected to https://elogin.put.poznan.pl/app/authorize?system=ekursy.esys.put.poznan.pl
3. Client extracts csrf_token from the initial HTML response form
4. Client POSTs credentials to login URL:
   - login: <username or email>
   - password: <password>
   - csrf_token: <csrf_token>
   - send: ""
5. eLogin responds with an HTML page containing an auto-submitting POST form:
   - form#redirectForm or form[name="frm"]
6. Client extracts hidden input values and POSTs to form.action
7. Process repeats (up to 5 redirects) until target service responds with session cookies
8. For eKursy, successful login yields the 'MoodleSession' cookie
```

### Local Storage & Persistence
- Configuration directory is determined dynamically using `appdirs.user_config_dir("put-esys")`:
  - **Linux / macOS**: `~/.config/put-esys/`
  - **Windows**: `%APPDATA%\put-esys\`
- `config.json`: Stored username and password (when configured via `put-esys config set`).
- `session_cookies.json`: Stored cookie dictionary (including `MoodleSession`).

---

## 2. eKursy Platform (Moodle)

eKursy (`https://ekursy.put.poznan.pl/`) is the university's Moodle-based Learning Management System.

### Key Endpoints
| Component | URL Pattern | Description |
| :--- | :--- | :--- |
| **Course View** | `https://ekursy.put.poznan.pl/course/view.php?id=<id>` | Sections, resource links, activities |
| **Course Categories** | `https://ekursy.put.poznan.pl/course/index.php?categoryid=<id>` | Hierarchy of faculties, programs, and semesters |
| **Course Search** | `https://ekursy.put.poznan.pl/course/search.php?search=<query>` | Global course search across all categories |
| **Course Enrolment** | `https://ekursy.put.poznan.pl/enrol/index.php?id=<id>` | Self-enrolment landing page and password form |
| **Assignment View** | `https://ekursy.put.poznan.pl/mod/assign/view.php?id=<id>` | Status, due date, submission files |
| **Assignment Edit** | `https://ekursy.put.poznan.pl/mod/assign/view.php?id=<id>&action=editsubmission` | File upload form and text area |
| **Quiz View** | `https://ekursy.put.poznan.pl/mod/quiz/view.php?id=<id>` | Attempts, status, timing rules |
| **Quiz Attempt** | `https://ekursy.put.poznan.pl/mod/quiz/attempt.php?attempt=<id>` | Questions, answer inputs, submission controls |
| **Resource Download** | `https://ekursy.put.poznan.pl/mod/resource/view.php?id=<id>` | Direct link or landing page to `pluginfile.php` |

### Course Self-Enrolment Protocol (`enrol/index.php`)
1. Visiting `course/view.php?id=<id>` while unenrolled redirects to `enrol/index.php?id=<id>`.
2. The page inspects whether self-enrolment is allowed. If disabled, a warning notification is displayed.
3. If self-enrolment is enabled, the form exposes:
   - `id`: Target course ID
   - `instance`: Enrolment plugin instance ID
   - `sesskey`: Session token
   - `enrolpassword`: Enrolment key/password (if required)
4. POSTing this payload to `enrol/index.php` enrolls the user and redirects to `course/view.php?id=<id>`. If the password is invalid, Moodle returns HTTP 200 with an `.alert-danger` / `.error` element.


### Moodle File Upload Protocol (`draftfiles.php`)
1. Accessing the assignment edit page exposes a hidden input: `files_filemanager` containing a numeric `draftitemid`.
2. Files cannot be POSTed directly to the assignment endpoint; they must first be uploaded to the draft repository (`/repository/repository_ajax.php?action=upload`) associated with the `draftitemid`.
3. The main assignment form is then submitted containing the `draftitemid` reference and any online submission text (`onlinetext_editor[text]`).

### Quiz Offline Markdown Dump & Sync Protocol
1. `put-esys quiz dump <quiz_id> -o <path>.md`: Parses attempt questions and generates a structured Markdown document where each question block contains question text and editable answer blocks.
2. The user or AI agent modifies the answers in the file.
3. `put-esys quiz sync <quiz_id> -f <path>.md`: Reads the file, computes diffs against current server values, maps question inputs (e.g. radios, text fields, essay editors), and sends form submissions in batch.

---

## 3. Student Mail (`poczta.put.poznan.pl`)

PUT provides email accounts for students and faculty.

### Network Protocols & Hostnames
- **IMAP Server**: `mail.put.poznan.pl` (Port `993`, SSL/TLS)
- **SMTP Server**: `mail.put.poznan.pl` (Port `465`, SSL/TLS)
- **Authentication**: Uses the student's PUT email address (e.g. `firstname.lastname@student.put.poznan.pl`) and password.

### Mail Operations
- **Folder Traversal**: UTF-7 encoded IMAP folder names (e.g. `INBOX`, `Sent`, `Trash`).
- **Searching**: Standard IMAP search filters (`FROM`, `SUBJECT`, `TEXT`, `SINCE`).
- **Attachments**: Parsed from multipart MIME messages and saved directly to disk.
