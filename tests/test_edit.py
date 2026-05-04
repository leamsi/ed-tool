"""End-to-end tests for ed-tool edit subcommands (append, insert, delete, change)."""

import binascii
import pytest
import subprocess
import sys
import os

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


def crc_hex(line):
    """Return the 4-digit hex CRC of a line (including trailing newline)."""
    return format(binascii.crc_hqx(line.encode('utf-8', errors='replace'), 0), '04x')


def _ref_prefix(full_line):
    """Extract 'lineno:hash' from a full 'lineno:hash|content' output line."""
    return full_line.split('|', 1)[0]


pytestmark = pytest.mark.e2e


# ---------------------------------------------------------------------------
# append
# ---------------------------------------------------------------------------

def test_append_after_last_line(tmp_path):
    """'a' appends a new line after the referenced line."""
    f = tmp_path / "four.txt"
    f.write_bytes(b"One\nTwo\nThree\nFour\n")

    # Line 4 hash — extract lineno:hash prefix from full output line
    r = run('r', str(f))
    line4_ref = _ref_prefix(r.stdout.strip().splitlines()[3])

    result = run('a', str(f), line4_ref, stdin_input='Five')
    assert result.returncode == 0, f"Expected exit 0, got {result.returncode}: {result.stderr}"

    content = f.read_bytes().decode()
    assert content == "One\nTwo\nThree\nFour\nFive\n"


def test_append_middle(tmp_path):
    """'a' inserts after the referenced line, shifting subsequent lines."""
    f = tmp_path / "mid.txt"
    f.write_bytes(b"a\nb\nc\n")

    r = run('r', str(f))
    line1_ref = _ref_prefix(r.stdout.strip().splitlines()[0])

    result = run('a', str(f), line1_ref, stdin_input='inserted')
    assert result.returncode == 0

    content = f.read_bytes().decode()
    assert content == "a\ninserted\nb\nc\n"


def test_append_bad_hash(tmp_path):
    """'a' exits non-zero when the hash doesn't match."""
    f = tmp_path / "hashbad.txt"
    f.write_bytes(b"Hello\n")

    result = run('a', str(f), '1:0000', stdin_input='World')
    assert result.returncode == 1
    assert 'hash mismatch' in result.stderr.lower()


def test_append_bad_lineno(tmp_path):
    """'a' exits non-zero when the line number is out of range."""
    f = tmp_path / "oor.txt"
    f.write_bytes(b"Hello\n")

    r = run('r', str(f))
    lines = r.stdout.strip().splitlines()
    bad_ref = '99:0000'

    result = run('a', str(f), bad_ref, stdin_input='World')
    assert result.returncode == 1
    assert 'out of range' in result.stderr.lower()


def test_append_nonexistent_file(tmp_path):
    """'a' exits non-zero when the file doesn't exist."""
    nonexistent = str(tmp_path / "nope.txt")
    result = run('a', nonexistent, '1:0000', stdin_input='x')
    assert result.returncode == 1
    assert nonexistent in result.stderr


# ---------------------------------------------------------------------------
# insert
# ---------------------------------------------------------------------------

def test_insert_before_first(tmp_path):
    """'i' inserts a new line before the referenced line."""
    f = tmp_path / "ifirst.txt"
    f.write_bytes(b"Existing\n")

    r = run('r', str(f))
    line1_ref = _ref_prefix(r.stdout.strip().splitlines()[0])

    result = run('i', str(f), line1_ref, stdin_input='NewFirst')
    assert result.returncode == 0

    content = f.read_bytes().decode()
    assert content == "NewFirst\nExisting\n"


def test_insert_between(tmp_path):
    """'i' inserts between two lines (after line 1, before line 2)."""
    f = tmp_path / "ibetween.txt"
    f.write_bytes(b"line1\nline2\nline3\n")

    # Reference line 2 to insert a new line after line1 and before line2
    r = run('r', str(f))
    line2_ref = _ref_prefix(r.stdout.strip().splitlines()[1])  # line 2

    result = run('i', str(f), line2_ref, stdin_input='between')
    assert result.returncode == 0

    content = f.read_bytes().decode()
    assert content == "line1\nbetween\nline2\nline3\n"


