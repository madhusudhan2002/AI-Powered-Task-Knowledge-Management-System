import sys
import os
import hashlib
import uuid
import secrets
import time

import streamlit as st
import pandas as pd
from io import StringIO
from sqlalchemy import func

# ==================================================
# Add backend to Python path
# ==================================================

BACKEND_PATH = os.path.join(
    os.path.dirname(__file__),
    "backend"
)

if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)

# ==================================================
# ACTIVITY LOG
# ==================================================

def show_activity_log():

    st.header("🕘 Activity Log")

    user = st.session_state.user

    # --------------------------------------------------
    # Admin-only access
    # --------------------------------------------------

    if not is_admin():
        st.warning("🔒 Activity Log is available only to administrators.")
        return

    st.write(
        "View recent activities performed by users in the system."
    )

    st.divider()

    db = SessionLocal()

    try:

        # ----------------------------------------------
        # Get activities
        # ----------------------------------------------

        activities = (
            db.query(ActivityLog)
            .order_by(
                ActivityLog.created_at.desc()
            )
            .limit(100)
            .all()
        )

        if not activities:

            st.info(
                "No activity has been recorded yet."
            )

            return

        # ----------------------------------------------
        # Action filter
        # ----------------------------------------------

        action_values = sorted(
            {
                activity.action
                for activity in activities
                if activity.action
            }
        )

        selected_action = st.selectbox(
            "🔍 Filter by Action",
            ["All"] + action_values
        )

        if selected_action != "All":

            activities = [
                activity
                for activity in activities
                if activity.action == selected_action
            ]

        # ----------------------------------------------
        # Activity count
        # ----------------------------------------------

        st.metric(
            "Total Activities",
            len(activities)
        )

        st.divider()

        # ----------------------------------------------
        # Display activities
        # ----------------------------------------------

        for activity in activities:

            activity_user = (
                db.query(User)
                .filter(
                    User.id == activity.user_id
                )
                .first()
            )

            if activity_user:

                user_name = (
                    activity_user.name
                    or activity_user.email
                )

            else:

                user_name = "Unknown User"

            action = (
                activity.action
                or "Unknown Action"
            )

            details = (
                activity.details
                or "No details available"
            )

            created_at = (
                activity.created_at
                or "Unknown time"
            )

            with st.container():

                col1, col2, col3 = st.columns(
                    [2, 2, 4]
                )

                with col1:

                    st.write(
                        f"👤 **{user_name}**"
                    )

                with col2:

                    st.write(
                        f"⚡ **{action}**"
                    )

                with col3:

                    st.write(
                        f"🕒 {created_at}"
                    )

                st.write(
                    f"📝 {details}"
                )

                st.divider()

    except Exception as e:

        st.error(
            f"❌ Error loading activity log: {e}"
        )

    finally:

        db.close()
        
# ==================================================
# Backend Imports
# ==================================================

from app.database import SessionLocal
from app.models import (
    User,
    Task,
    Document,
    DocumentChunk,
    ActivityLog,
    SearchQuery,
    Role
)
from app.auth import verify_password, hash_password
from sqlalchemy.orm import joinedload
from app.services.file_parser import (
    extract_text,
    chunk_text
)
from app.services.vector_store import (
    add_chunks,
    search
)


# ==================================================
# Streamlit Configuration
# ==================================================

st.set_page_config(
    page_title="AI Task & Knowledge Management System",
    page_icon="🤖",
    layout="wide"
)


# ==================================================
# Session State
# ==================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = None

if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"

if "reset_step" not in st.session_state:
    st.session_state.reset_step = 1

if "reset_email" not in st.session_state:
    st.session_state.reset_email = ""

if "reset_otp_hash" not in st.session_state:
    st.session_state.reset_otp_hash = ""

if "reset_otp_created_at" not in st.session_state:
    st.session_state.reset_otp_created_at = 0

if "reset_otp_attempts" not in st.session_state:
    st.session_state.reset_otp_attempts = 0


# ==================================================
# Login Function
# ==================================================

def login_user(email, password):

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .options(joinedload(User.role))
            .filter(User.email == email)
            .first()
        )

        if user and verify_password(
            password,
            user.hashed_password
        ):
            return user

        return None

    finally:
        db.close()


# ==================================================
# Sign Up Page
# ==================================================

def show_signup():

    st.subheader("📝 Create Account")
    st.caption("Create a new user account to access the system.")

    with st.form("signup_form"):

        name = st.text_input(
            "Full Name",
            placeholder="Enter your full name"
        )

        email = st.text_input(
            "Email",
            placeholder="Enter your email address"
        )

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter a password"
        )

        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
            placeholder="Re-enter your password"
        )

        submitted = st.form_submit_button(
            "Create Account",
            use_container_width=True
        )

        if submitted:

            name = name.strip()
            email = email.strip().lower()

            if not name:
                st.error("Please enter your full name.")

            elif len(name) < 2:
                st.error("Name must contain at least 2 characters.")

            elif not email:
                st.error("Please enter your email address.")

            elif not password:
                st.error("Please enter a password.")

            elif len(password) < 6:
                st.error("Password must contain at least 6 characters.")

            elif len(password.encode("utf-8")) > 72:
                st.error("Password must not exceed 72 bytes.")

            elif password != confirm_password:
                st.error("Passwords do not match.")

            else:

                db = SessionLocal()

                try:

                    existing_user = (
                        db.query(User)
                        .filter(User.email == email)
                        .first()
                    )

                    if existing_user:

                        st.error(
                            "An account with this email already exists."
                        )

                    else:

                        # Always create public registrations as normal users.
                        # Admin accounts remain controlled by administrators.
                        user_role = (
                            db.query(Role)
                            .filter(Role.name == "user")
                            .first()
                        )

                        if not user_role:

                            st.error(
                                "The user role was not found in the database."
                            )

                        else:

                            new_user = User(
                                name=name,
                                email=email,
                                hashed_password=hash_password(password),
                                role_id=user_role.id
                            )

                            db.add(new_user)
                            db.commit()

                            st.success(
                                "✅ Account created successfully! "
                                "You can now sign in."
                            )

                except Exception as e:

                    db.rollback()

                    st.error(
                        f"❌ Error creating account: {e}"
                    )

                finally:

                    db.close()


# ==================================================
# Forgot Password Helpers
# ==================================================

def generate_reset_otp():
    """Generate a cryptographically secure 6-digit OTP."""
    return f"{secrets.randbelow(1_000_000):06d}"


def find_user_by_email(email):
    """Find a user by email address."""
    db = SessionLocal()

    try:
        return (
            db.query(User)
            .filter(func.lower(User.email) == email.strip().lower())
            .first()
        )

    finally:
        db.close()


def reset_user_password(email, new_password):
    """Update the user's password after OTP verification."""
    db = SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(func.lower(User.email) == email.strip().lower())
            .first()
        )

        if not user:
            return False

        user.hashed_password = hash_password(new_password)
        db.commit()

        return True

    except Exception:
        db.rollback()
        return False

    finally:
        db.close()


def clear_password_reset_state():
    """Clear all password-reset session data."""
    st.session_state.reset_step = 1
    st.session_state.reset_email = ""
    st.session_state.reset_otp_hash = ""
    st.session_state.reset_otp_created_at = 0
    st.session_state.reset_otp_attempts = 0


