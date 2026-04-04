# AURA Backend Setup Guide

## Prerequisites

- Python 3.13+
- Git

## Quick Start

### 1. Clone and Navigate

```bash
cd backend
```

### 2. Create Virtual Environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set the **required** values:

```bash
# Generate a secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Copy the output into .env as SECRET_KEY
# Also set GOOGLE_API_KEY from https://makersuite.google.com/app/apikey
```

### 5. Run the Application

```bash
python main.py
```

The API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Database Setup

### SQLite (Default - Development)

No setup needed. The database file `app.db` is created automatically.

### PostgreSQL (Production)

1. Install PostgreSQL
2. Create a database:
   ```sql
   CREATE DATABASE aura_db;
   ```
3. Update `.env`:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/aura_db
   ```
4. Run migrations:
   ```bash
   alembic upgrade head
   ```

## Running Tests

```bash
cd backend
pytest test/ -v
```

## Troubleshooting

### "SECRET_KEY not set" error

Make sure you've created `.env` from `.env.example` and set the `SECRET_KEY`.

### "GOOGLE_API_KEY not set" error

Set `GOOGLE_API_KEY` in your `.env` file. Get a key from https://makersuite.google.com/app/apikey.

### Database connection errors

- For SQLite: Delete `app.db` and restart
- For PostgreSQL: Verify connection string and database exists
