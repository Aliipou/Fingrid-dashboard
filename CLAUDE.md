# CLAUDE.md — Engineering Guidelines for Ali's Projects

> **این فایل را در root هر پروژه قرار بده.**
> Claude Code این فایل را به‌عنوان context اصلی می‌خواند و تمام تصمیمات باید با این اصول همخوانی داشته باشند.

---

## 0. First Rule — Read Before Writing Anything

Before writing a single line of code or suggesting any architecture, answer these three questions:

1. **Does this feature exist in the PRD / task description?** If no → do not build it.
2. **Is there a simpler way to do this with less code?** If yes → do that instead.
3. **Will this decision create tech debt in 6 months?** If yes → flag it, don't hide it.

---

## 1. Complexity Budget

Every project has a **complexity budget**. Spending from it must be justified.

| Layer | Allowed complexity | Needs justification |
|---|---|---|
| Data models | Simple fields, clear relations | Custom metaclasses, multi-inheritance |
| API layer | REST with standard verbs | GraphQL, RPC, custom protocols |
| Business logic | Plain functions / services | Design patterns (Factory, Strategy, etc.) |
| Infrastructure | Docker + docker-compose | Kubernetes (only if scale demands it) |
| Async | Only when I/O bound and measured | Async by default "just in case" |

**Rule:** If you are about to introduce a design pattern, stop and ask: *"What concrete problem does this solve today?"*

---

## 2. Anti-Overengineering Rules

### 2.1 No Premature Abstraction
- Do NOT create base classes, mixins, or abstract interfaces until there are **at least 3 concrete use cases**.
- Do NOT create a generic utility if it is only used once.
- Prefer duplication over the wrong abstraction.

```python
# ❌ Overengineered — one use case
class BaseRepositoryFactory(ABC):
    @abstractmethod
    def create_repository(self, model: Type[T]) -> Repository[T]: ...

# ✅ Simple — solves the actual problem
def get_user(db: Session, user_id: int) -> User:
    return db.query(User).filter(User.id == user_id).first()
```

### 2.2 No Speculative Features
- Do NOT build features that are "probably needed later."
- Do NOT add config flags for behavior that has only one current use.
- Do NOT add plugin systems, event buses, or hook registries unless explicitly requested.

### 2.3 Dependency Discipline
- Every new dependency must justify itself: *"What does this replace, and is the tradeoff worth it?"*
- Prefer stdlib over third-party for small tasks.
- If a library is only used in one file, consider inlining the logic instead.

### 2.4 No Over-Layering
```
# ❌ 6-layer architecture for a CRUD API
Request → Router → Controller → Service → Repository → Model → DB

# ✅ For simple CRUD
Request → Router (with inline service logic) → Model → DB
# Add layers only when business logic grows
```

---

## 3. Anti-Overfitting Rules

Overfitting here means: **the solution is too specific to the current example/test/dataset and breaks on real-world variation.**

### 3.1 No Hardcoded Assumptions
```python
# ❌ Overfitted — assumes Finnish locale always
def format_date(dt):
    return dt.strftime("%d.%m.%Y")  # hardcoded

# ✅ Generalized
def format_date(dt, locale="fi_FI"):
    return babel.dates.format_date(dt, locale=locale)
```

### 3.2 No Magic Numbers / Strings
```python
# ❌ What is 7? What is "active"?
if user.status == "active" and days_since_login < 7:

# ✅ Named and configurable
MAX_INACTIVE_DAYS = int(os.getenv("MAX_INACTIVE_DAYS", 7))
UserStatus = Literal["active", "inactive", "banned"]
if user.status == UserStatus.active and days_since_login < MAX_INACTIVE_DAYS:
```

### 3.3 Tests Must Cover Edge Cases, Not Just Happy Path
- Minimum: happy path + one failure case + one boundary/edge case per function.
- Do NOT write tests that only pass because the test data matches the implementation exactly.
- If a test breaks when you rename a variable, it's testing the wrong thing.

### 3.4 ML / AI Specific (for ML projects)
- Always split: train / validation / **held-out test** — never touch test set during development.
- Report metrics on validation AND test. If they diverge >5%, investigate before shipping.
- Do NOT tune hyperparameters against the test set.
- Log all experiments: model version, dataset version, metrics, date.
- Prefer interpretable models (Logistic Regression, XGBoost) unless complexity is justified by metric gain.
- SHAP / feature importance is mandatory before declaring a model production-ready.

---

## 4. Stack Conventions (Ali's Default Stack)