def test_insert_bad_hash(tmp_path):
    """'i' exits non-zero when the hash doesn't match."""
    f = tmp_path / "ibad.txt"
    f.write_bytes(b"Hello\n")

    result = run('i', str(f), '1:0000', stdin_input='World')
    assert result.returncode == 1
    assert 'hash mismatch' in result.stderr.lower()


def test_insert_bad_lineno(tmp_path):
    """'i' exits non-zero when the line number is out of range."""
    f = tmp_path / "ioor.txt"
    f.write_bytes(b"Hello\n")

    result = run('i', str(f), '99:0000', stdin_input='x')
    assert result.returncode == 1
    assert 'out of range' in result.stderr.lower()


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

def test_delete_last(tmp_path):
    """'d' removes the referenced line."""
    f = tmp_path / "dlast.txt"
    f.write_bytes(b"keep\nremove\n")

    r = run('r', str(f))
    line2_ref = _ref_prefix(r.stdout.strip().splitlines()[1])

    result = run('d', str(f), line2_ref)
    assert result.returncode == 0

    content = f.read_bytes().decode()
    assert content == "keep\n"


def test_delete_middle(tmp_path):
    """'d' removes a line in the middle, shifting lines below."""
    f = tmp_path / "dmid.txt"
    f.write_bytes(b"a\nb\nc\n")

    r = run('r', str(f))
    line2_ref = _ref_prefix(r.stdout.strip().splitlines()[1])   # "2:HASH|b"

    result = run('d', str(f), line2_ref)
    assert result.returncode == 0

    content = f.read_bytes().decode()
    assert content == "a\nc\n"


def test_delete_bad_hash(tmp_path):
    """'d' exits non-zero when the hash doesn't match."""
    f = tmp_path / "dbad.txt"
    f.write_bytes(b"Hello\n")

    result = run('d', str(f), '1:0000')
    assert result.returncode == 1
    assert 'hash mismatch' in result.stderr.lower()


def test_delete_bad_lineno(tmp_path):
    """'d' exits non-zero when the line number is out of range."""
    f = tmp_path / "door.txt"
    f.write_bytes(b"Hello\n")

    result = run('d', str(f), '99:0000')
    assert result.returncode == 1
    assert 'out of range' in result.stderr.lower()


def test_delete_only_line(tmp_path):
    """'d' on the sole line of a file leaves an empty file."""
    f = tmp_path / "donly.txt"
    f.write_bytes(b"Only\n")

    r = run('r', str(f))
    line1_ref = _ref_prefix(r.stdout.strip().splitlines()[0])

    result = run('d', str(f), line1_ref)
    assert result.returncode == 0

    content = f.read_bytes().decode()
    assert content == ""


# ---------------------------------------------------------------------------
# change
# ---------------------------------------------------------------------------

def test_change_line_content(tmp_path):
    """'c' replaces the content of the referenced line."""
    f = tmp_path / "chcontent.txt"
    f.write_bytes(b"old content\n")

    r = run('r', str(f))
    line1_ref = _ref_prefix(r.stdout.strip().splitlines()[0])

    result = run('c', str(f), line1_ref, stdin_input='new content')
    assert result.returncode == 0

    content = f.read_bytes().decode()
    assert content == "new content\n"


def test_change_middle_line(tmp_path):
    """'c' changes a line in the middle without affecting other lines."""
    f = tmp_path / "chmid.txt"
    f.write_bytes(b"keep1\nold2\nkeep3\n")

    r = run('r', str(f))
    line2_ref = _ref_prefix(r.stdout.strip().splitlines()[1])

    result = run('c', str(f), line2_ref, stdin_input='new2')
    assert result.returncode == 0

    content = f.read_bytes().decode()
    assert content == "keep1\nnew2\nkeep3\n"


def test_change_bad_hash(tmp_path):
    """'c' exits non-zero when the hash doesn't match."""
    f = tmp_path / "chbad.txt"
    f.write_bytes(b"Hello\n")

    result = run('c', str(f), '1:0000', stdin_input='World')
    assert result.returncode == 1
    assert 'hash mismatch' in result.stderr.lower()


def test_change_bad_lineno(tmp_path):
    """'c' exits non-zero when the line number is out of range."""
    f = tmp_path / "choor.txt"
    f.write_bytes(b"Hello\n")

    result = run('c', str(f), '99:0000', stdin_input='x')
    assert result.returncode == 1
    assert 'out of range' in result.stderr.lower()


