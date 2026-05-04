"""End-to-end tests for the 'ed-tool r' read subcommand."""

import binascii
import pytest
import subprocess
import sys
import tempfile
import os

ED_TOOL = os.path.join(os.path.dirname(__file__), '..', 'ed-tool')


def run(*args):
    """Run ed-tool with the given arguments, return CompletedProcess."""
    return subprocess.run(
        [sys.executable, ED_TOOL] + list(args),
        capture_output=True,
        text=True,
    )


pytestmark = pytest.mark.e2e


def test_crc_computation():
    """Verify binascii.crc_hqx produces the expected 4-hex-digit value for 'Hello\\n'.

    The tool computes CRC over the raw line (including the trailing newline),
    so we test against crc_hqx(b'Hello\\n', 0) = '1f6d'.
    """
    result = format(binascii.crc_hqx(b'Hello\n', 0), '04x')
    assert result == '1f6d', f"Expected '1f6d' but got '{result}'"


def test_read_happy_path(tmp_path):
    """ed-tool r <file> exits 0 and produces lineno:4hex-crc| prefixed lines."""
    test_file = tmp_path / "hello.txt"
    test_file.write_bytes(b'Hello\nWorld\n')

    result = run('r', str(test_file))
    lines = result.stdout.splitlines()

    assert result.returncode == 0, f"Expected exit 0, got {result.returncode}: {result.stderr}"
    assert any('1:1f6d|Hello' in line for line in lines), f"Missing line 1 in output: {lines}"
    assert any('2:e343|World' in line for line in lines), f"Missing line 2 in output: {lines}"


def test_read_empty_file(tmp_path):
    """ed-tool r <emptyfile> exits 0 and produces no output."""
    test_file = tmp_path / "empty.txt"
    test_file.write_bytes(b'')

    result = run('r', str(test_file))

    assert result.returncode == 0, f"Expected exit 0, got {result.returncode}: {result.stderr}"
    assert result.stdout == '', f"Expected empty stdout, got: {result.stdout!r}"


def test_read_nonexistent_file():
    """ed-tool r /nonexistent exits non-zero with an error message."""
    result = run('r', '/tmp/nonexistent_xyz_edtool_test.txt')

    assert result.returncode == 1, f"Expected exit 1, got {result.returncode}"
    assert '/tmp/nonexistent_xyz_edtool_test.txt' in result.stderr, (
        f"Expected filename in stderr, got: {result.stderr!r}"
    )


def test_read_binary_file(tmp_path):
    """ed-tool r <binaryfile> exits 0 and includes the line content (replacement chars OK)."""
    # but the line must still be produced without crashing.
    test_file = tmp_path / "binary.bin"
    test_file.write_bytes(b'\xff\xfe\n')
    test_file.write_bytes(b'\xff\xff\n')
    test_file.write_bytes(b'\x00\xff\n')

    result = run('r', str(test_file))

    assert result.returncode == 0, f"Expected exit 0, got {result.returncode}: {result.stderr}"
    # The only line should start with 1: and contain some content after the pipe
    lines = [l for l in result.stdout.splitlines() if l]
    assert len(lines) == 1, f"Expected exactly 1 output line, got {len(lines)}: {lines}"
    assert lines[0].startswith('1:'), f"Expected line to start with '1:', got: {lines[0]!r}"


def test_read_range_simple(tmp_path):
    test_file = tmp_path / "multi.txt"
    test_file.write_text("L1\nL2\nL3\nL4\nL5\n")

    # r <file> 2,4 -> lines 2, 3
    result = run('r', str(test_file), '2,4')
    lines = result.stdout.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("2:") and "L2" in lines[0]
    assert lines[1].startswith("3:") and "L3" in lines[1]


def test_read_range_negative_begin(tmp_path):
    test_file = tmp_path / "multi.txt"
    test_file.write_text("L1\nL2\nL3\nL4\nL5\n")

    # r <file> -2 -> last 2 lines (4, 5)
    result = run('r', str(test_file), '-2')
    lines = result.stdout.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("4:")
    assert lines[1].startswith("5:")


def test_read_range_negative_end(tmp_path):
    test_file = tmp_path / "multi.txt"
    test_file.write_text("L1\nL2\nL3\nL4\nL5\n")

    # r <file> ,-2 -> everything but last 2 (1, 2, 3)
    result = run('r', str(test_file), ',-2')
    lines = result.stdout.splitlines()
    assert len(lines) == 3
    assert lines[0].startswith("1:")
    assert lines[1].startswith("2:")
    assert lines[2].startswith("3:")


def test_read_range_both_negative(tmp_path):
    test_file = tmp_path / "multi.txt"
    test_file.write_text("L1\nL2\nL3\nL4\nL5\n")

    # r <file> -3,-1 -> antepenultimate and penultimate (3, 4)
    result = run('r', str(test_file), '-3,-1')
    lines = result.stdout.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("3:")
    assert lines[1].startswith("4:")


def test_read_range_permissive(tmp_path):
    test_file = tmp_path / "multi.txt"
    test_file.write_text("L1\nL2\nL3\nL4\nL5\n")

    # r <file> 0,100 -> all lines
    result = run('r', str(test_file), '0,100')
    lines = result.stdout.splitlines()
    assert len(lines) == 5

    # r <file> 4,2 -> empty
    result = run('r', str(test_file), '4,2')
    assert result.stdout == ""


def test_read_range_comma_only(tmp_path):
    test_file = tmp_path / "multi.txt"
    test_file.write_text("L1\nL2\nL3\nL4\nL5\n")

    # r <file> , -> all lines (same as empty)
    result = run('r', str(test_file), ',')
    lines = result.stdout.splitlines()
    assert len(lines) == 5


def test_read_range_begin_only(tmp_path):
    test_file = tmp_path / "multi.txt"
    test_file.write_text("L1\nL2\nL3\nL4\nL5\n")

    # r <file> 3, -> from 3 to end
    result = run('r', str(test_file), '3,')
    lines = result.stdout.splitlines()
    assert len(lines) == 3
    assert lines[0].startswith("3:")
    assert lines[-1].startswith("5:")
