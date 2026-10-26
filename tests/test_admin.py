"""
Dedicated Test Suite for Admin Portal:
Validates Authentication, Authorization (route protection),
FAQ CRUD operations, input validation, dashboard statistics,
and secure password management.
"""

import os
import unittest
import tempfile
import json

from app import app, agent
from database import (
    init_db,
    get_all_faqs,
    get_faq_by_id,
    add_faq,
    authenticate_admin,
    update_admin_password,
    VALID_CATEGORIES
)


class TestAdminPortal(unittest.TestCase):

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
        # Ensure default credentials are clean before each test
        update_admin_password("admin", "admin123", db_path=self.temp_db_path)

    # -------------------------------------------------------------
    # 1. Authentication Tests
    # -------------------------------------------------------------

    def test_login_page_renders(self):
        """GET /admin/login loads with HTTP 200 and renders the sign-in form."""
        res = self.client.get("/admin/login")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Admin Sign In", res.data)
        self.assertIn(b"Username", res.data)
        self.assertIn(b"Password", res.data)

    def test_login_success(self):
        """POST /admin/login with valid credentials authenticates admin session."""
        res = self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=True
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Administrator Dashboard", res.data)
        self.assertIn(b"Welcome back", res.data)

        # Verify session is established
        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get("is_admin"))
            self.assertEqual(sess.get("admin_username"), "admin")

    def test_login_failure_invalid_password(self):
        """POST /admin/login with incorrect password fails with error alert."""
        res = self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "wrongpassword123"},
            follow_redirects=True
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Invalid administrator credentials", res.data)

        # Verify session is NOT established
        with self.client.session_transaction() as sess:
            self.assertFalse(sess.get("is_admin", False))

    def test_login_failure_unknown_username(self):
        """POST /admin/login with non-existent user fails."""
        res = self.client.post(
            "/admin/login",
            data={"username": "unknown_admin", "password": "admin123"},
            follow_redirects=True
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Invalid administrator credentials", res.data)

    def test_logout(self):
        """GET /admin/logout clears session and redirects to login."""
        # First log in
        self.client.post("/admin/login", data={"username": "admin", "password": "admin123"})
        # Then log out
        res = self.client.get("/admin/logout", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"You have been signed out successfully", res.data)

        with self.client.session_transaction() as sess:
            self.assertFalse(sess.get("is_admin", False))

    # -------------------------------------------------------------
    # 2. Authorization / Route Protection Tests
    # -------------------------------------------------------------

    def test_protected_routes_redirect_unauthenticated_users(self):
        """Unauthenticated requests to all admin endpoints must redirect (302) to login."""
        protected_routes = [
            "/admin",
            "/admin/faqs",
            "/admin/faqs/new",
            "/admin/faqs/1/edit",
            "/admin/logs",
            "/admin/debug",
            "/admin/password"
        ]
        for route in protected_routes:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 302, f"Route {route} failed protection")
            self.assertIn("/admin/login", res.headers["Location"])

    def test_protected_post_routes_redirect_unauthenticated_users(self):
        """Unauthenticated POST requests must also be rejected."""
        res = self.client.post("/admin/faqs/1/delete")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/admin/login", res.headers["Location"])

    # -------------------------------------------------------------
    # 3. FAQ CRUD Operations & Input Validation Tests
    # -------------------------------------------------------------

    def test_add_faq_crud_and_validation(self):
        """Test adding FAQ with valid and invalid inputs."""
        # Log in as admin
        self.client.post("/admin/login", data={"username": "admin", "password": "admin123"})

        # Case 1: Validation failure - question too short
        res_fail1 = self.client.post(
            "/admin/faqs/new",
            data={"question": "No", "answer": "Valid answer text here", "category": "Admissions"},
            follow_redirects=True
        )
        self.assertEqual(res_fail1.status_code, 200)
        self.assertIn(b"Question is required and must be at least 5 characters long", res_fail1.data)

        # Case 2: Validation failure - invalid category
        res_fail2 = self.client.post(
            "/admin/faqs/new",
            data={"question": "Valid Question Here?", "answer": "Valid answer text", "category": "InvalidCategoryName"},
            follow_redirects=True
        )
        self.assertEqual(res_fail2.status_code, 200)
        self.assertIn(b"Invalid category selected", res_fail2.data)

        # Case 3: Valid creation
        new_q = "What is the procedure for obtaining a college bonafide certificate?"
        new_a = "[DEMO DATA] Apply online via the Student ERP portal. Digital copy issued within 2 working days."
        res_success = self.client.post(
            "/admin/faqs/new",
            data={
                "question": new_q,
                "answer": new_a,
                "category": "Academics",
                "keywords": "bonafide certificate student proof erp",
                "is_demo": "1"
            },
            follow_redirects=True
        )
        self.assertEqual(res_success.status_code, 200)
        self.assertIn(b"created successfully", res_success.data)

        # Verify FAQ in SQLite
        faqs = get_all_faqs(db_path=self.temp_db_path)
        matching = [f for f in faqs if f["question"] == new_q]
        self.assertEqual(len(matching), 1)
        created_faq = matching[0]

        # Case 4: Edit existing FAQ
        updated_a = "[DEMO DATA] Updated answer text for bonafide certificate verification."
        res_edit = self.client.post(
            f"/admin/faqs/{created_faq['id']}/edit",
            data={
                "question": new_q,
                "answer": updated_a,
                "category": "Academics",
                "keywords": "bonafide certificate updated",
                "is_demo": "1"
            },
            follow_redirects=True
        )
        self.assertEqual(res_edit.status_code, 200)
        self.assertIn(b"updated successfully", res_edit.data)

        # Verify update persisted
        updated_record = get_faq_by_id(created_faq["id"], db_path=self.temp_db_path)
        self.assertEqual(updated_record["answer"], updated_a)

        # Case 5: Delete existing FAQ
        res_delete = self.client.post(f"/admin/faqs/{created_faq['id']}/delete", follow_redirects=True)
        self.assertEqual(res_delete.status_code, 200)
        self.assertIn(b"deleted successfully", res_delete.data)
        self.assertIsNone(get_faq_by_id(created_faq["id"], db_path=self.temp_db_path))

    def test_edit_nonexistent_faq(self):
        """Editing an invalid ID redirects with an error flash."""
        self.client.post("/admin/login", data={"username": "admin", "password": "admin123"})
        res = self.client.get("/admin/faqs/999999/edit", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"does not exist", res.data)

    def test_admin_faq_search_and_category_filter(self):
        """Admin FAQ management list can be searched and filtered by category."""
        self.client.post("/admin/login", data={"username": "admin", "password": "admin123"})

        # Search by keyword
        res_search = self.client.get("/admin/faqs?q=attendance")
        self.assertEqual(res_search.status_code, 200)
        self.assertIn(b"attendance", res_search.data.lower())

        # Filter by category
        res_cat = self.client.get("/admin/faqs?category=Library")
        self.assertEqual(res_cat.status_code, 200)
        self.assertIn(b"Library", res_cat.data)

    # -------------------------------------------------------------
    # 4. Admin Dashboard Statistics Tests
    # -------------------------------------------------------------

    def test_dashboard_statistics_rendered(self):
        """Verify dashboard statistics: total FAQs, questions asked, and helpful feedback."""
        self.client.post("/admin/login", data={"username": "admin", "password": "admin123"})

        # Send a student query to generate log
        self.client.post(
            "/api/chat",
            data=json.dumps({"query": "What is the attendance criteria?", "category": ""}),
            content_type="application/json"
        )

        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"stat-total-faqs", res.data)
        self.assertIn(b"stat-questions-asked", res.data)
        self.assertIn(b"stat-helpful-feedback", res.data)
        self.assertIn(b"stat-resolution-rate", res.data)

    # -------------------------------------------------------------
    # 5. Admin Password Management Tests
    # -------------------------------------------------------------

    def test_admin_password_change(self):
        """Test changing admin password with validation and subsequent sign-in."""
        self.client.post("/admin/login", data={"username": "admin", "password": "admin123"})

        # 1. Wrong current password
        res_wrong = self.client.post(
            "/admin/password",
            data={
                "current_password": "wrongpassword",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123"
            },
            follow_redirects=True
        )
        self.assertEqual(res_wrong.status_code, 200)
        self.assertIn(b"current password entered is incorrect", res_wrong.data)

        # 2. Mismatched confirmation
        res_mismatch = self.client.post(
            "/admin/password",
            data={
                "current_password": "admin123",
                "new_password": "newpassword123",
                "confirm_password": "differentpassword"
            },
            follow_redirects=True
        )
        self.assertEqual(res_mismatch.status_code, 200)
        self.assertIn(b"do not match", res_mismatch.data)

        # 3. Successful change
        res_success = self.client.post(
            "/admin/password",
            data={
                "current_password": "admin123",
                "new_password": "newsecurepassword123",
                "confirm_password": "newsecurepassword123"
            },
            follow_redirects=True
        )
        self.assertEqual(res_success.status_code, 200)
        self.assertIn(b"password updated successfully", res_success.data)

        # 4. Sign out and test new password
        self.client.get("/admin/logout")
        res_new_login = self.client.post(
            "/admin/login",
            data={"username": "admin", "password": "newsecurepassword123"},
            follow_redirects=True
        )
        self.assertEqual(res_new_login.status_code, 200)
        self.assertIn(b"Administrator Dashboard", res_new_login.data)


if __name__ == "__main__":
    unittest.main()
