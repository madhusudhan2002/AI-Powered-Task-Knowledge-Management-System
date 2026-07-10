# AI-Powered Task & Knowledge Management System
Admins upload documents and assign tasks. Users semantically search the
knowledge base and complete assigned tasks.

## Tech Stack
| Layer       | Technology |
|-------------|------------|
| Backend     | Python, FastAPI, SQLAlchemy |
| Database    | MySQL |
| Auth        | JWT (python-jose) + bcrypt (passlib) |
| AI / Search | sentence-transformers (`all-MiniLM-L6-v2`) for embeddings, FAISS for vector storage/search — **no external LLM API used for the core search logic** |
| Frontend    | React (Vite), React Router, Axios |

## Architecture
```
backend/
  app/
    main.py            FastAPI app, router registration, CORS
    config.py           env-based settings
    database.py          SQLAlchemy engine/session
    models.py            ORM models (schema)
    schemas.py           Pydantic request/response models
    auth.py               JWT + password hashing
    deps.py                get_current_user / require_admin (RBAC)
    routers/
      auth.py       /auth/register, /auth/login
      users.py       /users (admin: list users for task assignment)
      tasks.py         /tasks (create/list/filter/update/delete)
      documents.py    /documents (upload -> parse -> chunk -> embed)
      search.py         /search (embedding-based semantic search)
      analytics.py    /analytics (counts + top queries)
    services/
      file_parser.py     extract text from txt/pdf, chunk it
      vector_store.py     FAISS index + sentence-transformers embeddings
      logging_service.py    writes activity_logs rows
  seed.py               creates roles + default admin user
frontend/
  src/
    api/axios.js        Axios instance with JWT interceptor
    context/AuthContext.jsx
    pages/               Login, Tasks, Documents, Search, Analytics
    components/          Navbar, PrivateRoute
```

## Database Schema (MySQL)
- **roles** (id PK, name) — `admin` / `user`
- **users** (id PK, name, email, hashed_password, role_id FK→roles)
- **documents** (id PK, filename, filepath, file_type, uploaded_by FK→users, is_indexed, chunk_count)
- **document_chunks** (id PK, document_id FK→documents, chunk_text, vector_index) — maps each FAISS vector position back to its source text, enabling retrieval after similarity search
- **tasks** (id PK, title, description, status, assigned_to FK→users, created_by FK→users)
- **activity_logs** (id PK, user_id FK→users, action, details, created_at) — logs login, task_update, document_upload, search
- **search_queries** (id PK, user_id FK→users, query_text, result_count) — powers the "most searched queries" analytic
All tables use SQLAlchemy `ForeignKey` relationships with cascading ORM `relationship()` mappings (proper PK/FK, normalized).

## How Semantic Search Works (Core AI Requirement)
1. **Upload**: admin uploads a `.txt`/`.pdf` → text is extracted (`pypdf` for PDFs).
2. **Chunk**: text is split into overlapping ~500-word chunks (`file_parser.chunk_text`) so retrieval returns focused passages, not whole documents.
3. **Embed**: each chunk is converted to a 384-dim vector using `sentence-transformers/all-MiniLM-L6-v2`, run **locally** (no external API call).
4. **Store**: vectors are added to a FAISS `IndexFlatIP` (cosine similarity via L2-normalized vectors), persisted to disk (`vector_store/index.faiss`). The FAISS position is saved in MySQL (`document_chunks.vector_index`) so results map back to source text and filename.
5. **Query**: a search query is embedded the same way, FAISS returns the top-k nearest chunks by similarity score, and results are joined back to their document via SQL.
This satisfies "Do NOT rely only on LLM APIs — core logic must be implemented": chunking, embedding generation, indexing, and similarity search are all done with local models/libraries, not a hosted LLM.

## Setup
### 1. MySQL
```sql
CREATE DATABASE task_knowledge_db;
```

