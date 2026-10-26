"""
Smart FAQ Assistant - Main Flask Application
Provides routes for the student chatbot, public FAQ directory,
interaction logging and feedback API, and administrative dashboard.
"""

import os
from functools import wraps
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    flash
)
from dotenv import load_dotenv

# Load environment configuration
load_dotenv()

from database import (
    init_db,
    get_all_faqs,
    get_faq_by_id,
    add_faq,
    update_faq,
    delete_faq,
    get_categories,
    update_feedback,
    get_recent_logs,
    get_analytics_summary,
    authenticate_admin,
    update_admin_password,
    get_admin_user,
    VALID_CATEGORIES
)
from agent import SmartFAQAgent

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "college-smart-faq-assistant-secure-key-2026")

# Initialize SQLite database and tables
init_db()

# Initialize AI Agent
threshold_val = float(os.environ.get("FAQ_MATCH_THRESHOLD", 0.25))
agent = SmartFAQAgent(threshold=threshold_val)


def admin_required(f):
    """Decorator to enforce admin authentication for protected views."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Please sign in as administrator to access this area.", "warning")
            return redirect(url_for("admin_login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------------------------
# Public Student Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Unified Single-Page Application Interface."""
    categories = get_categories()
    analytics = get_analytics_summary()
    all_faqs = get_all_faqs()
    sample_suggestions = agent.get_quick_suggestions()
    recent_logs = get_recent_logs(limit=25) if session.get("is_admin") else []
    admin_user = get_admin_user(session.get("admin_username", "admin")) if session.get("is_admin") else None

    return render_template(
        "index.html",
        categories=categories,
        valid_categories=VALID_CATEGORIES,
        total_faqs=analytics["total_faqs"],
        total_queries=analytics["total_queries"],
        analytics=analytics,
        faqs=all_faqs,
        sample_suggestions=sample_suggestions,
        threshold=agent.threshold,
        recent_logs=recent_logs,
        admin_user=admin_user
    )


@app.route("/chat")
def chat():
    """Interactive Student Chatbot Interface."""
    initial_category = request.args.get("category", "")
    initial_query = request.args.get("q", "")
    categories = get_categories()
    sample_suggestions = agent.get_quick_suggestions(initial_category)
    return render_template(
        "chat.html",
        categories=categories,
        valid_categories=VALID_CATEGORIES,
        initial_category=initial_category,
        initial_query=initial_query,
        sample_suggestions=sample_suggestions
    )


@app.route("/faqs")
def faqs():
    """Searchable & Filterable Public FAQ Directory."""
    category = request.args.get("category", "")
    search = request.args.get("q", "")
    faq_list = get_all_faqs(category=category, search=search)
    categories = get_categories()
    return render_template(
        "faqs.html",
        faqs=faq_list,
        categories=categories,
        valid_categories=VALID_CATEGORIES,
        current_category=category,
        current_search=search
    )


