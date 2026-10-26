"""
Smart FAQ Assistant - AI Agent Module
Implements a deterministic, multi-stage retrieval-based question-answering agent pipeline:

1. Input Validation & Sanitization (rejection of empty, whitespace, and non-alphanumeric input)
2. Text Preprocessing & Normalization (contraction expansion, acronym preservation,
   conversational filler removal, typo correction, and token normalization)
3. Intent & Category Identification (phrase & keyword matching with ambiguity detection)
4. Knowledge Base Retrieval & TF-IDF Vectorization (unigram/bigram n-grams, sublinear TF)
5. Cosine Similarity Ranking & Candidate Evaluation (directional cosine metric)
6. Decision Engine & Configurable Confidence Assessment (thresholding, strict fallback)
7. Explainability & Diagnostics (transparent mathematical reasoning and top candidate ranking)

ARCHITECTURAL NOTE:
This system is an explainable, deterministic RETRIEVAL-BASED FAQ Agent using scikit-learn
TF-IDF and Cosine Similarity. It does NOT use a generative Large Language Model (LLM).
This architecture guarantees zero hallucinations, verifiable factual grounding directly
from college database records, instant offline execution, and complete student privacy.
"""

import os
import re
import string
import numpy as np
from sklearn.pipeline import FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from database import (
    get_all_faqs,
    log_interaction,
    VALID_CATEGORIES
)

DEFAULT_THRESHOLD = float(os.environ.get("FAQ_MATCH_THRESHOLD", 0.25))

# Common college domain category keywords for intent classification
CATEGORY_KEYWORDS = {
    "Admissions": [
        "admission", "admissions", "apply", "application", "eligibility", "criteria",
        "cutoff", "cutoffs", "entrance", "jee", "cet", "cap", "lateral", "polytechnic",
        "quota", "seats", "12th", "hsc", "documents", "counseling", "merit"
    ],
    "Academics": [
        "attendance", "absent", "leave", "medical", "cgpa", "sgpa", "gpa", "credit",
        "credits", "elective", "electives", "syllabus", "curriculum", "course",
        "semester", "hod", "counselor", "academic", "regulations"
    ],
    "Examinations": [
        "exam", "exams", "examination", "mid-term", "end-term", "unit test", "in-sem",
        "schedule", "timetable", "hall ticket", "admit card", "revaluation",
        "rechecking", "photocopy", "marksheet", "backlog", "arrear", "kt", "grade"
    ],
    "Library": [
        "library", "book", "books", "borrow", "issue", "return", "renew", "due",
        "fine", "overdue", "journal", "reading room", "hours", "timings", "smart card"
    ],
    "Fees": [
        "fee", "fees", "tuition", "payment", "pay", "online payment", "net banking",
        "upi", "dd", "demand draft", "installment", "installments", "scholarship",
        "concession", "ebc", "refund", "receipt"
    ],
    "Facilities": [
        "hostel", "room", "accommodation", "mess", "food", "warden", "gym", "gymnasium",
        "sports", "ground", "badminton", "cricket", "basketball", "bus", "transport",
        "transportation", "parking", "canteen", "wifi", "medical", "clinic"
    ]
}

# Multi-word key phrases for high-confidence intent classification
CATEGORY_PHRASES = {
    "Admissions": [
        "direct second year", "lateral entry", "b tech admission", "eligibility criteria",
        "admission documents", "cutoff marks", "cap process", "admission procedure"
    ],
    "Academics": [
        "minimum attendance", "attendance requirement", "attendance percentage", "medical leave",
        "grade point", "credit system", "syllabus copy", "academic calendar", "course registration"
    ],
    "Examinations": [
        "hall ticket", "admit card", "exam timetable", "semester exams", "paper revaluation",
        "revaluation procedure", "backlog exam", "unit test", "in sem exam", "end semester"
    ],
    "Library": [
        "central library", "library hours", "reading room", "borrow books", "book issue",
        "overdue fine", "library card", "smart card", "library fine"
    ],
    "Fees": [
        "tuition fee", "fee payment", "net banking", "demand draft", "fee concession",
        "merit scholarship", "hostel refund", "installment payment", "payment gateway"
    ],
    "Facilities": [
        "hostel accommodation", "sports complex", "badminton court", "college bus",
        "day scholar", "bus pass", "ev charging", "student parking", "gym facility"
    ]
}

