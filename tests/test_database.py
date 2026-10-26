"""
Unit tests for database.py
Validates schema creation, demo data seeding, CRUD operations,
interaction logging, feedback updates, and admin authentication.
"""

import os
import unittest
import tempfile
import sqlite3

from database import (
    init_db,
    get_db,
    get_all_faqs,
    get_faq_by_id,
    add_faq,
    update_faq,
    delete_faq,
    get_categories,
    log_interaction,
    update_feedback,
    get_analytics_summary,
    authenticate_admin,
    SAMPLE_FAQS,
    VALID_CATEGORIES
)


class TestDatabase(unittest.TestCase):

    def setUp(self):
        # Create a temporary database file for isolated testing
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(db_path=self.temp_db_path, force=True)

    def tearDown(self):
        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_schema_and_seeding(self):
        """Verify all tables exist and sample demo FAQs are seeded."""
        conn = get_db(self.temp_db_path)
        cursor = conn.cursor()

        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row["name"] for row in cursor.fetchall()}
        self.assertIn("faqs", tables)
        self.assertIn("admin_users", tables)
        self.assertIn("query_logs", tables)

        # Check seeded FAQs count
        faqs = get_all_faqs(db_path=self.temp_db_path)
        self.assertEqual(len(faqs), len(SAMPLE_FAQS))

        # Check default admin exists
        cursor.execute("SELECT COUNT(*) as count FROM admin_users;")
        self.assertGreater(cursor.fetchone()["count"], 0)
        conn.close()

    def test_faq_crud_operations(self):
        """Test adding, retrieving, updating, and deleting an FAQ."""
        # 1. Add
        new_id = add_faq(
            question="Can I get bus pass concession?",
            answer="Yes, bus passes have a 20% student concession.",
            category="Facilities",
            keywords="bus pass concession discount travel",
            is_demo=0,
            db_path=self.temp_db_path
        )
        self.assertIsNotNone(new_id)

        # 2. Get
        faq = get_faq_by_id(new_id, db_path=self.temp_db_path)
        self.assertIsNotNone(faq)
        self.assertEqual(faq["question"], "Can I get bus pass concession?")
        self.assertEqual(faq["category"], "Facilities")
        self.assertEqual(faq["is_demo"], 0)

        # 3. Update
        updated = update_faq(
            faq_id=new_id,
            question="Can I get bus pass concession updated?",
            answer="Yes, 25% discount available.",
            category="Facilities",
            keywords="bus pass 25 discount",
            is_demo=0,
            db_path=self.temp_db_path
        )
        self.assertTrue(updated)
        faq_updated = get_faq_by_id(new_id, db_path=self.temp_db_path)
        self.assertEqual(faq_updated["question"], "Can I get bus pass concession updated?")
        self.assertEqual(faq_updated["answer"], "Yes, 25% discount available.")

        # 4. Delete
        deleted = delete_faq(new_id, db_path=self.temp_db_path)
        self.assertTrue(deleted)
        self.assertIsNone(get_faq_by_id(new_id, db_path=self.temp_db_path))

    def test_category_filtering_and_search(self):
        """Test retrieving FAQs filtered by category and search keyword."""
        # By category
        lib_faqs = get_all_faqs(category="Library", db_path=self.temp_db_path)
        self.assertGreater(len(lib_faqs), 0)
        for f in lib_faqs:
            self.assertEqual(f["category"], "Library")

        # By search keyword
        search_results = get_all_faqs(search="attendance", db_path=self.temp_db_path)
        self.assertGreater(len(search_results), 0)
        self.assertTrue(any("attendance" in f["question"].lower() for f in search_results))

    def test_query_logging_and_feedback(self):
        """Test logging interactions and recording user feedback."""
        log_id = log_interaction(
            user_query="What is the attendance criteria?",
            category_filter="Academics",
            matched_faq_id=1,
            matched_question="What is the minimum attendance requirement to appear for semester exams?",
            similarity_score=0.88,
            response_status="RESOLVED",
            db_path=self.temp_db_path
        )
        self.assertIsNotNone(log_id)

        # Update feedback to HELPFUL
        updated = update_feedback(log_id, "HELPFUL", db_path=self.temp_db_path)
        self.assertTrue(updated)

        conn = get_db(self.temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT feedback FROM query_logs WHERE id = ?", (log_id,))
        row = cursor.fetchone()
        conn.close()
        self.assertEqual(row["feedback"], "HELPFUL")

    def test_analytics_summary(self):
        """Test calculation of analytics summary metrics."""
        # Log a resolved query
        log_interaction("Query 1", "Academics", 1, "Q1", 0.75, "RESOLVED", db_path=self.temp_db_path)
        # Log a fallback query
        log_interaction("Unknown Query", None, None, None, 0.05, "FALLBACK", db_path=self.temp_db_path)

        analytics = get_analytics_summary(db_path=self.temp_db_path)
        self.assertEqual(analytics["total_queries"], 2)
        self.assertEqual(analytics["resolved_count"], 1)
        self.assertEqual(analytics["fallback_count"], 1)
        self.assertEqual(analytics["resolution_rate"], 50.0)

    def test_admin_authentication(self):
        """Test admin authentication with valid and invalid credentials."""
        # Default seeded admin credentials
        self.assertTrue(authenticate_admin("admin", "admin123", db_path=self.temp_db_path))
        self.assertFalse(authenticate_admin("admin", "wrongpassword", db_path=self.temp_db_path))
        self.assertFalse(authenticate_admin("nonexistent_user", "admin123", db_path=self.temp_db_path))


if __name__ == "__main__":
    unittest.main()
