from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DBConfig

if not DBConfig.URL:
    raise RuntimeError(
        "DB_URI is required. Set DB_URI in your .env file.\n"
        "Example: DB_URI=postgresql://user:password@localhost:5432/ceap_schools"
    )

engine = create_engine(
    DBConfig.URL,
    echo=DBConfig.ECHO,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    import app.models
    Base.metadata.create_all(bind=engine)
    _ensure_columns()


_STUDENT_COLUMNS = [
    ("parent_email", "VARCHAR(255) DEFAULT '' NOT NULL"),
    ("parent_relation", "VARCHAR(50) DEFAULT '' NOT NULL"),
    ("blood_group", "VARCHAR(10) DEFAULT '' NOT NULL"),
    ("behavior", "TEXT"),
    ("recommendations_json", "JSONB DEFAULT '[]'::jsonb NOT NULL"),
    ("achievements_json", "JSONB DEFAULT '[]'::jsonb NOT NULL"),
    ("medical_json", "JSONB DEFAULT '{}'::jsonb NOT NULL"),
    ("timeline_json", "JSONB DEFAULT '[]'::jsonb NOT NULL"),
    ("documents_json", "JSONB DEFAULT '[]'::jsonb NOT NULL"),
]


_DOCUMENT_COLUMNS = [
    ("student_id", "VARCHAR(64) DEFAULT '' NOT NULL"),
]


_ADMISSION_COLUMNS = [
    ("student_id", "VARCHAR(64) DEFAULT '' NOT NULL"),
]


def _ensure_columns():
    with engine.connect() as c:
        base = c.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_name='students'")).scalar()
        if base:
            cols = {r[0] for r in c.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='students'"))}
            for name, ddl in _STUDENT_COLUMNS:
                if name not in cols:
                    c.execute(text(f'ALTER TABLE students ADD COLUMN "{name}" {ddl}'))

        doc_base = c.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_name='documents'")).scalar()
        if doc_base:
            cols = {r[0] for r in c.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='documents'"))}
            for name, ddl in _DOCUMENT_COLUMNS:
                if name not in cols:
                    c.execute(text(f'ALTER TABLE documents ADD COLUMN "{name}" {ddl}'))

        app_base = c.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_name='admission_applications'")).scalar()
        if app_base:
            cols = {r[0] for r in c.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='admission_applications'"))}
            for name, ddl in _ADMISSION_COLUMNS:
                if name not in cols:
                    c.execute(text(f'ALTER TABLE admission_applications ADD COLUMN "{name}" {ddl}'))

        c.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
