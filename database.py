"""
Smart FAQ Assistant - Database Layer
Provides SQLite database management, schema initialization, default admin creation,
sample college FAQ seeding, and CRUD operations for FAQs and analytics.
"""

import os
import sqlite3
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash

DB_FILE = os.environ.get("DATABASE_PATH", "faq_assistant.db")

SAMPLE_FAQS = [
    # -------------------------------------------------------------
    # 1. Admissions
    # -------------------------------------------------------------
    {
        "category": "Admissions",
        "question": "How can I apply for admission and what is the admission procedure?",
        "answer": "[DEMO DATA] Applications for first-year B.Tech admission can be submitted online through the College Admission Portal (www.demo-college.edu/admissions) or via the State Centralized Admission Process (CAP). The application procedure involves: (1) Registering online with your email and mobile number, (2) Filling in personal and academic details, (3) Uploading 10th/12th mark sheets, entrance exam scorecards (JEE/State CET), and photo ID, (4) Paying the application fee online, and (5) Submitting the application and tracking seat allotment rounds. For guidance, visit the Admissions Cell in Room 102, Administrative Block or email admissions@demo-college.edu.",
        "keywords": "how can i apply for admission what is the admission process admission procedure application process how to apply online admission registration steps fresh admission form apply btech entrance cap rounds",
        "is_demo": 1
    },
    {
        "category": "Admissions",
        "question": "What are the eligibility criteria for B.Tech CSE admission?",
        "answer": "[DEMO DATA] For B.Tech Computer Science & Engineering (CSE), candidates must have passed 10+2 with Physics, Mathematics, and Chemistry/Computer Science with a minimum of 60% aggregate marks (55% for reserved categories). Admission is based on State CET or JEE Main scores. Candidates must also participate in the Centralized Admission counseling rounds. For official cutoffs, contact the Admissions Cell at admissions@demo-college.edu.",
        "keywords": "eligibility criteria btech cse admission eligibility 12th percentage cutoff entrance exam jee cet requirements computer science qualifying marks minimum aggregate",
        "is_demo": 1
    },
    {
        "category": "Admissions",
        "question": "Which documents are required during college admission verification?",
        "answer": "[DEMO DATA] The mandatory documents for admission verification are: (1) 10th and 12th original mark sheets with 3 self-attested photocopies, (2) School/College Leaving or Transfer Certificate (TC), (3) Migration Certificate, (4) Entrance Exam Scorecard (JEE Main / State CET), (5) Caste/Category Certificate and Non-Creamy Layer (if applicable), (6) Domicile/Nationality Certificate, (7) 4 recent passport-size photographs, and (8) Government Photo ID (Aadhaar Card). Verification is conducted at Room 102, Administrative Block.",
        "keywords": "which documents are required for admission what documents are required during college admission verification admission document checklist certificates needed marksheets aadhaar tc migration verification papers required documents",
        "is_demo": 1
    },
    {
        "category": "Admissions",
        "question": "What are the important dates and deadlines for college admission?",
        "answer": "[DEMO DATA] For the upcoming academic year, B.Tech admission registrations open on June 10th and close on July 15th. Document verification rounds run from July 16th to July 25th, followed by Merit List declaration on July 28th. CAP round seat allotments take place in August, and the academic session commences on August 16th. Specific dates are announced on the College Portal at www.demo-college.edu/admissions.",
        "keywords": "what are the admission dates admission schedule admission deadlines last date to apply application dates counseling dates merit list registration deadline cutoff dates",
        "is_demo": 1
    },
    {
        "category": "Admissions",
        "question": "What is the admission procedure for lateral entry students into second year?",
        "answer": "[DEMO DATA] Diploma holders in Engineering/Technology with at least 50% aggregate marks (45% for reserved category) or B.Sc. degree holders with Mathematics are eligible for Direct Second Year (Lateral Entry) B.Tech admission. Applications must be submitted through the State Centralized Admission Process (CAP). Inquire at Room 102 on weekdays between 10:00 AM and 4:00 PM for branch-wise vacancy details.",
        "keywords": "lateral entry diploma direct second year admission cap process polytechnic btech 2nd year transfer engineering diploma lateral admission",
        "is_demo": 1
    },

    # -------------------------------------------------------------
    # 2. Courses & Degree Programs (Academics)
    # -------------------------------------------------------------
    {
        "category": "Academics",
        "question": "What courses and engineering branches are available at our college?",
        "answer": "[DEMO DATA] Our college offers 4-year undergraduate B.Tech degree programs in six major branches: (1) Computer Science & Engineering (CSE - 180 seats), (2) Artificial Intelligence & Data Science (AI & DS - 120 seats), (3) Information Technology (IT - 60 seats), (4) Electronics & Telecommunication (ENTC - 60 seats), (5) Mechanical Engineering (60 seats), and (6) Civil Engineering (60 seats). We also offer postgraduate M.Tech in Computer Engineering. All courses are AICTE-approved and affiliated with the State Technological University.",
        "keywords": "what courses are available which branches are available available engineering branches btech cse ai data science it mechanical civil degrees programs offered course options degree branches",
        "is_demo": 1
    },
    {
        "category": "Academics",
        "question": "What is the course duration and curriculum structure of B.Tech degree programs?",
        "answer": "[DEMO DATA] All undergraduate B.Tech programs have a duration of 4 years divided into 8 semesters (each lasting 16 weeks). The curriculum comprises Foundation Sciences in Year 1, Core Departmental Courses in Years 2 and 3, and Advanced Professional Electives, Industry Internships, and a Capstone Project in Year 4. A total of 160 academic credits is required for degree award.",
        "keywords": "course duration btech duration how many semesters credits curriculum structure btech cse ai data science it years total semesters graduation requirements",
        "is_demo": 1
    },

    # -------------------------------------------------------------
    # 3. Academics & Regulations
    # -------------------------------------------------------------
    {
        "category": "Academics",
        "question": "Where can I download the course syllabus and academic curriculum?",
        "answer": "[DEMO DATA] The complete semester-wise syllabus and curriculum structure for all engineering branches can be downloaded in PDF format from the Student ERP Portal under 'Academic Resources' -> 'Curriculum & Syllabi'. Alternatively, physical copies are available in the respective Department Library and Main Academic Section.",
        "keywords": "where can i download syllabus course syllabus curriculum subject list semester syllabus download academic subjects credits scheme syllabus copy",
        "is_demo": 1
    },
    {
        "category": "Academics",
        "question": "Where can I find the official college academic calendar for the semester?",
        "answer": "[DEMO DATA] The official Academic Calendar is published before the start of each semester on the college website and Student ERP notice board. It details term commencement, internal assessment dates, mid-term examinations, festival holidays, practical exam windows, and end-semester theory exam schedules.",
        "keywords": "academic calendar semester dates college calendar term start holidays schedule exam timetable academic planner term dates term schedule",
        "is_demo": 1
    },
    {
        "category": "Academics",
        "question": "How can I contact faculty members or find my class mentor/counselor?",
        "answer": "[DEMO DATA] Every student is assigned a Faculty Mentor/Counselor upon admission. Faculty email IDs, office locations, and weekly consultation hours (typically 3:30 PM to 4:30 PM) are listed in the Department Faculty Directory on the college website and the Student ERP portal. You can also meet Head of the Departments (HOD) during official visiting hours.",
        "keywords": "faculty contact teacher professor mentor counselor hod meeting hours department faculty directory email phone office room consultation teacher contact",
        "is_demo": 1
    },
    {
        "category": "Academics",
        "question": "What is the minimum attendance requirement to appear for semester exams?",
        "answer": "[DEMO DATA] As per academic regulations, a minimum of 75% aggregate attendance across theory lectures and laboratory practicals is mandatory to appear for semester examinations. Students with attendance between 65% and 74% due to medical reasons or approved sports representation may apply for condonation by submitting original medical certificates to the HOD within 3 days of resuming classes.",
        "keywords": "what is the 75 attendance rule attendance requirement 75 attendance rule minimum attendance compulsory attendance shortage condonation medical certificate medical leave",
        "is_demo": 1
    },
    {
        "category": "Academics",
        "question": "How is the CGPA and SGPA calculated in our credit system?",
        "answer": "[DEMO DATA] SGPA (Semester Grade Point Average) is calculated as the sum of (Course Credits × Grade Points) divided by total semester credits. CGPA (Cumulative Grade Point Average) is the cumulative weighted average of all semesters. The grading scale ranges from O (Outstanding - 10) down to P (Pass - 4); an F grade (0 points) denotes a backlog that must be cleared.",
        "keywords": "cgpa sgpa calculation credit system grade points pointer marks percentage formula grades backlog calculation how is cgpa calculated",
        "is_demo": 1
    },
    {
        "category": "Academics",
        "question": "How can I apply for an elective or course change?",
        "answer": "[DEMO DATA] Professional and open elective selection forms are made available on the Student ERP portal 15 days before the semester starts. Elective change requests are accepted within the first 10 days of classes, subject to prerequisite clearance and department seat limits.",
        "keywords": "elective change course subject selection erp portal academic swap elective subject registration change elective",
        "is_demo": 1
    },

    # -------------------------------------------------------------
    # 4. Examinations
    # -------------------------------------------------------------
    {
        "category": "Examinations",
        "question": "When are the mid-term and end-term examinations conducted?",
        "answer": "[DEMO DATA] Mid-term examinations (In-Sem tests) are held in the 7th to 8th week of the semester. End-semester exams take place in December for Odd semesters and May for Even semesters. The official exam timetable is published on the Examination Cell notice board and ERP portal 3 weeks before exams begin.",
        "keywords": "exam schedule mid term end semester exam date timetable in sem dates exam timetable examination dates when are semester exams",
        "is_demo": 1
    },
    {
        "category": "Examinations",
        "question": "How and when can I download my examination hall ticket / admit card?",
        "answer": "[DEMO DATA] Examination hall tickets (admit cards) are available for download on the Student ERP portal 5 to 7 days before exams begin. To download your hall ticket, ensure you have no pending tuition dues and meet the 75% minimum attendance rule. Print your hall ticket and carry it along with your college ID card to the exam hall.",
        "keywords": "how to download exam hall ticket hall ticket admit card download exam pass erp clearance dues verification hall ticket download admit card",
        "is_demo": 1
    },
    {
        "category": "Examinations",
        "question": "When and where are semester examination results declared?",
        "answer": "[DEMO DATA] End-semester examination results are declared within 30 to 45 days after the conclusion of exams. Results and provisional grade cards can be viewed on the College Result Portal by logging in with your Student PRN and Date of Birth. Official printed grade cards are issued by the Exam Cell through your department.",
        "keywords": "exam results semester results result declaration grade card marksheet check result online marks prn when are exam results declared",
        "is_demo": 1
    },
    {
        "category": "Examinations",
        "question": "What is the procedure for exam paper revaluation or photocopy?",
        "answer": "[DEMO DATA] Students dissatisfied with their marks may apply for photocopy of answer books or revaluation within 7 days of result declaration via the Examination Cell portal. The fee is Rs. 300 per subject for revaluation and Rs. 150 for photocopy. Revised results are released within 15 working days.",
        "keywords": "revaluation photocopy marks checking exam paper verification result grievance rechecking paper revaluation apply for revaluation",
        "is_demo": 1
    },

    # -------------------------------------------------------------
    # 5. Fees & Financial Services
    # -------------------------------------------------------------
    {
        "category": "Fees",
        "question": "What are the accepted payment modes for college semester tuition fees?",
        "answer": "[DEMO DATA] Semester tuition and institutional fees can be paid online through the official College Payment Gateway using Net Banking, UPI (Google Pay, PhonePe, Paytm), and Credit/Debit Cards. Alternatively, payments can be made by Demand Draft (DD) drawn in favor of 'College Principal/Registrar'. Cash payments are strictly not accepted. Visit Counter 3 in the Admin Block for payment queries.",
        "keywords": "how can i pay my fees fee payment procedure payment modes tuition fee online net banking upi dd demand draft accounts pay tuition fee online fee payment pay fees online",
        "is_demo": 1
    },
    {
        "category": "Fees",
        "question": "How can I download or collect my college fee payment receipt?",
        "answer": "[DEMO DATA] Immediately after completing an online payment through the portal, an electronic fee receipt with a digital transaction ID is generated. You can download and reprint fee receipts anytime from your Student ERP account under 'Fee History'. For official stamped receipts required for education loans or tax exemptions, visit the Accounts Section in the Admin Block.",
        "keywords": "fee receipt download fee payment receipt tuition fee receipt fee challan duplicate receipt tax exemption education loan receipt accounts download fee receipt",
        "is_demo": 1
    },
    {
        "category": "Fees",
        "question": "Can semester fees be paid in installments?",
        "answer": "[DEMO DATA] Students experiencing financial hardships can request to pay semester tuition fees in two installments. An application addressed to the Principal along with supporting documents must be submitted to the Student Accounts Section at least 15 days before the fee deadline. The first installment (60%) is due at admission/registration, and the remaining 40% before mid-term exams.",
        "keywords": "installment fees payment partial installment concession permission finance application pay in parts fees in installments",
        "is_demo": 1
    },
    {
        "category": "Fees",
        "question": "What scholarship schemes and fee concessions are available?",
        "answer": "[DEMO DATA] Our college facilitates multiple scholarship schemes: (1) Government Post-Matric Scholarships for SC/ST/OBC/SBC/VJNT categories, (2) EBC (Economically Backward Class) 50% tuition fee waiver, (3) Central Sector National Scholarship Portal (NSP), (4) Pragati & Saksham scholarships for female and specially-abled students, and (5) College Merit Scholarships for university rankers. Contact Room 105 or email scholarships@demo-college.edu.",
        "keywords": "scholarship fee concession ebc merit government assistance financial aid freeship post matric fee waiver scholarship schemes",
        "is_demo": 1
    },

    # -------------------------------------------------------------
    # 6. Library
    # -------------------------------------------------------------
    {
        "category": "Library",
        "question": "What are the central library working hours and opening timings?",
        "answer": "[DEMO DATA] The Central Library is open from 8:00 AM to 8:00 PM on Monday through Saturday. During preparatory leave and examination periods, the reading hall facility remains open extended hours until 11:00 PM. The library is closed on Sundays and national public holidays.",
        "keywords": "when does the library open what are the central library working hours and timings library hours timings open timing reading room schedule closing time exam hours library timings",
        "is_demo": 1
    },
    {
        "category": "Library",
        "question": "How many books can a student borrow and for how many days?",
        "answer": "[DEMO DATA] Undergraduate B.Tech students are entitled to borrow up to 3 books simultaneously for a 14-day loan period using their RFID Smart Library Card. Postgraduate M.Tech students may borrow up to 5 books. Books can be renewed once online via the OPAC portal provided no other user has placed a hold on them.",
        "keywords": "how many books can a student borrow borrow books book issue limit return renew smart card library account duration borrowing rules book limit",
        "is_demo": 1
    },
    {
        "category": "Library",
        "question": "How can I check book availability or access digital e-journals?",
        "answer": "[DEMO DATA] You can check physical book availability, shelf location, and reservation status through the Online Public Access Catalog (OPAC) terminals inside the library or via the college intranet. For digital resources, the library subscribes to IEEE Xplore, ScienceDirect, Springer, and DELNET. Remote access credentials are provided during library orientation.",
        "keywords": "check book availability opac catalog digital library e books journals ieee access online library search book reservation book availability",
        "is_demo": 1
    },
    {
        "category": "Library",
        "question": "What is the overdue fine for returning library books late?",
        "answer": "[DEMO DATA] A fine of Rs. 2 per day per book is charged for the first 7 days after the due date. From day 8 onwards, the fine increases to Rs. 5 per day. If a book is damaged or lost, the student must either replace it with an identical or newer edition, or pay 1.5 times the current replacement cost plus processing charges.",
        "keywords": "library fine late return penalty overdue book charges fee lost book overdue fines late fee library overdue penalty",
        "is_demo": 1
    },

    # -------------------------------------------------------------
    # 7. Campus Facilities
    # -------------------------------------------------------------
    {
        "category": "Facilities",
        "question": "What computer laboratories and specialized engineering labs are available on campus?",
        "answer": "[DEMO DATA] The college maintains 18 advanced departmental laboratories, including high-performance computing labs, an AI & Robotics Center of Excellence, an IoT Embedded Systems Lab, Cloud Computing Lab, and Workshop facilities. All computer labs feature gigabit networking, licensed CAD/simulation software, and are accessible from 8:30 AM to 6:30 PM under faculty supervision.",
        "keywords": "laboratories computer labs computing facility engineering labs hardware software lab center of excellence practical equipment lab facilities",
        "is_demo": 1
    },
    {
        "category": "Facilities",
        "question": "How do students connect to the college campus Wi-Fi network?",
        "answer": "[DEMO DATA] High-speed Wi-Fi (300 Mbps fiber backbone) is available across academic blocks, laboratories, the library, and hostels. To connect: (1) Connect your device to the 'CAMPUS-STUDENT-WIFI' SSID, (2) Open your browser to the captive authentication portal, and (3) Sign in using your college ERP username and password. For network MAC registration or password reset, contact the IT Helpdesk in Room 204.",
        "keywords": "how do students connect to wifi campus wifi internet access wireless student wifi laptop connection wifi password network login erp wifi",
        "is_demo": 1
    },
    {
        "category": "Facilities",
        "question": "Are college bus transportation routes available for day scholars?",
        "answer": "[DEMO DATA] Yes, a fleet of 15 college buses operates across 12 designated routes covering all major city neighborhoods and suburbs. Buses depart campus at 5:15 PM daily. Students can apply for an annual bus pass through the Transport Office in the Admin Block. Real-time GPS bus tracking is accessible via the College Mobile App.",
        "keywords": "bus transport transportation route pickup timings pass day scholar travel stops bus timing route details college bus transport",
        "is_demo": 1
    },
    {
        "category": "Facilities",
        "question": "What is the procedure for hostel room accommodation and allocation?",
        "answer": "[DEMO DATA] On-campus hostel facilities are available separately for male and female students with double and triple occupancy rooms. Accommodation applications open on the admission day. Allotment is merit-and-distance based with preference to outstation students. Facilities include furnished rooms, 24/7 power backup, Wi-Fi, hygienic mess, and RO water. Inquire with the Chief Warden at hostel@demo-college.edu.",
        "keywords": "hostel room accommodation warden mess allotment stay living hostelites curfew hostel application fees room booking hostel allocation",
        "is_demo": 1
    },
    {
        "category": "Facilities",
        "question": "What sports and gym facilities are available on campus?",
        "answer": "[DEMO DATA] Campus sports infrastructure includes floodlit basketball and volleyball courts, outdoor football and cricket grounds, indoor badminton courts, table tennis tables, and a modern gymnasium equipped with cardio and strength equipment. Gym timings are 6:00 AM to 8:30 AM and 5:00 PM to 8:00 PM on weekdays.",
        "keywords": "sports gym complex basketball football grounds fitness timings facility physical education indoor games outdoor gym facilities",
        "is_demo": 1
    },
    {
        "category": "Facilities",
        "question": "What student support, grievance redressal, and mental wellness counseling services are available?",
        "answer": "[DEMO DATA] The college provides comprehensive student support: (1) Student Counseling & Mental Wellness Cell with certified counselors (Room 112, confidential appointments), (2) Internal Complaints Committee (ICC) for anti-harassment, (3) Anti-Ragging Committee (toll-free helpline 1800-180-5522), and (4) Equal Opportunity Cell. All student grievances can also be logged online through the ERP Grievance Portal.",
        "keywords": "student support counseling cell mental wellness grievance redressal anti ragging helpline complaints committee psychological counseling student wellness",
        "is_demo": 1
    },
    {
        "category": "Facilities",
        "question": "What are the official contact details and helpline numbers for college departments?",
        "answer": "[DEMO DATA] Official contact details for campus departments are: (1) Admissions Cell: admissions@demo-college.edu | Ext: 101, (2) Academic Dean Office: academics@demo-college.edu | Ext: 102, (3) Examination Cell: examcell@demo-college.edu | Ext: 103, (4) Accounts & Fees: accounts@demo-college.edu | Ext: 104, (5) Central Library: library@demo-college.edu | Ext: 105, (6) Hostel & Campus Care: campuscare@demo-college.edu | Ext: 106. General college reception: +91-20-12345678 (Mon-Sat, 9:00 AM - 5:00 PM).",
        "keywords": "contact information department contact details helpline numbers phone numbers email directory college office extension numbers reception department contacts",
        "is_demo": 1
    }
]

