"""Tests for ed-tool delete range functionality."""

import pytest
import os
import sys
import subprocess
import binascii

ED_TOOL = os.path.join(os.path.dirname(__file__), '..', 'ed-tool')

def run(*args, cwd=None, stdin_input=None):
    """Run ed-tool with the given arguments, return CompletedProcess."""
    return subprocess.run(
        [sys.executable, ED_TOOL] + list(args),
        cwd=cwd or os.path.dirname(__file__),
        capture_output=True,
        text=True,
        input=stdin_input,
    )

def _get_refs(file_path):
    """Return a list of lineno:hash strings for the file."""
    r = run('r', str(file_path))
    return [line.split('|', 1)[0] for line in r.stdout.strip().splitlines()]

def test_delete_single_line(tmp_path):
    f = tmp_path / "single.txt"
    f.write_text("1\n2\n3\n4\n", encoding="utf-8")
    refs = _get_refs(f)
    
    # Delete line 2
    result = run('d', str(f), refs[1])
    assert result.returncode == 0
    assert f.read_text() == "1\n3\n4\n"

def test_delete_range_from_to(tmp_path):
    f = tmp_path / "range.txt"
    f.write_text("1\n2\n3\n4\n5\n", encoding="utf-8")
    refs = _get_refs(f)
    
    # Delete [2, 4) -> lines 2 and 3
    result = run('d', str(f), f"{refs[1]},{refs[3]}")
    assert result.returncode == 0
    assert f.read_text() == "1\n4\n5\n"

def test_delete_from_line_to_eof(tmp_path):
    f = tmp_path / "to_eof.txt"
    f.write_text("1\n2\n3\n4\n5\n", encoding="utf-8")
    refs = _get_refs(f)
    
    # Delete 3:hash, -> lines 3, 4, 5
    result = run('d', str(f), f"{refs[2]},")
    assert result.returncode == 0
    assert f.read_text() == "1\n2\n"

def test_delete_before_line(tmp_path):
    f = tmp_path / "before.txt"
    f.write_text("1\n2\n3\n4\n5\n", encoding="utf-8")
    refs = _get_refs(f)
    
    # Delete ,3:hash -> lines 1, 2
    result = run('d', str(f), f",{refs[2]}")
    assert result.returncode == 0
    assert f.read_text() == "3\n4\n5\n"

def test_delete_range_error_hash_mismatch(tmp_path):
    f = tmp_path / "mismatch.txt"
    f.write_text("1\n2\n3\n", encoding="utf-8")
    refs = _get_refs(f)
    
    # Valid start, invalid end hash
    result = run('d', str(f), f"{refs[0]},3:0000")
    assert result.returncode != 0
    assert "hash mismatch" in result.stderr
    assert f.read_text() == "1\n2\n3\n"

def test_delete_range_error_out_of_range(tmp_path):
    f = tmp_path / "oor.txt"
    f.write_text("1\n2\n3\n", encoding="utf-8")
    refs = _get_refs(f)
    
    # Valid start, out of range end
    result = run('d', str(f), f"{refs[0]},10:abcd")
    assert result.returncode != 0
    assert "out of range" in result.stderr
    assert f.read_text() == "1\n2\n3\n"

def test_delete_range_start_after_end(tmp_path):
    f = tmp_path / "after.txt"
    f.write_text("1\n2\n3\n4\n", encoding="utf-8")
    refs = _get_refs(f)
    
    # Range [3, 2)
    result = run('d', str(f), f"{refs[2]},{refs[1]}")
    assert result.returncode != 0
    assert "invalid range" in result.stderr
    assert f.read_text() == "1\n2\n3\n4\n"

def test_delete_empty_range(tmp_path):
    f = tmp_path / "empty.txt"
    f.write_text("1\n2\n3\n4\n", encoding="utf-8")
    refs = _get_refs(f)
    
    # Range [2, 2)
    result = run('d', str(f), f"{refs[1]},{refs[1]}")
    assert result.returncode == 0
    assert f.read_text() == "1\n2\n3\n4\n"
