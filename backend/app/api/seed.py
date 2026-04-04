"""
API endpoint for seeding database with mock data.

Access at: POST /api/seed/populate
"""

from fastapi import APIRouter, Depends, HTTPException
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
from app.models.enums import (
    CategoryEnum,
    TaskTypeEnum,
    TaskStatusEnum
)
from app.schemas.user_schema import UserRole
from app.schemas.query_schema import QueryStatus, QueryCategory, QueryPriority
from app.core.security import hash_password


router = APIRouter(prefix="/seed", tags=["Seed Data"])


@router.post("/populate")
async def populate_database(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Populate database with mock data.

    Creates:
    - Test users (student, ta, instructor, admin)
    - Knowledge sources across all categories
    - Sample tasks
    - Sample queries

    **Warning**: This endpoint can be run multiple times but will skip existing data.
    """

    result = {
        "users_created": 0,
        "knowledge_sources_created": 0,
        "tasks_created": 0,
        "queries_created": 0,
        "message": ""
    }

    try:
        # Create users
        users_data = [
            {"email": "student@test.com", "full_name": "Test Student", "role": UserRole.STUDENT, "password": "student123"},
            {"email": "ta@test.com", "full_name": "Test TA", "role": UserRole.TA, "password": "ta123"},
            {"email": "instructor@test.com", "full_name": "Test Instructor", "role": UserRole.INSTRUCTOR, "password": "instructor123"},
            {"email": "admin@test.com", "full_name": "Test Admin", "role": UserRole.ADMIN, "password": "admin123"}
        ]

        created_users = {}
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
                created_users[user_data["role"].value] = user
                result["users_created"] += 1
            else:
                created_users[user_data["role"].value] = existing

        # Create knowledge sources
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
                "title": "Assignment 1: REST API Development",
                "description": "Build a RESTful API using FastAPI",
                "content": "Create a Library Management System API with CRUD operations, authentication, and testing. Requirements: Books endpoint, Users endpoint, Borrow/return functionality, Input validation, JWT authentication.",
                "category": CategoryEnum.ASSIGNMENTS
            },
            {
                "title": "Quiz: Object-Oriented Programming",
                "description": "Test on OOP concepts",
                "content": "Topics: Classes and Objects, Inheritance, Polymorphism, Encapsulation, Abstraction, SOLID principles. Format: 20 MCQs + 5 short answers. Time: 45 minutes.",
                "category": CategoryEnum.QUIZZES
            },
            {
                "title": "FAQ: Database Design",
                "description": "Common questions about database normalization",
                "content": "Q: What is normalization? A: Process of organizing data to reduce redundancy. Normal forms: 1NF, 2NF, 3NF, BCNF. Best practices: Define primary keys, use foreign keys, index frequently queried columns.",
                "category": CategoryEnum.QUERIES
            },
            {
                "title": "Graduate Program Admission Requirements",
                "description": "Requirements for MS in Computer Science",
                "content": "Requirements: Bachelor's degree in CS or related field, Min GPA 3.0, GRE scores (optional), Three letters of recommendation, Statement of Purpose. Deadline: January 15 for Fall admission.",
                "category": CategoryEnum.ADMISSION
            },
            {
                "title": "Technical Interview Preparation Guide",
                "description": "Comprehensive interview prep guide",
                "content": "Interview structure: Phone screen, coding rounds, system design, behavioral questions. Common topics: Arrays, Trees, Graphs, Dynamic Programming. Resources: LeetCode, HackerRank, Cracking the Coding Interview.",
                "category": CategoryEnum.PLACEMENT
            },
            {
                "title": "Python Programming Best Practices",
                "description": "Guidelines for clean Python code",
                "content": "Follow PEP 8 style guide. Use list comprehensions, context managers, generators, decorators. Write unit tests with pytest, aim for >80% coverage. Use type hints and docstrings.",
                "category": CategoryEnum.COURSES
            },
            {
                "title": "Agile Scrum Methodology",
                "description": "Scrum framework for project management",
                "content": "Roles: Product Owner, Scrum Master, Development Team. Events: Sprint Planning, Daily Standup, Sprint Review, Retrospective. Artifacts: Product Backlog, Sprint Backlog, Increment.",
                "category": CategoryEnum.COURSES
            },
            {
                "title": "Machine Learning Fundamentals",
                "description": "Introduction to ML concepts and algorithms",
                "content": "Supervised Learning: Linear Regression, Logistic Regression, Decision Trees, Random Forest. Unsupervised Learning: K-Means, PCA. Deep Learning: Neural Networks, CNN, RNN. Tools: scikit-learn, TensorFlow, PyTorch.",
                "category": CategoryEnum.COURSES
            }
        ]

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
                    chunk_count=1,  # Set chunk_count since we're creating 1 chunk
                    created_at=datetime.now(UTC)
                )
                db.add(source)
                db.flush()

                # Create a simple chunk
                chunk = KnowledgeChunk(
                    source_id=source.id,
                    text=data["content"],
                    index=0
                )
                db.add(chunk)

                result["knowledge_sources_created"] += 1

        # Create tasks
        tasks_data = [
            {"task_type": TaskTypeEnum.REPORT_GENERATION.value, "status": TaskStatusEnum.COMPLETED.value},
            {"task_type": TaskTypeEnum.DATA_PROCESSING.value, "status": TaskStatusEnum.IN_PROGRESS.value},
            {"task_type": TaskTypeEnum.DATA_PROCESSING.value, "status": TaskStatusEnum.COMPLETED.value},
            {"task_type": TaskTypeEnum.EMAIL.value, "status": TaskStatusEnum.PENDING.value},
            {"task_type": TaskTypeEnum.DATA_PROCESSING.value, "status": TaskStatusEnum.FAILED.value, "error": "Connection timeout"}
        ]

        for data in tasks_data:
            task = Task(
                task_type=data["task_type"],
                status=data["status"],
                error_message=data.get("error"),
                created_at=datetime.now(UTC) - timedelta(days=random.randint(0, 7))
            )
            db.add(task)
            result["tasks_created"] += 1

        # Create queries and responses
        student = created_users.get("student")
        ta = created_users.get("ta")
        instructor = created_users.get("instructor")

        if student:
            queries_data = [
                {
                    "title": "Help with Dijkstra complexity",
                    "description": "I implemented Dijkstra's algorithm using adjacency matrix and binary heap, but I'm getting O(n²) complexity. Is this expected for dense graphs? I thought using a heap would give me O((V+E)logV).",
                    "category": QueryCategory.TECHNICAL,
                    "priority": QueryPriority.MEDIUM,
                    "status": QueryStatus.OPEN,
                    "tags": ["algorithms", "graph-theory", "complexity"],
                    "days_ago": 0,
                    "responses": [
                        {
                            "user": "student",
                            "content": "I used adjacency matrix + binary heap and got O(n²). Is this expected for dense graphs?",
                            "minutes_ago": 45
                        },
                        {
                            "user": "ta",
                            "content": "Yes. With an adjacency matrix the edge scans dominate at O(n²). Use adjacency lists; on dense graphs, a Fibonacci heap won't help asymptotically versus array/heap implementations. Check that you don't relax edges already finalized. Expect O(n²) for matrix + array.",
                            "minutes_ago": 31
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
                    "days_ago": 1,
                    "responses": [
                        {
                            "user": "student",
                            "content": "Docker build fails on ARM machine. Getting 'exec format error'",
                            "minutes_ago": 1440
                        },
                        {
                            "user": "ta",
                            "content": "Use --platform linux/amd64 flag in your Dockerfile FROM statement. Or use docker buildx for multi-platform builds.",
                            "minutes_ago": 1400,
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
                    "days_ago": 2,
                    "responses": [
                        {
                            "user": "ta",
                            "content": "Both recursion and iteration work. Recursion is more elegant. For duplicates, you can either reject them or store count in node.",
                            "minutes_ago": 2800
                        }
                    ]
                },
                {
                    "title": "Assignment deadline extension",
                    "description": "Medical emergency in family. Need extension for Assignment 2. Can provide medical certificate.",
                    "category": QueryCategory.ASSIGNMENT,
                    "priority": QueryPriority.HIGH,
                    "status": QueryStatus.IN_PROGRESS,
                    "tags": ["deadline", "extension"],
                    "days_ago": 3,
                    "responses": [
                        {
                            "user": "instructor",
                            "content": "Please email me the medical certificate. Extension granted till next Monday.",
                            "minutes_ago": 4000
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
                    "days_ago": 5,
                    "responses": [
                        {
                            "user": "instructor",
                            "content": "Results will be published tomorrow. Sorry for the delay.",
                            "minutes_ago": 7000,
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
                    "days_ago": 10,
                    "responses": [
                        {
                            "user": "instructor",
                            "content": "Check out LeetCode, Cracking the Coding Interview, and System Design Interview books. Practice daily.",
                            "minutes_ago": 14000,
                            "is_solution": True
                        }
                    ]
                }
            ]

            for data in queries_data:
                existing = db.query(Query).filter(Query.title == data["title"]).first()
                if not existing:
                    # Create query
                    query = Query(
                        title=data["title"],
                        description=data["description"],
                        category=data["category"],
                        priority=data["priority"],
                        status=data["status"],
                        tags=data.get("tags", []),
                        student_id=student.id,
                        created_at=datetime.now(UTC) - timedelta(days=data.get("days_ago", 0))
                    )
                    db.add(query)
                    db.flush()  # Get query.id

                    # Create responses
                    for resp_data in data.get("responses", []):
                        responder = None
                        if resp_data["user"] == "student":
                            responder = student
                        elif resp_data["user"] == "ta":
                            responder = ta
                        elif resp_data["user"] == "instructor":
                            responder = instructor

                        if responder:
                            response = QueryResponse(
                                query_id=query.id,
                                user_id=responder.id,
                                content=resp_data["content"],
                                is_solution=resp_data.get("is_solution", False),
                                created_at=datetime.now(UTC) - timedelta(minutes=resp_data.get("minutes_ago", 0))
                            )
                            db.add(response)

                    result["queries_created"] += 1

        db.commit()

        result["message"] = "Database populated successfully!"
        result["test_credentials"] = {
            "student": "student@test.com / student123",
            "ta": "ta@test.com / ta123",
            "instructor": "instructor@test.com / instructor123",
            "admin": "admin@test.com / admin123"
        }

        return result

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error seeding database: {str(e)}")


@router.delete("/clear")
async def clear_seed_data(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Clear all seed data from database.

    **Warning**: This will delete all knowledge sources, tasks, and test queries!
    Test users will remain.
    """
    try:
        # Delete in correct order to respect foreign keys
        db.query(KnowledgeChunk).delete()
        db.query(KnowledgeSource).delete()
        db.query(Task).delete()

        # Delete test queries and responses
        test_emails = ["student@test.com", "ta@test.com", "instructor@test.com", "admin@test.com"]
        test_users = db.query(User).filter(User.email.in_(test_emails)).all()
        test_user_ids = [u.id for u in test_users]

        # Get all test queries
        test_queries = db.query(Query).filter(Query.student_id.in_(test_user_ids)).all()
        test_query_ids = [q.id for q in test_queries]

        # Delete query responses first (foreign key constraint)
        if test_query_ids:
            db.query(QueryResponse).filter(QueryResponse.query_id.in_(test_query_ids)).delete(synchronize_session=False)

        # Then delete queries
        db.query(Query).filter(Query.student_id.in_(test_user_ids)).delete(synchronize_session=False)

        db.commit()

        return {"message": "Seed data cleared successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error clearing data: {str(e)}")
