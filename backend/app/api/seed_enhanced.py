"""
Enhanced seed data endpoint with comprehensive mock data for analytics testing.

Access at: POST /api/seed/populate-enhanced
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, UTC, timedelta
import random

from app.core.db import get_db
from app.api.dependencies import get_current_user
from app.core.security import is_admin
from app.models.user import User
from app.models.knowledge import KnowledgeSource, KnowledgeChunk
from app.models.task import Task
from app.models.query import Query, QueryResponse
from app.models.chat_session import ChatSession
from app.models.enums import CategoryEnum, TaskTypeEnum, TaskStatusEnum
from app.schemas.user_schema import UserRole
from app.schemas.query_schema import QueryStatus, QueryCategory, QueryPriority
from app.core.security import hash_password


router = APIRouter(prefix="/seed", tags=["Seed Data"])


@router.post("/populate-enhanced")
async def populate_enhanced_database(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Populate database with comprehensive mock data for analytics testing.

    Creates:
    - 20+ users across all roles
    - 50+ queries with various statuses and dates
    - 100+ query responses
    - 30+ knowledge sources
    - 20+ chat sessions
    - 15+ tasks

    This generates realistic data patterns for testing analytics dashboards.
    """

    result = {
        "users_created": 0,
        "knowledge_sources_created": 0,
        "queries_created": 0,
        "responses_created": 0,
        "chat_sessions_created": 0,
        "tasks_created": 0
    }

    # Create diverse users
    users_data = [
        # Core test users
        {"email": "admin@test.com", "full_name": "Admin User", "role": UserRole.ADMIN, "password": "admin123"},
        {"email": "instructor@test.com", "full_name": "Dr. Sarah Johnson", "role": UserRole.INSTRUCTOR, "password": "instructor123"},

        # TAs
        {"email": "ta1@test.com", "full_name": "Alex Chen", "role": UserRole.TA, "password": "ta123"},
        {"email": "ta2@test.com", "full_name": "Maria Garcia", "role": UserRole.TA, "password": "ta123"},
        {"email": "ta3@test.com", "full_name": "David Kim", "role": UserRole.TA, "password": "ta123"},

        # Students
        {"email": "student1@test.com", "full_name": "Emma Wilson", "role": UserRole.STUDENT, "password": "student123"},
        {"email": "student2@test.com", "full_name": "Michael Brown", "role": UserRole.STUDENT, "password": "student123"},
        {"email": "student3@test.com", "full_name": "Sophia Taylor", "role": UserRole.STUDENT, "password": "student123"},
        {"email": "student4@test.com", "full_name": "James Anderson", "role": UserRole.STUDENT, "password": "student123"},
        {"email": "student5@test.com", "full_name": "Olivia Martinez", "role": UserRole.STUDENT, "password": "student123"},
        {"email": "student6@test.com", "full_name": "William Thomas", "role": UserRole.STUDENT, "password": "student123"},
        {"email": "student7@test.com", "full_name": "Ava Jackson", "role": UserRole.STUDENT, "password": "student123"},
        {"email": "student8@test.com", "full_name": "Noah White", "role": UserRole.STUDENT, "password": "student123"},
        {"email": "student9@test.com", "full_name": "Isabella Harris", "role": UserRole.STUDENT, "password": "student123"},
        {"email": "student10@test.com", "full_name": "Lucas Martin", "role": UserRole.STUDENT, "password": "student123"},
    ]

    created_users = []
    for user_data in users_data:
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if not existing:
            # Create user with varied creation dates
            days_ago = random.randint(30, 180)
            user = User(
                email=user_data["email"],
                full_name=user_data["full_name"],
                role=user_data["role"],
                password=hash_password(user_data["password"]),
                is_active=True,
                created_at=datetime.now(UTC) - timedelta(days=days_ago)
            )
            db.add(user)
            db.flush()
            created_users.append(user)
            result["users_created"] += 1
        else:
            created_users.append(existing)

    # Get users by role for easier access
    students = [u for u in created_users if u.role == UserRole.STUDENT]
    tas = [u for u in created_users if u.role == UserRole.TA]
    instructors = [u for u in created_users if u.role == UserRole.INSTRUCTOR]

    # Create diverse queries with realistic patterns
    query_templates = [
        # Technical queries
        ("How to implement binary search tree?", "I'm trying to implement a self-balancing BST but struggling with rotations", QueryCategory.TECHNICAL, QueryPriority.MEDIUM),
        ("Docker container won't start", "Getting 'port already allocated' error", QueryCategory.TECHNICAL, QueryPriority.HIGH),
        ("Git merge conflict help", "Stuck on merge conflict in main.py", QueryCategory.TECHNICAL, QueryPriority.HIGH),
        ("SQL query optimization", "My JOIN query is taking 30+ seconds", QueryCategory.TECHNICAL, QueryPriority.MEDIUM),
        ("Memory leak in Python", "Process memory keeps growing, suspect circular references", QueryCategory.TECHNICAL, QueryPriority.HIGH),

        # Assignment queries
        ("Assignment 2 deadline extension?", "Need a few more days due to medical issue", QueryCategory.ASSIGNMENTS, QueryPriority.MEDIUM),
        ("Clarification on Assignment 3 requirements", "Do we need to implement caching?", QueryCategory.ASSIGNMENTS, QueryPriority.LOW),
        ("Assignment submission format", "Should I submit as ZIP or GitHub repo?", QueryCategory.ASSIGNMENTS, QueryPriority.LOW),
        ("Test cases for Assignment 1", "Are we provided test cases or write our own?", QueryCategory.ASSIGNMENTS, QueryPriority.MEDIUM),

        # Course material queries
        ("Can't access lecture videos", "Getting 403 error on course portal", QueryCategory.COURSES, QueryPriority.HIGH),
        ("Difference between TCP and UDP?", "Need clarification from Week 5 lecture", QueryCategory.COURSES, QueryPriority.LOW),
        ("Recommended books for data structures?", "Looking for supplementary reading", QueryCategory.COURSES, QueryPriority.LOW),
        ("Week 7 quiz topics", "What chapters will be covered?", QueryCategory.COURSES, QueryPriority.MEDIUM),

        # Exam queries
        ("Exam date confirmation", "Is midterm on March 15 or 16?", QueryCategory.EXAMS, QueryPriority.HIGH),
        ("Can we use notes during exam?", "Open book or closed book?", QueryCategory.EXAMS, QueryPriority.MEDIUM),
        ("Exam venue location", "Which building and room number?", QueryCategory.EXAMS, QueryPriority.MEDIUM),

        # General queries
        ("Office hours this week?", "Will there be office hours on Friday?", QueryCategory.GENERAL, QueryPriority.LOW),
        ("How to join course Slack?", "Need invite link", QueryCategory.GENERAL, QueryPriority.LOW),
        ("Lab timings change?", "Heard labs moved to afternoons", QueryCategory.GENERAL, QueryPriority.LOW),
    ]

    # Duplicate some queries to create FAQs
    frequent_queries = [
        ("How do I submit my assignment?", "Where is the submission portal?", QueryCategory.ASSIGNMENTS, QueryPriority.LOW),
        ("What is the deadline for project submission?", "Final project due date?", QueryCategory.ASSIGNMENTS, QueryPriority.MEDIUM),
        ("Can I work in a group?", "Is group work allowed?", QueryCategory.ASSIGNMENTS, QueryPriority.LOW),
        ("How to access course materials?", "Can't find lecture slides", QueryCategory.COURSES, QueryPriority.MEDIUM),
    ]

    # Create regular queries
    for title, description, category, priority in query_templates * 2:  # Double the queries
        student = random.choice(students)
        days_ago = random.randint(0, 30)
        hours_offset = random.randint(0, 23)

        status = random.choices(
            [QueryStatus.OPEN, QueryStatus.IN_PROGRESS, QueryStatus.RESOLVED, QueryStatus.CLOSED],
            weights=[20, 15, 50, 15]  # More resolved queries
        )[0]

        query = Query(
            title=title,
            description=description,
            category=category,
            priority=priority,
            status=status,
            student_id=student.id,
            tags=f"{category.value.lower()},help",
            created_at=datetime.now(UTC) - timedelta(days=days_ago, hours=hours_offset)
        )
        db.add(query)
        db.flush()
        result["queries_created"] += 1

        # Add responses to some queries
        if status in [QueryStatus.IN_PROGRESS, QueryStatus.RESOLVED, QueryStatus.CLOSED]:
            # TA response
            ta = random.choice(tas) if tas else student
            response = QueryResponse(
                query_id=query.id,
                user_id=ta.id,
                content="I'm looking into this. Can you provide more details about your setup?",
                created_at=query.created_at + timedelta(hours=random.randint(1, 12))
            )
            db.add(response)
            result["responses_created"] += 1

            # Solution if resolved
            if status in [QueryStatus.RESOLVED, QueryStatus.CLOSED]:
                solution = QueryResponse(
                    query_id=query.id,
                    user_id=ta.id,
                    content="Here's the solution: " + random.choice([
                        "You need to update your configuration file.",
                        "Try reinstalling the dependencies.",
                        "This is a known issue, here's the workaround.",
                        "Please refer to the documentation section 4.2",
                        "I've uploaded the corrected version to the course portal."
                    ]),
                    is_solution=True,
                    created_at=query.created_at + timedelta(hours=random.randint(13, 48))
                )
                db.add(solution)
                result["responses_created"] += 1

    # Create FAQ pattern (same questions multiple times)
    for title, description, category, priority in frequent_queries:
        for _ in range(random.randint(5, 12)):  # Each FAQ asked 5-12 times
            student = random.choice(students)
            days_ago = random.randint(0, 30)

            query = Query(
                title=title,
                description=description,
                category=category,
                priority=priority,
                status=QueryStatus.RESOLVED,  # FAQs are usually resolved
                student_id=student.id,
                tags=f"{category.value.lower()},faq",
                created_at=datetime.now(UTC) - timedelta(days=days_ago)
            )
            db.add(query)
            db.flush()
            result["queries_created"] += 1

            # Add standard FAQ response
            ta = random.choice(tas) if tas else student
            response = QueryResponse(
                query_id=query.id,
                user_id=ta.id,
                content="This is a frequently asked question. Please check the course FAQ page for detailed instructions.",
                is_solution=True,
                created_at=query.created_at + timedelta(hours=random.randint(1, 6))
            )
            db.add(response)
            result["responses_created"] += 1

    # Create knowledge sources
    knowledge_sources = [
        ("Python Programming Basics", "Introduction to Python syntax and concepts", CategoryEnum.COURSES),
        ("Advanced Data Structures", "Trees, Graphs, Heaps, and Hash Tables", CategoryEnum.COURSES),
        ("Database Design Principles", "Normalization and optimization techniques", CategoryEnum.COURSES),
        ("Web Development with FastAPI", "Building RESTful APIs", CategoryEnum.COURSES),
        ("Machine Learning Fundamentals", "Supervised and unsupervised learning", CategoryEnum.COURSES),
        ("Assignment 1: Calculator App", "Build a command-line calculator", CategoryEnum.ASSIGNMENTS),
        ("Assignment 2: Web Scraper", "Create a web scraping tool", CategoryEnum.ASSIGNMENTS),
        ("Assignment 3: Database Project", "Design and implement a database", CategoryEnum.ASSIGNMENTS),
        ("Midterm Exam Format", "What to expect in the midterm", CategoryEnum.EXAMS),
        ("Final Project Guidelines", "Requirements and rubric", CategoryEnum.ASSIGNMENTS),
        ("Course Syllabus", "Complete course outline and schedule", CategoryEnum.COURSES),
        ("FAQ: Grading Policy", "How grades are calculated", CategoryEnum.QUERIES),
        ("FAQ: Late Submission Policy", "Penalties and procedures", CategoryEnum.QUERIES),
        ("System Architecture Overview", "Understanding the tech stack", CategoryEnum.COURSES),
        ("Testing Best Practices", "Unit testing and integration testing", CategoryEnum.COURSES),
    ]

    for title, description, category in knowledge_sources:
        existing = db.query(KnowledgeSource).filter(KnowledgeSource.title == title).first()
        if not existing:
            content = f"{description}. This is comprehensive material covering key concepts, examples, and best practices. " * 3

            source = KnowledgeSource(
                title=title,
                description=description,
                content=content,
                category=category,
                is_active=True,
                created_at=datetime.now(UTC) - timedelta(days=random.randint(10, 90))
            )
            db.add(source)
            db.flush()

            # Create chunk
            chunk = KnowledgeChunk(
                source_id=source.id,
                text=content,
                index=0
            )
            db.add(chunk)
            result["knowledge_sources_created"] += 1

    # Create chat sessions
    for student in students[:8]:  # First 8 students have chat history
        num_sessions = random.randint(2, 5)
        for _ in range(num_sessions):
            days_ago = random.randint(0, 30)
            session = ChatSession(
                user_id=student.id,
                title=f"Chat session about {random.choice(['assignments', 'exams', 'concepts', 'debugging'])}",
                created_at=datetime.now(UTC) - timedelta(days=days_ago)
            )
            db.add(session)
            result["chat_sessions_created"] += 1

    # Create diverse tasks
    tasks_data = [
        ("Weekly grade calculation", "Calculate student grades", TaskTypeEnum.REPORT_GENERATION, TaskStatusEnum.COMPLETED),
        ("Monthly performance report", "Generate analytics report", TaskTypeEnum.REPORT_GENERATION, TaskStatusEnum.COMPLETED),
        ("Process assignment submissions", "Batch process uploads", TaskTypeEnum.DATA_PROCESSING, TaskStatusEnum.COMPLETED),
        ("Index knowledge base", "Update search indices", TaskTypeEnum.DATA_PROCESSING, TaskStatusEnum.IN_PROGRESS, 75),
        ("Send deadline reminders", "Email notifications", TaskTypeEnum.EMAIL, TaskStatusEnum.COMPLETED),
        ("Backup database", "Daily backup", TaskTypeEnum.DATA_PROCESSING, TaskStatusEnum.COMPLETED),
        ("Generate attendance report", "Weekly attendance", TaskTypeEnum.REPORT_GENERATION, TaskStatusEnum.IN_PROGRESS, 50),
        ("Clean up old sessions", "Remove expired data", TaskTypeEnum.DATA_PROCESSING, TaskStatusEnum.PENDING),
        ("Export course analytics", "Generate CSV reports", TaskTypeEnum.REPORT_GENERATION, TaskStatusEnum.COMPLETED),
        ("Update course materials", "Sync with repository", TaskTypeEnum.DATA_PROCESSING, TaskStatusEnum.FAILED, 0, "Connection timeout"),
        ("Process quiz submissions", "Grade quizzes", TaskTypeEnum.DATA_PROCESSING, TaskStatusEnum.COMPLETED),
        ("Send welcome emails", "New student onboarding", TaskTypeEnum.EMAIL, TaskStatusEnum.COMPLETED),
        ("Archive old queries", "Clean up database", TaskTypeEnum.DATA_PROCESSING, TaskStatusEnum.IN_PROGRESS, 30),
        ("Generate completion certificates", "Create PDFs", TaskTypeEnum.REPORT_GENERATION, TaskStatusEnum.PENDING),
        ("Sync calendar events", "Update course calendar", TaskTypeEnum.DATA_PROCESSING, TaskStatusEnum.COMPLETED),
    ]

    for task_data in tasks_data:
        name, desc, task_type, status = task_data[:4]
        progress = task_data[4] if len(task_data) > 4 else 0
        error = task_data[5] if len(task_data) > 5 else None

        task = Task(
            task_type=task_type.value if hasattr(task_type, 'value') else task_type,
            status=status.value if hasattr(status, 'value') else status,
            error_message=error,
            created_at=datetime.now(UTC) - timedelta(days=random.randint(0, 14))
        )
        db.add(task)
        result["tasks_created"] += 1

    db.commit()

    result["message"] = "Enhanced mock data created successfully"
    result["test_credentials"] = {
        "admin": {"email": "admin@test.com", "password": "admin123"},
        "instructor": {"email": "instructor@test.com", "password": "instructor123"},
        "ta": {"email": "ta1@test.com", "password": "ta123"},
        "student": {"email": "student1@test.com", "password": "student123"}
    }

    return result


@router.delete("/clear-all")
async def clear_all_data(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Clear ALL data from database (use with caution!).

    **Warning**: This will delete everything including users!
    Only use in development/testing environments.
    """
    try:
        # Delete in correct order to respect foreign key constraints
        db.query(QueryResponse).delete()
        db.query(Query).delete()
        db.query(KnowledgeChunk).delete()
        db.query(KnowledgeSource).delete()
        db.query(ChatSession).delete()
        db.query(Task).delete()
        db.query(User).delete()

        db.commit()

        return {"message": "All data cleared successfully"}
    except Exception as e:
        db.rollback()
        from fastapi import HTTPException; raise HTTPException(status_code=500, detail="Failed to clear data")