def show_forgot_password():
    """Forgot-password flow using a temporary OTP for development/testing."""
    st.title("🔑 Forgot Password")
    st.caption("Reset your password using a 6-digit OTP.")

    # --------------------------------------------------
    # STEP 1: EMAIL
    # --------------------------------------------------

    if st.session_state.reset_step == 1:

        st.subheader("📧 Enter your registered email")

        with st.form("forgot_password_email_form"):

            email = st.text_input(
                "Email",
                placeholder="Enter your registered email"
            )

            submitted = st.form_submit_button(
                "Send OTP",
                use_container_width=True
            )

            if submitted:

                email = email.strip().lower()

                if not email:

                    st.error("Please enter your email address.")

                else:

                    user = find_user_by_email(email)

                    if not user:

                        st.error(
                            "No account found with this email address."
                        )

                    else:

                        otp = generate_reset_otp()

                        st.session_state.reset_email = email
                        st.session_state.reset_otp_hash = hashlib.sha256(
                            otp.encode("utf-8")
                        ).hexdigest()
                        st.session_state.reset_otp_created_at = time.time()
                        st.session_state.reset_otp_attempts = 0
                        st.session_state.reset_step = 2

                        # Temporary development/testing display.
                        # Replace with email sending after local testing.
                        st.success("OTP generated successfully.")
                        st.info(f"🔢 Your OTP is: **{otp}**")

                        st.rerun()

    # --------------------------------------------------
    # STEP 2: VERIFY OTP
    # --------------------------------------------------

    elif st.session_state.reset_step == 2:

        st.subheader("🔢 Verify OTP")

        st.info(
            f"OTP was generated for **{st.session_state.reset_email}**."
        )

        with st.form("verify_reset_otp_form"):

            entered_otp = st.text_input(
                "6-digit OTP",
                max_chars=6,
                placeholder="Enter OTP"
            )

            submitted = st.form_submit_button(
                "Verify OTP",
                use_container_width=True
            )

            if submitted:

                entered_otp = entered_otp.strip()

                otp_age = (
                    time.time()
                    - st.session_state.reset_otp_created_at
                )

                if otp_age > 300:

                    st.error(
                        "OTP has expired. Please request a new OTP."
                    )

                elif st.session_state.reset_otp_attempts >= 5:

                    st.error(
                        "Too many incorrect attempts. "
                        "Please request a new OTP."
                    )

                elif not entered_otp.isdigit() or len(entered_otp) != 6:

                    st.session_state.reset_otp_attempts += 1

                    st.error(
                        "Please enter a valid 6-digit OTP."
                    )

                else:

                    entered_hash = hashlib.sha256(
                        entered_otp.encode("utf-8")
                    ).hexdigest()

                    if entered_hash != st.session_state.reset_otp_hash:

                        st.session_state.reset_otp_attempts += 1

                        remaining = max(
                            0,
                            5 - st.session_state.reset_otp_attempts
                        )

                        st.error(
                            f"Invalid OTP. {remaining} attempt(s) remaining."
                        )

                    else:

                        st.session_state.reset_step = 3
                        st.session_state.reset_otp_hash = ""
                        st.session_state.reset_otp_attempts = 0

                        st.success("✅ OTP verified successfully.")

                        st.rerun()

        if st.button(
            "🔄 Resend OTP",
            use_container_width=True
        ):

            otp = generate_reset_otp()

            st.session_state.reset_otp_hash = hashlib.sha256(
                otp.encode("utf-8")
            ).hexdigest()
            st.session_state.reset_otp_created_at = time.time()
            st.session_state.reset_otp_attempts = 0

            # Temporary development/testing display.
            st.success("New OTP generated.")
            st.info(f"🔢 Your new OTP is: **{otp}**")

        if st.button(
            "⬅️ Back to Login",
            use_container_width=True
        ):

            clear_password_reset_state()
            st.rerun()

    # --------------------------------------------------
    # STEP 3: NEW PASSWORD
    # --------------------------------------------------

    elif st.session_state.reset_step == 3:

        st.subheader("🔐 Create New Password")

        with st.form("reset_password_form"):

            new_password = st.text_input(
                "New Password",
                type="password",
                placeholder="Enter your new password"
            )

            confirm_password = st.text_input(
                "Confirm New Password",
                type="password",
                placeholder="Re-enter your new password"
            )

            submitted = st.form_submit_button(
                "Reset Password",
                use_container_width=True
            )

            if submitted:

                if not new_password:

                    st.error("Please enter a new password.")

                elif len(new_password) < 6:

                    st.error(
                        "Password must contain at least 6 characters."
                    )

                elif len(new_password.encode("utf-8")) > 72:

                    st.error(
                        "Password must not exceed 72 bytes."
                    )

                elif new_password != confirm_password:

                    st.error("Passwords do not match.")

                else:

                    success = reset_user_password(
                        st.session_state.reset_email,
                        new_password
                    )

                    if success:

                        clear_password_reset_state()

                        st.success(
                            "✅ Password reset successfully! "
                            "You can now sign in with your new password."
                        )

                        st.rerun()

                    else:

                        st.error(
                            "❌ Unable to reset the password. "
                            "Please try again."
                        )

        if st.button(
            "⬅️ Back to Login",
            use_container_width=True
        ):

            clear_password_reset_state()
            st.rerun()


# ==================================================
# Login Page
# ==================================================

def show_login():

    st.title(
        "🤖 AI-Powered Task & Knowledge Management System"
    )

    login_tab, signup_tab = st.tabs(
        ["🔐 Sign In", "📝 Sign Up"]
    )

    with login_tab:

        st.subheader("🔐 Sign In")

        with st.form("login_form"):

            email = st.text_input(
                "Email",
                placeholder="Enter your email",
                key="login_email"
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
                key="login_password"
            )

            submitted = st.form_submit_button(
                "Login",
                use_container_width=True
            )

            if submitted:

                email = email.strip().lower()

                if not email or not password:

                    st.error(
                        "Please enter email and password."
                    )

                else:

                    user = login_user(
                        email,
                        password
                    )

                    if user:

                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.session_state.auth_page = "login"

                        st.success(
                            "Login successful!"
                        )

                        st.rerun()

                    else:

                        st.error(
                            "Invalid email or password."
                        )

        st.write("")

        if st.button(
            "🔑 Forgot Password?",
            use_container_width=True
        ):
            st.session_state.reset_step = 1
            st.session_state.reset_email = ""
            st.session_state.reset_otp_hash = ""
            st.session_state.reset_otp_created_at = 0
            st.session_state.reset_otp_attempts = 0
            st.session_state.auth_page = "forgot_password"
            st.rerun()

    with signup_tab:

        show_signup()


# ==================================================
# Task Management
# ==================================================