### Backend
- **Language:** Python 3.11+
- **API:** FastAPI (preferred) or Django REST Framework
- **ORM:** SQLAlchemy (async) or Django ORM
- **Validation:** Pydantic v2
- **DB:** PostgreSQL (primary), Redis (cache/queue only)
- **Auth:** JWT via python-jose or Django SimpleJWT

### Infrastructure
- **Local dev:** Docker + docker-compose (mandatory — no "works on my machine")
- **CI/CD:** GitHub Actions
- **Cloud:** Azure (primary), AWS Free Tier (for demos/thesis work)
- **Container orchestration:** Docker Compose for dev/small prod; Kubernetes only if documented scale requirement exists

### Forbidden by default (needs explicit approval)
- Celery (use FastAPI BackgroundTasks or APScheduler first)
- Elasticsearch (use PostgreSQL full-text search first)
- Microservices (use modular monolith first)
- Redis Pub/Sub as primary event bus
- Any ORM other than SQLAlchemy / Django ORM

---

## 5. Code Style Rules

### 5.1 Function Size
- Max ~30 lines per function. If longer → extract and name the extracted piece clearly.
- One function = one responsibility. The name should describe it completely.

### 5.2 Error Handling
```python
# ❌ Silent failures
try:
    result = do_thing()
except Exception:
    pass

# ✅ Explicit, logged, typed
try:
    result = do_thing()
except ValueError as e:
    logger.warning("Invalid input for do_thing: %s", e)
    raise HTTPException(status_code=422, detail=str(e)) from e
```

### 5.3 Comments
- Comment **why**, not **what**. The code already shows what.
- If you need a comment to explain what a block does → refactor it into a named function.

### 5.4 Naming
- Variables: `snake_case`, descriptive (`user_id` not `uid`, `active_sessions` not `as`)
- No abbreviations except established ones: `db`, `id`, `url`, `api`, `http`
- Boolean variables: `is_`, `has_`, `can_` prefix always

---

## 6. Project Structure (Default)

```
project-name/
├── CLAUDE.md               ← this file
├── README.md               ← setup + usage (mandatory)
├── .env.example            ← all env vars documented, no defaults for secrets
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml          ← or requirements.txt if simple
├── src/
│   └── app/
│       ├── main.py
│       ├── config.py       ← settings via pydantic-settings
│       ├── models/         ← DB models
│       ├── schemas/        ← Pydantic schemas
│       ├── routers/        ← FastAPI routers
│       ├── services/       ← business logic (only if needed)
│       └── utils/          ← pure utility functions
└── tests/
    ├── conftest.py
    ├── unit/
    └── integration/
```

**Do NOT create this structure speculatively.** Add folders as they are needed.

---

## 7. Decision Log (Mandatory for Non-Obvious Choices)

When you make a non-trivial architectural decision, add a record to `DECISIONS.md`:

```markdown
## [DATE] — Why X instead of Y

**Context:** What problem were we solving?
**Decision:** What did we choose?
**Reason:** Why this and not the alternative?
**Trade-offs accepted:** What did we give up?
**Revisit when:** Under what conditions should we reconsider?
```

---

## 8. What Claude Code Should NOT Do Without Asking

1. **Change the database schema** without a migration file.
2. **Add a new dependency** to pyproject.toml / requirements.txt without noting it.
3. **Rename public API endpoints** — breaking change.
4. **Add environment variables** without updating `.env.example`.
5. **Delete files** — archive them or ask first.
6. **Refactor working code** unless the task explicitly asks for it.
7. **Generate test data** that is tied to production-like PII.

---

## 9. The Simplicity Check (Run Before Every PR / Commit)

Ask yourself:

- [ ] Could a junior dev understand this without asking me?
- [ ] Is every abstraction here actually used more than once?
- [ ] Does this work with inputs I didn't write myself?
- [ ] Are there any TODO/FIXME comments? → Fix them or file an issue, don't leave them.
- [ ] Does the README explain how to run this from scratch?

If any answer is "no" → fix before committing.

---

## 10. Communication Protocol with Claude Code

When giving Claude Code a task, use this format for best results:

```
TASK: [one sentence — what to build]
SCOPE: [what is IN scope — explicit list]
OUT OF SCOPE: [what NOT to touch]
CONSTRAINTS: [tech stack, existing patterns to follow]
DONE WHEN: [acceptance criteria — how do we know it's finished]
```

Example:
```
TASK: Add password reset endpoint to the existing auth router
SCOPE: POST /auth/reset-password, email sending via existing EmailService
OUT OF SCOPE: Frontend, new auth provider, changing existing login flow
CONSTRAINTS: FastAPI, existing User model, no new dependencies
DONE WHEN: Endpoint tested with valid + invalid token, README updated
```

---

*Last updated: May 2026 | Owner: Ali (github.com/Aliipou)*