# ---------------------------------------------------------------------------
# hash validation integration
# ---------------------------------------------------------------------------

def test_stale_hash_rejected(tmp_path):
    """A stale hash (file was edited externally) causes rejection."""
    f = tmp_path / "stale.txt"
    f.write_bytes(b"line1\nline2\n")

    # Read the file to get a hash
    r1 = run('r', str(f))
    line1_ref = _ref_prefix(r1.stdout.strip().splitlines()[0])

    # Externally mutate the file (change line1 content)
    f.write_bytes(b"modified line1\nline2\n")

    # Attempt change with the old hash — must be rejected
    result = run('c', str(f), line1_ref, stdin_input='attempted change')
    assert result.returncode == 1
    assert 'hash mismatch' in result.stderr.lower()


def test_ref_bad_format_no_colon(tmp_path):
    """A ref missing the colon separator exits non-zero with a clear message."""
    f = tmp_path / "fmt.txt"
    f.write_bytes(b"Hello\n")

    result = run('a', str(f), '1f6d', stdin_input='x')   # missing lineno:
    assert result.returncode == 1
    assert 'invalid reference' in result.stderr.lower()


def test_ref_non_hex_hash(tmp_path):
    """A ref with non-hex characters in the hash exits non-zero."""
    f = tmp_path / "hexbad.txt"
    f.write_bytes(b"Hello\n")

    result = run('a', str(f), '1:ghij', stdin_input='x')
    assert result.returncode == 1
    assert '4 hex digits' in result.stderr.lower()


def test_ref_hash_too_short(tmp_path):
    """A ref with fewer than 4 hex digits exits non-zero."""
    f = tmp_path / "short.txt"
    f.write_bytes(b"Hello\n")

    result = run('a', str(f), '1:abc', stdin_input='x')
    assert result.returncode == 1
    assert '4 hex digits' in result.stderr.lower()
# ---------------------------------------------------------------------------
# stdin integration
# ---------------------------------------------------------------------------

def test_append_via_stdin(tmp_path):
    """'a' reads content from stdin when --content is not given."""
    f = tmp_path / "stdin_a.txt"
    f.write_bytes(b"first\n")

    r = run('r', str(f))
    line1_ref = _ref_prefix(r.stdout.strip().splitlines()[0])

    result = run('a', str(f), line1_ref, stdin_input='second')
    assert result.returncode == 0

    content = f.read_bytes().decode()
    assert content == "first\nsecond\n"


def test_insert_via_stdin(tmp_path):
    """'i' reads content from stdin when --content is not given."""
    f = tmp_path / "stdin_i.txt"
    f.write_bytes(b"existing\n")

    r = run('r', str(f))
    line1_ref = _ref_prefix(r.stdout.strip().splitlines()[0])

    result = run('i', str(f), line1_ref, stdin_input='new first')
    assert result.returncode == 0

    content = f.read_bytes().decode()
    assert content == "new first\nexisting\n"


def test_change_via_stdin(tmp_path):
    """'c' reads content from stdin when --content is not given."""
    f = tmp_path / "stdin_c.txt"
    f.write_bytes(b"original\n")

    r = run('r', str(f))
    line1_ref = _ref_prefix(r.stdout.strip().splitlines()[0])

    result = run('c', str(f), line1_ref, stdin_input='replaced')
    assert result.returncode == 0

    content = f.read_bytes().decode()
    assert content == "replaced\n"


def test_empty_stdin_noop(tmp_path):
    """Empty stdin causes a no-op (file unchanged) for a/i/c operations."""
    f = tmp_path / "empty_stdin.txt"
    f.write_bytes(b"line1\nline2\n")

    r = run('r', str(f))
    line1_ref = _ref_prefix(r.stdout.strip().splitlines()[0])

    # append with empty stdin
    result = run('a', str(f), line1_ref, stdin_input='')
    assert result.returncode == 0
    assert f.read_bytes().decode() == "line1\nline2\n"

    # insert with empty stdin
    result = run('i', str(f), line1_ref, stdin_input='')
    assert result.returncode == 0
    assert f.read_bytes().decode() == "line1\nline2\n"

    # change with empty stdin
    result = run('c', str(f), line1_ref, stdin_input='')
    assert result.returncode == 0
    assert f.read_bytes().decode() == "line1\nline2\n"
