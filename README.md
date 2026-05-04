# ed-tool

**A line-oriented file editor with content-stable addressing.**

`ed-tool` is a CLI tool for editing files using *hash-stabilized line references*. Instead of fragile line numbers that shift when content changes, each line carries a CRC-16-CCITT hash that proves its identity. Edit the right line guaranteed.

---

## Why Hash-Based Line Referencing?

Traditional line editors (like `sed`) use line numbers (`sed -i 5d file` deletes line 5). But line numbers are fragile: any edit above line 5 shifts all subsequent line numbers, and your script now edits the wrong line.

`ed-tool` solves this with hash-validated references:

```
$ ed-tool r myfile.txt
1:1f6d|Hello
2:e343|World
3:67a7|Something
```

Each line is tagged with a 4-character CRC hash. When you reference `2:e343`, `ed-tool` verifies that line 2 still contains "World" before editing. If someone else edited the line, the line number or the hash won't match — and `ed-tool` refuses to edit, protecting you from corrupting the wrong line.

**This is the key difference.** Use `ed-tool` when you need confidence that your edits go exactly where you intend, even in files being edited concurrently.

---

## Installation

```bash
# Make executable and add to PATH
chmod +x ed-tool
sudo cp ed-tool /usr/local/bin/

# Or run directly from the repo
./ed-tool --version
```

Requires Python 3 (stdlib only — no dependencies).

To make your agent know about this tool copy the SKILL.md file to a subdirectory
in your agent's skill directory. For example:

```bash
mkdir -p ~/.pi/agent/skills/ed-tool && cp SKILL.md ~/.pi/agent/skills/ed-tool/SKILL.md
```

---

## Commands

`ed-tool` supports five commands: `r` (read), `a` (append), `i` (insert), `d` (delete), and `c` (change).

### `ed-tool r <file> [range]`

Read a file and display each line with its hash reference. Optionally specify a line range.

```
$ echo -e "L1\nL2\nL3\nL4\nL5" > example.txt
$ ed-tool r example.txt
1:ff22|L1
2:aa71|L2
3:9940|L3
4:00d7|L4
5:33e6|L5
```

The output format is `lineno:4-hex-crc|content`. Use these references for edit commands.

**Range support:**
You can specify a range as `[begin][,end]` using 1-based line numbers. The range is half-open: `[begin, end)`.

- `ed-tool r file 2,4` Read lines 2, 3
- `ed-tool r file 2` Read from line 2 to end of file
- `ed-tool r file ,3` Read lines 1, 2 (first 2 lines)
- `ed-tool r file -2` Read last 2 lines (tail)
- `ed-tool r file ,-2` Read everything but last 2 lines (head)
- `ed-tool r file -3,-1` Read antepenultimate and penultimate lines, but not last line.

Ranges are permissive: `begin` can be 0 (means 1), and `end` can exceed the number of lines. Negative indices count from the end of the file (-1 is the last line).

---

### `ed-tool a <file> <ref>`

Append a new line *after* the referenced line. Reads new content from stdin (or use `-c`).

```
$ ed-tool r example.txt
1:1f6d|Hello
2:e343|World

$ echo "New line" | ed-tool a example.txt 2:e343

$ ed-tool r example.txt
1:1f6d|Hello
2:e343|World
3:ac28|New line
```

The hash (`2:e343`) proves you're appending after the correct line. If the file changed externally, the hash won't match and `ed-tool` exits with an error — file unchanged.

**With `-c` flag** (alternative to stdin):

```bash
ed-tool a example.txt 2:e343 -c "New line"
```

**Empty stdin = no-op.** If you pipe nothing, nothing is appended.

---

### `ed-tool i <file> <ref>`

Insert a new line *before* the referenced line. Reads from stdin (or `-c`).

```
$ ed-tool r example.txt
1:1f6d|Hello
2:e343|World

$ echo "Before World" | ed-tool i example.txt 2:e343

$ ed-tool r example.txt
1:1f6d|Hello
2:4aa5|Before World
3:e343|World
```

Hash validation prevents inserting before the wrong line.