### 2. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: set DB_PASSWORD, JWT_SECRET_KEY, etc.
```
> **If your MySQL password contains special characters** (e.g. `@`, `#`, `%`), that's fine — `config.py` URL-encodes the username/password before building the connection string, so characters like `@` in `Madhusudhan@143` won't break the connection.
```bash
python seed.py                # creates roles + default admin
uvicorn app.main:app --reload --port 8000
```
The first document upload / search will download the `all-MiniLM-L6-v2`
model (~80MB) from Hugging Face — this requires internet access once, then
it's cached locally.
API docs available at `http://localhost:8000/docs` (open this in a real
browser tab — Chrome/Edge — not VS Code's built-in Simple Browser, which
sometimes fails to connect to local dev servers).
Default admin login (from `.env`): `admin@example.com` / `Admin@123`.
Register regular users via `POST /auth/register` (role defaults to `user`),
or via the app if you add a signup page.

### 3. Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Visit `http://localhost:5173`.

## API Summary
| Method | Endpoint | Access |
|--------|----------|--------|
| POST | `/auth/register` | public |
| POST | `/auth/login` | public |
| GET  | `/users` | admin |
| POST | `/tasks` | admin |
| GET  | `/tasks?status=&assigned_to=` | admin/user (users see only their own) |
| PATCH | `/tasks/{id}` | admin (full edit) / owner (status only) |
| DELETE | `/tasks/{id}` | admin |
| POST | `/documents/upload` | admin |
| GET  | `/documents` | admin/user |
| GET  | `/search?q=&top_k=` | admin/user |
| GET  | `/analytics` | admin/user |

## RBAC
- JWT issued at login carries `sub` (user id) and `role`.
- `get_current_user` dependency resolves the user from the token on every
  protected route.
- `require_admin` dependency additionally blocks non-admins from
  admin-only routes (task creation, document upload, user listing).
- Regular users can only view/update tasks assigned to them; `/tasks`
  automatically scopes results to the logged-in user when they aren't an
  admin.

## Activity Logging
Every login, task status update, document upload, and search query writes
a row to `activity_logs` (and searches additionally to `search_queries`
for the analytics endpoint).

## Troubleshooting
Issues that came up during Windows/VS Code setup, in case you hit the same:
| Symptom | Cause | Fix |
|---|---|---|
| `Access denied for user 'root'@'localhost'` | `.env` still has the placeholder `DB_PASSWORD=your_mysql_password` | Edit `.env`, set the real MySQL root password, confirm with `Get-Content .env` |
| `Can't connect to MySQL server on '<numbers>@localhost'` | Password contains `@` (e.g. `Madhusudhan@143`), which broke the raw connection string | Already fixed in `config.py` — it URL-encodes credentials via `urllib.parse.quote_plus` before building `SQLALCHEMY_DATABASE_URL` |
| `ValueError: password cannot be longer than 72 bytes` during `seed.py` | `passlib==1.7.4` is incompatible with newer `bcrypt` releases (4.1+) | Pin `bcrypt==4.0.1` (already in `requirements.txt`) |
| `ImportError: email-validator is not installed` on `uvicorn` startup | Pydantic's `EmailStr` needs `email-validator`, which wasn't listed as a dependency | Already added to `requirements.txt` |
| `ERROR: No matching distribution found for faiss-cpu==1.8.0.post1` | That exact patch version isn't published for newer Python/Windows wheels | `requirements.txt` now pins `faiss-cpu>=1.9.0` instead |
| Browser says `ERR_CONNECTION_REFUSED` when clicking a `localhost` link inside VS Code | VS Code's built-in Simple Browser preview is unreliable with local dev servers | Copy the URL from the terminal and paste it into a real browser (Chrome/Edge) instead |
| PowerShell says `mysql` is not recognized | MySQL client not on PATH, or PATH not yet reloaded in the current terminal | Either fully restart VS Code after editing PATH, or bypass it: `& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p` |
- Currently uses a single global FAISS index shared across all documents;
  for large-scale multi-tenant use you'd partition or use a per-namespace
  Chroma collection instead.
- Add a `/auth/register` screen in the frontend if self-signup is desired
  (backend endpoint already supports it).
- Add pagination to `/tasks` and `/documents` for large datasets.