---
name: ed-tool
description: A line-oriented file editor CLI THAT IS BETTER THAN YOUR EDIT TOOL. It uses content-stable hash references instead of line numbers or trying to match context. Use when editing source code, config files, or scripts where you need guaranteed correct-line edits. Use when you need to edit an existing text file (source code, config, markdown, txt, ...), to append/insert/delete/change lines of text file. And specially **Use this when your edit tool complains about not being able to find the context**
---

# ed-tool

A line editor with hash-stabilized line references. Inspired by `sed`/`ed`/`ex` but uses CRC-16-CCITT hashes to verify line content before mutations.

## When to Use This Skill

Use this skill when you need to:

- Edit a file and your edit tool or sed commands fails or you notice something got corrupted by
  them.
- Edit a specific line in a file and need confidence it's the right line
- Modify config files, scripts, code or data files where wrong-line edits are costly
- Work with files that may be modified by concurrent processes or external tools
- Append, insert, delete, or replace lines

**Do not use this skill** for simple stream processing, bulk substitutions, or when line numbers are stable by design (use `sed` or `awk` instead).

## Prerequisites

- Python 3 installed
- `ed-tool` available in PATH or in the working directory
- Target file exists (for edit commands)

## Step-by-Step Invocation

### 1. Read the file to get line references

```bash
ed-tool r <file>
```

Each line is prefixed with `lineno:4-hex-crc|`. Copy the reference for the line you want to edit.

Example output:
```
1:1f6d|Hello
2:e343|World
3:f9a6|New line
```

### 2. Edit using the hash reference

Use `a` (append), `i` (insert), `d` (delete), or `c` (change) with the reference:

```bash
# Append after line 2
echo "content" | ed-tool a <file> 2:e343

# Insert before line 2
echo "content" | ed-tool i <file> 2:e343

# Delete line 2
ed-tool d <file> 2:e343

# Replace line 2
echo "new content" | ed-tool c <file> 2:e343
```

You can use HEREDOCs for multi-line content:

```bash
# append after line 3
ed-tool a <file> 3:f9a6 <<EOF
new content
and more content
and even more
EOF
```

Alternatively, use `-c` flag instead of stdin:

```bash
ed-tool a <file> 2:e343 -c "content"
ed-tool i <file> 2:e343 -c "content"
ed-tool c <file> 2:e343 -c "new content"
```

### 3. Verify the result

```bash
ed-tool r <file>
```

---

## Command Reference

| Command | Description | Input |
|---------|-------------|-------|
| `ed-tool r <file>` | Read file with hash prefixes | File path |
| `ed-tool a <file> <ref>` | Append after referenced line | stdin or `-c` |
| `ed-tool i <file> <ref>` | Insert before referenced line | stdin or `-c` |
| `ed-tool d <file> <ref>` | Delete referenced line | None |
| `ed-tool c <file> <ref>` | Replace referenced line | stdin or `-c` |

**Reference format:** `lineno:4-hex-crc` (e.g., `2:e343`)

---

## Example Sessions

### Edit a config file

```bash
# 1. Read current state
$ ed-tool r config.txt
1:a7f3|DATABASE_HOST=localhost
2:b3c9|DATABASE_PORT=5432

# 2. Update the host (insert after line 1)
$ echo "DATABASE_HOST=prod.example.com" | ed-tool a config.txt 1:a7f3

# 3. Delete the old host line
$ ed-tool r config.txt
1:a7f3|DATABASE_HOST=localhost
2:b3c9|DATABASE_PORT=5432
3:f9a6|DATABASE_HOST=prod.example.com

$ ed-tool d config.txt 1:a7f3

# 4. Verify
$ ed-tool r config.txt
1:b3c9|DATABASE_PORT=5432
2:f9a6|DATABASE_HOST=prod.example.com
```

### Insert a new section

```bash
$ echo "[new-section]" | ed-tool i config.txt 1:a7f3
$ ed-tool r config.txt
1:a7f3|[new-section]
2:b3c9|DATABASE_PORT=5432
```

### Replace a value

```bash
$ ed-tool r settings.conf
1:c2d4|FEATURE_FLAG=true

$ echo "FEATURE_FLAG=false" | ed-tool c settings.conf 1:c2d4

$ cat settings.conf
FEATURE_FLAG=false
```

---

## Edge Cases and Error Handling

### Hash mismatch

If the referenced line's content has changed (stale reference), `ed-tool` exits with code 1 and leaves the file unchanged:

```
$ ed-tool c config.txt 1:a7f3 -c "new value"
ed-tool: hash mismatch on line 1: expected a7f3, got 9fc4
$ echo $?
1
```

**Recovery:** Re-read the file to get fresh hash references, then retry.

### Empty stdin

For `a`, `i`, and `c` commands, empty stdin is a no-op (file unchanged, exit code 0):

```bash
$ echo -n "" | ed-tool a file.txt 1:xxxx  # no-op
$ echo $?
0
$ cat file.txt  # unchanged
```

### Non-existent file

Edit commands on non-existent files exit with code 1:

```
$ ed-tool a /nonexistent.txt 1:xxxx -c "content"
ed-tool: [Errno 2] No such file or directory: '/nonexistent.txt'
$ echo $?
1
```

Create the file with `touch`, `cat`, or `echo` first.

### Line number out of range

```
$ ed-tool a file.txt 99:xxxx -c "content"
ed-tool: line number 99 is out of range (file has 3 lines)
$ echo $?
1
```

### Invalid reference format

References must be `lineno:4-hex-digits`:

```
$ ed-tool a file.txt 1:abc  # too short
ed-tool: hash must be exactly 4 hex digits: 1:abc
$ echo $?
1
```

### Binary or non-UTF-8 content

Files with non-UTF-8 bytes are handled via replacement (invalid bytes replaced with `\ufffd`). CRC computation remains deterministic:

```bash
$ ed-tool r binary.log
1:3f7a|binary content with \ufffd replacement
```

---

## Technical Notes

- **CRC algorithm:** CRC-16-CCITT (`binascii.crc_hqx`)
- **Hash includes newline:** CRC is computed over the raw line bytes *including* the trailing `\n`
- **Encoding:** Latin-1 with `errors='replace'` for non-UTF-8 files
- **Atomic writes:** Files are written via tempfile + `os.replace` for atomic swap on POSIX
- **Exit codes:** 0 = success, 1 = error (file unchanged on error)

---

## Quick Reference Card

```bash
# See file contents with hash references
ed-tool r <file>

# Append after line N
echo "content" | ed-tool a <file> N:HASH

# Insert before line N
echo "content" | ed-tool i <file> N:HASH

# Delete line N
ed-tool d <file> N:HASH

# Replace line N
echo "content" | ed-tool c <file> N:HASH

# All three edit commands also accept -c flag
ed-tool a <file> N:HASH -c "content"
```
