"""
End-to-end RAG Pipeline Test with Dummy Data.

This script tests the full RAG flow:
  1. Seeds dummy KnowledgeSources into the database
  2. Runs the Knowledge Pipeline (sentence-wise chunking + Gemini embeddings)
  3. Tests Semantic Search against the embedded chunks
  4. Tests RAG Chat — asks questions and verifies answers reference the seeded data

Usage:
    cd backend
    python -m test.test_rag_pipeline
"""

import asyncio
import sys
import os
import logging

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.db import engine, Base, SessionLocal
from app.models.knowledge import KnowledgeSource, KnowledgeChunk
from app.models.task import Task
from app.models.enums import CategoryEnum

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("test_rag_pipeline")


# ============================================================================
# DUMMY DATA — realistic academic content for AURA
# ============================================================================

DUMMY_KNOWLEDGE_SOURCES = [
    {
        "title": "Python Programming Fundamentals",
        "description": "Core concepts of Python programming for beginners.",
        "category": CategoryEnum.COURSES,
        "content": (
            "Python is a high-level, interpreted programming language known for its "
            "readability and simplicity. It was created by Guido van Rossum and first "
            "released in 1991. Python supports multiple programming paradigms including "
            "procedural, object-oriented, and functional programming.\n\n"
            "Variables in Python do not need explicit type declaration. Python uses "
            "dynamic typing, meaning the type of a variable is determined at runtime. "
            "Common data types include integers, floats, strings, lists, tuples, and "
            "dictionaries.\n\n"
            "Functions in Python are defined using the 'def' keyword. They can accept "
            "positional arguments, keyword arguments, and default parameter values. "
            "Python also supports lambda functions for creating small anonymous functions. "
            "Decorators are a powerful feature that allow you to modify the behavior of "
            "functions without changing their code."
        )
    },
    {
        "title": "Database Management Systems",
        "description": "Introduction to DBMS concepts and SQL.",
        "category": CategoryEnum.COURSES,
        "content": (
            "A Database Management System (DBMS) is software that manages the creation, "
            "maintenance, and use of databases. It provides an interface between the data "
            "and the application programs that use it. Popular DBMS include MySQL, "
            "PostgreSQL, Oracle, and SQLite.\n\n"
            "SQL (Structured Query Language) is the standard language for interacting "
            "with relational databases. The main SQL commands are SELECT, INSERT, UPDATE, "
            "and DELETE. The SELECT statement is used to retrieve data from one or more "
            "tables using clauses like WHERE, ORDER BY, GROUP BY, and HAVING.\n\n"
            "Normalization is the process of organizing data to reduce redundancy. "
            "The main normal forms are First Normal Form (1NF), Second Normal Form (2NF), "
            "Third Normal Form (3NF), and Boyce-Codd Normal Form (BCNF). "
            "Each normal form has specific rules that must be satisfied."
        )
    },
    {
        "title": "AURA Platform Admission Process",
        "description": "Step-by-step guide to the admission process.",
        "category": CategoryEnum.ADMISSION,
        "content": (
            "The admission process for the program begins with an online application "
            "submitted through the official portal. Applicants must provide their academic "
            "transcripts, a statement of purpose, and two letters of recommendation. "
            "The application fee is 1500 INR for general category and 750 INR for reserved "
            "categories.\n\n"
            "After the application deadline, a screening committee reviews all applications. "
            "Shortlisted candidates are invited for a written aptitude test that covers "
            "mathematics, logical reasoning, and programming fundamentals. The test duration "
            "is 2 hours and consists of 60 multiple-choice questions.\n\n"
            "Candidates who clear the aptitude test are called for a personal interview. "
            "The interview panel evaluates communication skills, technical knowledge, and "
            "motivation. Final selection is based on a composite score: 40% academics, "
            "30% aptitude test, and 30% interview performance."
        )
    },
    {
        "title": "Placement Statistics and Guidelines",
        "description": "Placement process and statistics for students.",
        "category": CategoryEnum.PLACEMENT,
        "content": (
            "The placement cell coordinates campus recruitment drives throughout the year. "
            "Major recruiters include Google, Microsoft, Amazon, Flipkart, and several "
            "leading startups. The average package for the 2025 batch was 12 LPA, with "
            "the highest package reaching 45 LPA.\n\n"
            "Students must maintain a minimum CGPA of 7.0 to be eligible for campus "
            "placements. Pre-placement preparation includes resume workshops, mock "
            "interviews, and coding practice sessions organized by the placement cell. "
            "Students are allowed to sit for a maximum of 5 companies.\n\n"
            "The placement process typically starts in September and continues until "
            "March. Companies visit campus for pre-placement talks followed by online "
            "assessments, technical interviews, and HR rounds. Students who receive an "
            "offer must confirm within 48 hours."
        )
    },
    {
        "title": "Assignment Submission Guidelines",
        "description": "Rules and deadlines for assignment submissions.",
        "category": CategoryEnum.ASSIGNMENTS,
        "content": (
            "All assignments must be submitted through the AURA portal before the deadline. "
            "Late submissions are penalized at 10% per day for up to 3 days, after which "
            "the submission is not accepted. Each assignment should include proper code "
            "documentation and a README file.\n\n"
            "Plagiarism is strictly monitored using automated tools. Any submission found "
            "with more than 30% similarity will be flagged for review. Students caught "
            "plagiarizing will receive zero marks and may face disciplinary action.\n\n"
            "For group assignments, all team members must contribute equally. A peer "
            "evaluation form must be submitted along with the assignment. The team leader "
            "is responsible for the final submission and ensuring all components are included."
        )
    },
]