CONTRACTIONS = {
    "what's": "what is",
    "where's": "where is",
    "how's": "how is",
    "when's": "when is",
    "who's": "who is",
    "can't": "cannot",
    "won't": "will not",
    "don't": "do not",
    "doesn't": "does not",
    "didn't": "did not",
    "i'm": "i am",
    "i've": "i have",
    "i'll": "i will",
    "it's": "it is",
    "there's": "there is",
    "aren't": "are not",
    "isn't": "is not"
}

# Normalization of academic acronyms and dot notations before punctuation removal
ACRONYM_MAP = {
    r"\bb\.tech\b": "btech",
    r"\bb-tech\b": "btech",
    r"\bm\.tech\b": "mtech",
    r"\bc\.g\.p\.a\b": "cgpa",
    r"\bs\.g\.p\.a\b": "sgpa",
    r"\bg\.p\.a\b": "gpa",
    r"\bwi-fi\b": "wifi",
    r"\bj\.e\.e\b": "jee",
    r"\bc\.e\.t\b": "cet",
    r"\be\.r\.p\b": "erp",
    r"\bh\.o\.d\b": "hod",
    r"\bt\.c\b": "tc",
    r"\be\.b\.c\b": "ebc",
    r"\bu\.p\.i\b": "upi",
    r"\bd\.d\b": "demand draft",
    r"\bi\.d\b": "id card",
}

# Conversational prefix and filler expressions to strip for focused vectorization
CONVERSATIONAL_PREFIXES = [
    r"^can you (please )?(tell|explain|inform) (me )?(about )?",
    r"^could you (please )?(tell|explain|inform) (me )?(about )?",
    r"^please (tell|explain|let me know|help me with|inform) (me )?(about )?",
    r"^kindly (tell|explain|let me know|inform) (me )?(about )?",
    r"^i (want|would like) to know (about )?",
    r"^tell me (about )?",
    r"^give me (information|details) (about|on) ?",
    r"^do you know (about )?",
    r"^can someone (tell|explain) (me )?(about )?",
    r"^what is the process (to|for) ?",
    r"^how do i go about ?"
]

# Spelling correction and academic synonym expansion
SYNONYM_MAP = {
    r"\battendence\b": "attendance",
    r"\bcriterias\b": "criteria",
    r"\bhallticket\b": "hall ticket",
    r"\bhall-ticket\b": "hall ticket",
    r"\breval\b": "revaluation",
    r"\bre-valuation\b": "revaluation",
    r"\bmarksheets\b": "marksheet",
    r"\bmark-sheet\b": "marksheet",
    r"\bfee structure\b": "fees tuition amount",
    r"\btuition fee\b": "fees tuition",
    r"\blate fee\b": "overdue fine penalty",
    r"\blate fees\b": "overdue fine penalty",
    r"\bhostel room\b": "hostel accommodation",
    r"\btimetables\b": "timetable schedule",
    r"\btime-table\b": "timetable schedule",
    r"\bgymnasium\b": "gym sports fitness",
    r"\bapply\b": "apply admission application",
    r"\bapplying\b": "apply admission application",
    r"\bprocess\b": "procedure process",
    r"\bhow can i apply\b": "admission application procedure apply",
    r"\bavailable courses\b": "available courses degree branches programs",
}

DEPARTMENT_CONTACTS = {
    "Admissions": "Admissions Cell: admissions@demo-college.edu | Room 102, Admin Block (Ext: 101)",
    "Academics": "Academic Dean Office: academics@demo-college.edu | Room 201, Main Block (Ext: 102)",
    "Examinations": "Examination Cell: examcell@demo-college.edu | Room 104, Exam Building (Ext: 103)",
    "Library": "Central Library Helpdesk: library@demo-college.edu | Central Library 1st Floor (Ext: 105)",
    "Fees": "Student Accounts Section: accounts@demo-college.edu | Counter 3, Admin Block (Ext: 104)",
    "Facilities": "Campus Care / Hostel Office: campuscare@demo-college.edu | Warden Office (Ext: 106)"
}