def show_tasks():

    st.header("✅ Task Management")

    user = st.session_state.user

    # ==================================================
    # CREATE NEW TASK
    # ==================================================

    st.subheader("➕ Create New Task")

    with st.form("create_task_form"):

        title = st.text_input(
            "Task Title",
            placeholder="Enter task title"
        )

        description = st.text_area(
            "Description",
            placeholder="Enter task description"
        )

        status_options = {
            "Pending": "pending",
            "Completed": "completed"
        }

        selected_status = st.selectbox(
            "Status",
            list(status_options.keys())
        )

        status = status_options[selected_status]

        submitted = st.form_submit_button(
            "Create Task",
            use_container_width=True
        )

        if submitted:

            if not title.strip():

                st.error(
                    "Task title is required."
                )

            else:

                db = SessionLocal()

                try:

                    new_task = Task(
                        title=title,
                        description=description,
                        status=status,
                        created_by=user.id,
                        assigned_to=user.id
                    )

                    db.add(new_task)
                    db.commit()
                    db.refresh(new_task)

                    st.success(
                        f"Task #{new_task.id} created successfully!"
                    )

                    st.rerun()

                except Exception as e:

                    db.rollback()

                    st.error(
                        f"Error creating task: {e}"
                    )

                finally:
                    db.close()

    st.divider()

    # ==================================================
    # DISPLAY TASKS
    # ==================================================

    st.subheader("📋 Your Tasks")

    db = SessionLocal()

    try:

        tasks = (
            db.query(Task)
            .filter(
                Task.created_by == user.id
            )
            .order_by(
                Task.created_at.desc()
            )
            .all()
        )

        # ==================================================
        # TASK FILTERS
        # ==================================================

        filter_col1, filter_col2 = st.columns([2, 1])

        with filter_col1:
            task_search = st.text_input(
                "🔍 Search Tasks",
                placeholder="Search by task title...",
                key="task_search"
            )

        with filter_col2:
            task_status_filter = st.selectbox(
                "📌 Status",
                ["All", "Pending", "Completed"],
                key="task_status_filter"
            )

        filtered_tasks = tasks

        if task_search.strip():
            search_text = task_search.strip().lower()
            filtered_tasks = [
                task
                for task in filtered_tasks
                if search_text in (task.title or "").lower()
            ]

        if task_status_filter != "All":
            status_value = task_status_filter.lower()
            filtered_tasks = [
                task
                for task in filtered_tasks
                if (
                    task.status.value
                    if hasattr(task.status, "value")
                    else str(task.status)
                ).lower() == status_value
            ]

        st.info(
            f"Showing {len(filtered_tasks)} of {len(tasks)} task(s)"
        )

        if not tasks:

            st.info(
                "No tasks found. Create your first task above."
            )

        else:

            for task in filtered_tasks:

                # ------------------------------------------
                # Get actual database status
                # ------------------------------------------

                status_value = (
                    task.status.value
                    if hasattr(task.status, "value")
                    else task.status
                )

                status_display = status_value.title()

                # ------------------------------------------
                # TASK DETAILS
                # ------------------------------------------

                with st.expander(
                    f"📋 #{task.id} — {task.title}"
                ):

                    st.write(
                        f"**Description:** "
                        f"{task.description or 'No description'}"
                    )

                    st.write(
                        f"**Current Status:** "
                        f"{status_display}"
                    )

                    st.write(
                        f"**Created:** "
                        f"{task.created_at}"
                    )

                    st.write(
                        f"**Assigned To:** "
                        f"{task.assigned_to}"
                    )

                    st.divider()

                    # ======================================
                    # UPDATE STATUS
                    # ======================================

                    st.write(
                        "### 🔄 Update Task Status"
                    )

                    update_options = {
                        "Pending": "pending",
                        "Completed": "completed"
                    }

                    if status_value == "completed":
                        current_index = 1
                    else:
                        current_index = 0

                    new_status_display = st.selectbox(
                        "Select Status",
                        list(update_options.keys()),
                        index=current_index,
                        key=f"status_{task.id}"
                    )

                    new_status = update_options[
                        new_status_display
                    ]

                    # --------------------------------------
                    # UPDATE BUTTON
                    # --------------------------------------

                    if st.button(
                        "🔄 Update Status",
                        key=f"update_{task.id}",
                        use_container_width=True
                    ):

                        db_update = SessionLocal()

                        try:

                            task_to_update = (
                                db_update.query(Task)
                                .filter(
                                    Task.id == task.id,
                                    Task.created_by == user.id
                                )
                                .first()
                            )

                            if task_to_update:

                                task_to_update.status = new_status

                                db_update.commit()

                                st.success(
                                    f"Task #{task.id} status "
                                    f"updated to "
                                    f"{new_status_display}."
                                )

                                st.rerun()

                            else:

                                st.error(
                                    "Task not found or you do "
                                    "not have permission to "
                                    "update it."
                                )

                        except Exception as e:

                            db_update.rollback()

                            st.error(
                                f"Error updating task: {e}"
                            )

                        finally:
                            db_update.close()

    finally:
        db.close()


# ==================================================
# Dashboard
# ==================================================

def show_dashboard():

    user = st.session_state.user

    st.title(
        "🤖 AI-Powered Task & Knowledge Management System"
    )

    st.success(
        f"Welcome, {user.name}!"
    )

    st.write(
        f"**Email:** {user.email}"
    )

    st.write(
        f"**Role:** {user.role.name.value}"
    )

    st.divider()

    # ==================================================
    # DASHBOARD STATISTICS
    # ==================================================

    st.header("📊 Dashboard")

    db = SessionLocal()

    try:

        # ----------------------------------------------
        # Task statistics
        # ----------------------------------------------

        total_tasks = (
            db.query(Task)
            .filter(
                Task.created_by == user.id
            )
            .count()
        )

        pending_tasks = (
            db.query(Task)
            .filter(
                Task.created_by == user.id,
                Task.status == "pending"
            )
            .count()
        )

        completed_tasks = (
            db.query(Task)
            .filter(
                Task.created_by == user.id,
                Task.status == "completed"
            )
            .count()
        )

        # ----------------------------------------------
        # Document statistics
        # ----------------------------------------------

        total_documents = (
            db.query(Document)
            .filter(
                Document.uploaded_by == user.id
            )
            .count()
        )

        total_chunks = (
            db.query(DocumentChunk)
            .join(
                Document,
                Document.id == DocumentChunk.document_id
            )
            .filter(
                Document.uploaded_by == user.id
            )
            .count()
        )

        # ----------------------------------------------
        # Search statistics
        # ----------------------------------------------
        # Count searches belonging to the current user
        # when the SearchQuery table has a user_id column.
        # Otherwise fall back to the existing global count.

        search_query_columns = {
            column.name
            for column in SearchQuery.__table__.columns
        }

        if "user_id" in search_query_columns:
            total_searches = (
                db.query(SearchQuery)
                .filter(
                    SearchQuery.user_id == user.id
                )
                .count()
            )
        else:
            total_searches = (
                db.query(SearchQuery)
                .count()
            )
    finally:

        db.close()

    # ==================================================
    # MAIN METRICS
    # ==================================================

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "📋 Total Tasks",
            total_tasks
        )

    with col2:

        st.metric(
            "📄 Documents",
            total_documents
        )

    with col3:

        st.metric(
            "🔍 Searches",
            total_searches
        )

    st.divider()

    # ==================================================
    # TASK SUMMARY
    # ==================================================

    st.subheader("📋 Task Summary")

    task_col1, task_col2 = st.columns(2)

    with task_col1:

        st.metric(
            "⏳ Pending Tasks",
            pending_tasks
        )

    with task_col2:

        st.metric(
            "✅ Completed Tasks",
            completed_tasks
        )

    st.divider()

    # ==================================================
    # DOCUMENT SUMMARY
    # ==================================================

    st.subheader("📄 Document Summary")

    doc_col1, doc_col2 = st.columns(2)

    with doc_col1:

        st.metric(
            "📚 Total Documents",
            total_documents
        )

    with doc_col2:

        st.metric(
            "🧩 Total Chunks",
            total_chunks
        )

    st.divider()

    # ==================================================
    # SYSTEM INFORMATION
    # ==================================================

    st.subheader("ℹ️ System Information")

    st.write(
        "This dashboard displays live statistics "
        "from the MySQL database."
    )

    st.write(
        "Documents are processed into text chunks, "
        "converted into embeddings, and indexed "
        "using FAISS for semantic search."
    )

