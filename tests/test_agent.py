"""
Unit tests for agent.py
Tests the Deterministic Retrieval-Based AI Agent pipeline:
- Exact and paraphrased question matching
- Ambiguous query handling and category overlap detection
- Empty, whitespace, and punctuation-only input rejection
- Irrelevant / out-of-domain query handling with safe department fallback
- Fine-grained discrimination between similar FAQs within the same category
- Configurable confidence threshold (at initialization and per-call override)
- Prevention of incorrect answers when similarity is below threshold
- Dynamic knowledge base reloading
- Admin diagnostics and explainability report structure
"""

import os
import unittest
import tempfile

from database import init_db, add_faq
from agent import SmartFAQAgent


class TestSmartFAQAgent(unittest.TestCase):

    def setUp(self):
        # Create an isolated temporary SQLite database for agent testing
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(db_path=self.temp_db_path, force=True)
        # Initialize agent pointing to temporary DB with default threshold 0.25
        self.agent = SmartFAQAgent(threshold=0.25, db_path=self.temp_db_path)

    def tearDown(self):
        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    # -------------------------------------------------------------------------
    # 1. Exact and Paraphrased Questions
    # -------------------------------------------------------------------------

    def test_exact_question_match(self):
        """Verifies an exact question returns high confidence (>= 0.7) and RESOLVED status."""
        query = "What are the eligibility criteria for B.Tech CSE admission?"
        result = self.agent.ask(query, record_log=False)

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "RESOLVED")
        self.assertGreaterEqual(result["confidence"], 0.70)
        self.assertEqual(result["matched_faq"]["category"], "Admissions")
        self.assertIn("60% aggregate", result["answer"])

    def test_paraphrased_reworded_questions(self):
        """
        Verifies that questions asked in different natural-language variations
        and conversational phrases still match the intended FAQ:
        - Conversational attendance question -> matches 75% attendance FAQ
        - Online tuition payment via UPI -> matches fee payment FAQ
        - Book borrowing quantity -> matches library book borrowing FAQ
        - Direct 2nd year entry -> matches lateral entry FAQ
        """
        # Test 1: Attendance with conversational prefix
        res1 = self.agent.ask("Could you please tell me how much attendance is compulsory for semester exams?", record_log=False)
        self.assertEqual(res1["status"], "RESOLVED")
        self.assertEqual(res1["matched_faq"]["category"], "Academics")
        self.assertIn("75%", res1["answer"])

        # Test 2: Fee payment reworded with acronym
        res2 = self.agent.ask("Can I pay my semester tuition fees through UPI or net banking?", record_log=False)
        self.assertEqual(res2["status"], "RESOLVED")
        self.assertEqual(res2["matched_faq"]["category"], "Fees")
        self.assertIn("Payment Gateway", res2["answer"])

        # Test 3: Library books limit reworded
        res3 = self.agent.ask("how many books can I issue from the library at once?", record_log=False)
        self.assertEqual(res3["status"], "RESOLVED")
        self.assertEqual(res3["matched_faq"]["category"], "Library")
        self.assertIn("3 books", res3["answer"])

        # Test 4: Lateral entry polytechnic diploma
        res4 = self.agent.ask("I completed my diploma, how to get admission in direct second year engineering?", record_log=False)
        self.assertEqual(res4["status"], "RESOLVED")
        self.assertEqual(res4["matched_faq"]["category"], "Admissions")
        self.assertIn("Lateral Entry", res4["answer"])

    # -------------------------------------------------------------------------
    # 2. Similar FAQs / Fine-Grained Discrimination
    # -------------------------------------------------------------------------

    def test_similar_faqs_library_discrimination(self):
        """
        Ensures that distinct questions within the same category (Library)
        discriminate correctly between:
        - FAQ #10: Working hours and timings
        - FAQ #11: Borrowing limits and duration
        - FAQ #12: Overdue late return fine
        """
        # Query A: Timings
        res_a = self.agent.ask("what are the central library working hours and timings?", record_log=False)
        self.assertEqual(res_a["status"], "RESOLVED")
        self.assertIn("8:00 AM to 8:00 PM", res_a["answer"])
        self.assertIn("timings", res_a["matched_faq"]["question"].lower())

        # Query B: Borrowing book limits
        res_b = self.agent.ask("how many books can a student take and for how many days?", record_log=False)
        self.assertEqual(res_b["status"], "RESOLVED")
        self.assertIn("3 books", res_b["answer"])
        self.assertIn("borrow", res_b["matched_faq"]["question"].lower())

        # Query C: Overdue late fines
        res_c = self.agent.ask("what is the late fee penalty for delayed book returns in library?", record_log=False)
        self.assertEqual(res_c["status"], "RESOLVED")
        self.assertIn("Rs. 2 per day", res_c["answer"])
        self.assertIn("fine", res_c["matched_faq"]["question"].lower())

    def test_similar_faqs_admissions_discrimination(self):
        """
        Ensures fine-grained discrimination between similar FAQs in Admissions:
        - FAQ #1: Eligibility criteria (percentages, cutoff)
        - FAQ #2: Documents required for verification (certificates, marksheet)
        - FAQ #3: Lateral entry admission (diploma, 2nd year)
        """
        res_eligibility = self.agent.ask("what is the minimum percentage required for btech admission?", record_log=False)
        self.assertEqual(res_eligibility["status"], "RESOLVED")
        self.assertIn("60% aggregate", res_eligibility["answer"])

        res_docs = self.agent.ask("which certificates and documents are needed for admission verification?", record_log=False)
        self.assertEqual(res_docs["status"], "RESOLVED")
        self.assertIn("mark sheets", res_docs["answer"])
        self.assertIn("documents", res_docs["matched_faq"]["question"].lower())

        res_lateral = self.agent.ask("what is the process for direct second year lateral entry admission?", record_log=False)
        self.assertEqual(res_lateral["status"], "RESOLVED")
        self.assertIn("Lateral Entry", res_lateral["answer"])

    # -------------------------------------------------------------------------
    # 3. Ambiguous Queries
    # -------------------------------------------------------------------------

    def test_ambiguous_queries_handling(self):
        """
        Verifies handling of queries that span multiple categories or touch multiple FAQs:
        e.g. 'minimum attendance for semester exams' (spans Academics and Examinations)
        Verifies the agent does not crash, provides a top candidate, and detects
        category ambiguity in the intent analysis.
        """
        query = "minimum attendance for semester exams"
        res = self.agent.ask(query, record_log=False)
        self.assertEqual(res["status"], "RESOLVED")
        self.assertIn(res["matched_faq"]["category"], ["Academics", "Examinations"])
        self.assertGreaterEqual(len(res["suggested_questions"]), 1)

        # Verify category intent report detects ambiguity between Academics and Examinations
        report = self.agent.get_category_intent_report(query)
        self.assertTrue(report["is_ambiguous"])
        self.assertIn("Academics", report["competing_categories"])
        self.assertIn("Examinations", report["competing_categories"])

    # -------------------------------------------------------------------------
    # 4. Empty and Punctuation-Only Inputs
    # -------------------------------------------------------------------------

    def test_empty_and_whitespace_input(self):
        """Verifies empty or whitespace-only messages are cleanly rejected."""
        res_empty = self.agent.ask("", record_log=False)
        self.assertEqual(res_empty["status"], "EMPTY_QUERY")
        self.assertFalse(res_empty["success"])
        self.assertEqual(res_empty["confidence"], 0.0)

        res_spaces = self.agent.ask("     ", record_log=False)
        self.assertEqual(res_spaces["status"], "EMPTY_QUERY")
        self.assertFalse(res_spaces["success"])

        res_tabs = self.agent.ask("\t \n \r", record_log=False)
        self.assertEqual(res_tabs["status"], "EMPTY_QUERY")

    def test_punctuation_only_input_rejection(self):
        """
        Verifies inputs with only punctuation or symbols (e.g. '???', '!@#$')
        are cleanly rejected as EMPTY_QUERY rather than causing all-zero vector lookups.
        """
        res_q = self.agent.ask("???", record_log=False)
        self.assertEqual(res_q["status"], "EMPTY_QUERY")
        self.assertFalse(res_q["success"])

        res_symbols = self.agent.ask("!@#$%^&*()_+", record_log=False)
        self.assertEqual(res_symbols["status"], "EMPTY_QUERY")
        self.assertFalse(res_symbols["success"])

    # -------------------------------------------------------------------------
    # 5. Irrelevant and Out-of-Domain Questions
    # -------------------------------------------------------------------------

    def test_unknown_question_reliable_fallback(self):
        """
        Verifies that completely irrelevant questions trigger a polite fallback
        without hallucination or fabricated answers, and do not show contact directory.
        """
        res = self.agent.ask("How do I bake chocolate chip cookies in Python?", record_log=False)
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "FALLBACK")
        self.assertIsNone(res["matched_faq"])
        self.assertIn("not available in the current FAQ knowledge base", res["answer"])
        self.assertNotIn("College Contact Directory", res["answer"])

    def test_irrelevant_queries_fallback_safeguard(self):
        """
        Additional tests for arbitrary out-of-domain queries:
        - 'who is the president of Mars?'
        - 'how to write quicksort in C++'
        - 'what is the recipe for pasta'
        """
        irrelevant_queries = [
            "who won the football world cup in 1998?",
            "explain quantum entanglement in Hindi",
            "how to repair a flat bicycle tire"
        ]
        for query in irrelevant_queries:
            res = self.agent.ask(query, record_log=False)
            self.assertFalse(res["success"])
            self.assertEqual(res["status"], "FALLBACK")
            self.assertIsNone(res["matched_faq"])
            self.assertLess(res["confidence"], self.agent.threshold)

    # -------------------------------------------------------------------------
    # 6. Configurable Confidence Threshold & Low Similarity Protection
    # -------------------------------------------------------------------------

    def test_configurable_threshold(self):
        """Verifies that increasing the threshold causes borderline matches to fall back."""
        query = "Can you tell me about the campus facilities?"

        # Low threshold (0.15) should resolve
        agent_low = SmartFAQAgent(threshold=0.15, db_path=self.temp_db_path)
        res_low = agent_low.ask(query, record_log=False)
        self.assertEqual(res_low["status"], "RESOLVED")

        # Extremely high threshold (0.95) should fall back unless exact
        agent_high = SmartFAQAgent(threshold=0.95, db_path=self.temp_db_path)
        res_high = agent_high.ask(query, record_log=False)
        self.assertEqual(res_high["status"], "FALLBACK")

    def test_per_call_threshold_override(self):
        """Verifies passing a threshold directly to ask() overrides the agent instance threshold."""
        query = "Can you tell me about the campus facilities?"

        # With default agent threshold (0.25):
        res_default = self.agent.ask(query, record_log=False)
        self.assertEqual(res_default["status"], "RESOLVED")

        # Passing threshold=0.85 per call:
        res_strict = self.agent.ask(query, threshold=0.85, record_log=False)
        self.assertEqual(res_strict["status"], "FALLBACK")
        self.assertIsNone(res_strict["matched_faq"])

    def test_low_similarity_never_returns_incorrect_answer(self):
        """
        Ensures that when similarity is below threshold, an answer is NEVER returned as RESOLVED.
        Status must be FALLBACK, matched_faq must be None, and success must be False.
        """
        query = "Do alien spaceships land in the college football field?"
        res = self.agent.ask(query, record_log=False)
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "FALLBACK")
        self.assertIsNone(res["matched_faq"])
        self.assertLess(res["confidence"], self.agent.threshold)
        self.assertIn("not available in the current FAQ knowledge base", res["answer"])

    # -------------------------------------------------------------------------
    # 7. Greetings and Conversational Utility
    # -------------------------------------------------------------------------

    def test_greeting_handling(self):
        """Verifies standard greetings return a welcoming introduction without error."""
        res = self.agent.ask("Hello!", record_log=False)
        self.assertEqual(res["status"], "GREETING")
        self.assertTrue(res["success"])
        self.assertIn("Smart College FAQ Assistant", res["answer"])

    def test_category_filtering(self):
        """
        Verifies that applying a category filter restricts matching to only that category.
        """
        res = self.agent.ask("how can I change or update my courses?", category_filter="Academics", record_log=False)
        self.assertEqual(res["status"], "RESOLVED")
        self.assertEqual(res["matched_faq"]["category"], "Academics")

    # -------------------------------------------------------------------------
    # 8. Diagnostics & Retrieval-Based Non-LLM Architecture Verification
    # -------------------------------------------------------------------------

    def test_explain_query_debug_structure(self):
        """
        Verifies the explain_query debug output contains required analytical components,
        including top match details, confidence score, and retrieval-based engine type.
        """
        report = self.agent.explain_query("What is the attendance criteria?")
        self.assertIn("raw_query", report)
        self.assertIn("normalized_query", report)
        self.assertIn("decision", report)
        self.assertIn("top_match", report)
        self.assertIn("all_ranked_candidates", report)
        self.assertIn("engine_type", report)
        self.assertIn("Retrieval-Based", report["engine_type"])
        self.assertIn("Non-Generative", report["engine_type"])
        self.assertGreater(len(report["all_ranked_candidates"]), 0)

        # Check top_match contains full metadata for admin diagnostics
        top = report["top_match"]
        self.assertIn("faq_id", top)
        self.assertIn("question", top)
        self.assertIn("answer", top)
        self.assertIn("similarity_score", top)
        self.assertIn("confidence_percent", top)

    def test_knowledge_base_reloading(self):
        """Verifies dynamic reloading after adding a new FAQ into SQLite."""
        new_q = "Is electric scooter charging permitted on college campus?"
        new_a = "[DEMO DATA] EV charging stations are available in the Student Parking Area near Gate 2."
        add_faq(new_q, new_a, "Facilities", "electric scooter ev charging vehicle", 0, db_path=self.temp_db_path)

        self.agent.reload_knowledge_base()
        res = self.agent.ask("where can I charge my electric scooter?", record_log=False)
        self.assertEqual(res["status"], "RESOLVED")
        self.assertIn("EV charging stations", res["answer"])

    # -------------------------------------------------------------------------
    # 9. Automated Verification for Required Test Queries & Paraphrases
    # -------------------------------------------------------------------------

    def test_nine_core_prompt_examples(self):
        """
        Explicitly verifies the 9 mandatory query examples from project specification:
        1. 'How can I apply for admission?' -> Admission application procedure
        2. 'What is the admission process?' -> Admission application procedure
        3. 'What courses are available?' -> Available courses / branches
        4. 'Which documents are required for admission?' -> Admission document checklist
        5. 'What are the eligibility criteria for B.Tech CSE?' -> Eligibility criteria FAQ
        6. 'When does the library open?' -> Library opening hours / timings
        7. 'How can I pay my fees?' -> Fee payment procedure
        8. 'What is the weather on Mars?' -> Polite unknown fallback, NO contact directory
        9. '' (empty message) -> Prompt user to enter a question
        """
        # 1. Admission Application
        r1 = self.agent.ask("How can I apply for admission?", record_log=False)
        self.assertTrue(r1["success"])
        self.assertEqual(r1["status"], "RESOLVED")
        self.assertEqual(r1["matched_faq"]["category"], "Admissions")
        self.assertIn("application procedure", r1["answer"].lower())

        # 2. Admission Process
        r2 = self.agent.ask("What is the admission process?", record_log=False)
        self.assertTrue(r2["success"])
        self.assertEqual(r2["status"], "RESOLVED")
        self.assertEqual(r2["matched_faq"]["category"], "Admissions")
        self.assertEqual(r2["matched_faq"]["id"], r1["matched_faq"]["id"])

        # 3. Available Courses
        r3 = self.agent.ask("What courses are available?", record_log=False)
        self.assertTrue(r3["success"])
        self.assertEqual(r3["status"], "RESOLVED")
        self.assertEqual(r3["matched_faq"]["category"], "Academics")
        self.assertIn("Computer Science & Engineering", r3["answer"])

        # 4. Required Documents
        r4 = self.agent.ask("Which documents are required for admission?", record_log=False)
        self.assertTrue(r4["success"])
        self.assertEqual(r4["status"], "RESOLVED")
        self.assertEqual(r4["matched_faq"]["category"], "Admissions")
        self.assertIn("mandatory documents", r4["answer"].lower())

        # 5. Eligibility Criteria B.Tech CSE
        r5 = self.agent.ask("What are the eligibility criteria for B.Tech CSE?", record_log=False)
        self.assertTrue(r5["success"])
        self.assertEqual(r5["status"], "RESOLVED")
        self.assertEqual(r5["matched_faq"]["category"], "Admissions")
        self.assertIn("60% aggregate", r5["answer"])

        # 6. Library Timings
        r6 = self.agent.ask("When does the library open?", record_log=False)
        self.assertTrue(r6["success"])
        self.assertEqual(r6["status"], "RESOLVED")
        self.assertEqual(r6["matched_faq"]["category"], "Library")
        self.assertIn("8:00 AM", r6["answer"])

        # 7. Fee Payment
        r7 = self.agent.ask("How can I pay my fees?", record_log=False)
        self.assertTrue(r7["success"])
        self.assertEqual(r7["status"], "RESOLVED")
        self.assertEqual(r7["matched_faq"]["category"], "Fees")
        self.assertIn("Net Banking", r7["answer"])

        # 8. Weather on Mars (Out-of-domain)
        r8 = self.agent.ask("What is the weather on Mars?", record_log=False)
        self.assertFalse(r8["success"])
        self.assertEqual(r8["status"], "FALLBACK")
        self.assertIsNone(r8["matched_faq"])
        self.assertIn("not available in the current FAQ knowledge base", r8["answer"])
        self.assertNotIn("College Contact Directory", r8["answer"])
        self.assertNotIn("admissions@demo-college.edu", r8["answer"])

        # 9. Empty message
        r9 = self.agent.ask("", record_log=False)
        self.assertFalse(r9["success"])
        self.assertEqual(r9["status"], "EMPTY_QUERY")
        self.assertIn("Please enter a question", r9["answer"])

    def test_paraphrased_core_questions(self):
        """Verifies paraphrased natural-language formulations of the core FAQ queries."""
        paraphrases = [
            ("how do i register for freshman admission?", "Admissions", "application procedure"),
            ("what branches of study can students choose from?", "Academics", "branches"),
            ("what certificates must i submit during admission verification?", "Admissions", "documents"),
            ("what marks are required to get into btech cse?", "Admissions", "60% aggregate"),
            ("what are the opening hours of central library?", "Library", "8:00 AM"),
            ("can i pay my tuition fees via UPI or cards?", "Fees", "payment")
        ]
        for query, expected_cat, answer_cue in paraphrases:
            res = self.agent.ask(query, record_log=False)
            self.assertTrue(res["success"], f"Failed query: {query}")
            self.assertEqual(res["status"], "RESOLVED", f"Expected RESOLVED for '{query}'")
            self.assertEqual(res["matched_faq"]["category"], expected_cat)
            self.assertIn(answer_cue.lower(), res["answer"].lower())

    def test_database_failure_handling(self):
        """Verifies the agent gracefully handles empty or non-existent database paths without crashing."""
        empty_fd, empty_path = tempfile.mkstemp(suffix=".db")
        os.close(empty_fd)
        try:
            # Point agent to a completely empty SQLite file without tables
            broken_agent = SmartFAQAgent(threshold=0.25, db_path=empty_path)
            res = broken_agent.ask("How to apply for admission?", record_log=False)
            self.assertFalse(res["success"])
            self.assertEqual(res["status"], "FALLBACK")
        finally:
            if os.path.exists(empty_path):
                os.remove(empty_path)


if __name__ == "__main__":
    unittest.main()
