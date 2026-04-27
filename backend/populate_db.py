"""
Script to populate database with mock data.

Run this script to add test users, queries, knowledge sources, and tasks.
Usage: python populate_db.py

This script ensures at least 10 entries in each table.
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta, timezone
import random
import uuid

from config.db import SessionLocal, engine, Base
from app.models.user import User
from app.models.profile import Profile
from app.models.course import Course
from app.models.knowledge import KnowledgeSource, KnowledgeChunk
from app.models.task import Task
from app.models.query import Query, QueryResponse
from app.models.chat_session import ChatSession
from app.models.doubts import DoubtUpload, DoubtMessage
from app.models.announcement import Announcement
from app.models.resource import Resource
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.slide_deck import SlideDeck
from app.models.tag import Tag
from app.models.call import Call
from app.models.enums import CategoryEnum, TaskTypeEnum, TaskStatusEnum, CallStatusEnum
from app.schemas.user_schema import UserRole
from app.schemas.query_schema import QueryStatus, QueryCategory, QueryPriority
from app.schemas.announcement_schema import AnnouncementType, AnnouncementTarget
from app.schemas.resource_schema import ResourceType, ResourceVisibility
from config.security import hash_password
from datetime import date


def populate_database():
    """Populate database with comprehensive mock data (at least 10 entries per table)."""

    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created\n")

    db = SessionLocal()

    try:
        result = {
            "users_created": 0,
            "profiles_created": 0,
            "courses_created": 0,
            "chat_sessions_created": 0,
            "knowledge_sources_created": 0,
            "knowledge_chunks_created": 0,
            "tasks_created": 0,
            "queries_created": 0,
            "query_responses_created": 0,
            "doubt_uploads_created": 0,
            "doubt_messages_created": 0,
            "announcements_created": 0,
            "resources_created": 0,
            "quizzes_created": 0,
            "quiz_attempts_created": 0,
            "slide_decks_created": 0,
            "tags_created": 0,
            "calls_created": 0
        }

        # ============================================================
        # CREATE USERS (10+ entries)
        # ============================================================
        print("Creating test users...")
        users_data = [
            # Students (5)
            {"email": "student@test.com", "full_name": "Test Student", "role": UserRole.STUDENT, "password": "student123"},
            {"email": "alice.smith@test.com", "full_name": "Alice Smith", "role": UserRole.STUDENT, "password": "alice123"},
            {"email": "bob.johnson@test.com", "full_name": "Bob Johnson", "role": UserRole.STUDENT, "password": "bob123"},
            {"email": "carol.williams@test.com", "full_name": "Carol Williams", "role": UserRole.STUDENT, "password": "carol123"},
            {"email": "david.brown@test.com", "full_name": "David Brown", "role": UserRole.STUDENT, "password": "david123"},
            # TAs (2)
            {"email": "ta@test.com", "full_name": "Test TA", "role": UserRole.TA, "password": "ta123"},
            {"email": "emma.davis@test.com", "full_name": "Emma Davis", "role": UserRole.TA, "password": "emma123"},
            # Instructors (2)
            {"email": "instructor@test.com", "full_name": "Test Instructor", "role": UserRole.INSTRUCTOR, "password": "instructor123"},
            {"email": "frank.miller@test.com", "full_name": "Prof. Frank Miller", "role": UserRole.INSTRUCTOR, "password": "frank123"},
            # Admins (2)
            {"email": "admin@test.com", "full_name": "Test Admin", "role": UserRole.ADMIN, "password": "admin123"},
            {"email": "grace.wilson@test.com", "full_name": "Grace Wilson", "role": UserRole.ADMIN, "password": "grace123"},
            # Extra students (to ensure variety)
            {"email": "henry.taylor@test.com", "full_name": "Henry Taylor", "role": UserRole.STUDENT, "password": "henry123"},
        ]

        created_users = {}
        all_students = []
        all_tas = []
        all_instructors = []

        for user_data in users_data:
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if not existing:
                user = User(
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    password=hash_password(user_data["password"]),
                    is_active=True
                )
                db.add(user)
                db.flush()
                created_users[user_data["email"]] = user
                result["users_created"] += 1
                print(f"  + Created user: {user_data['email']}")
            else:
                created_users[user_data["email"]] = existing
                print(f"  - User already exists: {user_data['email']}")

            # Categorize users
            user_obj = created_users[user_data["email"]]
            if user_data["role"] == UserRole.STUDENT:
                all_students.append(user_obj)
            elif user_data["role"] == UserRole.TA:
                all_tas.append(user_obj)
            elif user_data["role"] == UserRole.INSTRUCTOR:
                all_instructors.append(user_obj)

        # ============================================================
        # CREATE PROFILES (10+ entries - one per user)
        # ============================================================
        print("\nCreating user profiles...")

        profiles_data = [
            # Students
            {"email": "student@test.com", "bio": "Computer Science student passionate about AI and ML", "department": "Computer Science", "year": 3, "interests": ["AI", "Machine Learning", "Python"], "phone": "+1-555-0101"},
            {"email": "alice.smith@test.com", "bio": "Data Science enthusiast, love working with big data", "department": "Data Science", "year": 2, "interests": ["Data Analysis", "Statistics", "R"], "phone": "+1-555-0102"},
            {"email": "bob.johnson@test.com", "bio": "Full-stack developer interested in web technologies", "department": "Computer Science", "year": 4, "interests": ["React", "Node.js", "TypeScript"], "phone": "+1-555-0103"},
            {"email": "carol.williams@test.com", "bio": "Cybersecurity researcher focusing on network security", "department": "Information Security", "year": 3, "interests": ["Security", "Networking", "Cryptography"], "phone": "+1-555-0104"},
            {"email": "david.brown@test.com", "bio": "Mobile app developer with iOS and Android experience", "department": "Software Engineering", "year": 2, "interests": ["iOS", "Android", "Flutter"], "phone": "+1-555-0105"},
            {"email": "henry.taylor@test.com", "bio": "Cloud computing enthusiast interested in DevOps", "department": "Computer Science", "year": 4, "interests": ["AWS", "Docker", "Kubernetes"], "phone": "+1-555-0106"},
            # TAs
            {"email": "ta@test.com", "bio": "Graduate TA for Data Structures and Algorithms", "department": "Computer Science", "year": None, "interests": ["Teaching", "Algorithms", "Problem Solving"], "phone": "+1-555-0201"},
            {"email": "emma.davis@test.com", "bio": "Research assistant in NLP and computational linguistics", "department": "Computer Science", "year": None, "interests": ["NLP", "Deep Learning", "Research"], "phone": "+1-555-0202"},
            # Instructors
            {"email": "instructor@test.com", "bio": "Professor with 15 years of teaching experience in software engineering", "department": "Computer Science", "year": None, "interests": ["Software Engineering", "Agile", "Teaching"], "phone": "+1-555-0301"},
            {"email": "frank.miller@test.com", "bio": "Associate Professor specializing in database systems and distributed computing", "department": "Computer Science", "year": None, "interests": ["Databases", "Distributed Systems", "Research"], "phone": "+1-555-0302"},
            # Admins
            {"email": "admin@test.com", "bio": "System administrator managing the AURA platform", "department": "IT Services", "year": None, "interests": ["System Administration", "DevOps", "Security"], "phone": "+1-555-0401"},
            {"email": "grace.wilson@test.com", "bio": "Academic coordinator and platform manager", "department": "Academic Affairs", "year": None, "interests": ["Education Technology", "Management", "Student Success"], "phone": "+1-555-0402"},
        ]

        for profile_data in profiles_data:
            user = created_users.get(profile_data["email"])
            if user:
                existing_profile = db.query(Profile).filter(Profile.user_id == user.id).first()
                if not existing_profile:
                    profile = Profile(
                        user_id=user.id,
                        full_name=user.full_name,
                        bio=profile_data["bio"],
                        department=profile_data["department"],
                        year_of_study=profile_data["year"],
                        interests=profile_data["interests"],
                        phone=profile_data["phone"],
                        social_links={"github": f"https://github.com/{profile_data['email'].split('@')[0]}", "linkedin": f"https://linkedin.com/in/{profile_data['email'].split('@')[0]}"},
                        query_count=random.randint(0, 10),
                        resolved_count=random.randint(0, 5),
                        resource_count=random.randint(0, 3),
                        reputation_score=random.randint(10, 100)
                    )
                    db.add(profile)
                    result["profiles_created"] += 1
                    print(f"  + Created profile for: {profile_data['email']}")
                else:
                    print(f"  - Profile already exists for: {profile_data['email']}")

        # ============================================================
        # CREATE TAGS (5 entries)
        # ============================================================
        print("\nCreating tags...")
        tags_data = [
            "Python",
            "Database",
            "Algorithms",
            "Web Development",
            "Machine Learning",
        ]

        instructor_for_tags = all_instructors[0] if all_instructors else list(created_users.values())[0]
        created_tags = []
        for tag_name in tags_data:
            existing_tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not existing_tag:
                tag = Tag(
                    name=tag_name,
                    created_by_id=instructor_for_tags.id
                )
                db.add(tag)
                db.flush()
                created_tags.append(tag)
                result["tags_created"] += 1
                print(f"  + Created tag: {tag_name}")
            else:
                created_tags.append(existing_tag)
                print(f"  - Tag already exists: {tag_name}")

        # ============================================================
        # CREATE COURSES (10+ entries)
        # ============================================================
        print("\nCreating courses...")

        # Get an instructor to create courses
        course_creator = all_instructors[0] if all_instructors else list(created_users.values())[0]

        courses_data = [
            {"name": "Introduction to Programming", "description": "Fundamentals of programming using Python. Covers variables, control structures, functions, and basic data structures."},
            {"name": "Data Structures and Algorithms", "description": "Study of fundamental data structures (arrays, linked lists, trees, graphs) and algorithms (sorting, searching, dynamic programming)."},
            {"name": "Database Management Systems", "description": "Relational database design, SQL, normalization, transactions, and database optimization techniques."},
            {"name": "Operating Systems", "description": "Process management, memory management, file systems, and I/O. Includes practical labs with Linux."},
            {"name": "Computer Networks", "description": "OSI model, TCP/IP, routing protocols, network security, and socket programming."},
            {"name": "Software Engineering", "description": "Software development lifecycle, agile methodologies, testing, version control, and project management."},
            {"name": "Machine Learning", "description": "Supervised and unsupervised learning, neural networks, model evaluation, and practical applications with scikit-learn."},
            {"name": "Web Development", "description": "Full-stack web development covering HTML, CSS, JavaScript, React, Node.js, and RESTful APIs."},
            {"name": "Cybersecurity Fundamentals", "description": "Network security, cryptography, ethical hacking, and security best practices."},
            {"name": "Cloud Computing", "description": "Cloud architecture, AWS/Azure services, containerization with Docker, and orchestration with Kubernetes."},
            {"name": "Artificial Intelligence", "description": "Search algorithms, knowledge representation, planning, and introduction to neural networks."},
            {"name": "Mobile App Development", "description": "Cross-platform mobile development using Flutter and React Native."},
        ]

        created_courses = []
        for course_data in courses_data:
            existing_course = db.query(Course).filter(Course.name == course_data["name"]).first()
            if not existing_course:
                course = Course(
                    name=course_data["name"],
                    description=course_data["description"],
                    created_by_id=course_creator.id
                )
                db.add(course)
                db.flush()
                created_courses.append(course)
                result["courses_created"] += 1
                print(f"  + Created course: {course_data['name']}")
            else:
                created_courses.append(existing_course)
                print(f"  - Course already exists: {course_data['name']}")

        # ============================================================
        # ASSIGN COURSES TO USERS
        # ============================================================
        print("\nAssigning courses to users...")
        from app.models.user_course import UserCourse
        
        # Assign all students to a subset of courses
        if all_students and created_courses:
            for student in all_students:
                # Each student gets 2-4 random courses
                num_courses = min(random.randint(2, 4), len(created_courses))
                assigned_courses = random.sample(created_courses, num_courses)
                
                for course in assigned_courses:
                    existing = db.query(UserCourse).filter(
                        UserCourse.user_id == student.id,
                        UserCourse.course_id == course.id
                    ).first()
                    
                    if not existing:
                        user_course = UserCourse(user_id=student.id, course_id=course.id)
                        db.add(user_course)
                        print(f"  + Assigned {student.email} to {course.name}")
        
        # TAs are already assigned via signup (if they selected courses)
        # Instructors are already assigned via signup (if they selected courses)

        # ============================================================
        # CREATE ANNOUNCEMENTS (5 entries)
        # ============================================================
        print("\nCreating announcements...")
        announcements_data = [
            {
                "title": "Midterm Exam Schedule Released",
                "content": "The midterm exams will be conducted from Dec 15-20. Check your course pages for specific dates and times. Good luck!",
                "announcement_type": AnnouncementType.DEADLINE,
                "target_audience": AnnouncementTarget.STUDENTS,
                "is_pinned": True,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=20)
            },
            {
                "title": "New AI Course Registration Open",
                "content": "Registration for the new Artificial Intelligence course is now open. Limited seats available. Register before Dec 10.",
                "announcement_type": AnnouncementType.GENERAL,
                "target_audience": AnnouncementTarget.ALL,
                "is_pinned": False
            },
            {
                "title": "Campus Network Maintenance",
                "content": "The campus network will undergo maintenance on Dec 5, 2-4 AM. Services may be temporarily unavailable.",
                "announcement_type": AnnouncementType.URGENT,
                "target_audience": AnnouncementTarget.ALL,
                "is_pinned": True,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=3)
            },
            {
                "title": "TA Office Hours Updated",
                "content": "TA office hours have been updated for all courses. Check the course pages for new timings.",
                "announcement_type": AnnouncementType.UPDATE,
                "target_audience": AnnouncementTarget.STUDENTS,
                "is_pinned": False
            },
            {
                "title": "Research Paper Submission Deadline",
                "content": "Reminder: Research paper submissions for the conference are due by Dec 31. Submit via the portal.",
                "announcement_type": AnnouncementType.DEADLINE,
                "target_audience": AnnouncementTarget.INSTRUCTORS,
                "is_pinned": False,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=30)
            },
        ]

        admin_user = created_users.get("admin@test.com")
        if admin_user:
            for ann_data in announcements_data:
                existing = db.query(Announcement).filter(Announcement.title == ann_data["title"]).first()
                if not existing:
                    announcement = Announcement(
                        title=ann_data["title"],
                        content=ann_data["content"],
                        announcement_type=ann_data["announcement_type"],
                        target_audience=ann_data["target_audience"],
                        created_by_id=admin_user.id,
                        is_pinned=ann_data.get("is_pinned", False),
                        expires_at=ann_data.get("expires_at"),
                        view_count=random.randint(10, 200)
                    )
                    db.add(announcement)
                    result["announcements_created"] += 1
                    print(f"  + Created announcement: {ann_data['title']}")
                else:
                    print(f"  - Announcement already exists: {ann_data['title']}")

        # ============================================================
        # CREATE RESOURCES (5 entries)
        # ============================================================
        print("\nCreating resources...")
        resources_data = [
            {
                "title": "Python Programming Guide",
                "description": "Comprehensive Python tutorial from basics to advanced",
                "resource_type": ResourceType.PDF,
                "url": "https://example.com/python-guide.pdf",
                "visibility": ResourceVisibility.PUBLIC,
                "tags": ["Python", "Programming", "Tutorial"]
            },
            {
                "title": "Database Design Video Series",
                "description": "Complete video series on database design and normalization",
                "resource_type": ResourceType.VIDEO,
                "url": "https://youtube.com/playlist?id=db-design",
                "visibility": ResourceVisibility.PUBLIC,
                "tags": ["Database", "SQL", "Video"]
            },
            {
                "title": "Data Structures Cheat Sheet",
                "description": "Quick reference for common data structures and their operations",
                "resource_type": ResourceType.DOCUMENT,
                "url": "https://example.com/ds-cheatsheet.pdf",
                "visibility": ResourceVisibility.PUBLIC,
                "tags": ["Algorithms", "Data Structures", "Reference"]
            },
            {
                "title": "Web Development Bootcamp",
                "description": "Full-stack web development course materials",
                "resource_type": ResourceType.LINK,
                "url": "https://example.com/web-bootcamp",
                "visibility": ResourceVisibility.COURSE,
                "tags": ["Web Development", "Frontend", "Backend"]
            },
            {
                "title": "Machine Learning Research Papers",
                "description": "Collection of important ML research papers and implementations",
                "resource_type": ResourceType.LINK,
                "url": "https://example.com/ml-papers",
                "visibility": ResourceVisibility.PUBLIC,
                "tags": ["Machine Learning", "Research", "AI"]
            },
        ]

        instructor_user = all_instructors[0] if all_instructors else admin_user
        if instructor_user:
            for res_data in resources_data:
                existing = db.query(Resource).filter(Resource.title == res_data["title"]).first()
                if not existing:
                    resource = Resource(
                        title=res_data["title"],
                        description=res_data["description"],
                        resource_type=res_data["resource_type"],
                        url=res_data["url"],
                        visibility=res_data["visibility"],
                        created_by_id=instructor_user.id,
                        course_id=created_courses[0].id if created_courses and res_data["visibility"] == ResourceVisibility.COURSE else None,
                        tags=res_data["tags"],
                        download_count=random.randint(10, 500),
                        view_count=random.randint(50, 1000)
                    )
                    db.add(resource)
                    result["resources_created"] += 1
                    print(f"  + Created resource: {res_data['title']}")
                else:
                    print(f"  - Resource already exists: {res_data['title']}")

        # ============================================================
        # CREATE KNOWLEDGE SOURCES (10+ entries)
        # ============================================================
        print("\nCreating knowledge sources...")
        knowledge_data = [
            {
                "title": "Introduction to Software Engineering",
                "description": "Comprehensive guide to software engineering principles",
                "content": "Software Engineering covers SDLC, design patterns, best practices, and quality assurance. Key topics include requirements analysis, system design, implementation strategies, testing methodologies, and deployment practices.",
                "category": CategoryEnum.COURSES
            },
            {
                "title": "Data Structures and Algorithms",
                "description": "Essential data structures and algorithmic techniques",
                "content": "Core concepts: Arrays, Linked Lists, Trees, Graphs, Hash Tables. Algorithms: Sorting (Quick, Merge, Heap), Searching (Binary, DFS, BFS), Dynamic Programming, Greedy Algorithms.",
                "category": CategoryEnum.COURSES
            },
            {
                "title": "Database Management Systems",
                "description": "Fundamentals of database design and SQL",
                "content": "Topics covered: Relational model, SQL queries, normalization (1NF, 2NF, 3NF, BCNF), indexing, transactions, ACID properties, concurrency control, and database optimization techniques.",
                "category": CategoryEnum.COURSES
            },
            {
                "title": "Operating Systems Concepts",
                "description": "Core operating system principles and mechanisms",
                "content": "Process management, memory management, file systems, I/O systems, CPU scheduling algorithms (FCFS, SJF, Round Robin), deadlock detection and prevention, virtual memory, paging and segmentation.",
                "category": CategoryEnum.COURSES
            },
            {
                "title": "Computer Networks",
                "description": "Network protocols and architecture",
                "content": "OSI model, TCP/IP stack, HTTP/HTTPS, DNS, routing algorithms, socket programming, network security basics, firewalls, VPNs, and wireless networking.",
                "category": CategoryEnum.COURSES
            },
            {
                "title": "Assignment 1: REST API Development",
                "description": "Build a RESTful API using FastAPI",
                "content": "Create a Library Management System API with CRUD operations, authentication, and testing. Requirements: Books endpoint, Users endpoint, Borrow/return functionality, Input validation, JWT authentication. Due: Week 4.",
                "category": CategoryEnum.ASSIGNMENTS
            },
            {
                "title": "Assignment 2: Database Design Project",
                "description": "Design and implement a relational database",
                "content": "Design an e-commerce database with proper normalization. Include ER diagrams, schema design, sample queries, and indexing strategy. Implement using PostgreSQL. Due: Week 6.",
                "category": CategoryEnum.ASSIGNMENTS
            },
            {
                "title": "Assignment 3: Multi-threaded Application",
                "description": "Implement a concurrent program",
                "content": "Build a producer-consumer system with proper synchronization. Use mutexes, semaphores, or condition variables. Handle race conditions and deadlock prevention. Due: Week 8.",
                "category": CategoryEnum.ASSIGNMENTS
            },
            {
                "title": "Quiz: Object-Oriented Programming",
                "description": "Test on OOP concepts",
                "content": "Topics: Classes and Objects, Inheritance, Polymorphism, Encapsulation, Abstraction, SOLID principles. Format: 20 MCQs + 5 short answers. Time: 45 minutes.",
                "category": CategoryEnum.QUIZZES
            },
            {
                "title": "Quiz: SQL and Database Queries",
                "description": "Test on SQL fundamentals",
                "content": "Topics: SELECT queries, JOINs, GROUP BY, HAVING, subqueries, stored procedures, triggers. Format: 15 query writing + 10 MCQs. Time: 60 minutes.",
                "category": CategoryEnum.QUIZZES
            },
            {
                "title": "Quiz: Network Protocols",
                "description": "Test on networking concepts",
                "content": "Topics: TCP vs UDP, HTTP methods, DNS resolution, IP addressing, subnetting, routing protocols. Format: 25 MCQs. Time: 30 minutes.",
                "category": CategoryEnum.QUIZZES
            },
            {
                "title": "Python Programming Best Practices",
                "description": "Guidelines for clean Python code",
                "content": "Follow PEP 8 style guide. Use list comprehensions, context managers, generators, decorators. Write unit tests with pytest, aim for >80% coverage. Use type hints and docstrings.",
                "category": CategoryEnum.COURSES
            },
            {
                "title": "Machine Learning Fundamentals",
                "description": "Introduction to ML algorithms",
                "content": "Supervised learning (regression, classification), unsupervised learning (clustering, dimensionality reduction), model evaluation metrics, cross-validation, bias-variance tradeoff.",
                "category": CategoryEnum.COURSES
            },
            {
                "title": "FAQ: Course Registration",
                "description": "Frequently asked questions about registration",
                "content": "Q: How to register for courses? A: Use the student portal. Q: Can I change courses after registration? A: Yes, within the first 2 weeks. Q: What is the credit limit? A: 24 credits per semester.",
                "category": CategoryEnum.ADMISSION
            },
            {
                "title": "FAQ: Exam Guidelines",
                "description": "Information about examination procedures",
                "content": "Q: What to bring to exams? A: ID card, pens, calculator (if allowed). Q: Late arrival policy? A: Up to 15 minutes allowed. Q: Cheating policy? A: Zero tolerance, F grade and disciplinary action.",
                "category": CategoryEnum.QUERIES
            },
            {
                "title": "Placement Preparation Guide",
                "description": "Comprehensive guide for campus placements",
                "content": "Placement process overview: Pre-placement talks, aptitude tests, technical rounds, HR interviews. Companies visiting: TCS, Infosys, Wipro, Google, Microsoft, Amazon. Preparation timeline: Start 6 months before placement season.",
                "category": CategoryEnum.PLACEMENT
            },
        ]

        knowledge_sources = []
        for data in knowledge_data:
            existing = db.query(KnowledgeSource).filter(
                KnowledgeSource.title == data["title"]
            ).first()

            if not existing:
                source = KnowledgeSource(
                    title=data["title"],
                    description=data["description"],
                    content=data["content"],
                    category=data["category"],
                    is_active=True,
                    created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))
                )
                db.add(source)
                db.flush()

                # Create chunks for each source (2-3 chunks per source)
                content_parts = data["content"].split(". ")
                chunk_size = max(1, len(content_parts) // 2)
                for i in range(0, len(content_parts), chunk_size):
                    chunk_text = ". ".join(content_parts[i:i+chunk_size])
                    if chunk_text:
                        chunk = KnowledgeChunk(
                            source_id=source.id,
                            text=chunk_text,
                            index=i // chunk_size
                        )
                        db.add(chunk)
                        result["knowledge_chunks_created"] += 1

                knowledge_sources.append(source)
                result["knowledge_sources_created"] += 1
                print(f"  + Created: {data['title']}")
            else:
                knowledge_sources.append(existing)
                print(f"  - Already exists: {data['title']}")

        # ============================================================
        # CREATE QUIZZES (5 entries)
        # ============================================================
        print("\nCreating quizzes...")
        if created_courses and all_instructors:
            quizzes_data = [
                {
                    "title": "Python Basics Quiz",
                    "description": "Test your knowledge of Python fundamentals",
                    "course_id": created_courses[0].id,
                    "questions": [
                        {"question": "What is a list in Python?", "options": ["Array", "Mutable sequence", "String", "Dictionary"], "correct_answer": 1},
                        {"question": "Which keyword is used for function?", "options": ["func", "def", "function", "define"], "correct_answer": 1},
                    ],
                    "use_latex": False,
                    "is_published": True
                },
                {
                    "title": "Database Normalization Quiz",
                    "description": "Questions on database normalization forms",
                    "course_id": created_courses[2].id if len(created_courses) > 2 else created_courses[0].id,
                    "questions": [
                        {"question": "What is 3NF?", "options": ["Third Normal Form", "Three Node Format", "Triple Nested Function", "Third Null Field"], "correct_answer": 0},
                    ],
                    "use_latex": False,
                    "is_published": True
                },
                {
                    "title": "Algorithms Complexity Quiz",
                    "description": "Time and space complexity questions",
                    "course_id": created_courses[1].id if len(created_courses) > 1 else created_courses[0].id,
                    "questions": [
                        {"question": "Best case complexity of Quick Sort?", "options": ["O(n)", "O(n log n)", "O(n²)", "O(log n)"], "correct_answer": 1},
                    ],
                    "use_latex": True,
                    "is_published": False
                },
                {
                    "title": "Web Development Fundamentals",
                    "description": "HTML, CSS, JavaScript basics",
                    "course_id": created_courses[7].id if len(created_courses) > 7 else created_courses[0].id,
                    "questions": [
                        {"question": "Which tag is used for hyperlinks?", "options": ["<link>", "<a>", "<href>", "<url>"], "correct_answer": 1},
                    ],
                    "use_latex": False,
                    "is_published": True
                },
                {
                    "title": "Machine Learning Basics",
                    "description": "Introduction to ML concepts",
                    "course_id": created_courses[6].id if len(created_courses) > 6 else created_courses[0].id,
                    "questions": [
                        {"question": "What is supervised learning?", "options": ["Learning with labels", "Unsupervised learning", "Reinforcement learning", "None"], "correct_answer": 0},
                    ],
                    "use_latex": False,
                    "is_published": True
                },
            ]

            created_quizzes = []
            for quiz_data in quizzes_data:
                existing = db.query(Quiz).filter(Quiz.title == quiz_data["title"]).first()
                if not existing:
                    quiz = Quiz(
                        title=quiz_data["title"],
                        description=quiz_data["description"],
                        course_id=quiz_data["course_id"],
                        created_by_id=all_instructors[0].id,
                        questions=quiz_data["questions"],
                        use_latex=quiz_data["use_latex"],
                        is_published=quiz_data["is_published"]
                    )
                    db.add(quiz)
                    db.flush()
                    created_quizzes.append(quiz)
                    result["quizzes_created"] += 1
                    print(f"  + Created quiz: {quiz_data['title']}")
                else:
                    created_quizzes.append(existing)
                    print(f"  - Quiz already exists: {quiz_data['title']}")

            # Create quiz attempts
            print("\nCreating quiz attempts...")
            if created_quizzes and all_students:
                for i, quiz in enumerate(created_quizzes[:3]):
                    student = all_students[i % len(all_students)]
                    total_questions = len(quiz.questions)
                    score = random.randint(50, 100)
                    attempt = QuizAttempt(
                        quiz_id=quiz.id,
                        user_id=student.id,
                        submitted_answers=[0, 1] if i % 2 == 0 else [1, 0],
                        score=score,
                        total_marks=100
                    )
                    db.add(attempt)
                    result["quiz_attempts_created"] += 1
                    print(f"  + Created quiz attempt for quiz: {quiz.title}")

        # ============================================================
        # CREATE SLIDE DECKS (5 entries)
        # ============================================================
        print("\nCreating slide decks...")
        if created_courses and all_instructors:
            slide_decks_data = [
                {
                    "title": "Introduction to Python Programming",
                    "description": "Beginner-friendly Python slides",
                    "course_id": created_courses[0].id,
                    "slides": [
                        {"title": "What is Python?", "content": "# Python\n\nPython is a high-level, interpreted programming language."},
                        {"title": "Variables and Data Types", "content": "## Variables\n\n```python\nx = 5\nname = 'John'\n```"},
                    ]
                },
                {
                    "title": "Database Design Principles",
                    "description": "ER diagrams and normalization",
                    "course_id": created_courses[2].id if len(created_courses) > 2 else created_courses[0].id,
                    "slides": [
                        {"title": "Entity Relationship Model", "content": "# ER Model\n\nEntities, Attributes, Relationships"},
                    ]
                },
                {
                    "title": "Sorting Algorithms",
                    "description": "Comparison of sorting techniques",
                    "course_id": created_courses[1].id if len(created_courses) > 1 else created_courses[0].id,
                    "slides": [
                        {"title": "Bubble Sort", "content": "# Bubble Sort\n\nTime: O(n²)"},
                        {"title": "Quick Sort", "content": "# Quick Sort\n\nTime: O(n log n)"},
                    ]
                },
                {
                    "title": "Web Development Stack",
                    "description": "Frontend and backend technologies",
                    "course_id": created_courses[7].id if len(created_courses) > 7 else created_courses[0].id,
                    "slides": [
                        {"title": "Frontend", "content": "# Frontend\n\nHTML, CSS, JavaScript, React"},
                    ]
                },
                {
                    "title": "Neural Networks Introduction",
                    "description": "Basic concepts of neural networks",
                    "course_id": created_courses[6].id if len(created_courses) > 6 else created_courses[0].id,
                    "slides": [
                        {"title": "Perceptron", "content": "# Perceptron\n\nSimplest neural network unit"},
                    ]
                },
            ]

            for slide_data in slide_decks_data:
                existing = db.query(SlideDeck).filter(SlideDeck.title == slide_data["title"]).first()
                if not existing:
                    slide_deck = SlideDeck(
                        title=slide_data["title"],
                        description=slide_data["description"],
                        course_id=slide_data["course_id"],
                        created_by_id=all_instructors[0].id,
                        slides=slide_data["slides"]
                    )
                    db.add(slide_deck)
                    result["slide_decks_created"] += 1
                    print(f"  + Created slide deck: {slide_data['title']}")
                else:
                    print(f"  - Slide deck already exists: {slide_data['title']}")

        # ============================================================
        # CREATE TASKS (10+ entries)
        # ============================================================
        print("\nCreating background tasks...")

        task_types = [TaskTypeEnum.EMBEDDING, TaskTypeEnum.QUERY, TaskTypeEnum.DATA_PROCESSING]
        task_statuses = [TaskStatusEnum.PENDING, TaskStatusEnum.IN_PROGRESS, TaskStatusEnum.COMPLETED, TaskStatusEnum.FAILED]

        tasks_data = [
            {
                "task_type": TaskTypeEnum.EMBEDDING.value,
                "status": TaskStatusEnum.COMPLETED.value,
                "source_id": knowledge_sources[0].id if knowledge_sources else None,
                "metadata_": '{"chunks_processed": 5, "model": "text-embedding-3-small"}',
                "created_at": datetime.now(timezone.utc) - timedelta(days=2),
                "completed_at": datetime.now(timezone.utc) - timedelta(days=2, hours=-1)
            },
            {
                "task_type": TaskTypeEnum.EMBEDDING.value,
                "status": TaskStatusEnum.IN_PROGRESS.value,
                "source_id": knowledge_sources[1].id if len(knowledge_sources) > 1 else None,
                "metadata_": '{"chunks_processed": 3, "total_chunks": 5}',
                "created_at": datetime.now(timezone.utc) - timedelta(hours=2)
            },
            {
                "task_type": TaskTypeEnum.QUERY.value,
                "status": TaskStatusEnum.COMPLETED.value,
                "metadata_": '{"query": "What is polymorphism?", "response_time": 1.2}',
                "created_at": datetime.now(timezone.utc) - timedelta(hours=5),
                "completed_at": datetime.now(timezone.utc) - timedelta(hours=5, minutes=-30)
            },
            {
                "task_type": TaskTypeEnum.DATA_PROCESSING.value,
                "status": TaskStatusEnum.FAILED.value,
                "error_message": "Connection timeout while processing data",
                "metadata_": '{"retry_count": 3}',
                "created_at": datetime.now(timezone.utc) - timedelta(hours=1)
            },
            {
                "task_type": TaskTypeEnum.EMBEDDING.value,
                "status": TaskStatusEnum.COMPLETED.value,
                "source_id": knowledge_sources[2].id if len(knowledge_sources) > 2 else None,
                "metadata_": '{"chunks_processed": 8, "model": "text-embedding-3-small"}',
                "created_at": datetime.now(timezone.utc) - timedelta(days=5),
                "completed_at": datetime.now(timezone.utc) - timedelta(days=5, hours=-2)
            },
            {
                "task_type": TaskTypeEnum.QUERY.value,
                "status": TaskStatusEnum.COMPLETED.value,
                "metadata_": '{"query": "Explain ACID properties", "response_time": 0.8}',
                "created_at": datetime.now(timezone.utc) - timedelta(days=3),
                "completed_at": datetime.now(timezone.utc) - timedelta(days=3, hours=-1)
            },
            {
                "task_type": TaskTypeEnum.DATA_PROCESSING.value,
                "status": TaskStatusEnum.COMPLETED.value,
                "metadata_": '{"records_processed": 1500, "duration_seconds": 45}',
                "created_at": datetime.now(timezone.utc) - timedelta(days=4),
                "completed_at": datetime.now(timezone.utc) - timedelta(days=4, hours=-3)
            },
            {
                "task_type": TaskTypeEnum.EMBEDDING.value,
                "status": TaskStatusEnum.PENDING.value,
                "source_id": knowledge_sources[5].id if len(knowledge_sources) > 5 else None,
                "metadata_": '{"scheduled": true}',
                "created_at": datetime.now(timezone.utc) - timedelta(minutes=30)
            },
            {
                "task_type": TaskTypeEnum.QUERY.value,
                "status": TaskStatusEnum.FAILED.value,
                "error_message": "Model rate limit exceeded",
                "metadata_": '{"query": "Complex query", "retry_count": 2}',
                "created_at": datetime.now(timezone.utc) - timedelta(hours=8)
            },
            {
                "task_type": TaskTypeEnum.DATA_PROCESSING.value,
                "status": TaskStatusEnum.IN_PROGRESS.value,
                "metadata_": '{"records_total": 2000, "records_processed": 850}',
                "created_at": datetime.now(timezone.utc) - timedelta(minutes=45)
            },
            {
                "task_type": TaskTypeEnum.EMBEDDING.value,
                "status": TaskStatusEnum.COMPLETED.value,
                "source_id": knowledge_sources[8].id if len(knowledge_sources) > 8 else None,
                "metadata_": '{"chunks_processed": 3, "model": "text-embedding-3-small"}',
                "created_at": datetime.now(timezone.utc) - timedelta(days=1),
                "completed_at": datetime.now(timezone.utc) - timedelta(days=1, hours=-1)
            },
            {
                "task_type": TaskTypeEnum.QUERY.value,
                "status": TaskStatusEnum.COMPLETED.value,
                "metadata_": '{"query": "TCP vs UDP differences", "response_time": 1.5}',
                "created_at": datetime.now(timezone.utc) - timedelta(hours=12),
                "completed_at": datetime.now(timezone.utc) - timedelta(hours=12, minutes=-5)
            },
        ]

        for data in tasks_data:
            task = Task(**data)
            db.add(task)
            result["tasks_created"] += 1
            print(f"  + Created {data['task_type']} task ({data['status']})")

        # ============================================================
        # CREATE QUERIES WITH RESPONSES (10+ queries, 15+ responses)
        # ============================================================
        print("\nCreating queries with responses...")

        # Get first student, TA, and instructor for basic queries
        student = all_students[0] if all_students else None
        ta = all_tas[0] if all_tas else None
        instructor = all_instructors[0] if all_instructors else None

        if student and ta and instructor:
            queries_data = [
                {
                    "title": "Help with Dijkstra complexity",
                    "description": "I implemented Dijkstra's algorithm using adjacency matrix and binary heap, but I'm getting O(n^2) complexity. Is this expected for dense graphs? I thought using a heap would give me O((V+E)logV).",
                    "category": QueryCategory.TECHNICAL,
                    "priority": QueryPriority.MEDIUM,
                    "status": QueryStatus.RESOLVED,
                    "tags": ["algorithms", "graph-theory", "complexity"],
                    "student": student,
                    "days_ago": 0,
                    "responses": [
                        {
                            "user": ta,
                            "content": "Yes. With an adjacency matrix the edge scans dominate at O(n^2). Use adjacency lists; on dense graphs, a Fibonacci heap won't help asymptotically versus array/heap implementations. Check that you don't relax edges already finalized.",
                            "hours_ago": 1,
                            "is_solution": True
                        }
                    ]
                },
                {
                    "title": "Systems lab Docker error",
                    "description": "Docker build fails on ARM machine with error 'exec format error'. Running on M1 Mac. Works fine on Intel machines.",
                    "category": QueryCategory.TECHNICAL,
                    "priority": QueryPriority.HIGH,
                    "status": QueryStatus.RESOLVED,
                    "tags": ["docker", "systems", "ARM"],
                    "student": all_students[1] if len(all_students) > 1 else student,
                    "days_ago": 1,
                    "responses": [
                        {
                            "user": ta,
                            "content": "Use --platform linux/amd64 flag in your Dockerfile FROM statement. Or use docker buildx for multi-platform builds.",
                            "hours_ago": 24,
                            "is_solution": True
                        }
                    ]
                },
                {
                    "title": "Office hour booking confirmation",
                    "description": "Want to confirm the location for Friday office hours. Is it still Room 301 or has it moved?",
                    "category": QueryCategory.GENERAL,
                    "priority": QueryPriority.LOW,
                    "status": QueryStatus.OPEN,
                    "tags": ["office-hours", "logistics"],
                    "student": all_students[2] if len(all_students) > 2 else student,
                    "days_ago": 1,
                    "responses": []
                },
                {
                    "title": "How to implement binary search tree?",
                    "description": "Confused about BST insert operation. Should I use recursion or iteration? How do I handle duplicate values?",
                    "category": QueryCategory.TECHNICAL,
                    "priority": QueryPriority.MEDIUM,
                    "status": QueryStatus.IN_PROGRESS,
                    "tags": ["data-structures", "BST", "trees"],
                    "student": student,
                    "days_ago": 2,
                    "responses": [
                        {
                            "user": ta,
                            "content": "Both recursion and iteration work. Recursion is more elegant. For duplicates, you can either reject them or store count in node.",
                            "hours_ago": 36
                        }
                    ]
                },
                {
                    "title": "Assignment deadline extension",
                    "description": "Medical emergency in family. Need extension for Assignment 2. Can provide medical certificate.",
                    "category": QueryCategory.ASSIGNMENT,
                    "priority": QueryPriority.HIGH,
                    "status": QueryStatus.RESOLVED,
                    "tags": ["deadline", "extension"],
                    "student": all_students[3] if len(all_students) > 3 else student,
                    "days_ago": 3,
                    "responses": [
                        {
                            "user": instructor,
                            "content": "Please email me the medical certificate. Extension granted till next Monday.",
                            "hours_ago": 60,
                            "is_solution": True
                        }
                    ]
                },
                {
                    "title": "Quiz results when?",
                    "description": "When will OOP quiz results be published? It's been a week since we took the quiz.",
                    "category": QueryCategory.EXAM,
                    "priority": QueryPriority.LOW,
                    "status": QueryStatus.RESOLVED,
                    "tags": ["quiz", "results"],
                    "student": all_students[4] if len(all_students) > 4 else student,
                    "days_ago": 5,
                    "responses": [
                        {
                            "user": instructor,
                            "content": "Results will be published tomorrow. Sorry for the delay.",
                            "hours_ago": 120,
                            "is_solution": True
                        }
                    ]
                },
                {
                    "title": "PhD program requirements",
                    "description": "What are the prerequisites for PhD in AI? Do I need research experience?",
                    "category": QueryCategory.GENERAL,
                    "priority": QueryPriority.MEDIUM,
                    "status": QueryStatus.OPEN,
                    "tags": ["PhD", "admission", "AI"],
                    "student": student,
                    "days_ago": 7,
                    "responses": []
                },
                {
                    "title": "Interview prep resources",
                    "description": "Looking for resources to prepare for FAANG interviews. Any recommendations?",
                    "category": QueryCategory.GENERAL,
                    "priority": QueryPriority.MEDIUM,
                    "status": QueryStatus.RESOLVED,
                    "tags": ["interview", "FAANG", "placement"],
                    "student": all_students[1] if len(all_students) > 1 else student,
                    "days_ago": 10,
                    "responses": [
                        {
                            "user": instructor,
                            "content": "Check out LeetCode, Cracking the Coding Interview, and System Design Interview books. Practice daily.",
                            "hours_ago": 240,
                            "is_solution": True
                        }
                    ]
                },
                {
                    "title": "SQL JOIN types confusion",
                    "description": "What's the difference between INNER JOIN, LEFT JOIN, RIGHT JOIN, and FULL OUTER JOIN? When should I use each?",
                    "category": QueryCategory.TECHNICAL,
                    "priority": QueryPriority.MEDIUM,
                    "status": QueryStatus.RESOLVED,
                    "tags": ["SQL", "database", "joins"],
                    "student": all_students[2] if len(all_students) > 2 else student,
                    "days_ago": 4,
                    "responses": [
                        {
                            "user": ta,
                            "content": "INNER JOIN returns only matching rows. LEFT JOIN returns all rows from left table + matches from right. RIGHT JOIN is opposite. FULL OUTER returns all rows from both. Use INNER for exact matches, LEFT when you need all records from one table regardless of match.",
                            "hours_ago": 80,
                            "is_solution": True
                        },
                        {
                            "user": all_tas[1] if len(all_tas) > 1 else ta,
                            "content": "Here's a visual representation: Think of Venn diagrams. INNER is the intersection, LEFT includes all of left circle, etc.",
                            "hours_ago": 75
                        }
                    ]
                },
                {
                    "title": "Git merge vs rebase",
                    "description": "Our team is debating whether to use merge or rebase for feature branches. What's the recommended approach?",
                    "category": QueryCategory.TECHNICAL,
                    "priority": QueryPriority.LOW,
                    "status": QueryStatus.IN_PROGRESS,
                    "tags": ["git", "version-control", "workflow"],
                    "student": all_students[3] if len(all_students) > 3 else student,
                    "days_ago": 2,
                    "responses": [
                        {
                            "user": ta,
                            "content": "Both have their place. Rebase creates cleaner history but rewrites commits. Merge preserves history but can create complex graphs. Golden rule: never rebase public branches.",
                            "hours_ago": 40
                        }
                    ]
                },
                {
                    "title": "Deadlock in producer-consumer",
                    "description": "My producer-consumer implementation sometimes hangs. I'm using two mutexes. How do I debug this?",
                    "category": QueryCategory.TECHNICAL,
                    "priority": QueryPriority.HIGH,
                    "status": QueryStatus.OPEN,
                    "tags": ["concurrency", "deadlock", "threading"],
                    "student": all_students[4] if len(all_students) > 4 else student,
                    "days_ago": 0,
                    "responses": [
                        {
                            "user": ta,
                            "content": "Classic deadlock scenario with two mutexes. Always acquire locks in the same order across all threads. Better yet, use a single mutex with condition variables. Share your code and I can point out the exact issue.",
                            "hours_ago": 2
                        }
                    ]
                },
                {
                    "title": "REST API authentication",
                    "description": "Should I use JWT or session-based auth for my REST API? What are the security considerations?",
                    "category": QueryCategory.TECHNICAL,
                    "priority": QueryPriority.MEDIUM,
                    "status": QueryStatus.RESOLVED,
                    "tags": ["REST", "authentication", "security"],
                    "student": student,
                    "days_ago": 6,
                    "responses": [
                        {
                            "user": instructor,
                            "content": "For REST APIs, JWT is preferred as it's stateless. Store tokens securely (httpOnly cookies), use short expiration, implement refresh tokens. Always use HTTPS.",
                            "hours_ago": 130,
                            "is_solution": True
                        }
                    ]
                },
                {
                    "title": "Virtual memory page fault",
                    "description": "Getting too many page faults in my simulation. How can I optimize page replacement algorithm?",
                    "category": QueryCategory.TECHNICAL,
                    "priority": QueryPriority.MEDIUM,
                    "status": QueryStatus.IN_PROGRESS,
                    "tags": ["OS", "memory", "paging"],
                    "student": all_students[1] if len(all_students) > 1 else student,
                    "days_ago": 3,
                    "responses": [
                        {
                            "user": ta,
                            "content": "Which algorithm are you using? FIFO has Belady's anomaly. Try LRU or Clock algorithm. Also check your working set size - if it exceeds physical frames, thrashing is inevitable.",
                            "hours_ago": 60
                        }
                    ]
                },
                {
                    "title": "Final exam format",
                    "description": "Will the final exam be open book? Can we bring formula sheets?",
                    "category": QueryCategory.EXAM,
                    "priority": QueryPriority.HIGH,
                    "status": QueryStatus.RESOLVED,
                    "tags": ["exam", "final", "policy"],
                    "student": all_students[2] if len(all_students) > 2 else student,
                    "days_ago": 8,
                    "responses": [
                        {
                            "user": instructor,
                            "content": "The final will be closed book but you can bring one A4 sheet of handwritten notes (both sides). Calculators allowed. No electronic devices.",
                            "hours_ago": 180,
                            "is_solution": True
                        }
                    ]
                },
                {
                    "title": "Group project member not responding",
                    "description": "One team member hasn't contributed to our project and isn't responding to messages. What should we do?",
                    "category": QueryCategory.GENERAL,
                    "priority": QueryPriority.HIGH,
                    "status": QueryStatus.IN_PROGRESS,
                    "tags": ["project", "teamwork", "conflict"],
                    "student": all_students[3] if len(all_students) > 3 else student,
                    "days_ago": 1,
                    "responses": [
                        {
                            "user": instructor,
                            "content": "Document all communication attempts. I'll reach out to the student. In the meantime, redistribute work among active members. Peer evaluation will reflect individual contributions.",
                            "hours_ago": 20
                        }
                    ]
                },
            ]

            for data in queries_data:
                existing = db.query(Query).filter(Query.title == data["title"]).first()
                if not existing:
                    query = Query(
                        title=data["title"],
                        description=data["description"],
                        category=data["category"],
                        priority=data["priority"],
                        status=data["status"],
                        tags=data.get("tags", []),
                        student_id=data["student"].id,
                        created_at=datetime.now(timezone.utc) - timedelta(days=data.get("days_ago", 0))
                    )
                    db.add(query)
                    db.flush()

                    # Add responses
                    for resp_data in data.get("responses", []):
                        response = QueryResponse(
                            query_id=query.id,
                            user_id=resp_data["user"].id,
                            content=resp_data["content"],
                            is_solution=resp_data.get("is_solution", False),
                            created_at=datetime.now(timezone.utc) - timedelta(hours=resp_data.get("hours_ago", 0))
                        )
                        db.add(response)
                        result["query_responses_created"] += 1

                    result["queries_created"] += 1
                    print(f"  + Created: {data['title']} ({len(data.get('responses', []))} responses)")
                else:
                    print(f"  - Already exists: {data['title']}")

        # ============================================================
        # CREATE DOUBT UPLOADS & MESSAGES (5 entries)
        # ============================================================
        print("\nCreating doubt uploads and messages...")
        if created_courses and all_students and all_tas:
            doubt_uploads_data = [
                {
                    "course_code": "CS101",
                    "source": "Assignment 1 - Question 3",
                    "student": all_students[0],
                    "messages": [
                        {"role": "student", "text": "I'm stuck on implementing binary search. My code returns wrong indices."},
                        {"role": "ta", "text": "Check your mid calculation. Use (left + right) // 2. Also verify your boundary conditions."},
                        {"role": "student", "text": "Thanks! That fixed it. The issue was integer overflow in mid calculation."},
                    ]
                },
                {
                    "course_code": "CS201",
                    "source": "Lab 5 - Database Queries",
                    "student": all_students[1] if len(all_students) > 1 else all_students[0],
                    "messages": [
                        {"role": "student", "text": "My JOIN query is returning duplicate rows. How do I fix this?"},
                        {"role": "ta", "text": "Use DISTINCT keyword or check if you need INNER JOIN instead of CROSS JOIN. Share your query."},
                    ]
                },
                {
                    "course_code": "CS301",
                    "source": "Project - Threading Issue",
                    "student": all_students[2] if len(all_students) > 2 else all_students[0],
                    "messages": [
                        {"role": "student", "text": "Getting race condition in my producer-consumer code. Mutex isn't working."},
                        {"role": "ta", "text": "Make sure you're locking before accessing shared variables and unlocking after. Use condition variables for signaling."},
                        {"role": "student", "text": "I was unlocking too early. Fixed now!"},
                    ]
                },
                {
                    "course_code": "CS202",
                    "source": "Midterm Preparation",
                    "student": all_students[3] if len(all_students) > 3 else all_students[0],
                    "messages": [
                        {"role": "student", "text": "Can you explain the difference between TCP and UDP protocols?"},
                        {"role": "ta", "text": "TCP is connection-oriented, reliable, ordered. UDP is connectionless, faster, no guarantee. Use TCP for accuracy, UDP for speed."},
                    ]
                },
                {
                    "course_code": "CS401",
                    "source": "ML Assignment - Model Overfitting",
                    "student": all_students[4] if len(all_students) > 4 else all_students[0],
                    "messages": [
                        {"role": "student", "text": "My model has 99% training accuracy but only 60% test accuracy. Is it overfitting?"},
                        {"role": "ta", "text": "Yes, classic overfitting. Try: 1) Add dropout layers, 2) Reduce model complexity, 3) Get more training data, 4) Use regularization."},
                        {"role": "student", "text": "Added dropout and regularization. Test accuracy improved to 85%!"},
                    ]
                },
            ]

            for doubt_data in doubt_uploads_data:
                existing = db.query(DoubtUpload).filter(
                    DoubtUpload.course_code == doubt_data["course_code"],
                    DoubtUpload.source == doubt_data["source"]
                ).first()

                if not existing:
                    doubt_upload = DoubtUpload(
                        course_code=doubt_data["course_code"],
                        source=doubt_data["source"],
                        created_by_id=doubt_data["student"].id,
                        created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 10))
                    )
                    db.add(doubt_upload)
                    db.flush()
                    result["doubt_uploads_created"] += 1

                    # Add messages
                    for msg_data in doubt_data["messages"]:
                        message = DoubtMessage(
                            upload_id=doubt_upload.id,
                            author_role=msg_data["role"],
                            text=msg_data["text"]
                        )
                        db.add(message)
                        result["doubt_messages_created"] += 1

                    print(f"  + Created doubt: {doubt_data['source']} ({len(doubt_data['messages'])} messages)")
                else:
                    print(f"  - Doubt already exists: {doubt_data['source']}")

        # ============================================================
        # CREATE CALL SESSIONS (5 entries)
        # ============================================================
        print("\nCreating call sessions...")
        calls_data = [
            {
                "caller_number": "+1-555-0101",
                "twilio_sid": f"CA{uuid.uuid4().hex[:32]}",
                "language": "en",
                "location": "California, USA",
                "status": CallStatusEnum.COMPLETED,
                "duration": "5:23"
            },
            {
                "caller_number": "+1-555-0102",
                "twilio_sid": f"CA{uuid.uuid4().hex[:32]}",
                "language": "en",
                "location": "New York, USA",
                "status": CallStatusEnum.COMPLETED,
                "duration": "3:45"
            },
            {
                "caller_number": "+1-555-0103",
                "twilio_sid": f"CA{uuid.uuid4().hex[:32]}",
                "language": "en",
                "location": "Texas, USA",
                "status": CallStatusEnum.ACTIVE,
                "duration": None
            },
            {
                "caller_number": "+1-555-0104",
                "twilio_sid": f"CA{uuid.uuid4().hex[:32]}",
                "language": "en",
                "location": "Florida, USA",
                "status": CallStatusEnum.COMPLETED,
                "duration": "8:12"
            },
            {
                "caller_number": "+1-555-0105",
                "twilio_sid": f"CA{uuid.uuid4().hex[:32]}",
                "language": "en",
                "location": "Washington, USA",
                "status": CallStatusEnum.FAILED,
                "duration": "0:15"
            },
        ]

        for call_data in calls_data:
            existing = db.query(Call).filter(Call.twilio_sid == call_data["twilio_sid"]).first()
            if not existing:
                call = Call(
                    caller_number=call_data["caller_number"],
                    twilio_sid=call_data["twilio_sid"],
                    language=call_data["language"],
                    location=call_data["location"],
                    status=call_data["status"],
                    duration=call_data["duration"],
                    metadata_={"call_type": "student_query", "topic": "course_help"},
                    created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 7))
                )
                db.add(call)
                result["calls_created"] += 1
                print(f"  + Created call session: {call_data['caller_number']} ({call_data['status'].value})")
            else:
                print(f"  - Call already exists: {call_data['twilio_sid']}")

        # ============================================================
        # CREATE CHAT SESSIONS (10+ entries)
        # ============================================================
        print("\nCreating chat sessions...")

        # Sample chat session data
        chat_sessions_data = [
            {"user_email": "student@test.com", "ip": "192.168.1.100", "device": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0", "language": "en", "messages": 5, "last_msg": "How do I implement binary search?"},
            {"user_email": "alice.smith@test.com", "ip": "192.168.1.101", "device": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) Safari/605.1", "language": "en", "messages": 3, "last_msg": "Explain SQL joins please"},
            {"user_email": "bob.johnson@test.com", "ip": "192.168.1.102", "device": "Mozilla/5.0 (Linux; Android 13) Mobile Chrome/120.0", "language": "en", "messages": 8, "last_msg": "What is polymorphism?"},
            {"user_email": "carol.williams@test.com", "ip": "192.168.1.103", "device": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Safari/604.1", "language": "en", "messages": 2, "last_msg": "Help with network protocols"},
            {"user_email": "david.brown@test.com", "ip": "192.168.1.104", "device": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/121.0", "language": "en", "messages": 6, "last_msg": "Docker container issues"},
            {"user_email": "henry.taylor@test.com", "ip": "192.168.1.105", "device": "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0", "language": "en", "messages": 4, "last_msg": "Kubernetes deployment help"},
            {"user_email": "student@test.com", "ip": "192.168.1.100", "device": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0", "language": "en", "messages": 7, "last_msg": "Explain recursion with examples"},
            {"user_email": "alice.smith@test.com", "ip": "10.0.0.50", "device": "Mozilla/5.0 (iPad; CPU OS 17_0) Safari/604.1", "language": "en", "messages": 1, "last_msg": "What are design patterns?"},
            {"user_email": "ta@test.com", "ip": "192.168.1.200", "device": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/120.0", "language": "en", "messages": 10, "last_msg": "Best practices for code review"},
            {"user_email": "instructor@test.com", "ip": "192.168.1.201", "device": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) Chrome/120.0", "language": "en", "messages": 3, "last_msg": "Course material suggestions"},
            {"user_email": "bob.johnson@test.com", "ip": "172.16.0.10", "device": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0", "language": "en", "messages": 9, "last_msg": "REST API authentication"},
            {"user_email": "carol.williams@test.com", "ip": "192.168.1.103", "device": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Safari/604.1", "language": "en", "messages": 4, "last_msg": "Cybersecurity best practices"},
        ]

        for idx, session_data in enumerate(chat_sessions_data):
            user = created_users.get(session_data["user_email"])
            if user:
                # Create chat session
                chat_session = ChatSession(
                    ip_address=session_data["ip"],
                    device_info=session_data["device"],
                    language=session_data["language"],
                    metadata_={
                        "user_id": user.id,
                        "user_email": user.email,
                        "user_role": user.role.value if hasattr(user.role, 'value') else str(user.role),
                        "conversation_id": f"conv-{uuid.uuid4().hex[:12]}",
                        "message_count": session_data["messages"],
                        "last_message": session_data["last_msg"],
                        "endpoint": "enhanced" if idx % 2 == 0 else "basic"
                    },
                    created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 14), hours=random.randint(0, 23)),
                    updated_at=datetime.now(timezone.utc) - timedelta(hours=random.randint(0, 48))
                )
                db.add(chat_session)
                result["chat_sessions_created"] += 1
                print(f"  + Created chat session for: {session_data['user_email']} ({session_data['messages']} messages)")

        # ============================================================
        # COMMIT ALL CHANGES
        # ============================================================
        print("\nCommitting changes to database...")
        db.commit()
        print("All changes committed!\n")

        # ============================================================
        # SUMMARY
        # ============================================================
        print("=" * 60)
        print("DATABASE POPULATED SUCCESSFULLY!")
        print("=" * 60)
        print(f"  Users created:             {result['users_created']}")
        print(f"  Profiles created:          {result['profiles_created']}")
        print(f"  Courses created:           {result['courses_created']}")
        print(f"  Tags created:              {result['tags_created']}")
        print(f"  Announcements created:     {result['announcements_created']}")
        print(f"  Resources created:         {result['resources_created']}")
        print(f"  Chat sessions created:     {result['chat_sessions_created']}")
        print(f"  Knowledge sources created: {result['knowledge_sources_created']}")
        print(f"  Knowledge chunks created:  {result['knowledge_chunks_created']}")
        print(f"  Quizzes created:           {result['quizzes_created']}")
        print(f"  Quiz attempts created:     {result['quiz_attempts_created']}")
        print(f"  Slide decks created:       {result['slide_decks_created']}")
        print(f"  Tasks created:             {result['tasks_created']}")
        print(f"  Queries created:           {result['queries_created']}")
        print(f"  Query responses created:   {result['query_responses_created']}")
        print(f"  Doubt uploads created:     {result['doubt_uploads_created']}")
        print(f"  Doubt messages created:    {result['doubt_messages_created']}")
        print(f"  Call sessions created:     {result['calls_created']}")
        print()
        print("=" * 60)
        print("TEST CREDENTIALS:")
        print("=" * 60)
        print("Students:")
        print("  student@test.com         / student123")
        print("  alice.smith@test.com     / alice123")
        print("  bob.johnson@test.com     / bob123")
        print("  carol.williams@test.com  / carol123")
        print("  david.brown@test.com     / david123")
        print("TAs:")
        print("  ta@test.com              / ta123")
        print("  emma.davis@test.com      / emma123")
        print("Instructors:")
        print("  instructor@test.com      / instructor123")
        print("  frank.miller@test.com    / frank123")
        print("Admins:")
        print("  admin@test.com           / admin123")
        print("  grace.wilson@test.com    / grace123")
        print("=" * 60)

        return result

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("AURA DATABASE POPULATION SCRIPT")
    print("=" * 60)
    print()

    try:
        populate_database()
        print("\nSuccess! Database is ready to use.")
        print("\nNext steps:")
        print("  1. Start backend:  python main.py")
        print("  2. Start frontend: cd ../frontend && npm run dev")
        print("  3. Login with:     student@test.com / student123")
        print("  4. Visit queries:  http://localhost:5173/student/queries")
    except Exception as e:
        print(f"\nFailed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