def rebuild_faiss_index():
    """
    Rebuild FAISS index from all remaining document chunks.
    Also updates vector_index values in MySQL.
    """

    import faiss
    from app.config import settings
    from app.services.vector_store import embed_texts

    db = SessionLocal()

    try:
        chunks = (
            db.query(DocumentChunk)
            .order_by(DocumentChunk.id)
            .all()
        )

        if not chunks:
            embedding_dimension = 384

            new_index = faiss.IndexFlatIP(
                embedding_dimension
            )

            index_path = os.path.join(
                settings.VECTOR_STORE_DIR,
                "index.faiss"
            )

            faiss.write_index(
                new_index,
                index_path
            )

            return 0

        texts = [
            chunk.chunk_text
            for chunk in chunks
        ]

        vectors = embed_texts(texts)

        new_index = faiss.IndexFlatIP(
            vectors.shape[1]
        )

        new_index.add(vectors)

        index_path = os.path.join(
            settings.VECTOR_STORE_DIR,
            "index.faiss"
        )

        faiss.write_index(
            new_index,
            index_path
        )

        # Update vector indexes in MySQL
        for new_index_value, chunk in enumerate(chunks):
            chunk.vector_index = new_index_value

        db.commit()

        return len(chunks)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

# ==================================================
# Document Management
# ==================================================

def show_documents():

    st.header("📄 Document Management")

    user = st.session_state.user

    # ==================================================
    # UPLOAD DOCUMENT
    # ==================================================

    st.subheader("📤 Upload Document")

    uploaded_file = st.file_uploader(
        "Choose a PDF or TXT file",
        type=["pdf", "txt"]
    )

    if uploaded_file is not None:

        st.write(
            f"**Selected file:** {uploaded_file.name}"
        )

        if st.button(
            "📤 Upload & Index Document",
            use_container_width=True
        ):

            # ==================================================
            # STEP 1: GET FILE EXTENSION
            # ==================================================

            file_extension = (
                uploaded_file.name
                .rsplit(".", 1)[-1]
                .lower()
            )

            # ==================================================
            # STEP 2: VALIDATE FILE TYPE
            # ==================================================

            if file_extension not in ["pdf", "txt"]:

                st.error(
                    "Only PDF and TXT files are allowed."
                )

                st.stop()

            # ==================================================
            # STEP 3: READ FILE CONTENT
            # ==================================================

            file_bytes = uploaded_file.getvalue()

            # ==================================================
            # STEP 4: CALCULATE SHA-256 HASH
            # ==================================================

            file_hash = hashlib.sha256(
                file_bytes
            ).hexdigest()

            # ==================================================
            # STEP 5: CHECK DUPLICATE IN MYSQL
            # ==================================================

            db_check = SessionLocal()

            try:

                existing_document = (
                    db_check.query(Document)
                    .filter(
                        Document.file_hash == file_hash
                    )
                    .first()
                )

            finally:

                db_check.close()

            # ==================================================
            # STEP 6: STOP IF DUPLICATE
            # ==================================================

            if existing_document:

                st.warning(
                    "⚠️ Duplicate file detected!"
                )

                st.info(
                    f"This file has already been uploaded as "
                    f"**{existing_document.filename}**."
                )

                st.stop()

            # ==================================================
            # STEP 7: DATABASE SESSION
            # ==================================================

            db = SessionLocal()

            filepath = None

            try:

                # ==================================================
                # CREATE UNIQUE STORED FILENAME
                # ==================================================

                stored_name = (
                    f"{uuid.uuid4().hex}_"
                    f"{uploaded_file.name}"
                )

                upload_dir = os.path.join(
                    BACKEND_PATH,
                    "uploads"
                )

                os.makedirs(
                    upload_dir,
                    exist_ok=True
                )

                filepath = os.path.join(
                    upload_dir,
                    stored_name
                )

                # ==================================================
                # SAVE FILE
                # ==================================================

                with open(
                    filepath,
                    "wb"
                ) as file:

                    file.write(file_bytes)

                # ==================================================
                # CREATE DOCUMENT RECORD
                # ==================================================

                document = Document(
                    filename=uploaded_file.name,
                    filepath=filepath,
                    file_type=file_extension,
                    uploaded_by=user.id,
                    file_hash=file_hash,
                    is_indexed=False,
                    chunk_count=0
                )

                db.add(document)
                db.commit()
                db.refresh(document)

                # ==================================================
                # EXTRACT TEXT
                # ==================================================

                with st.spinner(
                    "📖 Extracting text..."
                ):

                    raw_text = extract_text(
                        filepath,
                        file_extension
                    )

                if not raw_text.strip():

                    st.warning(
                        "No readable text was found "
                        "in this document."
                    )

                    return

                # ==================================================
                # CREATE CHUNKS
                # ==================================================

                with st.spinner(
                    "✂️ Splitting document into chunks..."
                ):

                    chunks = chunk_text(
                        raw_text
                    )

                if not chunks:

                    st.warning(
                        "No text chunks were created."
                    )

                    return

                # ==================================================
                # CREATE EMBEDDINGS + FAISS
                # ==================================================

                with st.spinner(
                    "🧠 Creating embeddings and "
                    "indexing document..."
                ):

                    vector_ids = add_chunks(
                        chunks
                    )

                # ==================================================
                # SAVE CHUNKS TO MYSQL
                # ==================================================

                for chunk, vector_id in zip(
                    chunks,
                    vector_ids
                ):

                    db.add(
                        DocumentChunk(
                            document_id=document.id,
                            chunk_text=chunk,
                            vector_index=vector_id
                        )
                    )

                # ==================================================
                # UPDATE DOCUMENT
                # ==================================================

                document.is_indexed = True

                document.chunk_count = len(
                    chunks
                )

                db.commit()
                db.refresh(document)

                # ==================================================
                # SUCCESS
                # ==================================================

                st.success(
                    f"✅ '{uploaded_file.name}' "
                    f"uploaded successfully!"
                )

                st.info(
                    f"📄 {len(chunks)} text chunks "
                    f"were indexed."
                )

                st.rerun()

            except Exception as e:

                db.rollback()

                # ------------------------------------------
                # Remove physical file if processing failed
                # ------------------------------------------

                if filepath and os.path.exists(filepath):

                    try:
                        os.remove(filepath)
                    except Exception:
                        pass

                st.error(
                    f"❌ Error processing document: {e}"
                )

            finally:

                db.close()

    st.divider()

    # ==================================================
    # LIST DOCUMENTS
    # ==================================================

    st.subheader("📚 Uploaded Documents")

    db = SessionLocal()

    try:

        documents = (
            db.query(Document)
            .filter(
                Document.uploaded_by == user.id
            )
            .order_by(
                Document.uploaded_at.desc()
            )
            .all()
        )

        if not documents:

            st.info(
                "No documents have been uploaded yet."
            )

        else:

            for document in documents:

                with st.expander(
                    f"📄 {document.filename}"
                ):

                    st.write(
                        f"**File Type:** "
                        f"{document.file_type.upper()}"
                    )

                    st.write(
                        f"**Uploaded At:** "
                        f"{document.uploaded_at}"
                    )

                    st.write(
                        f"**Chunks:** "
                        f"{document.chunk_count}"
                    )

                    st.write(
                        f"**Indexed:** "
                        f"{'Yes' if document.is_indexed else 'No'}"
                    )

                    st.divider()

                    # ----------------------------------
                    # PREVIEW / DOWNLOAD DOCUMENT
                    # ----------------------------------

                    if (
                        document.filepath
                        and os.path.exists(document.filepath)
                    ):

                        try:
                            with open(document.filepath, "rb") as file:
                                document_bytes = file.read()

                            mime_type = (
                                "application/pdf"
                                if document.file_type.lower() == "pdf"
                                else "text/plain"
                            )

                            download_col, preview_col = st.columns(2)

                            with download_col:
                                st.download_button(
                                    "⬇️ Download Document",
                                    data=document_bytes,
                                    file_name=document.filename,
                                    mime=mime_type,
                                    key=f"download_document_{document.id}",
                                    use_container_width=True
                                )

                            with preview_col:
                                if document.file_type.lower() == "txt":
                                    if st.button(
                                        "👁️ Preview TXT",
                                        key=f"preview_document_{document.id}",
                                        use_container_width=True
                                    ):
                                        st.text_area(
                                            "Document Preview",
                                            document_bytes.decode(
                                                "utf-8",
                                                errors="ignore"
                                            ),
                                            height=300,
                                            key=f"preview_text_{document.id}"
                                        )
                                else:
                                    st.info(
                                        "📄 PDF preview: use Download Document to open the file."
                                    )

                        except Exception as e:
                            st.warning(f"Unable to read this document: {e}")

                    else:
                        st.warning("⚠️ Physical document file is not available.")

                    st.divider()

                    # ----------------------------------
                    # DELETE DOCUMENT
                    # ----------------------------------

                    if st.button(
                        "🗑️ Delete Document",
                        key=f"delete_document_{document.id}",
                        use_container_width=True
                    ):

                        document_id = document.id
                        document_filename = document.filename
                        document_filepath = document.filepath

                        delete_db = SessionLocal()

                        try:

                            # ----------------------------------
                            # Find document
                            # ----------------------------------

                            document_to_delete = (
                                delete_db.query(Document)
                                .filter(
                                    Document.id == document_id
                                )
                                .first()
                            )

                            if not document_to_delete:

                                st.error(
                                    "Document not found."
                                )

                            else:

                                # ----------------------------------
                                # Delete physical file
                                # ----------------------------------

                                if (
                                    document_filepath
                                    and os.path.exists(
                                        document_filepath
                                    )
                                ):

                                    os.remove(
                                        document_filepath
                                    )

                                # ----------------------------------
                                # Delete database record
                                # ----------------------------------
                                #
                                # DocumentChunk records are deleted
                                # automatically because the model
                                # relationship uses
                                # delete-orphan cascade.
                                # ----------------------------------

                                delete_db.delete(
                                    document_to_delete
                                )

                                delete_db.commit()

                                st.success(
                                    f"✅ '{document_filename}' "
                                    f"deleted successfully."
                                )

                                # ----------------------------------
                                # Rebuild FAISS
                                # ----------------------------------

                                with st.spinner(
                                    "🧠 Rebuilding search index..."
                                ):

                                    remaining_vectors = (
                                        rebuild_faiss_index()
                                    )

                                st.info(
                                    f"🔄 FAISS index rebuilt. "
                                    f"{remaining_vectors} "
                                    f"chunks remain indexed."
                                )

                                st.rerun()

                        except Exception as e:

                            delete_db.rollback()

                            st.error(
                                f"❌ Error deleting document: {e}"
                            )

                        finally:

                            delete_db.close()

    finally:

        db.close()


