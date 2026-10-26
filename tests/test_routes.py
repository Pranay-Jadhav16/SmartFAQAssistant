"""
Integration and Route Tests for app.py
Validates:
- Public endpoints (/, /chat, /faqs)
- Chatbot JSON APIs (/api/chat, /api/feedback, /api/categories)
- Route protection and access control for admin endpoints
- Admin authentication (login, session, logout)
- Admin FAQ CRUD actions and Debugger
"""

import os
import unittest
import tempfile
import json

from app import app, agent
from database import init_db, get_all_faqs


class TestAppRoutes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.orig_db_path = os.environ.get("DATABASE_PATH")
        cls.temp_db_fd, cls.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.environ["DATABASE_PATH"] = cls.temp_db_path
        init_db(db_path=cls.temp_db_path, force=True)
        cls.orig_agent_db = agent.db_path
        agent.db_path = cls.temp_db_path
        agent.reload_knowledge_base()

    @classmethod
    def tearDownClass(cls):
        os.close(cls.temp_db_fd)
        if os.path.exists(cls.temp_db_path):
            os.remove(cls.temp_db_path)
        if cls.orig_db_path:
            os.environ["DATABASE_PATH"] = cls.orig_db_path
        else:
            os.environ.pop("DATABASE_PATH", None)
        agent.db_path = cls.orig_agent_db
        agent.reload_knowledge_base()

    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_public_pages(self):
        """Test GET /, /chat, /faqs load with status 200."""
        # 1. Home
        res_home = self.client.get("/")
        self.assertEqual(res_home.status_code, 200)
        self.assertIn(b"Smart FAQ Assistant", res_home.data)

        # 2. Chat
        res_chat = self.client.get("/chat")
        self.assertEqual(res_chat.status_code, 200)
        self.assertIn(b"Campus Assistant", res_chat.data)

        # 3. FAQs directory
        res_faqs = self.client.get("/faqs")
        self.assertEqual(res_faqs.status_code, 200)
        self.assertIn(b"College FAQ Knowledge Base", res_faqs.data)

    def test_api_chat(self):
        """Test POST /api/chat with various questions."""
        # Query 1: Regular query matching attendance
        payload = {"query": "What is the minimum attendance required?", "category": ""}
        res = self.client.post("/api/chat", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "RESOLVED")
        self.assertIn("75%", data["answer"])
        self.assertIsNotNone(data["log_id"])

        # Query 2: Empty query
        res_empty = self.client.post("/api/chat", data=json.dumps({"query": ""}), content_type="application/json")
        self.assertEqual(res_empty.status_code, 200)
        data_empty = json.loads(res_empty.data)
        self.assertEqual(data_empty["status"], "EMPTY_QUERY")

        # Query 3: Out-of-domain query triggering fallback
        payload_unknown = {"query": "How to make espresso coffee?", "category": ""}
        res_unknown = self.client.post("/api/chat", data=json.dumps(payload_unknown), content_type="application/json")
        self.assertEqual(res_unknown.status_code, 200)
        data_unknown = json.loads(res_unknown.data)
        self.assertFalse(data_unknown["success"])
        self.assertEqual(data_unknown["status"], "FALLBACK")
        self.assertIn("not available in the current FAQ knowledge base", data_unknown["answer"])
        self.assertNotIn("College Contact Directory", data_unknown["answer"])

    def test_api_feedback(self):
        """Test POST /api/feedback saves user reaction."""
        # First generate a log
        payload = {"query": "What is the CGPA calculation?", "category": "Academics"}
        res_chat = self.client.post("/api/chat", data=json.dumps(payload), content_type="application/json")
        data_chat = json.loads(res_chat.data)
        log_id = data_chat["log_id"]
        self.assertIsNotNone(log_id)

        # Now submit feedback
        res_fb = self.client.post(
            "/api/feedback",
            data=json.dumps({"log_id": log_id, "feedback": "HELPFUL"}),
            content_type="application/json"
        )
        self.assertEqual(res_fb.status_code, 200)
        data_fb = json.loads(res_fb.data)
        self.assertTrue(data_fb["success"])

    def test_api_categories(self):
        """Test GET /api/categories returns category counts."""
        res = self.client.get("/api/categories")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("categories", data)
        self.assertGreater(len(data["categories"]), 0)

    def test_admin_route_protection(self):
        """Test that unauthenticated requests to /admin are redirected to login."""
        protected_routes = ["/admin", "/admin/faqs", "/admin/faqs/new", "/admin/logs", "/admin/debug"]
        for route in protected_routes:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 302)
            self.assertIn("/admin/login", res.headers["Location"])

    def test_admin_auth_and_crud(self):
        """Test admin login, CRUD operations on FAQs, and logout."""
        # 1. Invalid login
        res_fail = self.client.post("/admin/login", data={"username": "admin", "password": "wrongpassword"})
        self.assertEqual(res_fail.status_code, 200)
        self.assertIn(b"Invalid administrator credentials", res_fail.data)

        # 2. Valid login
        res_login = self.client.post("/admin/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b"Administrator Dashboard", res_login.data)

        # 3. Access admin faqs
        res_faqs = self.client.get("/admin/faqs")
        self.assertEqual(res_faqs.status_code, 200)

        # 4. Add new FAQ via form
        res_add = self.client.post(
            "/admin/faqs/new",
            data={
                "question": "Can I get Wi-Fi access on campus for my laptop?",
                "answer": "[DEMO DATA] Yes, connect to 'College-Student-WiFi' and log in with your ERP student ID.",
                "category": "Facilities",
                "keywords": "wifi internet laptop network connection erp",
                "is_demo": "1"
            },
            follow_redirects=True
        )
        self.assertEqual(res_add.status_code, 200)
        self.assertIn(b"created successfully", res_add.data)

        # Verify added FAQ is now in database
        all_faqs = get_all_faqs(db_path=self.temp_db_path)
        added_list = [f for f in all_faqs if "Wi-Fi access" in f["question"]]
        self.assertEqual(len(added_list), 1)
        added_faq = added_list[0]

        # 5. Access debugger with query
        res_debug = self.client.get(f"/admin/debug?q=how+to+connect+to+college+wifi")
        self.assertEqual(res_debug.status_code, 200)
        self.assertIn(b"Stage 1", res_debug.data)

        # 6. Delete the FAQ
        res_del = self.client.post(f"/admin/faqs/{added_faq['id']}/delete", follow_redirects=True)
        self.assertEqual(res_del.status_code, 200)
        self.assertIn(b"deleted successfully", res_del.data)

        # 7. Logout
        res_logout = self.client.get("/admin/logout", follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn(b"Admin Sign In", res_logout.data)

    def test_all_template_links_valid(self):
        """Verifies that all url_for calls in all HTML templates map to real Flask routes."""
        import glob
        import re

        registered_endpoints = set(app.view_functions.keys())
        broken = []
        for template_file in glob.glob("templates/*.html"):
            with open(template_file, encoding="utf-8") as f:
                content = f.read()
            matches = re.findall(r"url_for\(['\"]([a-zA-Z0-9_]+)['\"]", content)
            for ep in matches:
                if ep != "static" and ep not in registered_endpoints:
                    broken.append((template_file, ep))
        self.assertEqual(broken, [], f"Found broken url_for endpoints in templates: {broken}")


if __name__ == "__main__":
    unittest.main()