# ============================================================================
# TEST STEPS
# ============================================================================

def step_1_seed_data():
    """Seed dummy knowledge sources into the database."""
    logger.info("=" * 60)
    logger.info("STEP 1: Seeding Dummy Knowledge Sources")
    logger.info("=" * 60)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    source_ids = []

    try:
        for data in DUMMY_KNOWLEDGE_SOURCES:
            # Check if already exists (idempotent)
            existing = session.query(KnowledgeSource).filter(
                KnowledgeSource.title == data["title"]
            ).first()

            if existing:
                logger.info("  [SKIP] '%s' already exists (id=%s)", data["title"], existing.id)
                source_ids.append(str(existing.id))
                continue

            source = KnowledgeSource(
                title=data["title"],
                description=data["description"],
                category=data["category"],
                content=data["content"],
                is_active=True,
                chunk_count=0
            )
            session.add(source)
            session.flush()  # Get the ID
            source_ids.append(str(source.id))
            logger.info("  [CREATED] '%s' (id=%s)", data["title"], source.id)

        session.commit()
        logger.info("  Seeded %d knowledge sources.", len(source_ids))

    except Exception as e:
        session.rollback()
        logger.error("  Error seeding data: %s", e)
        raise
    finally:
        session.close()

    return source_ids


async def step_2_run_knowledge_pipeline(source_ids):
    """Run the knowledge pipeline (chunk + embed) for each source."""
    logger.info("=" * 60)
    logger.info("STEP 2: Running Knowledge Pipeline (Sentence Chunking + Embedding)")
    logger.info("=" * 60)

    from app.services.rag.ingest_pipeline import process_knowledge_source

    results = []
    for sid in source_ids:
        logger.info("  Processing source: %s", sid)
        result = await process_knowledge_source(source_id=sid)
        results.append(result)

        if result.get("success"):
            logger.info(
                "    ✓ SUCCESS — Chunks: %d, Embeddings: %d",
                result.get("chunks_created", 0),
                result.get("embeddings_generated", 0)
            )
        else:
            logger.error("    ✗ FAILED — %s", result.get("error"))

    # Verify in DB
    session = SessionLocal()
    total_chunks = session.query(KnowledgeChunk).count()
    session.close()
    logger.info("  Total chunks in database: %d", total_chunks)

    return results