# ==================================================
# Search History Helpers
# ==================================================

def _search_history_columns():
    """
    Detect the actual SearchQuery table columns at runtime.
    This keeps the Streamlit app compatible with the
    existing SQLAlchemy model without assuming column names.
    """

    columns = list(
        SearchQuery.__table__.columns
    )

    names = [
        column.name
        for column in columns
    ]

    query_candidates = [
        "query",
        "query_text",
        "search_query",
        "question",
        "text"
    ]

    time_candidates = [
        "created_at",
        "searched_at",
        "timestamp",
        "created_on"
    ]

    query_column = next(
        (
            name
            for name in query_candidates
            if name in names
        ),
        None
    )

    time_column = next(
        (
            name
            for name in time_candidates
            if name in names
        ),
        None
    )

    # Fallback: find a non-ID string-like column.
    if query_column is None:

        for column in columns:

            name = column.name.lower()

            if name in {
                "id",
                "user_id",
                "created_by",
                "document_id"
            }:
                continue

            if hasattr(column.type, "length"):

                query_column = column.name
                break

    return query_column, time_column


def save_search_history(query_text, user_id=None):

    db = SessionLocal()

    try:

        query_column, time_column = (
            _search_history_columns()
        )

        if query_column is None:

            return False

        values = {
            query_column: query_text
        }

        column_names = {
            column.name
            for column in SearchQuery.__table__.columns
        }

        if (
            user_id is not None
            and "user_id" in column_names
        ):

            values["user_id"] = user_id

        history = SearchQuery(
            **values
        )

        db.add(history)
        db.commit()

        return True

    except Exception:

        db.rollback()
        return False

    finally:

        db.close()


def load_search_history(limit=10):

    db = SessionLocal()

    try:

        query_column, time_column = (
            _search_history_columns()
        )

        if query_column is None:

            return []

        rows = (
            db.query(SearchQuery)
            .all()
        )

        # Newest first. Prefer the actual timestamp column,
        # otherwise fall back to the row ID.
        if time_column:

            rows.sort(
                key=lambda row: (
                    getattr(row, time_column, None)
                    is not None,
                    getattr(row, time_column, None)
                ),
                reverse=True
            )

        else:

            rows.sort(
                key=lambda row: (
                    getattr(row, "id", 0)
                    or 0
                ),
                reverse=True
            )

        history = []

        for row in rows[:limit]:

            query_value = getattr(
                row,
                query_column,
                None
            )

            timestamp_value = (
                getattr(
                    row,
                    time_column,
                    None
                )
                if time_column
                else None
            )

            if query_value:

                history.append(
                    (
                        str(query_value),
                        timestamp_value
                    )
                )

        return history

    finally:

        db.close()


# ==================================================
# Notifications
# ==================================================

def get_notifications(user_id=None, limit=10):
    db = SessionLocal()

    try:
        query = (
            db.query(ActivityLog)
            .order_by(ActivityLog.created_at.desc())
        )

        if user_id is not None:
            query = query.filter(ActivityLog.user_id == user_id)

        activities = query.limit(limit).all()

        notifications = []

        for activity in activities:
            action = activity.action or "activity"
            details = activity.details or "System activity"

            if action == "task_update":
                icon = "📋"
            elif action == "task_create":
                icon = "📝"
            elif action == "document_upload":
                icon = "📄"
            elif action == "document_delete":
                icon = "🗑️"
            elif action == "search":
                icon = "🔍"
            elif action == "profile_update":
                icon = "👤"
            else:
                icon = "🔔"

            notifications.append({
                "icon": icon,
                "action": action,
                "details": details,
                "created_at": activity.created_at
            })

        return notifications

    finally:
        db.close()
        
