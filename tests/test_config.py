from config import normalize_database_url


def test_render_postgresql_url_uses_installed_psycopg_driver():
    database_url = normalize_database_url(
        "postgresql://student:secret@database.internal:5432/studentsuccess",
    )

    assert database_url == (
        "postgresql+psycopg://student:secret@database.internal:5432/"
        "studentsuccess"
    )


def test_legacy_render_postgres_url_uses_installed_psycopg_driver():
    database_url = normalize_database_url(
        "postgres://student:secret@database.internal:5432/studentsuccess",
    )

    assert database_url.startswith("postgresql+psycopg://")
