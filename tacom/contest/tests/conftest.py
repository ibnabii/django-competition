import re
import warnings

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext


@pytest.fixture(autouse=True)
def detect_duplicate_queries(request):
    """
    Detects if test executes same query more than once
    """

    # Ignore tests not using client
    if "client" not in request.fixturenames:
        yield
        return

    with CaptureQueriesContext(connection) as ctx:
        yield

    queries = [q["sql"] for q in ctx.captured_queries]
    duplicates = {q for q in queries if queries.count(q) > 1}

    if duplicates:
        pytest.fail(f"Duplicated DB queries found in {request.node.name}: {duplicates}")


# Extract common table references
TABLE_REGEX = re.compile(
    r'\bFROM\s+"?(\w+)"?'
    r'|\bJOIN\s+"?(\w+)"?'
    r'|\bUPDATE\s+"?(\w+)"?'
    r'|\bINTO\s+"?(\w+)"?',
    re.IGNORECASE,
)


def warn_on_repeated_table_queries(func):
    """Decorator for Django TestCase methods to warn on repeated table hits."""

    def wrapper(self, *args, **kwargs):
        with CaptureQueriesContext(connection) as ctx:
            result = func(self, *args, **kwargs)

        table_hits = {}
        for q in ctx.captured_queries:
            sql = re.sub(r"\bAS\s+\w+_\d+\b", "", q["sql"], flags=re.I)
            matches = TABLE_REGEX.findall(sql)
            for groups in matches:
                table = next(g for g in groups if g)
                table_hits[table] = table_hits.get(table, 0) + 1

        repeated = {t: c for t, c in table_hits.items() if c > 1}
        if repeated:
            warnings.warn(
                f"Same table queried multiple times in test '{func.__name__}': {repeated}",
                RuntimeWarning,
            )
        return result

    return wrapper