VALID_CATEGORIES = [
    "Admissions",
    "Academics",
    "Examinations",
    "Library",
    "Fees",
    "Facilities"
]


def get_db(db_path=None):
    """Returns a SQLite connection with dict-like row access."""
    target_path = db_path or os.environ.get("DATABASE_PATH", DB_FILE)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path=None, force=False):
    """
    Initializes database tables, creates default admin user if not present,
    and seeds sample college demo FAQs if the faqs table is empty.
    """
    conn = get_db(db_path)
    cursor = conn.cursor()

    if force:
        cursor.execute("DROP TABLE IF EXISTS query_logs;")
        cursor.execute("DROP TABLE IF EXISTS faqs;")
        cursor.execute("DROP TABLE IF EXISTS admin_users;")

    # 1. FAQs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            category TEXT NOT NULL,
            keywords TEXT DEFAULT '',
            is_demo INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Admin Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 3. Query Logs / Analytics Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_query TEXT NOT NULL,
            category_filter TEXT,
            matched_faq_id INTEGER,
            matched_question TEXT,
            similarity_score REAL,
            response_status TEXT NOT NULL, -- 'RESOLVED', 'FALLBACK', 'EMPTY_QUERY'
            feedback TEXT,                 -- 'HELPFUL', 'NOT_HELPFUL', or NULL
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (matched_faq_id) REFERENCES faqs(id) ON DELETE SET NULL
        );
    """)

    # Indices for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_faqs_category ON faqs(category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_created_at ON query_logs(created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_status ON query_logs(response_status);")

    # Seed Default Admin if table is empty
    cursor.execute("SELECT COUNT(*) as count FROM admin_users;")
    admin_count = cursor.fetchone()["count"]
    if admin_count == 0:
        default_user = os.environ.get("ADMIN_USERNAME", "admin")
        default_pass = os.environ.get("ADMIN_PASSWORD", "admin123")
        hashed = generate_password_hash(default_pass, method="scrypt")
        cursor.execute(
            "INSERT INTO admin_users (username, password_hash) VALUES (?, ?);",
            (default_user, hashed)
        )

    # Seed or synchronize Sample FAQs
    cursor.execute("SELECT question, is_demo FROM faqs;")
    existing_rows = cursor.fetchall()
    existing_map = {row["question"]: row["is_demo"] for row in existing_rows}

    for faq in SAMPLE_FAQS:
        if faq["question"] not in existing_map:
            cursor.execute(
                """
                INSERT INTO faqs (question, answer, category, keywords, is_demo)
                VALUES (?, ?, ?, ?, ?);
                """,
                (faq["question"], faq["answer"], faq["category"], faq["keywords"], faq["is_demo"])
            )
        elif existing_map[faq["question"]] == 1:
            # Update demo FAQs if modified in code to keep keywords and answers current
            cursor.execute(
                """
                UPDATE faqs
                SET answer = ?, category = ?, keywords = ?, is_demo = ?
                WHERE question = ? AND is_demo = 1;
                """,
                (faq["answer"], faq["category"], faq["keywords"], faq["is_demo"], faq["question"])
            )

    conn.commit()
    conn.close()


# -------------------------------------------------------------
# FAQ CRUD Functions
# -------------------------------------------------------------

def get_all_faqs(category=None, search=None, db_path=None):
    """Retrieves all FAQs, optionally filtered by category and search keyword."""
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM faqs WHERE 1=1"
        params = []

        if category and category.strip() and category.lower() != "all":
            query += " AND category = ?"
            params.append(category.strip())

        if search and search.strip():
            query += " AND (question LIKE ? OR answer LIKE ? OR keywords LIKE ?)"
            like_term = f"%{search.strip()}%"
            params.extend([like_term, like_term, like_term])

        query += " ORDER BY category ASC, id ASC"
        cursor.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        return rows
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def get_faq_by_id(faq_id, db_path=None):
    """Retrieves a single FAQ by its ID."""
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM faqs WHERE id = ?", (faq_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()


def add_faq(question, answer, category, keywords="", is_demo=0, db_path=None):
    """Adds a new FAQ entry to the database."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        INSERT INTO faqs (question, answer, category, keywords, is_demo, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (question.strip(), answer.strip(), category.strip(), keywords.strip(), is_demo, now, now)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_faq(faq_id, question, answer, category, keywords="", is_demo=0, db_path=None):
    """Updates an existing FAQ."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        UPDATE faqs
        SET question = ?, answer = ?, category = ?, keywords = ?, is_demo = ?, updated_at = ?
        WHERE id = ?
        """,
        (question.strip(), answer.strip(), category.strip(), keywords.strip(), is_demo, now, faq_id)
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def delete_faq(faq_id, db_path=None):
    """Deletes an FAQ by ID."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM faqs WHERE id = ?", (faq_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def get_categories(db_path=None):
    """Returns list of distinct categories with FAQ counts."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT category, COUNT(*) as count 
        FROM faqs 
        GROUP BY category 
        ORDER BY category ASC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