**With `-c` flag:**

```bash
ed-tool i example.txt 2:e343 -c "Before World"
```

**Empty stdin = no-op.**

---

### `ed-tool d <file> <ref>`

Delete the referenced line. No content input needed.

```
$ ed-tool r example.txt
1:1f6d|Hello
2:e343|World
3:ac28|New line

$ ed-tool d example.txt 2:e343

$ ed-tool r example.txt
1:1f6d|Hello
2:ac28|New line
```

The hash (`2:e343`) confirms you're deleting the correct line. Line 3 becomes line 2.

---

### `ed-tool c <file> <ref>`

Replace the referenced line's content. Reads new content from stdin (or `-c`).

```
$ ed-tool r example.txt
1:1f6d|Hello
2:e343|World

$ echo "Replaced" | ed-tool c example.txt 2:e343

$ ed-tool r example.txt
1:1f6d|Hello
2:b860|Replaced
```

The new content gets a new CRC hash (`b860`).

**With `-c` flag:**

```bash
ed-tool c example.txt 2:e343 -c "Replaced"
```

**Empty stdin = no-op.**

---

## Worked Examples

### Example 1: Read a File (with Range)

```
$ cat greetings.txt
L1
L2
L3
L4
L5

$ ed-tool r greetings.txt 2,4
2:aa71|L2
3:9940|L3

$ ed-tool r greetings.txt -2
4:00d7|L4
5:33e6|L5
```

### Example 2: Append a Line

```
$ ed-tool r greetings.txt
1:1f6d|Hello
2:e343|World

$ echo "New line" | ed-tool a greetings.txt 2:e343

$ cat greetings.txt
Hello
World
New line
```

### Example 3: Delete a Line

```
$ echo -e "keep\nremove" > lines.txt
$ ed-tool r lines.txt
1:c93c|keep
2:723c|remove

$ ed-tool d lines.txt 2:f9a6

$ cat lines.txt
keep
```

### Example 4: Change Line Content

```
$ echo -e "line1\nline2\nline3" > myfile.txt
$ ed-tool r myfile.txt
1:f9a6|line1
2:acf5|line2
3:9fc4|line3

$ echo "CHANGED" | ed-tool c myfile.txt 2:acf5

$ cat myfile.txt
line1
CHANGED
line3
```

### Example 5: Hash Mismatch Protection

If the referenced line's content has changed (stale reference), `ed-tool` refuses to edit:

```
$ cat greetings.txt
Hello
World

$ ed-tool c greetings.txt 1:1f6d -c "Hi"
ed-tool: hash mismatch on line 1: expected 1f6d, got 6016
$ echo $?
1
$ cat greetings.txt
Hello
World
```

`ed-tool` exits with code 1, prints a diagnostic, and leaves the file untouched. Re-read the file to get fresh hash references.

---

## Use Cases

**Use `ed-tool` when:**
- Editing config files where wrong-line edits have consequences
- Scripts that edit files that might be modified concurrently
- Anything where you want confidence that you're editing the intended line
- You are an LLM and your patch tool is confused because of spaces or other
  trivialities

**Stick with `sed`/`awk`/`ex` when:**
- Simple, one-off substitutions
- Stream processing where line numbers are stable by design
- Performance-critical bulk transformations

The hash model adds overhead per edit, but buys correctness insurance.

---

## Reference: Hash Format

- **CRC algorithm:** CRC-16-CCITT (`binascii.crc_hqx`)
- **Hash scope:** 4 hexadecimal characters (16-bit)
- **What's hashed:** The raw line bytes *including* the trailing newline (`\n`)
- **Encoding:** Latin-1 with `errors='replace'` (non-UTF-8 bytes are replaced, CRC remains deterministic)

```
CRC computed over: b'Hello\n'
Result: 0x1f6d → displayed as "1f6d"
```

A hash mismatch means the line content (including its newline) has changed since you last read the file.

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid reference, hash mismatch, file not found, out of range) |

On error, `ed-tool` writes a diagnostic to stderr and exits without modifying the file.