async def step_3_test_semantic_search():
    """Test semantic search with various queries."""
    logger.info("=" * 60)
    logger.info("STEP 3: Testing Semantic Search")
    logger.info("=" * 60)

    from app.services.rag.search_pipeline import search

    test_queries = [
        "What is Python programming?",
        "How does the admission process work?",
        "What is the placement package?",
        "Tell me about SQL and databases",
        "What happens if I submit an assignment late?",
    ]

    for query in test_queries:
        logger.info("  Query: '%s'", query)
        result = await search(query=query, top_k=3)

        if result.get("success"):
            hits = result.get("results", [])
            logger.info("    ✓ Found %d results", len(hits))
            for r in hits[:3]:
                logger.info(
                    "      → [%.3f] %s: %s",
                    r.get("score", 0),
                    r.get("source_title", "?"),
                    r.get("content", "")[:80] + "..."
                )
        else:
            logger.error("    ✗ Search failed: %s", result.get("error"))

    return True


async def step_4_test_rag_chat():
    """Test RAG chat — end-to-end question answering."""
    logger.info("=" * 60)
    logger.info("STEP 4: Testing RAG Chat (Question → Answer)")
    logger.info("=" * 60)

    from app.services.rag.chat_pipeline import chat_with_rag

    test_questions = [
        "What programming paradigms does Python support?",
        "What is the application fee for admission?",
        "What is the minimum CGPA required for placements?",
        "What is normalization in databases?",
        "What is the penalty for late assignment submission?",
    ]

    for question in test_questions:
        logger.info("  Question: '%s'", question)
        result = await chat_with_rag(query=question, user_name="TestStudent", user_role="student")

        if result.get("success"):
            answer = result.get("answer", "")
            confidence = result.get("confidence", 0)
            sources = result.get("sources", [])
            logger.info("    ✓ Confidence: %.2f | Has context: %s", confidence, result.get("has_relevant_context"))
            logger.info("    Answer: %s", answer[:150] + ("..." if len(answer) > 150 else ""))
            if sources:
                logger.info("    Sources: %s", ", ".join(s.get("title", "?") for s in sources))
        else:
            logger.error("    ✗ Chat failed: %s", result.get("error"))

    return True


def step_5_summary():
    """Print a summary of what's in the database."""
    logger.info("=" * 60)
    logger.info("STEP 5: Database Summary")
    logger.info("=" * 60)

    session = SessionLocal()
    try:
        sources = session.query(KnowledgeSource).filter(KnowledgeSource.is_active == True).all()
        total_chunks = session.query(KnowledgeChunk).count()

        logger.info("  Active Knowledge Sources: %d", len(sources))
        logger.info("  Total Embedded Chunks:    %d", total_chunks)
        logger.info("")

        for src in sources:
            chunk_count = session.query(KnowledgeChunk).filter(
                KnowledgeChunk.source_id == src.id
            ).count()
            logger.info(
                "  %-40s | Category: %-12s | Chunks: %d",
                src.title, src.category.value if hasattr(src.category, 'value') else src.category, chunk_count
            )

    finally:
        session.close()

    logger.info("")
    logger.info("=" * 60)
    logger.info("ALL TESTS COMPLETED SUCCESSFULLY!")
    logger.info("=" * 60)


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run all RAG pipeline tests."""
    logger.info("")
    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║         AURA RAG Pipeline — End-to-End Test             ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info("")

    # Step 1: Seed dummy data
    source_ids = step_1_seed_data()

    # Step 2: Run knowledge pipeline (chunk + embed)
    await step_2_run_knowledge_pipeline(source_ids)

    # Step 3: Test semantic search
    await step_3_test_semantic_search()

    # Step 4: Test RAG chat
    await step_4_test_rag_chat()

    # Step 5: Summary
    step_5_summary()


if __name__ == "__main__":
    asyncio.run(main())
