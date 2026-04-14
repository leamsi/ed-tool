"""Pytest configuration and shared fixtures for ed-tool tests."""

import pytest
import subprocess
import sys
import os

# Path to the ed-tool script (project root)
ED_TOOL = os.path.join(os.path.dirname(__file__), '..', 'ed-tool')


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "e2e: end-to-end tests that invoke the ed-tool subprocess"
    )


@pytest.fixture
def ed_tool():
    """Return the path to the ed-tool script."""
    return ED_TOOL


@pytest.fixture
def run_ed_tool():
    """Return a callable that runs ed-tool as a subprocess and returns CompletedProcess."""
    def _run(*args, cwd=None, check=False):
        cmd = [sys.executable, ED_TOOL] + list(args)
        return subprocess.run(
            cmd,
            cwd=cwd or os.path.dirname(__file__),
            capture_output=True,
            text=True,
            check=check,
        )
    return _run
