"""10 道更难的题。每题：id、函数名、规格（给模型看的原文）、是否禁止修改输入、隐藏测试、参考答案。

隐藏测试的格式和 tasks_base 一样：(参数元组, 期望值)；期望抛错写成 VE = ("__raises__", "ValueError")。
"""
VE = ("__raises__", "ValueError")

HARD = [
    {
        "id": "t21_parse_size",
        "func": "parse_size",
        "spec": """Implement `parse_size(s: str) -> int` that converts a human-readable size to a number of bytes.
- `s` is a number optionally followed by a unit. Leading/trailing whitespace is allowed, and any amount of whitespace (including none) may separate the number from the unit.
- The number is a non-negative integer or a decimal with a dot, written with ASCII digits: `12`, `1.5`, `0.25`. No sign, no exponent, no thousands separators, no leading dot, no trailing dot. `1,5` and `.5` and `5.` are invalid.
- Units, matched case-insensitively: `B` (bytes), `KB`, `MB`, `GB`, `TB` (powers of 1000) and `KiB`, `MiB`, `GiB`, `TiB` (powers of 1024). No unit means bytes. Any other unit text (for example a bare `K`, or `PB`) is invalid.
- Nothing may follow the unit except whitespace.
- The result is the exact product rounded to the nearest integer; ties (a fractional part of exactly .5) round up. For example `2.5 B` -> 3 and `1.5 KB` -> 1500. Avoid binary floating-point error: `0.1 GB` must give exactly 100000000.
- Raise `ValueError` for anything invalid, including an empty string.""",
        "no_mutate": False,
        "tests": [
            (("0",), 0), (("123",), 123), (("123 B",), 123), (("1KB",), 1000), (("1 kb",), 1000),
            (("1KiB",), 1024), (("1.5 KiB",), 1536), (("1.5 KB",), 1500), (("2.5 B",), 3), (("0.5B",), 1),
            (("3 GiB",), 3221225472), (("0.1 GB",), 100000000), (("2 TB",), 2000000000000),
            (("  7 MiB ",), 7340032), (("1.1 TB",), 1100000000000), (("10 Mb",), 10000000),
            (("",), VE), (("1,5GB",), VE), ((".5KB",), VE), (("5.",), VE), (("1e3",), VE), (("5 PB",), VE),
            (("-1 KB",), VE), (("KB",), VE), (("1 KB B",), VE), (("1 K",), VE),
        ],
        "reference": r'''
import re
from decimal import Decimal, ROUND_HALF_UP

def parse_size(s):
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([A-Za-z]*)\s*", s)
    if not m:
        raise ValueError("invalid size: %r" % (s,))
    num, unit = m.group(1), m.group(2).upper()
    units = {"": 1, "B": 1, "KB": 1000, "MB": 1000 ** 2, "GB": 1000 ** 3, "TB": 1000 ** 4,
             "KIB": 1024, "MIB": 1024 ** 2, "GIB": 1024 ** 3, "TIB": 1024 ** 4}
    if unit not in units:
        raise ValueError("unknown unit: %r" % (unit,))
    value = Decimal(num) * units[unit]
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))
''',
    },
    {
        "id": "t22_shell_split",
        "func": "shell_split",
        "spec": """Implement `shell_split(s: str) -> list[str]` that splits a command line into words the way a POSIX shell does (a small subset of the rules).
- Outside quotes, spaces and tabs separate words. Runs of separators count as one. Leading/trailing separators produce no empty words; an empty or whitespace-only string gives `[]`.
- Outside quotes, a backslash makes the next character literal, whatever it is (including a space, a quote or another backslash). A backslash at the very end of the string is an error.
- Single quotes: everything up to the next single quote is literal; there are no escapes inside single quotes.
- Double quotes: everything up to the next unescaped double quote is literal, except that `\\"` becomes `"` and `\\\\` becomes `\\`. Any other backslash inside double quotes is kept as is (so `"a\\nb"` yields the 4 characters a, backslash, n, b).
- Quoted and unquoted pieces that touch each other form one word: `a"b"'c'` is the single word `abc`.
- An empty quoted string is a real word: `''` gives `['']` and `a '' b` gives `['a', '', 'b']`.
- An unterminated quote is an error.
- Raise `ValueError` for errors.""",
        "no_mutate": False,
        "tests": [
            (("a b  c",), ["a", "b", "c"]), (("'a b' c",), ["a b", "c"]), (('"a b" c',), ["a b", "c"]),
            (("a\\ b",), ["a b"]), (('"a\\"b"',), ['a"b']), (("'a\\'",), ["a\\"]), (("a'b'c",), ["abc"]),
            (("''",), [""]), (("a '' b",), ["a", "", "b"]), (('""',), [""]), (("  ",), []), (("",), []),
            (("a\tb",), ["a", "b"]), (('"a\\\\b"',), ["a\\b"]), (('"a\\nb"',), ["a\\nb"]), (("a\\\"b",), ['a"b']),
            (("  x  ",), ["x"]), (("a\\\\b",), ["a\\b"]), (("'it''s'",), ["its"]),
            (("'abc",), VE), (('"abc',), VE), (("abc\\",), VE), (("a 'b",), VE),
        ],
        "reference": r'''
def shell_split(s):
    out, cur, in_word = [], [], False
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in " \t":
            if in_word:
                out.append("".join(cur))
                cur, in_word = [], False
            i += 1
        elif c == "\\":
            if i + 1 >= n:
                raise ValueError("trailing backslash")
            cur.append(s[i + 1])
            in_word = True
            i += 2
        elif c == "'":
            j = s.find("'", i + 1)
            if j < 0:
                raise ValueError("unterminated single quote")
            cur.append(s[i + 1:j])
            in_word = True
            i = j + 1
        elif c == '"':
            i += 1
            in_word = True
            while True:
                if i >= n:
                    raise ValueError("unterminated double quote")
                c = s[i]
                if c == '"':
                    i += 1
                    break
                if c == "\\" and i + 1 < n and s[i + 1] in '"\\':
                    cur.append(s[i + 1])
                    i += 2
                else:
                    cur.append(c)
                    i += 1
        else:
            cur.append(c)
            in_word = True
            i += 1
    if in_word:
        out.append("".join(cur))
    return out
''',
    },
    {
        "id": "t23_evaluate",
        "func": "evaluate",
        "spec": """Implement `evaluate(expr: str)` that evaluates an arithmetic expression given as a string and returns a number.
- Tokens: integer literals (ASCII digits), decimal literals (digits, a dot, digits), the operators `+ - * / ^`, and parentheses. Whitespace between tokens is allowed anywhere and is otherwise ignored.
- `+ -` have the lowest precedence, `* /` are higher, `^` (exponentiation) is highest. `+ - * /` are left-associative; `^` is right-associative, so `2 ^ 3 ^ 2` is 512.
- Unary minus is allowed before a number, a parenthesis, or another unary minus (`--3` is 3). It binds less tightly than `^`: `-2 ^ 2` is -4. The exponent itself may start with a unary minus: `2 ^ -1` is 0.5.
- Integer literals are `int`, decimal literals are `float`. Arithmetic follows Python's numeric rules, except that `/` is always true division (`7 / 2` is 3.5) and `^` means `**`.
- Division by zero raises `ValueError` (not ZeroDivisionError).
- Any malformed input raises `ValueError`: empty string, unknown characters, two numbers in a row (`2 3`), a missing operand (`2 +`), unbalanced parentheses, `**`, implicit multiplication (`2(3)`).""",
        "no_mutate": False,
        "tests": [
            (("1 + 2 * 3",), 7), (("(1 + 2) * 3",), 9), (("-2 ^ 2",), -4), (("2 ^ 3 ^ 2",), 512), (("--3",), 3),
            (("10 - 4 - 3",), 3), (("100 / 8 / 2",), 6.25), (("7 / 2",), 3.5), (("2 * -3",), -6), (("1.5 * 4",), 6.0),
            ((" ( 2 ) ",), 2), (("2 ^ -1",), 0.5), (("0 ^ 0",), 1), (("2^10",), 1024), (("(2 + 3) ^ 2 - 1",), 24),
            (("-(1 + 2)",), -3), (("8 / 2 * 2",), 8.0),
            (("",), VE), (("2 +",), VE), (("(2",), VE), (("2 3",), VE), (("1 / 0",), VE), (("2 ** 3",), VE),
            (("a + 1",), VE), (("1 +* 2",), VE), (("2(3)",), VE), (("2 )",), VE), (("1 / (2 - 2)",), VE),
        ],
        "reference": r'''
def evaluate(expr):
    toks = []
    i, n = 0, len(expr)
    while i < n:
        c = expr[i]
        if c.isspace():
            i += 1
        elif c.isdigit():
            j = i
            while j < n and expr[j].isdigit():
                j += 1
            if j < n and expr[j] == ".":
                k = j + 1
                if k >= n or not expr[k].isdigit():
                    raise ValueError("bad number")
                while k < n and expr[k].isdigit():
                    k += 1
                toks.append(float(expr[i:k]))
                i = k
            else:
                toks.append(int(expr[i:j]))
                i = j
        elif c in "+-*/^()":
            toks.append(c)
            i += 1
        else:
            raise ValueError("unexpected character %r" % c)
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        t = peek()
        pos[0] += 1
        return t

    def parse_expr():
        v = parse_term()
        while peek() in ("+", "-"):
            op = take()
            r = parse_term()
            v = v + r if op == "+" else v - r
        return v

    def parse_term():
        v = parse_unary()
        while peek() in ("*", "/"):
            op = take()
            r = parse_unary()
            if op == "*":
                v = v * r
            else:
                if r == 0:
                    raise ValueError("division by zero")
                v = v / r
        return v

    def parse_unary():
        if peek() == "-":
            take()
            return -parse_unary()
        return parse_power()

    def parse_power():
        base = parse_atom()
        if peek() == "^":
            take()
            return base ** parse_unary()
        return base

    def parse_atom():
        t = take()
        if t is None:
            raise ValueError("unexpected end")
        if t == "(":
            v = parse_expr()
            if take() != ")":
                raise ValueError("expected )")
            return v
        if isinstance(t, (int, float)):
            return t
        raise ValueError("unexpected token %r" % (t,))

    value = parse_expr()
    if pos[0] != len(toks):
        raise ValueError("trailing input")
    return value
''',
    },
    {
        "id": "t24_glob_match",
        "func": "glob_match",
        "spec": """Implement `glob_match(pattern: str, name: str) -> bool` that tests whether a path-like string matches a glob pattern. The whole of `name` must match (anchored at both ends); matching is case-sensitive.
- `*` matches any sequence of characters (possibly empty) that contains no `/`.
- `**` matches any sequence of characters, including `/` and the empty string.
- `?` matches exactly one character that is not `/`.
- `[...]` matches one character from the set. The set may contain single characters and ranges like `a-z`. A `!` right after `[` negates the set. A `]` placed first in the set (right after `[` or after `[!`) is a literal `]`. A `[` with no closing `]` is an error.
- A backslash makes the next pattern character literal (`\\*` matches a real asterisk). A backslash at the end of the pattern is an error.
- Every other character matches itself.
- Raise `ValueError` for pattern errors.""",
        "no_mutate": False,
        "tests": [
            (("*.py", "a.py"), True), (("*.py", "a.pyc"), False), (("*.py", "dir/a.py"), False), (("**.py", "dir/a.py"), True),
            (("?.py", "a.py"), True), (("?.py", "ab.py"), False), (("[abc].txt", "b.txt"), True), (("[a-c].txt", "d.txt"), False),
            (("[!a-c].txt", "d.txt"), True), (("[]]x", "]x"), True), (("\\*.py", "*.py"), True), (("\\*.py", "a.py"), False),
            (("*", ""), True), (("?", ""), False), (("a*b*c", "abc"), True), (("a*b*c", "aXbYc"), True), (("a*b*c", "acb"), False),
            (("src/*/test_?.py", "src/x/test_1.py"), True), (("src/*/test_?.py", "src/x/y/test_1.py"), False),
            (("src/**/test_?.py", "src/x/y/test_1.py"), True), (("*.PY", "a.py"), False), (("a.b", "a.b"), True), (("a.b", "axb"), False),
            (("[!]]x", "ax"), True), (("[!]]x", "]x"), False),
            (("[a-", "a"), VE), (("abc\\", "abc"), VE),
        ],
        "reference": r'''
import re

def glob_match(pattern, name):
    out = []
    i, n = 0, len(pattern)
    while i < n:
        c = pattern[i]
        if c == "\\":
            if i + 1 >= n:
                raise ValueError("trailing backslash")
            out.append(re.escape(pattern[i + 1]))
            i += 2
        elif c == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                out.append(".*")
                i += 2
            else:
                out.append("[^/]*")
                i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c == "[":
            j = i + 1
            negate = j < n and pattern[j] == "!"
            if negate:
                j += 1
            body_start = j
            if j < n and pattern[j] == "]":
                j += 1
            k = pattern.find("]", j)
            if k < 0:
                raise ValueError("unterminated bracket")
            body = pattern[body_start:k]
            cls = "".join("\\" + ch if ch in "\\]^[" else ch for ch in body)
            out.append("[" + ("^" if negate else "") + cls + "]")
            i = k + 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.fullmatch("".join(out), name, flags=re.S) is not None
''',
    },
    {
        "id": "t25_parse_ini",
        "func": "parse_ini",
        "spec": """Implement `parse_ini(text: str) -> dict[str, dict[str, str]]` that parses a simple INI document.
- The text is split into lines; a trailing `\\r` on a line is ignored. Blank lines, and lines whose first non-whitespace character is `;` or `#`, are comments and are skipped.
- A section header is `[name]` with optional surrounding whitespace; `name` is trimmed and must be non-empty. After the `]` only whitespace or a comment (`;`/`#`) may follow. Section names are case-sensitive. Keys that appear before any header belong to the section named `""` (empty string); this `""` section exists in the result only if at least one such key appears, so `[s]\\nk=v\\n` gives `{"s": {"k": "v"}}` with no `""` key.
- A key/value line is `key = value` where the split is on the FIRST `=`. Key and value are trimmed; the key must be non-empty; the value may be empty.
- If the trimmed value starts with a double quote, it is a quoted value: everything up to the next double quote is taken literally (no escapes, no trimming inside, `;` and `#` inside do not start a comment). After the closing quote only whitespace or a comment may follow. A missing closing quote is an error.
- Otherwise, an inline comment starts at a `;` or `#` that is preceded by a space or tab; the value is cut there and trimmed. A `;` or `#` not preceded by whitespace is part of the value (so `url = http://x/#frag` keeps `#frag`).
- Duplicate keys in a section: the last one wins. A section that appears twice is merged. A header with no keys still creates an empty section.
- Any other non-comment line (for example one without `=`) is an error.
- Raise `ValueError` for errors.""",
        "no_mutate": False,
        "tests": [
            (("a=1\nb = 2\n",), {"": {"a": "1", "b": "2"}}), (("[s]\nk=v\n",), {"s": {"k": "v"}}),
            (("[s]\nk = v ; note\n",), {"s": {"k": "v"}}), (("[s]\nurl = http://x/#frag\n",), {"s": {"url": "http://x/#frag"}}),
            (("[s]\nk = \"a ; b\"\n",), {"s": {"k": "a ; b"}}), (("[s]\nk = \"  x \" ; c\n",), {"s": {"k": "  x "}}),
            (("[s]\nk=\n",), {"s": {"k": ""}}), (("[s]\nk=1\nk=2\n",), {"s": {"k": "2"}}),
            (("[s]\na=1\n[t]\nb=2\n[s]\nc=3\n",), {"s": {"a": "1", "c": "3"}, "t": {"b": "2"}}),
            (("[ sec ]\nk=v\n",), {"sec": {"k": "v"}}), (("[s]\nk = a = b\n",), {"s": {"k": "a = b"}}),
            (("[s]\r\nk=v\r\n",), {"s": {"k": "v"}}), (("# c\n; d\n\n[s] ; x\nk=v\n",), {"s": {"k": "v"}}),
            (("[s]\n",), {"s": {}}), (("",), {}), (("[s]\nk = v\t# tab comment\n",), {"s": {"k": "v"}}),
            (("[S]\nk=1\n[s]\nk=2\n",), {"S": {"k": "1"}, "s": {"k": "2"}}),
            (("[s",), VE), (("[s]\njusttext\n",), VE), (("[s]\n= v\n",), VE), (("[]\nk=v\n",), VE),
            (("[s] junk\n",), VE), (("[s]\nk = \"abc\n",), VE), (("[s]\nk = \"abc\" junk\n",), VE),
        ],
        "reference": r'''
def parse_ini(text):
    result = {}
    section = ""

    def cut_inline(v):
        for i, ch in enumerate(v):
            if ch in ";#" and (i == 0 or v[i - 1] in " \t"):
                return v[:i].rstrip()
        return v

    for raw in text.splitlines():
        line = raw.rstrip("\r").strip()
        if not line or line[0] in ";#":
            continue
        if line[0] == "[":
            k = line.find("]")
            if k < 0:
                raise ValueError("unterminated section header")
            name = line[1:k].strip()
            rest = line[k + 1:].strip()
            if not name or (rest and rest[0] not in ";#"):
                raise ValueError("bad section header")
            section = name
            result.setdefault(section, {})
            continue
        if "=" not in line:
            raise ValueError("expected key = value")
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key:
            raise ValueError("empty key")
        if value.startswith('"'):
            k = value.find('"', 1)
            if k < 0:
                raise ValueError("unterminated quote")
            rest = value[k + 1:].strip()
            if rest and rest[0] not in ";#":
                raise ValueError("junk after closing quote")
            value = value[1:k]
        else:
            value = cut_inline(value)
        result.setdefault(section, {})[key] = value
    return result
''',
    },
    {
        "id": "t26_earliest_slot",
        "func": "earliest_slot",
        "spec": """Implement `earliest_slot(busy: list[tuple[int, int]], duration: int, start: int, end: int)` that finds the earliest free meeting slot.
- All times are integers (minutes since midnight). `busy` is a list of `(begin, finish)` intervals that are half-open: the minute `finish` itself is free. The list may be unsorted and intervals may overlap or touch each other.
- Return the smallest integer `t` such that `start <= t`, `t + duration <= end`, and the interval `[t, t + duration)` does not overlap any busy interval. Return `None` if no such `t` exists.
- Busy time before `start` or after `end` is irrelevant except where it overlaps the window.
- Do not modify the input list.
- Raise `ValueError` if `duration` is not a positive integer or if any busy interval has `begin >= finish`.""",
        "no_mutate": True,
        "tests": [
            (([], 30, 540, 1020), 540), (([(540, 600)], 30, 540, 1020), 600), (([(540, 600), (600, 660)], 30, 540, 1020), 660),
            (([(540, 990)], 30, 540, 1020), 990), (([(540, 1020)], 30, 540, 1020), None), (([], 120, 540, 600), None),
            (([(0, 60)], 30, 540, 600), 540), (([(500, 560)], 30, 540, 600), 560), (([(700, 760), (540, 600)], 60, 540, 1020), 600),
            (([(540, 600), (620, 700)], 30, 540, 1020), 700), (([(540, 620), (560, 700)], 30, 540, 1020), 700),
            (([(600, 700)], 30, 540, 1020), 540), (([(600, 700)], 60, 540, 1020), 540), (([(570, 700)], 30, 540, 1020), 540),
            (([(571, 700)], 31, 540, 1020), 540), (([(560, 700)], 30, 540, 1020), 700), (([(540, 600)], 60, 540, 660), 600),
            (([(540, 600)], 61, 540, 660), None),
            (([(540, 600)], 0, 540, 1020), VE), (([(600, 540)], 30, 540, 1020), VE), (([(600, 600)], 30, 540, 1020), VE),
        ],
        "reference": r'''
def earliest_slot(busy, duration, start, end):
    if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
        raise ValueError("duration must be a positive integer")
    intervals = []
    for begin, finish in busy:
        if begin >= finish:
            raise ValueError("bad interval")
        intervals.append((begin, finish))
    intervals.sort()
    t = start
    for begin, finish in intervals:
        if finish <= t:
            continue
        if begin >= t + duration:
            break
        t = max(t, finish)
    return t if t + duration <= end else None
''',
    },
    {
        "id": "t27_topo_sort",
        "func": "topo_sort",
        "spec": """Implement `topo_sort(deps: dict[str, list[str]]) -> list[str]` that orders items so that every item comes after all of its dependencies.
- `deps` maps an item to the list of items it depends on. Every item mentioned anywhere (as a key or inside a list) is part of the result exactly once. Dependency lists may contain duplicates, which are ignored.
- The order must be deterministic: build it step by step, and whenever more than one item has all of its dependencies already placed, place the lexicographically smallest one (plain string comparison) first.
- A self-dependency or any cycle raises `ValueError`.
- Do not modify the input.
- An empty dict gives `[]`.""",
        "no_mutate": True,
        "tests": [
            (({"b": ["a"]},), ["a", "b"]), (({"a": []},), ["a"]), (({"c": ["b"], "b": ["a"]},), ["a", "b", "c"]),
            (({"a": [], "b": [], "c": []},), ["a", "b", "c"]), (({"z": ["m"], "a": ["m"]},), ["m", "a", "z"]),
            (({"x": ["y", "y"]},), ["y", "x"]), (({},), []), (({"d": ["b", "c"], "c": ["a"], "b": ["a"]},), ["a", "b", "c", "d"]),
            (({"d": ["c"], "c": ["a"], "b": ["a"]},), ["a", "b", "c", "d"]), (({"b": ["a"], "c": ["a"], "a": ["z"]},), ["z", "a", "b", "c"]),
            (({"a": ["b"], "c": []},), ["b", "a", "c"]), (({"B": ["a"], "a": []},), ["a", "B"]),
            (({"x": ["b"], "y": ["a"]},), ["a", "b", "x", "y"]), (({"a": ["c"], "b": ["c"], "c": ["d"], "d": []},), ["d", "c", "a", "b"]),
            (({"b": ["a"], "a": ["b"]},), VE), (({"a": ["a"]},), VE), (({"a": ["b"], "b": ["c"], "c": ["a"], "d": []},), VE),
        ],
        "reference": r'''
import heapq

def topo_sort(deps):
    nodes = set(deps)
    for item, reqs in deps.items():
        for r in reqs:
            if r == item:
                raise ValueError("self-dependency: %r" % item)
            nodes.add(r)
    remaining = {n: 0 for n in nodes}
    dependents = {n: set() for n in nodes}
    for item, reqs in deps.items():
        for r in set(reqs):
            dependents[r].add(item)
            remaining[item] += 1
    ready = [n for n in nodes if remaining[n] == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        n = heapq.heappop(ready)
        order.append(n)
        for d in sorted(dependents[n]):
            remaining[d] -= 1
            if remaining[d] == 0:
                heapq.heappush(ready, d)
    if len(order) != len(nodes):
        raise ValueError("cycle detected")
    return order
''',
    },
    {
        "id": "t28_parse_url",
        "func": "parse_url",
        "spec": """Implement `parse_url(url: str) -> dict` that splits a URL into parts and returns a dict with exactly these keys: `scheme`, `userinfo`, `host`, `port`, `path`, `query`, `fragment`.
- The URL must start with a scheme followed by `://`. A scheme is a letter followed by letters, digits, `+`, `-` or `.`; it is returned lowercased.
- The authority is everything after `://` up to the first `/`, `?` or `#` (or the end). It must be non-empty.
- If the authority contains `@`, everything before the LAST `@` is `userinfo` (returned as is); otherwise `userinfo` is `""`.
- The host comes next. It is either an IPv6 literal in square brackets (returned WITHOUT the brackets) or a non-empty run of characters containing none of space, `/`, `?`, `#`, `@`, `:`, `[`, `]`. The host is returned lowercased.
- An optional `:port` follows the host. The port must be 1 to 5 ASCII digits with a value from 1 to 65535 and is returned as an `int`; when absent, `port` is `None`. A colon with nothing valid after it is an error.
- The rest of the string is split as follows: the first `#` starts the `fragment` (everything after it, which may itself contain `?`); before that, the first `?` starts the `query`. What remains is the `path` (which starts with `/` if present). `path`, `query` and `fragment` are `""` when absent; none of them is decoded or normalised.
- Raise `ValueError` for anything that violates the rules above.""",
        "no_mutate": False,
        "tests": [
            (("https://example.com",), {"scheme": "https", "userinfo": "", "host": "example.com", "port": None, "path": "", "query": "", "fragment": ""}),
            (("HTTP://Example.COM:8080/a/b?x=1&y=2#frag",), {"scheme": "http", "userinfo": "", "host": "example.com", "port": 8080, "path": "/a/b", "query": "x=1&y=2", "fragment": "frag"}),
            (("http://user:pw@host/p",), {"scheme": "http", "userinfo": "user:pw", "host": "host", "port": None, "path": "/p", "query": "", "fragment": ""}),
            (("http://[::1]:443/",), {"scheme": "http", "userinfo": "", "host": "::1", "port": 443, "path": "/", "query": "", "fragment": ""}),
            (("http://a.b/?q",), {"scheme": "http", "userinfo": "", "host": "a.b", "port": None, "path": "/", "query": "q", "fragment": ""}),
            (("http://a.b#f?x",), {"scheme": "http", "userinfo": "", "host": "a.b", "port": None, "path": "", "query": "", "fragment": "f?x"}),
            (("http://a.b/p#",), {"scheme": "http", "userinfo": "", "host": "a.b", "port": None, "path": "/p", "query": "", "fragment": ""}),
            (("http://a.b:65535",), {"scheme": "http", "userinfo": "", "host": "a.b", "port": 65535, "path": "", "query": "", "fragment": ""}),
            (("http://a@b@c/",), {"scheme": "http", "userinfo": "a@b", "host": "c", "port": None, "path": "/", "query": "", "fragment": ""}),
            (("git+ssh://Git@GitHub.com:22/o/r.git",), {"scheme": "git+ssh", "userinfo": "Git", "host": "github.com", "port": 22, "path": "/o/r.git", "query": "", "fragment": ""}),
            (("http://h/path with space?a b#c d",), {"scheme": "http", "userinfo": "", "host": "h", "port": None, "path": "/path with space", "query": "a b", "fragment": "c d"}),
            (("http://h?x=1",), {"scheme": "http", "userinfo": "", "host": "h", "port": None, "path": "", "query": "x=1", "fragment": ""}),
            (("example.com",), VE), (("http:/example.com",), VE), (("http://",), VE), (("http://host:99999",), VE),
            (("http://host:0",), VE), (("http://host:",), VE), (("http://host:abc",), VE), (("1http://host",), VE),
            (("http://ho st",), VE), (("http://[::1",), VE), (("http://@host/",), {"scheme": "http", "userinfo": "", "host": "host", "port": None, "path": "/", "query": "", "fragment": ""}),
        ],
        "reference": r'''
import re

def parse_url(url):
    m = re.match(r"([A-Za-z][A-Za-z0-9+.\-]*)://", url)
    if not m:
        raise ValueError("missing scheme")
    scheme = m.group(1).lower()
    rest = url[m.end():]
    cut = len(rest)
    for ch in "/?#":
        j = rest.find(ch)
        if 0 <= j < cut:
            cut = j
    authority, rest = rest[:cut], rest[cut:]
    if not authority:
        raise ValueError("empty authority")
    at = authority.rfind("@")
    userinfo = authority[:at] if at >= 0 else ""
    hostport = authority[at + 1:] if at >= 0 else authority
    if hostport.startswith("["):
        j = hostport.find("]")
        if j < 0:
            raise ValueError("unterminated IPv6 literal")
        host, portpart = hostport[1:j], hostport[j + 1:]
        if not host:
            raise ValueError("empty host")
    else:
        j = hostport.find(":")
        host, portpart = (hostport[:j], hostport[j:]) if j >= 0 else (hostport, "")
        if not host or re.search(r"[\s/?#@:\[\]]", host):
            raise ValueError("bad host")
    if portpart:
        if not portpart.startswith(":"):
            raise ValueError("unexpected text after host")
        digits = portpart[1:]
        if not re.fullmatch(r"\d{1,5}", digits) or not 1 <= int(digits) <= 65535:
            raise ValueError("bad port")
        port = int(digits)
    else:
        port = None
    fragment = ""
    h = rest.find("#")
    if h >= 0:
        fragment, rest = rest[h + 1:], rest[:h]
    query = ""
    q = rest.find("?")
    if q >= 0:
        query, rest = rest[q + 1:], rest[:q]
    return {"scheme": scheme, "userinfo": userinfo, "host": host.lower(), "port": port,
            "path": rest, "query": query, "fragment": fragment}
''',
    },
    {
        "id": "t29_next_cron",
        "func": "next_cron",
        "spec": """Implement `next_cron(expr: str, after: str) -> str` that returns the next time a cron expression fires.
- `expr` has exactly 5 whitespace-separated fields: minute (0-59), hour (0-23), day of month (1-31), month (1-12), day of week (0-6, where 0 is Sunday; 7 is NOT accepted). No names, no `?`, no `L` or `W`.
- Each field is a comma-separated list of items. An item is `*`, a single number, a range `a-b` (a <= b), or any of those followed by `/n` (n >= 1): `*/n` means every n-th value starting from the field's minimum, `a-b/n` means every n-th value from a to b, and `a/n` means every n-th value from a up to the field's maximum.
- Values outside the field's range, a malformed item, or a wrong number of fields raise `ValueError`.
- Day matching follows standard cron: if BOTH the day-of-month field and the day-of-week field are restricted (not `*`), a day matches when EITHER of them matches; if only one is restricted, that one must match; if neither is restricted every day matches.
- `after` is a naive local time formatted `YYYY-MM-DD HH:MM`. Return the earliest matching time that is strictly later than `after`, in the same format (seconds are not involved).
- If no matching time exists within 5 years after `after` (for example `0 0 31 2 *`), raise `ValueError`.""",
        "no_mutate": False,
        "tests": [
            (("* * * * *", "2026-10-15 12:30"), "2026-10-15 12:31"), (("0 9 * * *", "2026-10-15 09:00"), "2026-10-16 09:00"),
            (("0 9 * * 1-5", "2026-10-16 10:00"), "2026-10-19 09:00"), (("*/15 * * * *", "2026-01-01 00:00"), "2026-01-01 00:15"),
            (("0 0 1 * *", "2026-01-31 23:59"), "2026-02-01 00:00"), (("0 0 29 2 *", "2026-01-01 00:00"), "2028-02-29 00:00"),
            (("30 2 15 * 0", "2026-10-01 00:00"), "2026-10-04 02:30"), (("0 12 1-7 * 1", "2026-10-01 00:00"), "2026-10-01 12:00"),
            (("0 0 */10 * *", "2026-10-01 00:00"), "2026-10-11 00:00"), (("0 0 * * *", "2026-12-31 00:00"), "2027-01-01 00:00"),
            (("5/20 * * * *", "2026-03-01 00:06"), "2026-03-01 00:25"), (("1-5/2 8 * * *", "2026-03-01 08:03"), "2026-03-01 08:05"),
            (("0 0 * * 6", "2026-10-15 00:00"), "2026-10-17 00:00"), (("0 0 15 * *", "2026-10-15 00:00"), "2026-11-15 00:00"),
            (("0 0 * 2 *", "2026-10-15 00:00"), "2027-02-01 00:00"), (("59 23 31 12 *", "2026-12-31 23:59"), "2027-12-31 23:59"),
            (("5 4 * * 7", "2026-01-01 00:00"), VE), (("0 0 31 2 *", "2026-01-01 00:00"), VE), (("* * * *", "2026-01-01 00:00"), VE),
            (("60 * * * *", "2026-01-01 00:00"), VE), (("* * 0 * *", "2026-01-01 00:00"), VE), (("*/0 * * * *", "2026-01-01 00:00"), VE),
            (("5-1 * * * *", "2026-01-01 00:00"), VE),
        ],
        "reference": r'''
from datetime import datetime, timedelta

def next_cron(expr, after):
    fields = expr.split()
    if len(fields) != 5:
        raise ValueError("expected 5 fields")
    bounds = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]

    def parse_field(text, lo, hi):
        values = set()
        for item in text.split(","):
            step = 1
            has_step = "/" in item
            if has_step:
                item, step_text = item.split("/", 1)
                if not step_text.isdigit() or int(step_text) < 1:
                    raise ValueError("bad step")
                step = int(step_text)
            if item == "*":
                a, b = lo, hi
            elif "-" in item:
                x, y = item.split("-", 1)
                if not (x.isdigit() and y.isdigit()):
                    raise ValueError("bad range")
                a, b = int(x), int(y)
                if a > b:
                    raise ValueError("bad range")
            elif item.isdigit():
                a = int(item)
                b = hi if has_step else a
            else:
                raise ValueError("bad item")
            if a < lo or b > hi:
                raise ValueError("value out of range")
            values.update(range(a, b + 1, step))
        return values

    minutes, hours, doms, months, dows = [parse_field(f, lo, hi) for f, (lo, hi) in zip(fields, bounds)]
    dom_restricted, dow_restricted = fields[2] != "*", fields[4] != "*"
    t0 = datetime.strptime(after, "%Y-%m-%d %H:%M")
    earliest = t0 + timedelta(minutes=1)
    day = earliest.replace(hour=0, minute=0)
    limit = t0 + timedelta(days=366 * 5)
    hour_list, minute_list = sorted(hours), sorted(minutes)
    while day <= limit:
        if day.month in months:
            dom_ok = day.day in doms
            dow_ok = (day.weekday() + 1) % 7 in dows
            if dom_restricted and dow_restricted:
                day_ok = dom_ok or dow_ok
            elif dom_restricted:
                day_ok = dom_ok
            elif dow_restricted:
                day_ok = dow_ok
            else:
                day_ok = True
            if day_ok:
                for h in hour_list:
                    for m in minute_list:
                        candidate = day.replace(hour=h, minute=m)
                        if candidate >= earliest:
                            return candidate.strftime("%Y-%m-%d %H:%M")
        day += timedelta(days=1)
    raise ValueError("no match within 5 years")
''',
    },
    {
        "id": "t30_semver_satisfies",
        "func": "semver_satisfies",
        "spec": """Implement `semver_satisfies(version: str, constraint: str) -> bool` that checks a semantic version against a constraint, following Semantic Versioning 2.0 ordering and npm-style constraint rules.
- A version is `MAJOR.MINOR.PATCH` (non-negative integers without leading zeros), optionally followed by `-` and a pre-release tag (dot-separated identifiers made of ASCII letters, digits and hyphens; identifiers are non-empty; numeric identifiers have no leading zeros), optionally followed by `+` and build metadata, which is ignored for everything. `v1.2.3`, `1.2`, `1.02.3` and `1.2.3-` are invalid.
- Ordering: compare MAJOR, MINOR, PATCH numerically. A version with a pre-release tag is lower than the same version without one. Pre-release tags are compared identifier by identifier from the left: two numeric identifiers compare as numbers, two alphanumeric ones compare as ASCII strings, a numeric identifier is lower than an alphanumeric one, and if all compared identifiers are equal the shorter tag is lower. So `1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-alpha.beta < 1.0.0-beta.2 < 1.0.0-beta.11 < 1.0.0`.
- A constraint is one or more groups separated by `||`; the version satisfies the constraint if it satisfies at least one group. A group is one or more comparators separated by whitespace, all of which must hold. A comparator is an operator directly followed by a version: `=`, `>`, `>=`, `<`, `<=`, `^`, `~`; a bare version means `=`; a bare `*` means any version.
- `^X.Y.Z` means `>=X.Y.Z` and `<(X+1).0.0` when X > 0; when X is 0 and Y > 0 it means `>=0.Y.Z` and `<0.(Y+1).0`; when X and Y are both 0 it means `>=0.0.Z` and `<0.0.(Z+1)`. `~X.Y.Z` means `>=X.Y.Z` and `<X.(Y+1).0`.
- Pre-release rule: a version that has a pre-release tag can satisfy a group only if, besides the ordering checks, at least one comparator in that group was written with a pre-release tag on the same MAJOR.MINOR.PATCH. For example `1.0.0-alpha` does not satisfy `<1.0.0`, but it does satisfy `<1.0.0-beta`.
- An invalid version, an invalid comparator, or an empty constraint raises `ValueError`.""",
        "no_mutate": False,
        "tests": [
            (("1.2.3", ">=1.2.0 <2.0.0"), True), (("2.0.0", ">=1.2.0 <2.0.0"), False), (("1.2.3", "^1.2.0"), True),
            (("2.0.0", "^1.2.0"), False), (("0.2.5", "^0.2.3"), True), (("0.3.0", "^0.2.3"), False), (("0.0.4", "^0.0.3"), False),
            (("0.0.3", "^0.0.3"), True), (("1.2.9", "~1.2.3"), True), (("1.3.0", "~1.2.3"), False), (("1.0.0-alpha", "<1.0.0"), False),
            (("1.0.0-alpha", "<1.0.0-beta"), True), (("1.0.0-beta", "<1.0.0-alpha"), False), (("1.0.0-alpha.1", "<1.0.0-alpha.beta"), True),
            (("1.0.0-alpha.10", "<1.0.0-alpha.2"), False), (("1.0.0-beta.11", ">1.0.0-beta.2"), True), (("1.0.0", "=1.0.0"), True),
            (("1.0.0+build.7", "=1.0.0"), True), (("1.0.0", "1.0.0"), True), (("3.1.4", "<2.0.0 || =3.1.4"), True),
            (("2.5.0", "<2.0.0 || >=3.0.0"), False), (("9.9.9", "*"), True), (("1.0.0", ">1.0.0"), False), (("1.0.0", ">=1.0.0-rc.1"), True),
            (("1.0.0-rc.1", ">=1.0.0-rc.1 <2.0.0"), True), (("1.1.0-rc.1", ">=1.0.0-rc.1 <2.0.0"), False), (("10.0.0", ">9.0.0"), True),
            (("1.2", ">=1.0.0"), VE), (("v1.2.3", ">=1.0.0"), VE), (("1.02.3", ">=1.0.0"), VE), (("1.2.3-", ">=1.0.0"), VE),
            (("1.2.3", ">>1.0.0"), VE), (("1.2.3", ""), VE), (("1.2.3", ">=1.0"), VE),
        ],
        "reference": r'''
import re

_VERSION = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.\-]+))?(?:\+[0-9A-Za-z.\-]+)?$")

def _parse(text):
    m = _VERSION.match(text)
    if not m:
        raise ValueError("invalid version: %r" % text)
    ids = []
    if m.group(4) is not None:
        for part in m.group(4).split("."):
            if not part:
                raise ValueError("empty pre-release identifier")
            if part.isdigit():
                if len(part) > 1 and part[0] == "0":
                    raise ValueError("leading zero in numeric identifier")
                ids.append((0, int(part)))
            else:
                ids.append((1, part))
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), tuple(ids))

def _compare(a, b):
    if a[:3] != b[:3]:
        return -1 if a[:3] < b[:3] else 1
    pa, pb = a[3], b[3]
    if not pa and not pb:
        return 0
    if not pa:
        return 1
    if not pb:
        return -1
    for x, y in zip(pa, pb):
        if x == y:
            continue
        if x[0] != y[0]:
            return -1 if x[0] < y[0] else 1
        return -1 if x[1] < y[1] else 1
    return (len(pa) > len(pb)) - (len(pa) < len(pb))

def semver_satisfies(version, constraint):
    v = _parse(version)
    if not constraint.strip():
        raise ValueError("empty constraint")
    for group in constraint.split("||"):
        tokens = group.split()
        if not tokens:
            raise ValueError("empty comparator group")
        comparators = []
        for tok in tokens:
            if tok == "*":
                continue
            m = re.match(r"^(>=|<=|>|<|=|\^|~)?(.*)$", tok)
            op, ver = m.group(1) or "=", m.group(2)
            pv = _parse(ver)
            if op == "^":
                if pv[0] > 0:
                    upper = (pv[0] + 1, 0, 0, ())
                elif pv[1] > 0:
                    upper = (0, pv[1] + 1, 0, ())
                else:
                    upper = (0, 0, pv[2] + 1, ())
                comparators += [(">=", pv), ("<", upper)]
            elif op == "~":
                comparators += [(">=", pv), ("<", (pv[0], pv[1] + 1, 0, ()))]
            else:
                comparators.append((op, pv))
        ok = True
        for op, pv in comparators:
            c = _compare(v, pv)
            if (op == "=" and c != 0) or (op == ">" and c <= 0) or (op == ">=" and c < 0) \
                    or (op == "<" and c >= 0) or (op == "<=" and c > 0):
                ok = False
                break
        if ok and v[3] and not any(pv[3] and pv[:3] == v[:3] for _, pv in comparators):
            ok = False
        if ok:
            return True
    return False
''',
    },
]
