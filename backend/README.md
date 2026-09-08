# AI Job Hunter Platform - Backend API

Production FastAPI Backend & AI Orchestrator for AI Job Hunter Platform.

## Features
- **FastAPI Core**: RESTful API with automated OpenAPI docs (`/docs`).
- **PostgreSQL & pgvector**: Vector similarity matching for candidates and jobs.
- **Resume Intelligence Engine**: Automatic JD-tailored resume generation with LaTeX & PDF compilation.
- **Multi-User Isolation**: Secure JWT authentication, Argon2id hashing, and sandbox isolation.

## Running Locally
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be available at `http://localhost:8000/docs`.