class SmartFAQAgent:
    """
    Deterministic Retrieval-Based FAQ AI Agent.
    
    Combines preprocessing, intent detection, TF-IDF vectorization,
    cosine similarity ranking, configurable threshold validation, and explainability.
    
    Note: Does NOT utilize a generative Large Language Model (LLM). All answers are
    retrieved strictly from verified SQLite records to eliminate hallucinations.
    """

    def __init__(self, threshold=None, db_path=None):
        self.threshold = float(threshold) if threshold is not None else DEFAULT_THRESHOLD
        self.db_path = db_path
        self.vectorizer = None
        self.faq_records = []
        self.tfidf_matrix = None
        self.corpus_texts = []
        self.reload_knowledge_base()

    def reload_knowledge_base(self):
        """
        Reloads all FAQs from SQLite and recomputes the TF-IDF representation.
        Enables live updates when FAQs are added, updated, or removed in Admin.
        """
        try:
            self.faq_records = get_all_faqs(db_path=self.db_path)
        except Exception:
            self.faq_records = []

        if not self.faq_records:
            self.vectorizer = None
            self.tfidf_matrix = None
            self.corpus_texts = []
            return

        # Build corpus emphasizing question repetition for high cosine similarity on exact questions,
        # augmented with category and keywords for semantic recall
        self.corpus_texts = []
        for faq in self.faq_records:
            enriched_text = f"{faq['question']} {faq['question']} {faq['category']} {faq.get('keywords', '')}"
            normalized_corpus_item = self.preprocess(enriched_text, remove_fillers=False)
            self.corpus_texts.append(normalized_corpus_item)

        # Initialize hybrid TF-IDF Vectorizer combining word n-grams (1, 2)
        # and character n-grams within word boundaries (3, 5) for robust morphological matching
        self.vectorizer = FeatureUnion([
            ('word', TfidfVectorizer(
                ngram_range=(1, 2),
                sublinear_tf=True,
                stop_words="english",
                strip_accents="unicode"
            )),
            ('char', TfidfVectorizer(
                analyzer='char_wb',
                ngram_range=(3, 5),
                sublinear_tf=True,
                strip_accents="unicode"
            ))
        ])
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus_texts)

    @classmethod
    def preprocess(cls, text, remove_fillers=True):
        """
        Stage 2: Text Preprocessing & Normalization.
        - Lowercasing
        - Expanding contractions
        - Normalizing academic acronyms (e.g. b.tech -> btech)
        - Stripping conversational filler prefixes
        - Correcting common typos and expanding synonyms
        - Removing special characters & punctuation
        - Normalizing whitespace
        """
        if not text:
            return ""

        text = text.lower().strip()

        # Expand contractions
        for contraction, expanded in CONTRACTIONS.items():
            text = re.sub(r'\b' + re.escape(contraction) + r'\b', expanded, text)

        # Normalize acronyms before punctuation removal
        for pattern, replacement in ACRONYM_MAP.items():
            text = re.sub(pattern, replacement, text)

        # Strip conversational prefix expressions if requested
        if remove_fillers:
            for prefix_pattern in CONVERSATIONAL_PREFIXES:
                text = re.sub(prefix_pattern, "", text, flags=re.IGNORECASE).strip()

        # Apply synonym expansions and spelling corrections
        for pattern, replacement in SYNONYM_MAP.items():
            text = re.sub(pattern, replacement, text)

        # Remove punctuation except alphanumeric and space
        text = re.sub(r'[^\w\s]', ' ', text)

        # Normalize multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def identify_category_intent(self, query):
        """
        Stage 3: Intent & Category Identification.
        Evaluates query against multi-word domain phrases (weight 3) and keywords (weight 1).
        Detects ambiguity if multiple categories have close scores.
        Returns the best matching category or None if ambiguous/unmatched.
        """
        report = self.get_category_intent_report(query)
        if report["is_ambiguous"]:
            # If ambiguous, prefer None to avoid over-constraining unless top candidate is clear
            return None
        return report["detected_category"]

    def get_category_intent_report(self, query):
        """
        Detailed Category Intent Analysis.
        Returns dictionary containing:
        - detected_category: Top scoring category or None
        - confidence_score: Raw match weight score
        - is_ambiguous: True if competing categories exist with close scores
        - category_scores: Breakdown of scores across all categories
        - matched_cues: Specific phrases or keywords found
        """
        normalized = self.preprocess(query, remove_fillers=False)
        words = set(normalized.split())

        scores = {cat: 0 for cat in VALID_CATEGORIES}
        matched_cues = {cat: [] for cat in VALID_CATEGORIES}

        # 1. Match multi-word phrases (higher weight: +3)
        for cat, phrases in CATEGORY_PHRASES.items():
            for phrase in phrases:
                if phrase in normalized:
                    scores[cat] += 3
                    matched_cues[cat].append(f"phrase: '{phrase}'")

        # 2. Match single keywords (weight: +1)
        for cat, keywords in CATEGORY_KEYWORDS.items():
            overlap = words.intersection(set(keywords))
            for word in overlap:
                scores[cat] += 1
                matched_cues[cat].append(f"keyword: '{word}'")

        # Filter categories with score > 0
        active_scores = {k: v for k, v in scores.items() if v > 0}

        if not active_scores:
            return {
                "detected_category": None,
                "confidence_score": 0,
                "is_ambiguous": False,
                "category_scores": scores,
                "matched_cues": matched_cues
            }

        sorted_cats = sorted(active_scores.items(), key=lambda x: x[1], reverse=True)
        top_cat, top_score = sorted_cats[0]

        # Check for ambiguity: if second category has same score or within 1 point and both >= 2
        is_ambiguous = False
        if len(sorted_cats) > 1:
            second_cat, second_score = sorted_cats[1]
            if top_score == second_score or (top_score - second_score <= 1 and second_score >= 2):
                is_ambiguous = True

        return {
            "detected_category": top_cat,
            "confidence_score": top_score,
            "is_ambiguous": is_ambiguous,
            "competing_categories": [c[0] for c in sorted_cats[:2]] if is_ambiguous else [top_cat],
            "category_scores": active_scores,
            "matched_cues": {k: v for k, v in matched_cues.items() if v}
        }

    def ask(self, user_query, category_filter=None, threshold=None, record_log=True):
        """
        Full Agent Execution Pipeline:
        1. Validate query (reject empty / whitespace / punctuation-only inputs)
        2. Preprocess & Normalize
        3. Category Intent Detection
        4. Vectorize & Rank Candidates using Cosine Similarity
        5. Evaluate Confidence vs. Configurable Threshold
        6. Produce Response with Suggestions & Explainability
        7. Record Interaction Log
        """
        active_threshold = float(threshold) if threshold is not None else self.threshold

        # --- Stage 1: Validation ---
        if not user_query or not user_query.strip():
            return {
                "success": False,
                "status": "EMPTY_QUERY",
                "answer": "Please enter a question so I can assist you with your college query.",
                "confidence": 0.0,
                "confidence_percent": 0.0,
                "matched_faq": None,
                "detected_category": None,
                "suggested_questions": self.get_quick_suggestions(),
                "log_id": None,
                "explanation": {
                    "reason": "Input was empty or contained only whitespace.",
                    "status": "EMPTY_QUERY",
                    "engine": "Retrieval-Based FAQ Agent (TF-IDF + Cosine Similarity)"
                }
            }

        raw_query = user_query.strip()

        # Reject inputs that contain no alphanumeric characters (e.g. "???", "!@#$", "...")
        if not re.search(r'[a-zA-Z0-9]', raw_query):
            return {
                "success": False,
                "status": "EMPTY_QUERY",
                "answer": "Please type a valid question using words or numbers so I can assist you.",
                "confidence": 0.0,
                "confidence_percent": 0.0,
                "matched_faq": None,
                "detected_category": None,
                "suggested_questions": self.get_quick_suggestions(),
                "log_id": None,
                "explanation": {
                    "reason": "Input contained only punctuation or symbols without textual content.",
                    "status": "EMPTY_QUERY",
                    "engine": "Retrieval-Based FAQ Agent (TF-IDF + Cosine Similarity)"
                }
            }

        normalized_query = self.preprocess(raw_query)

        # Check for very short / greeting queries
        greetings = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "namaste", "help"}
        if normalized_query in greetings:
            return {
                "success": True,
                "status": "GREETING",
                "answer": (
                    "Hello! 👋 I am your Smart College FAQ Assistant (Retrieval-Based QA System). "
                    "I can answer questions regarding Admissions, Academics, Examinations, "
                    "Library rules, Tuition Fees, and Campus Facilities. How can I help you today?"
                ),
                "confidence": 1.0,
                "confidence_percent": 100.0,
                "matched_faq": None,
                "detected_category": None,
                "suggested_questions": self.get_quick_suggestions(),
                "log_id": None,
                "explanation": {
                    "reason": "Detected standard greeting/welcome intent.",
                    "status": "GREETING",
                    "engine": "Retrieval-Based FAQ Agent (TF-IDF + Cosine Similarity)"
                }
            }

        # --- Stage 3: Category Identification ---
        category_report = self.get_category_intent_report(raw_query)
        detected_category = category_report["detected_category"]
        effective_category = category_filter if (category_filter and category_filter != "all") else None

        # --- Stage 4 & 5: Retrieval & Similarity Ranking ---
        if not self.faq_records or self.vectorizer is None or self.tfidf_matrix is None:
            return self._fallback_response(
                raw_query,
                detected_category or effective_category,
                threshold=active_threshold,
                reason="Knowledge base is currently empty.",
                record_log=record_log
            )

        # Transform query into TF-IDF vector space
        query_vec = self.vectorizer.transform([normalized_query])

        # Compute cosine similarity against all FAQs in corpus
        sim_scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Build candidate list with metadata
        candidates = []
        for idx, score in enumerate(sim_scores):
            faq = self.faq_records[idx]

            # If user selected an explicit category filter, apply hard constraint
            if effective_category and faq["category"].lower() != effective_category.lower():
                continue

            candidates.append({
                "index": idx,
                "faq": faq,
                "score": float(score)
            })

        # Rank candidates by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # Check if we have a valid candidate meeting the configured threshold
        if not candidates or candidates[0]["score"] < active_threshold:
            best_score = candidates[0]["score"] if candidates else 0.0
            return self._fallback_response(
                raw_query,
                effective_category or detected_category,
                best_score=best_score,
                threshold=active_threshold,
                candidates=candidates[:3],
                category_report=category_report,
                record_log=record_log
            )

        # --- Stage 6: Confident Match Found ---
        best_candidate = candidates[0]
        matched_faq = best_candidate["faq"]
        best_score = round(best_candidate["score"], 4)
        confidence_percent = round(best_score * 100, 1)

        # Check for ambiguity among top candidates (top 2 candidates very close in score)
        is_query_ambiguous = False
        if len(candidates) > 1:
            second_score = candidates[1]["score"]
            if best_score < 0.70 and (best_score - second_score) <= 0.04:
                is_query_ambiguous = True

        # Suggest 2-3 relevant follow-up questions from the same category
        suggested_questions = []
        for cand in candidates[1:6]:
            if cand["score"] > 0.05 and cand["faq"]["id"] != matched_faq["id"] and cand["faq"]["category"] == matched_faq["category"]:
                suggested_questions.append({
                    "id": cand["faq"]["id"],
                    "question": cand["faq"]["question"],
                    "category": cand["faq"]["category"]
                })
            if len(suggested_questions) >= 3:
                break

        # If not enough suggestions from top candidates in same category, fill from same category
        if len(suggested_questions) < 2:
            same_cat_faqs = [
                f for f in self.faq_records
                if f["category"] == matched_faq["category"] and f["id"] != matched_faq["id"]
            ]
            for extra in same_cat_faqs:
                if not any(s["id"] == extra["id"] for s in suggested_questions):
                    suggested_questions.append({
                        "id": extra["id"],
                        "question": extra["question"],
                        "category": extra["category"]
                    })
                if len(suggested_questions) >= 3:
                    break

        # Build explainability payload for admin diagnostics
        explanation = {
            "status": "RESOLVED",
            "similarity_score": best_score,
            "confidence_percent": confidence_percent,
            "threshold": active_threshold,
            "detected_category": detected_category,
            "category_intent_report": category_report,
            "is_ambiguous": is_query_ambiguous,
            "filter_applied": effective_category,
            "engine": "Retrieval-Based FAQ Agent (TF-IDF + Cosine Similarity - Non-Generative)",
            "decision": f"Matched FAQ #{matched_faq['id']} with score {best_score:.4f} (>= {active_threshold:.2f})",
            "top_candidates": [
                {
                    "id": c["faq"]["id"],
                    "question": c["faq"]["question"],
                    "category": c["faq"]["category"],
                    "score": round(c["score"], 4)
                } for c in candidates[:5]
            ]
        }

        # --- Stage 7: Interaction Logging ---
        log_id = None
        if record_log:
            try:
                log_id = log_interaction(
                    user_query=raw_query,
                    category_filter=effective_category,
                    matched_faq_id=matched_faq["id"],
                    matched_question=matched_faq["question"],
                    similarity_score=best_score,
                    response_status="RESOLVED",
                    db_path=self.db_path
                )
            except Exception:
                log_id = None

        return {
            "success": True,
            "status": "RESOLVED",
            "answer": matched_faq["answer"],
            "matched_faq": {
                "id": matched_faq["id"],
                "question": matched_faq["question"],
                "category": matched_faq["category"],
                "is_demo": matched_faq.get("is_demo", 0)
            },
            "confidence": best_score,
            "confidence_percent": confidence_percent,
            "is_ambiguous": is_query_ambiguous,
            "detected_category": detected_category or matched_faq["category"],
            "suggested_questions": suggested_questions,
            "log_id": log_id,
            "explanation": explanation
        }

    def _fallback_response(self, raw_query, category=None, best_score=0.0,
                           threshold=None, candidates=None, category_report=None,
                           reason=None, record_log=True):
        """
        Stage 6b: Reliable Unknown-Answer Handling.
        Generates a polite fallback response without fabricating information.
        Suggests relevant department contact based on detected or selected category.
        """
        active_threshold = float(threshold) if threshold is not None else self.threshold

        contact_info = ""
        # Only display department contact if a relevant category is detected or selected
        if category and category in DEPARTMENT_CONTACTS:
            contact_info = f"\n\n📍 **Recommended Department Contact ({category}):**\n{DEPARTMENT_CONTACTS[category]}"

        fallback_answer = (
            "I apologize, but an answer to your question is not available in the current FAQ knowledge base."
            f"{contact_info}\n\n"
            "Please try rephrasing your question or select a relevant college category (Admissions, Academics, "
            "Examinations, Library, Fees, or Facilities)."
        )

        explanation = {
            "status": "FALLBACK",
            "similarity_score": round(best_score, 4),
            "threshold": active_threshold,
            "detected_category": category,
            "category_intent_report": category_report,
            "engine": "Retrieval-Based FAQ Agent (TF-IDF + Cosine Similarity - Non-Generative)",
            "reason": reason or f"Best similarity score ({best_score:.4f}) fell below threshold ({active_threshold:.2f})",
            "top_candidates": [
                {
                    "id": c["faq"]["id"],
                    "question": c["faq"]["question"],
                    "category": c["faq"]["category"],
                    "score": round(c["score"], 4)
                } for c in (candidates or [])[:3]
            ]
        }

        log_id = None
        if record_log:
            try:
                top_faq_id = candidates[0]["faq"]["id"] if candidates else None
                top_q = candidates[0]["faq"]["question"] if candidates else None
                log_id = log_interaction(
                    user_query=raw_query,
                    category_filter=category,
                    matched_faq_id=top_faq_id,
                    matched_question=top_q,
                    similarity_score=best_score,
                    response_status="FALLBACK",
                    db_path=self.db_path
                )
            except Exception:
                log_id = None

        return {
            "success": False,
            "status": "FALLBACK",
            "answer": fallback_answer,
            "confidence": round(best_score, 4),
            "confidence_percent": round(best_score * 100, 1),
            "matched_faq": None,
            "detected_category": category,
            "suggested_questions": self.get_quick_suggestions(category),
            "log_id": log_id,
            "explanation": explanation
        }

    def get_quick_suggestions(self, category=None):
        """Returns at most 2-3 relevant sample questions."""
        if not self.faq_records:
            return []

        if category and category.lower() != "all":
            filtered = [f for f in self.faq_records if f["category"].lower() == category.lower()]
            if filtered:
                return [{"id": f["id"], "question": f["question"], "category": f["category"]} for f in filtered[:3]]

        # Pick 2-3 representative questions across core categories
        picked = []
        seen_cats = set()
        for faq in self.faq_records:
            if faq["category"] not in seen_cats:
                picked.append({
                    "id": faq["id"],
                    "question": faq["question"],
                    "category": faq["category"]
                })
                seen_cats.add(faq["category"])
                if len(picked) >= 3:
                    break
        return picked

    def explain_query(self, user_query, category_filter=None, threshold=None):
        """
        Admin Diagnostics & Inspection Method.
        Returns a detailed evaluation report showing TF-IDF top matches,
        cosine similarity distribution, confidence scores, and decision logic breakdown.
        """
        active_threshold = float(threshold) if threshold is not None else self.threshold
        raw_query = (user_query or "").strip()
        normalized = self.preprocess(raw_query)
        category_report = self.get_category_intent_report(raw_query)

        if not self.faq_records or self.vectorizer is None:
            return {
                "error": "Knowledge base is empty or vectorizer not fitted."
            }

        # Check if query has alphanumeric tokens
        if not re.search(r'[a-zA-Z0-9]', raw_query):
            return {
                "raw_query": raw_query,
                "normalized_query": "",
                "detected_category": None,
                "category_filter": category_filter,
                "threshold": active_threshold,
                "decision": "EMPTY_QUERY",
                "top_match": None,
                "all_ranked_candidates": [],
                "engine_type": "Retrieval-Based FAQ Agent (TF-IDF + Cosine Similarity - Non-Generative)",
                "category_report": category_report
            }

        query_vec = self.vectorizer.transform([normalized])
        sim_scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        ranked = []
        for idx, score in enumerate(sim_scores):
            faq = self.faq_records[idx]
            if category_filter and category_filter != "all" and faq["category"].lower() != category_filter.lower():
                continue
            ranked.append({
                "faq_id": faq["id"],
                "question": faq["question"],
                "answer": faq["answer"],
                "category": faq["category"],
                "keywords": faq.get("keywords", ""),
                "is_demo": faq.get("is_demo", 0),
                "similarity_score": round(float(score), 4),
                "confidence_percent": round(float(score) * 100, 1),
                "is_above_threshold": bool(score >= active_threshold)
            })

        ranked.sort(key=lambda x: x["similarity_score"], reverse=True)
        top_match = ranked[0] if ranked else None
        decision = "RESOLVED" if (top_match and top_match["similarity_score"] >= active_threshold) else "FALLBACK"

        return {
            "raw_query": raw_query,
            "normalized_query": normalized,
            "detected_category": category_report["detected_category"],
            "category_filter": category_filter,
            "threshold": active_threshold,
            "decision": decision,
            "top_match": top_match,
            "all_ranked_candidates": ranked[:8],
            "category_report": category_report,
            "engine_type": "Retrieval-Based FAQ Agent (TF-IDF + Cosine Similarity - Non-Generative)"
        }
