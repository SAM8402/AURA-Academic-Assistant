# AURA - Academic Assistant

![Vue.js](https://img.shields.io/badge/Vue.js-35495E?style=for-the-badge&logo=vue.js&logoColor=4FC08D)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)

**AURA (Academic Unified Response Assistant)** is an intelligent, multi-role platform designed to bridge the gap between student needs and instructional efficiency. By leveraging Retrieval-Augmented Generation (RAG) and specialized AI agents, AURA provides students with immediate, context-aware academic support while empowering Teaching Assistants (TAs) and Instructors with automated content generation, doubt summarization, and deep learning analytics.

##  Features

- **RAG-Powered Student Chat**: Instant, context-aware answers using advanced Retrieval-Augmented Generation (Google Gemini) for high accuracy.
- **Personal Student Resources**: A dedicated space for students to upload, pin, and manage study documents, images, and web links.
- **AI Onboarding Mentor**: A specialized conversational guide for TAs, trained on senior TA experiences and institutional best practices.
- **AI Learning Material Generation**: Automated generation of comprehensive slide decks and interactive quizzes based on course topics and user feedback.
- **Doubt Summarization**: Intelligent analysis and grouping of student queries over various periods (daily, weekly, monthly).
- **Automated Reporting**: Export summarized doubt reports to PDF and send them via SMTP (Gmail, Outlook, SES, etc.).
- **Role-Based Dashboards**: Specialized interfaces for Students, TAs, Instructors, and Admins.
- **Theming**: A modern UI with both light and dark modes.
- **High-Performance Backend**: Built with FastAPI, ensuring a fast and scalable API.

##  Tech Stack

| Area         | Technology                                                                                             |
|--------------|--------------------------------------------------------------------------------------------------------|
| **Frontend** | Vue.js, Pinia, Vue Router, Tailwind CSS |
| **Backend**  | Python 3.9+, FastAPI, SQLAlchemy, Pydantic, Alembic |
| **Database** | SQLite (default/dev), PostgreSQL (prod-ready)          |
| **AI/LLM**   | Google Gemini                                                                |
| **Emailing** | fastapi-mail (SMTP)                                                 |

##  File Structure

```text
.
├── backend/
│   ├── alembic/              # Database migrations
│   ├── app/
│   │   ├── api/              # API endpoints and routers
│   │   ├── core/             # Security and main configuration
│   │   ├── models/           # SQLAlchemy database models
│   │   ├── schemas/          # Pydantic validation schemas
│   │   └── services/         # Logic, RAG pipelines, and AI services
│   ├── config/               # DB connection and environment setup
│   ├── uploads/              # Local storage for student/knowledge files
│   ├── main.py               # FastAPI entry point
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── api/              # Axios service abstractions
│   │   ├── components/       # UI components (Admin, Student, TA, Instructor)
│   │   │   ├── Admin/        # Analytics and user management
│   │   │   ├── student/      # Chat and resource tools
│   │   │   ├── instructor/   # Content generation and reports
│   │   │   └── TA/           # Doubts and onboarding mentor
│   │   ├── router/           # Vue Router definitions per role
│   │   ├── store/            # Pinia state management
│   │   └── views/            # Main layout containers
│   ├── package.json          # Node.js dependencies
│   └── tailwind.config.js    # Styling configuration
├── EMAIL_CONFIGURATION.md    # Guide for SMTP setup
└── README.md                 # Project documentation
```

##  Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Python 3.9+
- Node.js v18+ (which includes npm) or Yarn
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/soft-engg-project-sep-2025-se-SEP-12.git
cd soft-engg-project-sep-2025-se-SEP-12
```

### 2. Backend Setup

The backend is a Python application powered by FastAPI.

```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment (recommended)
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create a .env file. You can copy the example:
# cp .env.example .env
```

Now, create and open a `.env` file in the `backend/` directory and fill in the required environment variables. See the **Configuration** section below for details.

#### Database Migration

The project uses Alembic to manage database schemas. Apply the migrations to create your database tables:

```bash
alembic upgrade head
```

#### Running the Backend

```bash
uvicorn main:app --reload
```

The backend API will be available at `http://localhost:8000`. You can access the interactive API documentation (Swagger UI) at `http://localhost:8000/docs`.

### 3. Frontend Setup

The frontend is a Vue.js single-page application.

```bash
# Navigate to the frontend directory from the root
cd ../frontend

# Install dependencies
npm install
# or
yarn install

# Run the development server
npm run dev
# or
yarn dev
```

The frontend application will be available at `http://localhost:5173` (or another port if 5173 is in use).

##  Configuration

Create a `.env` file in the `backend/` directory. This file stores sensitive credentials and environment-specific settings.

```ini
# backend/.env

# Application
APP_NAME=AURA
DEBUG=True
API_PREFIX=/api

# Database (SQLite by default)
# The path is relative to the `backend` directory.
DATABASE_URL=sqlite:///./app.db

# AI/LLM - Get your key from Google AI Studio
GOOGLE_API_KEY="your-gemini-api-key"

# Email Configuration (for report exporting)
# See EMAIL_CONFIGURATION.md for detailed setup guides for Gmail, etc.
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER="your-email@gmail.com"
SMTP_PASSWORD="your-16-digit-app-password"
EMAILS_FROM_EMAIL="your-email@gmail.com"
EMAILS_FROM_NAME="AURA - Academic Assistant"
SMTP_TLS=True
SMTP_SSL=False
```

> ** Important:** Never commit your `.env` file to version control. The `.gitignore` file is already configured to ignore it. For more details on setting up email, refer to `EMAIL_CONFIGURATION.md`.

##  Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request