# ==================================================
# Notifications Page
# ==================================================

def show_notifications():

    st.header("🔔 Notifications")

    st.caption(
        "Recent activities and important updates from the system."
    )

    st.divider()

    user = st.session_state.get("user")

    if not user:
        st.warning("Please log in to view notifications.")
        return

    notifications = get_notifications(
        user_id=user.id,
        limit=10
    )

    if not notifications:
        st.info("🔔 No notifications available yet.")
        return

    st.subheader("Recent Notifications")

    for notification in notifications:

        icon = notification["icon"]
        action = notification["action"]
        details = notification["details"]
        created_at = notification["created_at"]

        with st.container(border=True):

            col1, col2 = st.columns([1, 8])

            with col1:
                st.markdown(
                    f"# {icon}"
                )

            with col2:

                st.markdown(
                    f"**{action.replace('_', ' ').title()}**"
                )

                st.write(details)

                if created_at:
                    st.caption(
                        f"🕒 {created_at}"
                    )


# ==================================================
# User Profile & Account Management
# ==================================================

def show_profile():
    """Display the current user's profile and account settings."""

    user = st.session_state.user

    st.header("👤 My Profile")
    st.caption("View your account information and manage your profile.")

    # --------------------------------------------------
    # Load the latest user record from MySQL
    # --------------------------------------------------
    db = SessionLocal()

    try:
        current_user = (
            db.query(User)
            .options(joinedload(User.role))
            .filter(User.id == user.id)
            .first()
        )

        if not current_user:
            st.error("User account could not be found.")
            return

        # Keep the session user current after every page load.
        st.session_state.user = current_user
        user = current_user

        role_obj = getattr(user, "role", None)
        role_name = getattr(role_obj, "name", "user")
        role_value = str(getattr(role_name, "value", role_name)).lower()

        # --------------------------------------------------
        # Account Information
        # --------------------------------------------------
        st.subheader("📋 Account Information")

        col1, col2 = st.columns(2)

        with col1:
            st.text_input(
                "Email",
                value=user.email,
                disabled=True,
                key="profile_email"
            )

        with col2:
            st.text_input(
                "Role",
                value=role_value.upper(),
                disabled=True,
                key="profile_role"
            )

        st.divider()

        # --------------------------------------------------
        # Update Name
        # --------------------------------------------------
        st.subheader("✏️ Update Profile")

        with st.form("update_profile_form"):
            new_name = st.text_input(
                "Full Name",
                value=user.name or "",
                placeholder="Enter your full name"
            )

            profile_submitted = st.form_submit_button(
                "💾 Save Profile",
                use_container_width=True
            )

            if profile_submitted:
                clean_name = new_name.strip()

                if not clean_name:
                    st.error("Name is required.")
                elif len(clean_name) < 2:
                    st.error("Name must contain at least 2 characters.")
                else:
                    try:
                        current_user.name = clean_name
                        db.commit()
                        db.refresh(current_user)
                        st.session_state.user = current_user
                        st.success("✅ Profile updated successfully.")
                        st.rerun()
                    except Exception as e:
                        db.rollback()
                        st.error(f"❌ Error updating profile: {e}")

        st.divider()

        # --------------------------------------------------
        # Change Password
        # --------------------------------------------------
        st.subheader("🔐 Change Password")
        st.caption("Your new password must be between 6 and 72 bytes.")

        with st.form("change_password_form"):
            current_password = st.text_input(
                "Current Password",
                type="password",
                placeholder="Enter your current password"
            )

            new_password = st.text_input(
                "New Password",
                type="password",
                placeholder="Enter your new password"
            )

            confirm_password = st.text_input(
                "Confirm New Password",
                type="password",
                placeholder="Re-enter your new password"
            )

            password_submitted = st.form_submit_button(
                "🔑 Update Password",
                use_container_width=True
            )

            if password_submitted:

                if not current_password or not new_password or not confirm_password:
                    st.error("Please fill in all password fields.")

                elif not verify_password(
                    current_password,
                    current_user.hashed_password
                ):
                    st.error("Current password is incorrect.")

                elif len(new_password) < 6:
                    st.error("New password must contain at least 6 characters.")

                elif len(new_password.encode("utf-8")) > 72:
                    st.error("New password must not exceed 72 bytes.")

                elif new_password != confirm_password:
                    st.error("New password and confirmation do not match.")

                elif current_password == new_password:
                    st.error("New password must be different from your current password.")

                else:
                    try:
                        current_user.hashed_password = hash_password(new_password)
                        db.commit()

                        # Refresh the session copy so subsequent operations
                        # use the latest database values.
                        db.refresh(current_user)
                        st.session_state.user = current_user

                        st.success("✅ Password updated successfully. Please use the new password next time you log in.")

                    except Exception as e:
                        db.rollback()
                        st.error(f"❌ Error updating password: {e}")

        st.divider()

        # --------------------------------------------------
        # Account Summary
        # --------------------------------------------------
        st.subheader("ℹ️ Account Summary")

        summary_col1, summary_col2 = st.columns(2)

        with summary_col1:
            st.write(f"**User ID:** {user.id}")
            st.write(f"**Name:** {user.name}")

        with summary_col2:
            st.write(f"**Email:** {user.email}")
            st.write(f"**Role:** {role_value.upper()}")

    finally:
        db.close()


# ==================================================
# Role-Based Access Helpers
# ==================================================

def get_current_role():
    user = st.session_state.get("user")
    if not user or not getattr(user, "role", None):
        return "user"

    role = user.role
    role_name = getattr(role, "name", role)
    role_value = getattr(role_name, "value", role_name)
    return str(role_value).lower()


def is_admin():
    return get_current_role() == "admin"


def show_user_management():
    """Admin-only user and role management page."""

    if not is_admin():
        st.error("⛔ Access denied. Admin permission is required.")
        return

    st.header("👥 User Management")
    st.caption("Admin-only controls for viewing users and changing roles.")

    db = SessionLocal()

    try:
        users = (
            db.query(User)
            .options(joinedload(User.role))
            .order_by(User.id.asc())
            .all()
        )

        total_users = len(users)
        admin_count = sum(
            1 for item in users
            if getattr(getattr(item, "role", None), "name", "")
            and str(getattr(getattr(item.role, "name", ""), "value", item.role.name)).lower() == "admin"
        )
        user_count = total_users - admin_count

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("👤 Total Users", total_users)
        with col2:
            st.metric("🛡️ Admins", admin_count)
        with col3:
            st.metric("🙋 Users", user_count)

        st.divider()
        st.subheader("📋 Registered Users")

        if not users:
            st.info("No users found.")
            return

        rows = []
        for item in users:
            role_name = getattr(getattr(item, "role", None), "name", "user")
            role_value = getattr(role_name, "value", role_name)
            rows.append({
                "ID": item.id,
                "Name": getattr(item, "name", ""),
                "Email": item.email,
                "Role": str(role_value).upper()
            })

        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True
        )

        st.divider()
        st.subheader("🔐 Change User Role")

        current_user = st.session_state.user
        selectable_users = [item for item in users if item.id != current_user.id]

        if not selectable_users:
            st.info("There are no other users available for role management.")
            return

        selected_user = st.selectbox(
            "Select User",
            selectable_users,
            format_func=lambda item: f"{item.name} — {item.email}"
        )

        current_role_obj = getattr(selected_user, "role", None)
        current_role_name = getattr(current_role_obj, "name", "user")
        current_role = str(getattr(current_role_name, "value", current_role_name)).lower()

        new_role = st.selectbox(
            "Role",
            ["user", "admin"],
            index=0 if current_role == "user" else 1
        )

        if st.button(
            "💾 Update Role",
            use_container_width=True
        ):
            try:
                role_record = (
                    db.query(Role)
                    .filter(Role.name == new_role)
                    .first()
                )

                if not role_record:
                    st.error(f"Role '{new_role}' was not found in the roles table.")
                else:
                    selected_user.role_id = role_record.id
                    db.commit()
                    st.success(
                        f"✅ {selected_user.email} role updated to {new_role.upper()}."
                    )
                    st.rerun()

            except Exception as e:
                db.rollback()
                st.error(f"❌ Error updating role: {e}")

    finally:
        db.close()