# ---------------------------------------------------------------------------
# JSON API Endpoints for Chatbot & Feedback
# ---------------------------------------------------------------------------

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    Handles user questions sent from the chatbot interface.
    Accepts JSON: { "query": "...", "category": "..." }
    Returns: JSON response containing matched answer or fallback, confidence,
             category info, suggested questions, and log ID.
    """
    data = request.get_json(silent=True) or {}
    user_query = data.get("query", "")
    category_filter = data.get("category", "")

    response = agent.ask(user_query=user_query, category_filter=category_filter)
    return jsonify(response)


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    """
    Records helpful / not-helpful feedback for an interaction.
    Accepts JSON: { "log_id": 12, "feedback": "HELPFUL" | "NOT_HELPFUL" }
    """
    data = request.get_json(silent=True) or {}
    log_id = data.get("log_id")
    feedback_val = data.get("feedback")

    if not log_id:
        return jsonify({"success": False, "error": "Missing log ID."}), 400

    if feedback_val in ["HELPFUL", 1, "1", "helpful", True]:
        normalized_val = "HELPFUL"
    elif feedback_val in ["NOT_HELPFUL", -1, "-1", 0, "0", "not_helpful", False]:
        normalized_val = "NOT_HELPFUL"
    else:
        return jsonify({"success": False, "error": "Invalid feedback value. Must be HELPFUL (1) or NOT_HELPFUL (-1)."}), 400

    success = update_feedback(log_id=log_id, feedback_value=normalized_val)
    return jsonify({"success": bool(success)})


@app.route("/api/categories", methods=["GET"])
def api_categories():
    """Returns available FAQ categories and counts."""
    return jsonify({"categories": get_categories()})


# ---------------------------------------------------------------------------
# Administrative Routes & Protected Views
# ---------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Admin Login view."""
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if authenticate_admin(username, password):
            session["is_admin"] = True
            session["admin_username"] = username
            flash("Welcome back, Administrator!", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("admin_dashboard"))
        else:
            flash("Invalid administrator credentials. Please try again.", "danger")

    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    """Logs out current admin user."""
    session.pop("is_admin", None)
    session.pop("admin_username", None)
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    """Admin Dashboard Overview: Key Metrics, Charts, Recent Activity."""
    analytics = get_analytics_summary()
    recent_logs = get_recent_logs(limit=10)
    return render_template(
        "admin_dashboard.html",
        analytics=analytics,
        recent_logs=recent_logs,
        threshold=agent.threshold
    )


@app.route("/admin/faqs")
@admin_required
def admin_faqs():
    """Admin FAQ Management list view."""
    category = request.args.get("category", "")
    search = request.args.get("q", "")
    faq_list = get_all_faqs(category=category, search=search)
    return render_template(
        "admin_faqs.html",
        faqs=faq_list,
        categories=VALID_CATEGORIES,
        current_category=category,
        current_search=search
    )


@app.route("/admin/faqs/new", methods=["GET", "POST"])
@admin_required
def admin_add_faq():
    """Add new FAQ with input validation."""
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        answer = request.form.get("answer", "").strip()
        category = request.form.get("category", "").strip()
        keywords = request.form.get("keywords", "").strip()
        is_demo = 1 if request.form.get("is_demo") else 0

        # Input validation
        if not question or len(question) < 5:
            flash("Question is required and must be at least 5 characters long.", "danger")
            return render_template(
                "admin_faq_form.html",
                faq=None,
                form_data=request.form,
                categories=VALID_CATEGORIES
            )

        if not answer or len(answer) < 5:
            flash("Answer is required and must be at least 5 characters long.", "danger")
            return render_template(
                "admin_faq_form.html",
                faq=None,
                form_data=request.form,
                categories=VALID_CATEGORIES
            )

        if not category or category not in VALID_CATEGORIES:
            flash(f"Invalid category selected. Must be one of: {', '.join(VALID_CATEGORIES)}.", "danger")
            return render_template(
                "admin_faq_form.html",
                faq=None,
                form_data=request.form,
                categories=VALID_CATEGORIES
            )

        new_id = add_faq(question, answer, category, keywords, is_demo)
        agent.reload_knowledge_base()
        flash(f"FAQ #{new_id} created successfully and knowledge base updated!", "success")
        return redirect(url_for("admin_faqs"))

    return render_template("admin_faq_form.html", faq=None, form_data={}, categories=VALID_CATEGORIES)


