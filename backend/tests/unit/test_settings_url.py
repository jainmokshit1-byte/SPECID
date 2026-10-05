"""DEC-43: a hosted Postgres URL (Neon hands out `postgresql://...?sslmode=require`) works as is."""

import pytest

from app.main import allowed_hosts
from app.settings import Settings, psycopg_url

SECRET = "x" * 40


@pytest.mark.parametrize(
    ("given", "used"),
    [
        ("postgres://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql://u:p@h/db?sslmode=require", "postgresql+psycopg://u:p@h/db?sslmode=require"),
        ("postgresql+psycopg://u:p@db:5432/specid", "postgresql+psycopg://u:p@db:5432/specid"),
    ],
)
def test_hosted_urls_use_the_psycopg_driver(given: str, used: str) -> None:
    assert psycopg_url(given) == used
    assert Settings(database_url=given, jwt_secret=SECRET).database_url == used


def test_the_database_host_from_the_url_passes_the_egress_guard() -> None:
    s = Settings(
        database_url="postgresql://u:p@ep-calm-sea-123.ap-southeast-1.aws.neon.tech/neondb",
        jwt_secret=SECRET,
    )
    assert "ep-calm-sea-123.ap-southeast-1.aws.neon.tech" in allowed_hosts(s)
    assert "generativelanguage.googleapis.com" not in allowed_hosts(s)  # AI off by default