# -------------------------------------------------------------
# Interaction Logging & Feedback
# -------------------------------------------------------------

def log_interaction(user_query, category_filter, matched_faq_id, matched_question,
                    similarity_score, response_status, db_path=None):
    """Records user query interaction for agent performance tracking."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO query_logs 
        (user_query, category_filter, matched_faq_id, matched_question, similarity_score, response_status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_query,
            category_filter if category_filter else None,
            matched_faq_id if matched_faq_id else None,
            matched_question if matched_question else None,
            float(similarity_score) if similarity_score is not None else 0.0,
            response_status
        )
    )
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id


def update_feedback(log_id, feedback_value, db_path=None):
    """Updates feedback ('HELPFUL' or 'NOT_HELPFUL') for a specific interaction log."""
    valid_feedbacks = ["HELPFUL", "NOT_HELPFUL"]
    if feedback_value not in valid_feedbacks:
        return False

    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE query_logs SET feedback = ? WHERE id = ?",
        (feedback_value, log_id)
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def get_recent_logs(limit=50, db_path=None):
    """Retrieves recent query logs for the admin dashboard."""
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ql.*, f.category as matched_category
        FROM query_logs ql
        LEFT JOIN faqs f ON ql.matched_faq_id = f.id
        ORDER BY ql.id DESC
        LIMIT ?
        """,
        (limit,)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_analytics_summary(db_path=None):
    """
    Computes summary analytics for the admin dashboard:
    - total queries
    - resolved queries (score >= threshold)
    - fallback queries
    - resolution rate %
    - helpful / unhelpful counts
    - breakdown by category
    """
    conn = get_db(db_path)
    cursor = conn.cursor()

    # Total queries
    cursor.execute("SELECT COUNT(*) as total FROM query_logs;")
    total_queries = cursor.fetchone()["total"]

    # Status counts
    cursor.execute("""
        SELECT response_status, COUNT(*) as count 
        FROM query_logs 
        GROUP BY response_status;
    """)
    status_counts = {row["response_status"]: row["count"] for row in cursor.fetchall()}
    resolved_count = status_counts.get("RESOLVED", 0)
    fallback_count = status_counts.get("FALLBACK", 0)

    # Resolution rate
    resolution_rate = round((resolved_count / total_queries * 100), 1) if total_queries > 0 else 0.0

    # Feedback counts
    cursor.execute("""
        SELECT feedback, COUNT(*) as count 
        FROM query_logs 
        WHERE feedback IS NOT NULL 
        GROUP BY feedback;
    """)
    feedback_counts = {row["feedback"]: row["count"] for row in cursor.fetchall()}
    helpful_count = feedback_counts.get("HELPFUL", 0)
    unhelpful_count = feedback_counts.get("NOT_HELPFUL", 0)

    # Category breakdown from matched FAQs
    cursor.execute("""
        SELECT COALESCE(f.category, ql.category_filter, 'Uncategorized') as category, COUNT(*) as count
        FROM query_logs ql
        LEFT JOIN faqs f ON ql.matched_faq_id = f.id
        GROUP BY category
        ORDER BY count DESC;
    """)
    category_breakdown = [dict(row) for row in cursor.fetchall()]

    # Total FAQs in system
    cursor.execute("SELECT COUNT(*) as total_faqs FROM faqs;")
    total_faqs = cursor.fetchone()["total_faqs"]

    conn.close()

    return {
        "total_queries": total_queries,
        "resolved_count": resolved_count,
        "fallback_count": fallback_count,
        "resolution_rate": resolution_rate,
        "helpful_count": helpful_count,
        "unhelpful_count": unhelpful_count,
        "total_faqs": total_faqs,
        "category_breakdown": category_breakdown
    }


# -------------------------------------------------------------
# Admin Authentication
# -------------------------------------------------------------

def authenticate_admin(username, password, db_path=None):
    """Validates admin login credentials against stored scrypt hash."""
    if not username or not password:
        return False
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin_users WHERE username = ?", (username.strip(),))
    admin = cursor.fetchone()
    conn.close()

    if not admin:
        return False
    return check_password_hash(admin["password_hash"], password)


def update_admin_password(username, new_password, db_path=None):
    """Allows updating admin password."""
    if not new_password or len(new_password) < 6:
        return False
    conn = get_db(db_path)
    cursor = conn.cursor()
    hashed = generate_password_hash(new_password, method="scrypt")
    cursor.execute(
        "UPDATE admin_users SET password_hash = ? WHERE username = ?",
        (hashed, username)
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def get_admin_user(username, db_path=None):
    """Retrieves basic administrator profile details."""
    if not username:
        return None
    conn = get_db(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, created_at FROM admin_users WHERE username = ?", (username.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