# ==================================================
# Main Application
# ==================================================

if not st.session_state.logged_in:

    if st.session_state.get("auth_page") == "forgot_password":
        show_forgot_password()
    else:
        show_login()

else:

    # ==================================================
    # Sidebar
    # ==================================================

    st.sidebar.title(
        "Navigation"
    )

    navigation_pages = [
        "Dashboard",
        "Tasks",
        "Documents",
        "Semantic Search",
        "Analytics",
        "My Profile",
        "Notifications"
    ]

    if is_admin():
        navigation_pages.append("Activity Log")
        navigation_pages.append("User Management")

    page = st.sidebar.radio(
        "Go to",
        navigation_pages
    )

    # ==================================================
    # Logout
    # ==================================================

    if st.sidebar.button(
        "Logout"
    ):

        st.session_state.logged_in = False

        st.session_state.user = None
        st.session_state.auth_page = "login"
        clear_password_reset_state()

        st.rerun()

    # ==================================================
    # Pages
    # ==================================================

    if page == "Dashboard":

        show_dashboard()

    elif page == "Tasks":

        show_tasks()

    elif page == "Documents":

        show_documents()

    elif page == "Semantic Search":

        user = st.session_state.user

        st.header(
            "🔍 AI Semantic Search"
        )

        st.caption(
            "Search your uploaded PDF and TXT documents "
            "using natural language and FAISS embeddings."
        )

        st.divider()

        # ==================================================
        # SEARCH CONTROLS
        # ==================================================

        st.subheader("💬 Ask your knowledge base")

        query = st.text_input(
            "Enter your question",
            placeholder=(
                "Example: What are the technical skills "
                "mentioned in the document?"
            ),
            key="semantic_search_query"
        )

        control_col1, control_col2 = st.columns([2, 1])

        with control_col1:

            top_k = st.slider(
                "Number of results",
                min_value=1,
                max_value=10,
                value=5,
                help="Maximum number of matching chunks to display."
            )

        with control_col2:

            min_score = st.slider(
                "Minimum similarity",
                min_value=0.0,
                max_value=1.0,
                value=0.0,
                step=0.05,
                help=(
                    "Higher values show only more similar "
                    "semantic matches."
                )
            )

        search_clicked = st.button(
            "🔍 Search Documents",
            use_container_width=True,
            type="primary"
        )

        # ==================================================
        # SEARCH
        # ==================================================

        if search_clicked:

            if not query.strip():

                st.warning(
                    "⚠️ Please enter a question before searching."
                )

            else:

                clean_query = query.strip()

                with st.spinner(
                    "🧠 Searching the knowledge base..."
                ):

                    results = search(
                        clean_query,
                        top_k=top_k
                    )

                # Save the search in MySQL history.
                save_search_history(
                    clean_query,
                    user_id=(
                        user.id
                        if user
                        else None
                    )
                )

                filtered_results = [
                    (vector_id, score)
                    for vector_id, score in results
                    if score >= min_score
                ]

                st.session_state["last_search_query"] = (
                    clean_query
                )

                st.session_state["last_search_results"] = (
                    filtered_results
                )

                st.session_state["last_search_min_score"] = (
                    min_score
                )

        # ==================================================
        # DISPLAY LAST SEARCH
        # ==================================================

        if "last_search_results" in st.session_state:

            last_results = (
                st.session_state["last_search_results"]
            )

            last_query = (
                st.session_state.get(
                    "last_search_query",
                    ""
                )
            )

            if last_query:

                st.divider()

                st.subheader(
                    "📌 Search Results"
                )

                st.write(
                    f"**Question:** {last_query}"
                )

                if not last_results:

                    st.info(
                        "No results matched the selected "
                        "similarity threshold. Try lowering "
                        "the minimum similarity."
                    )

                else:

                    st.success(
                        f"Found {len(last_results)} relevant "
                        f"result(s)."
                    )

                    db = SessionLocal()

                    try:

                        displayed_results = 0

                        for rank, (vector_id, score) in enumerate(
                            last_results,
                            start=1
                        ):

                            chunk = (
                                db.query(DocumentChunk)
                                .filter(
                                    DocumentChunk.vector_index
                                    == vector_id
                                )
                                .first()
                            )

                            if not chunk:
                                continue

                            document = (
                                db.query(Document)
                                .filter(
                                    Document.id
                                    == chunk.document_id
                                )
                                .first()
                            )

                            if not document:
                                continue

                            displayed_results += 1

                            similarity_percent = max(
                                0.0,
                                min(
                                    100.0,
                                    score * 100
                                )
                            )

                            file_type = (
                                document.file_type.upper()
                                if document.file_type
                                else "FILE"
                            )

                            with st.container(
                                border=True
                            ):

                                result_col1, result_col2 = (
                                    st.columns([4, 1])
                                )

                                with result_col1:

                                    st.markdown(
                                        f"### {rank}. "
                                        f"📄 {document.filename}"
                                    )

                                    st.caption(
                                        f"{file_type} • "
                                        f"Chunk {chunk.id}"
                                    )

                                with result_col2:

                                    st.metric(
                                        "Similarity",
                                        f"{similarity_percent:.1f}%"
                                    )

                                st.divider()

                                st.write(
                                    chunk.chunk_text
                                )

                        if displayed_results == 0:

                            st.warning(
                                "The search returned vector IDs, "
                                "but their database chunks could "
                                "not be found."
                            )

                    finally:

                        db.close()

        # ==================================================
        # SEARCH HISTORY
        # ==================================================

        st.divider()

        st.subheader(
            "🕘 Search History"
        )

        history = load_search_history(
            limit=10
        )

        if not history:

            st.info(
                "No search history available yet. "
                "Run a search to create your first entry."
            )

        else:

            for index, (history_query, timestamp) in enumerate(
                history,
                start=1
            ):

                history_col1, history_col2 = (
                    st.columns([4, 1])
                )

                with history_col1:

                    st.write(
                        f"**{index}.** {history_query}"
                    )

                with history_col2:

                    if timestamp:

                        st.caption(
                            str(timestamp)
                        )

                    else:

                        st.caption(
                            "Search recorded"
                        )

        # ==================================================
        # SEARCH TIPS
        # ==================================================

        with st.expander(
            "💡 Search Tips"
        ):

            st.write(
                "• Ask natural-language questions instead of "
                "using exact keywords."
            )

            st.write(
                "• Use the similarity slider to control how "
                "closely results should match your question."
            )

            st.write(
                "• Increase the number of results when the "
                "information may be spread across several chunks."
            )

            st.write(
                "• Upload and index documents from the "
                "Documents page before searching."
            )

    elif page == "User Management":

        show_user_management()

    elif page == "My Profile":

        show_profile()
    
    elif page == "Notifications":

        show_notifications()
    
    elif page == "Activity Log":

        show_activity_log()


    elif page == "Analytics":

        st.header(
            "📈 Analytics Dashboard"
        )

        st.caption(
            "Live insights from your MySQL task and knowledge data."
        )

        st.divider()

        db = SessionLocal()

        try:

            # ==================================================
            # FETCH ANALYTICS DATA
            # ==================================================

            total_tasks = (
                db.query(Task)
                .count()
            )

            pending_tasks = (
                db.query(Task)
                .filter(Task.status == "pending")
                .count()
            )

            completed_tasks = (
                db.query(Task)
                .filter(Task.status == "completed")
                .count()
            )

            total_documents = (
                db.query(Document)
                .count()
            )

            total_chunks = (
                db.query(DocumentChunk)
                .count()
            )

            pdf_documents = (
                db.query(Document)
                .filter(Document.file_type == "pdf")
                .count()
            )

            txt_documents = (
                db.query(Document)
                .filter(Document.file_type == "txt")
                .count()
            )

            total_searches = (
                db.query(SearchQuery)
                .count()
            )

            # ==================================================
            # SEARCH ACTIVITY OVER TIME
            # ==================================================

            search_activity = []

            query_column, time_column = _search_history_columns()

            if time_column:
                search_rows = (
                    db.query(
                        func.date(
                            getattr(SearchQuery, time_column)
                        ).label("search_date"),
                        func.count(SearchQuery.id).label("search_count")
                    )
                    .group_by(
                        func.date(
                            getattr(SearchQuery, time_column)
                        )
                    )
                    .order_by(
                        func.date(
                            getattr(SearchQuery, time_column)
                        )
                    )
                    .all()
                )

                search_activity = [
                    {
                        "Date": row.search_date,
                        "Searches": row.search_count
                    }
                    for row in search_rows
                ]

            # ==================================================
            # EXPORT ANALYTICS REPORT
            # ==================================================

            analytics_data = pd.DataFrame([
                {
                    "Metric": "Total Tasks",
                    "Value": total_tasks
                },
                {
                    "Metric": "Pending Tasks",
                    "Value": pending_tasks
                },
                {
                    "Metric": "Completed Tasks",
                    "Value": completed_tasks
                },
                {
                    "Metric": "Total Documents",
                    "Value": total_documents
                },
                {
                    "Metric": "Total Chunks",
                    "Value": total_chunks
                },
                {
                    "Metric": "PDF Documents",
                    "Value": pdf_documents
                },
                {
                    "Metric": "TXT Documents",
                    "Value": txt_documents
                },
                {
                    "Metric": "Total Searches",
                    "Value": total_searches
                }
            ])

            csv_data = analytics_data.to_csv(index=False)

            st.download_button(
                label="📥 Download Analytics Report",
                data=csv_data,
                file_name="analytics_report.csv",
                mime="text/csv",
                use_container_width=True
            )

            st.divider()

            # ==================================================
            # KPI CARDS
            # ==================================================

            st.subheader("📊 Key Metrics")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "📋 Total Tasks",
                    total_tasks
                )

            with col2:
                st.metric(
                    "⏳ Pending",
                    pending_tasks
                )

            with col3:
                st.metric(
                    "✅ Completed",
                    completed_tasks
                )

            with col4:
                st.metric(
                    "🔍 Searches",
                    total_searches
                )

            st.divider()

            # ==================================================
            # TASK ANALYTICS
            # ==================================================

            st.subheader("📋 Task Analytics")

            task_col1, task_col2 = st.columns(2)

            with task_col1:

                st.metric(
                    "⏳ Pending Tasks",
                    pending_tasks
                )

                st.metric(
                    "✅ Completed Tasks",
                    completed_tasks
                )

            with task_col2:

                if total_tasks > 0:

                    completion_rate = (
                        completed_tasks / total_tasks
                    ) * 100

                else:

                    completion_rate = 0

                st.metric(
                    "📈 Completion Rate",
                    f"{completion_rate:.1f}%"
                )

                st.progress(
                    min(completion_rate / 100, 1.0)
                )

            st.write(
                "### Task Status Distribution"
            )

            task_chart_data = {
                "Completed": completed_tasks,
                "Pending": pending_tasks
            }

            st.bar_chart(
                task_chart_data,
                height=300
            )

            st.divider()

            # ==================================================
            # DOCUMENT ANALYTICS
            # ==================================================

            st.subheader("📄 Document Analytics")

            doc_col1, doc_col2, doc_col3 = st.columns(3)

            with doc_col1:

                st.metric(
                    "📚 Total Documents",
                    total_documents
                )

            with doc_col2:

                st.metric(
                    "🧩 Total Chunks",
                    total_chunks
                )

            with doc_col3:

                st.metric(
                    "📑 PDF / TXT",
                    f"{pdf_documents} / {txt_documents}"
                )

            st.write(
                "### Documents by File Type"
            )

            document_chart_data = {
                "PDF": pdf_documents,
                "TXT": txt_documents
            }

            st.bar_chart(
                document_chart_data,
                height=300
            )

            st.divider()

            # ==================================================
            # SEARCH ANALYTICS
            # ==================================================

            st.subheader("🔍 Search Analytics")

            search_col1, search_col2 = st.columns(2)

            with search_col1:

                st.metric(
                    "🔎 Total Semantic Searches",
                    total_searches
                )

            with search_col2:

                if total_documents > 0:

                    searches_per_document = (
                        total_searches / total_documents
                    )

                else:

                    searches_per_document = 0

                st.metric(
                    "📊 Searches / Document",
                    f"{searches_per_document:.1f}"
                )

            st.write("### 📈 Search Activity Over Time")

            if search_activity:

                search_activity_df = pd.DataFrame(
                    search_activity
                )

                st.line_chart(
                    search_activity_df.set_index("Date"),
                    height=300
                )

            else:

                st.info(
                    "No dated search activity is available yet."
                )

            st.divider()

            # ==================================================
            # KNOWLEDGE BASE SUMMARY
            # ==================================================

            st.subheader("🧠 Knowledge Base Summary")

            knowledge_col1, knowledge_col2 = st.columns(2)

            with knowledge_col1:

                st.write(
                    "### 📚 Documents"
                )

                st.write(
                    f"**Total documents:** {total_documents}"
                )

                st.write(
                    f"**PDF files:** {pdf_documents}"
                )

                st.write(
                    f"**TXT files:** {txt_documents}"
                )

            with knowledge_col2:

                st.write(
                    "### 🧩 Indexed Content"
                )

                st.write(
                    f"**Total chunks:** {total_chunks}"
                )

                st.write(
                    f"**Semantic searches:** {total_searches}"
                )

                st.write(
                    "FAISS is used for semantic similarity search."
                )

            st.success(
                "✅ Analytics data loaded successfully "
                "from the MySQL database."
            )

        except Exception as e:

            st.error(
                f"❌ Error loading analytics: {e}"
            )

        finally:

            db.close()
