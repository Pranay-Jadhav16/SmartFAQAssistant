"""
Live verification test suite for unified single-page layout, API endpoints,
and security constraints.
"""
import unittest
import urllib.request
import urllib.parse
import json
import http.cookiejar


class TestLiveSPA(unittest.TestCase):
    base_url = "http://127.0.0.1:5000"

    @classmethod
    def setUpClass(cls):
        try:
            req = urllib.request.urlopen(cls.base_url + "/", timeout=3)
            cls.server_running = (req.status == 200)
        except Exception:
            cls.server_running = False

    def setUp(self):
        if not getattr(self, "server_running", False):
            self.skipTest("Flask server is not running on http://127.0.0.1:5000")

    def test_live_spa_complete_flow(self):
        # 1. Root SPA Page Verification
        req = urllib.request.urlopen(self.base_url + "/")
        html = req.read().decode("utf-8")
        self.assertEqual(req.status, 200)
        self.assertIn("Smart FAQ Assistant", html)
        self.assertIn('id="section-home"', html)
        self.assertIn('id="section-chat"', html)
        self.assertIn('id="section-faqs"', html)
        self.assertIn('id="section-categories"', html)
        self.assertIn('id="section-about"', html)
        self.assertIn('id="section-admin"', html)

        # 2. Chatbot API: Verified Question Matching
        payload = json.dumps({"query": "What is the 75% attendance rule?", "category": ""}).encode("utf-8")
        req_chat = urllib.request.Request(f"{self.base_url}/api/chat", data=payload, headers={"Content-Type": "application/json"})
        res = urllib.request.urlopen(req_chat)
        chat_res = json.loads(res.read().decode("utf-8"))
        self.assertTrue(chat_res["success"])
        self.assertEqual(chat_res["status"], "RESOLVED")
        self.assertIn("75%", chat_res["answer"])
        log_id = chat_res.get("log_id")
        self.assertIsNotNone(log_id)

        # 3. Chatbot Feedback API
        feedback_payload = json.dumps({"log_id": log_id, "feedback": "HELPFUL"}).encode("utf-8")
        req_fb = urllib.request.Request(f"{self.base_url}/api/feedback", data=feedback_payload, headers={"Content-Type": "application/json"})
        res_fb = urllib.request.urlopen(req_fb)
        fb_res = json.loads(res_fb.read().decode("utf-8"))
        self.assertTrue(fb_res["success"])

        # 4. Chatbot Fallback for Out-of-Domain Question (Mars/arbitrary)
        fallback_payload = json.dumps({"query": "What is the weather on Mars?", "category": ""}).encode("utf-8")
        req_fbk = urllib.request.Request(f"{self.base_url}/api/chat", data=fallback_payload, headers={"Content-Type": "application/json"})
        res_fbk = urllib.request.urlopen(req_fbk)
        fbk_data = json.loads(res_fbk.read().decode("utf-8"))
        self.assertFalse(fbk_data["success"])
        self.assertEqual(fbk_data["status"], "FALLBACK")
        self.assertIn("not available in the current FAQ knowledge base", fbk_data["answer"])
        self.assertNotIn("College Contact Directory", fbk_data["answer"])

        # 5. Public Categories API
        req_cat = urllib.request.urlopen(f"{self.base_url}/api/categories")
        cat_data = json.loads(req_cat.read().decode("utf-8"))
        self.assertEqual(len(cat_data.get("categories", [])), 6)

        # 6. Admin Authentication & Route Protection
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

        login_data = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode("utf-8")
        req_login = urllib.request.Request(f"{self.base_url}/admin/login", data=login_data)
        res_login = opener.open(req_login)
        login_html = res_login.read().decode("utf-8")
        self.assertTrue("Administrator Dashboard" in login_html or res_login.status == 200)

        # 7. Access diagnostics while authenticated
        req_diag = urllib.request.Request(f"{self.base_url}/admin/debug?q=attendance")
        res_diag = opener.open(req_diag)
        diag_html = res_diag.read().decode("utf-8")
        self.assertEqual(res_diag.status, 200)
        self.assertIn("AI Agent Match Diagnostics", diag_html)


if __name__ == "__main__":
    unittest.main()