@app.route("/admin/faqs/<int:faq_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_faq(faq_id):
    """Edit existing FAQ with input validation."""
    faq = get_faq_by_id(faq_id)
    if not faq:
        flash(f"FAQ #{faq_id} does not exist.", "danger")
        return redirect(url_for("admin_faqs"))

    if request.method == "POST":
        question = request.form.get("question", "").strip()
        answer = request.form.get("answer", "").strip()
        category = request.form.get("category", "").strip()
        keywords = request.form.get("keywords", "").strip()
        is_demo = 1 if request.form.get("is_demo") else 0

        # Input validation
        if not question or len(question) < 5:
            flash("Question is required and must be at least 5 characters long.", "danger")
            return render_template("admin_faq_form.html", faq=faq, form_data=request.form, categories=VALID_CATEGORIES)

        if not answer or len(answer) < 5:
            flash("Answer is required and must be at least 5 characters long.", "danger")
            return render_template("admin_faq_form.html", faq=faq, form_data=request.form, categories=VALID_CATEGORIES)

        if not category or category not in VALID_CATEGORIES:
            flash(f"Invalid category selected. Must be one of: {', '.join(VALID_CATEGORIES)}.", "danger")
            return render_template("admin_faq_form.html", faq=faq, form_data=request.form, categories=VALID_CATEGORIES)

        update_faq(faq_id, question, answer, category, keywords, is_demo)
        agent.reload_knowledge_base()
        flash(f"FAQ #{faq_id} updated successfully and knowledge base re-indexed!", "success")
        return redirect(url_for("admin_faqs"))

    return render_template("admin_faq_form.html", faq=faq, form_data=faq, categories=VALID_CATEGORIES)


@app.route("/admin/faqs/<int:faq_id>/delete", methods=["POST"])
@admin_required
def admin_delete_faq(faq_id):
    """Delete an FAQ by ID."""
    existing = get_faq_by_id(faq_id)
    if not existing:
        flash(f"FAQ #{faq_id} not found.", "warning")
        return redirect(url_for("admin_faqs"))

    delete_faq(faq_id)
    agent.reload_knowledge_base()
    flash(f"FAQ #{faq_id} deleted successfully.", "info")
    return redirect(url_for("admin_faqs"))


@app.route("/admin/password", methods=["GET", "POST"])
@admin_required
def admin_password():
    """Secure Administrator Password Change."""
    username = session.get("admin_username")
    admin_user = get_admin_user(username)

    if request.method == "POST":
        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not current_password or not new_password or not confirm_password:
            flash("All password fields are required.", "danger")
            return render_template("admin_password.html", admin_user=admin_user)

        if not authenticate_admin(username, current_password):
            flash("The current password entered is incorrect.", "danger")
            return render_template("admin_password.html", admin_user=admin_user)

        if len(new_password) < 6:
            flash("New password must be at least 6 characters long.", "danger")
            return render_template("admin_password.html", admin_user=admin_user)

        if new_password != confirm_password:
            flash("New password and confirmation password do not match.", "danger")
            return render_template("admin_password.html", admin_user=admin_user)

        success = update_admin_password(username, new_password)
        if success:
            flash("Administrator password updated successfully! Please use your new password next time.", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Failed to update password. Please try again.", "danger")

    return render_template("admin_password.html", admin_user=admin_user)


@app.route("/admin/logs")
@admin_required
def admin_logs():
    """Detailed query interactions log."""
    logs = get_recent_logs(limit=100)
    return render_template("admin_logs.html", logs=logs)


@app.route("/admin/debug", methods=["GET", "POST"])
@admin_required
def admin_debug():
    """
    Interactive AI Agent Diagnostics & Debugger.
    Inspects user questions, shows TF-IDF vectorization tokens,
    confidence score comparison against configurable threshold, and ranked candidates.
    """
    query = request.args.get("q", "")
    category = request.args.get("category", "")
    threshold_param = request.args.get("threshold", "").strip()

    try:
        active_threshold = float(threshold_param) if threshold_param else agent.threshold
    except ValueError:
        active_threshold = agent.threshold

    report = None
    if query:
        report = agent.explain_query(query, category_filter=category, threshold=active_threshold)

    return render_template(
        "admin_debug.html",
        query=query,
        category=category,
        categories=VALID_CATEGORIES,
        report=report,
        threshold=active_threshold
    )


# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ["true", "1", "yes"]
    print(f"Starting Smart FAQ Assistant on http://127.0.0.1:{port} (Debug={debug})")
    app.run(host="127.0.0.1", port=port, debug=debug)
