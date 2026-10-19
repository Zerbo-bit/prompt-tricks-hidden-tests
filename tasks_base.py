"""20 道带陷阱的小编程题。

每道题：
- spec：发给模型的需求（英文），所有会被隐藏测试检查的要求都明确写在里面；
- tests：模型看不到的隐藏测试，(参数, 期望结果)；
- reference：参考答案，只用来自检测试本身有没有写错，不会发给模型。
"""

VE = ("__raises__", "ValueError")

TASKS = [
    {
        "id": "t01_parse_duration",
        "func": "parse_duration",
        "spec": (
            "Implement `parse_duration(s: str) -> int` that converts a duration string to seconds.\n"
            "- The string consists of one or more parts. Each part is a non-negative decimal integer "
            "(ASCII digits 0-9) immediately followed by a unit letter: d (86400), h (3600), m (60), s (1).\n"
            "- Parts may be separated by any number of space characters (U+0020), including none. "
            "Leading and trailing spaces are allowed.\n"
            "- Units may appear in any order, but each unit may appear at most once.\n"
            "- Raise ValueError for: an empty or space-only string, an unknown unit, a number without a unit, "
            "a unit without a number, a space between a number and its unit, a repeated unit, "
            "or any other character (signs, decimal points, etc.)."
        ),
        "no_mutate": False,
        "tests": [
            (("1h30m",), 5400), (("45s",), 45), (("2d 3h",), 183600), (("30m1h",), 5400),
            (("  10s  ",), 10), (("0s",), 0), (("1h1h",), VE), (("",), VE), (("   ",), VE),
            (("90",), VE), (("h",), VE), (("1.5h",), VE), (("-5m",), VE), (("1h 30",), VE),
            (("1w",), VE), (("1 h",), VE),
        ],
        "reference": '''
import re
def parse_duration(s):
    units = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    t = s.strip(" ")
    if not t:
        raise ValueError("empty")
    pat = re.compile(r"([0-9]+)([dhms])")
    seen, total, pos = set(), 0, 0
    while pos < len(t):
        if t[pos] == " ":
            pos += 1
            continue
        m = pat.match(t, pos)
        if not m or m.group(2) in seen:
            raise ValueError("bad part")
        seen.add(m.group(2))
        total += int(m.group(1)) * units[m.group(2)]
        pos = m.end()
    return total
''',
    },
    {
        "id": "t02_roman_to_int",
        "func": "roman_to_int",
        "spec": (
            "Implement `roman_to_int(s: str) -> int` that converts a Roman numeral to an integer.\n"
            "- Accept only the canonical uppercase representation of a number from 1 to 3999.\n"
            "- Raise ValueError for anything else: the empty string, lowercase letters, and non-canonical "
            'forms such as "IIII", "IC", "VX", "IIV", "XXXX" or "MMMM".'
        ),
        "no_mutate": False,
        "tests": [
            (("III",), 3), (("IV",), 4), (("IX",), 9), (("LVIII",), 58), (("MCMXCIV",), 1994),
            (("MMMCMXCIX",), 3999), (("XLIX",), 49), (("IIII",), VE), (("IC",), VE), (("VX",), VE),
            (("",), VE), (("iv",), VE), (("MMMM",), VE), (("IIV",), VE), (("XXXX",), VE),
        ],
        "reference": '''
import re
def roman_to_int(s):
    if not s or not re.fullmatch(r"M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})", s):
        raise ValueError("not canonical")
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    for i, ch in enumerate(s):
        v = vals[ch]
        if i + 1 < len(s) and vals[s[i + 1]] > v:
            total -= v
        else:
            total += v
    return total
''',
    },
    {
        "id": "t03_merge_intervals",
        "func": "merge_intervals",
        "spec": (
            "Implement `merge_intervals(intervals)`.\n"
            "- `intervals` is a list of [start, end] pairs of integers describing closed intervals.\n"
            "- Merge intervals that overlap or share an endpoint: [1, 2] and [2, 3] become [1, 3].\n"
            "- Intervals that are only adjacent integers are NOT merged: [1, 2] and [3, 4] stay separate.\n"
            "- The input may be unsorted and may be empty.\n"
            "- Return a new list of [start, end] lists sorted by start.\n"
            "- Do not modify the input list or its inner lists.\n"
            "- Raise ValueError if any interval has start > end."
        ),
        "no_mutate": True,
        "tests": [
            (([[1, 3], [2, 6], [8, 10], [15, 18]],), [[1, 6], [8, 10], [15, 18]]),
            (([[1, 2], [2, 3]],), [[1, 3]]),
            (([[1, 2], [3, 4]],), [[1, 2], [3, 4]]),
            (([],), []),
            (([[5, 7], [1, 2], [2, 4]],), [[1, 4], [5, 7]]),
            (([[1, 10], [2, 3]],), [[1, 10]]),
            (([[3, 1]],), VE),
            (([[1, 1], [1, 1]],), [[1, 1]]),
        ],
        "reference": '''
def merge_intervals(intervals):
    items = []
    for a, b in intervals:
        if a > b:
            raise ValueError("start > end")
        items.append([a, b])
    items.sort()
    out = []
    for a, b in items:
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out
''',
    },
    {
        "id": "t04_format_bytes",
        "func": "format_bytes",
        "spec": (
            "Implement `format_bytes(n: int) -> str`.\n"
            '- If n < 1024, return "<n> B", for example "0 B" or "1023 B".\n'
            "- Otherwise use the units KiB, MiB, GiB, TiB (powers of 1024). Choose the largest unit for which "
            "the value is at least 1, and print the value with exactly one digit after the decimal point, "
            'for example "1.5 KiB".\n'
            "- Rounding is exact round-half-up on the true mathematical value: 1.25 becomes 1.3 and 2.25 becomes 2.3.\n"
            '- If rounding produces 1024.0, switch to the next unit and print "1.0" (1048575 bytes is "1.0 MiB"). '
            'TiB is the largest unit, so values of 1024 TiB and more stay in TiB (for example "1024.0 TiB").\n'
            "- Raise ValueError if n is negative."
        ),
        "no_mutate": False,
        "tests": [
            ((0,), "0 B"), ((1023,), "1023 B"), ((1024,), "1.0 KiB"), ((1536,), "1.5 KiB"),
            ((1126,), "1.1 KiB"), ((1280,), "1.3 KiB"), ((2304,), "2.3 KiB"), ((1792,), "1.8 KiB"),
            ((1048575,), "1.0 MiB"), ((1048576,), "1.0 MiB"), ((5 * 1024 ** 3,), "5.0 GiB"),
            ((1024 ** 4,), "1.0 TiB"), ((1024 ** 5,), "1024.0 TiB"), ((-1,), VE),
        ],
        "reference": '''
def format_bytes(n):
    if n < 0:
        raise ValueError("negative")
    if n < 1024:
        return f"{n} B"
    units = ["KiB", "MiB", "GiB", "TiB"]
    for i, name in enumerate(units):
        unit = 1024 ** (i + 1)
        tenths = (n * 20 + unit) // (2 * unit)
        if tenths < 10240 or i == len(units) - 1:
            return f"{tenths // 10}.{tenths % 10} {name}"
''',
    },
    {
        "id": "t05_days_between",
        "func": "days_between",
        "spec": (
            "Implement `days_between(a: str, b: str) -> int`.\n"
            "- Both arguments must be dates in the exact format YYYY-MM-DD: four ASCII digits, a hyphen, "
            "two ASCII digits, a hyphen, two ASCII digits, and nothing else (no surrounding whitespace, "
            "no trailing newline).\n"
            "- Return the absolute number of days between the two dates.\n"
            "- Raise ValueError if either string is not in that exact format or is not a real calendar date."
        ),
        "no_mutate": False,
        "tests": [
            (("2024-01-01", "2024-01-31"), 30), (("2024-03-01", "2024-02-28"), 2),
            (("2023-03-01", "2023-02-28"), 1), (("2024-05-05", "2024-05-05"), 0),
            (("1999-12-31", "2000-01-01"), 1), (("2023-02-29", "2023-03-01"), VE),
            (("2024-1-01", "2024-01-02"), VE), ((" 2024-01-01", "2024-01-02"), VE),
            (("2024-01-01\n", "2024-01-02"), VE), (("2024-13-01", "2024-01-01"), VE),
            (("20240101", "2024-01-02"), VE),
        ],
        "reference": '''
import re, datetime
def days_between(a, b):
    def parse(s):
        if not isinstance(s, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", s):
            raise ValueError("bad format")
        return datetime.date(int(s[:4]), int(s[5:7]), int(s[8:]))
    return abs((parse(a) - parse(b)).days)
''',
    },
    {
        "id": "t06_top_k_words",
        "func": "top_k_words",
        "spec": (
            "Implement `top_k_words(text: str, k: int)`.\n"
            "- A word is a maximal run of ASCII letters (a-z, A-Z). Every other character, including digits, "
            "apostrophes and non-ASCII letters, is a separator.\n"
            "- Counting is case-insensitive; words are returned in lowercase.\n"
            "- Sort by count descending; break ties alphabetically ascending.\n"
            "- Return the first k entries as a list of [word, count] pairs. If k is larger than the number "
            "of distinct words, return all of them. If k <= 0, return an empty list."
        ),
        "no_mutate": False,
        "tests": [
            (("The cat and the hat. THE end!", 2), [["the", 3], ["and", 1]]),
            (("b a b a c", 2), [["a", 2], ["b", 2]]),
            (("", 3), []), (("x", 0), []), (("x", -1), []),
            (("don't stop", 3), [["don", 1], ["stop", 1], ["t", 1]]),
            (("Ünïcode café cafe", 5), [["caf", 1], ["cafe", 1], ["code", 1], ["n", 1]]),
            (("a1b2a", 5), [["a", 2], ["b", 1]]),
        ],
        "reference": '''
import re
def top_k_words(text, k):
    if k <= 0:
        return []
    counts = {}
    for w in re.findall(r"[A-Za-z]+", text):
        w = w.lower()
        counts[w] = counts.get(w, 0) + 1
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [[w, c] for w, c in items[:k]]
''',
    },
    {
        "id": "t07_is_valid_ipv4",
        "func": "is_valid_ipv4",
        "spec": (
            "Implement `is_valid_ipv4(s: str) -> bool`.\n"
            '- A valid address has exactly four parts separated by ".".\n'
            "- Each part is 1 to 3 ASCII digits (0-9 only; other Unicode digits are invalid) with a value from 0 to 255.\n"
            '- A part must not have leading zeros unless the part is exactly "0".\n'
            "- No other characters are allowed anywhere: no signs, no whitespace, no trailing newline.\n"
            "- Return True or False; do not raise for any string input."
        ),
        "no_mutate": False,
        "tests": [
            (("192.168.1.1",), True), (("0.0.0.0",), True), (("255.255.255.255",), True),
            (("256.1.1.1",), False), (("1.2.3",), False), (("1.2.3.4.5",), False),
            (("01.2.3.4",), False), (("1.2.3.4 ",), False), (("1.2.3.-4",), False),
            (("1.2.3.+4",), False), (("١.٢.٣.٤",), False), (("1..3.4",), False),
            (("",), False), (("1.2.3.4\n",), False), (("00.0.0.0",), False), (("1.2.3.0004",), False),
        ],
        "reference": '''
import re
def is_valid_ipv4(s):
    parts = s.split(".")
    if len(parts) != 4:
        return False
    for p in parts:
        if not re.fullmatch(r"[0-9]{1,3}", p):
            return False
        if len(p) > 1 and p[0] == "0":
            return False
        if int(p) > 255:
            return False
    return True
''',
    },
    {
        "id": "t08_rle_decode",
        "func": "rle_decode",
        "spec": (
            "Implement `rle_decode(s: str) -> str` for a run-length encoding.\n"
            "- The input is a sequence of groups. Each group is a positive decimal count (ASCII digits, "
            "at least 1, no leading zeros) followed by exactly one character that is not an ASCII digit.\n"
            '- "3a2b1c" decodes to "aaabbc". The empty string decodes to the empty string.\n'
            "- Raise ValueError if a count is missing, a count is 0 or has a leading zero, the string ends "
            "with digits, or the total decoded length would exceed 10000 characters."
        ),
        "no_mutate": False,
        "tests": [
            (("3a2b1c",), "aaabbc"), (("",), ""), (("12x",), "x" * 12), (("1a1b",), "ab"),
            (("2 3b",), "  bbb"), (("10000a",), "a" * 10000), (("a",), VE), (("0a",), VE),
            (("03a",), VE), (("3",), VE), (("2a3",), VE), (("10001a",), VE), (("5000a5001b",), VE),
        ],
        "reference": '''
def rle_decode(s):
    out, total, i, n = [], 0, 0, len(s)
    while i < n:
        j = i
        while j < n and s[j] in "0123456789":
            j += 1
        if j == i or j == n:
            raise ValueError("bad group")
        num = s[i:j]
        if num[0] == "0":
            raise ValueError("bad count")
        count = int(num)
        total += count
        if total > 10000:
            raise ValueError("too long")
        out.append(s[j] * count)
        i = j + 1
    return "".join(out)
''',
    },
    {
        "id": "t09_leftmost_index",
        "func": "leftmost_index",
        "spec": (
            "Implement `leftmost_index(a, x) -> int`.\n"
            "- `a` is a list of integers sorted in non-decreasing order. It may contain duplicates and may be empty.\n"
            "- Return the smallest index i such that a[i] == x, or -1 if x is not in the list.\n"
            "- Use binary search."
        ),
        "no_mutate": True,
        "tests": [
            (([1, 2, 2, 2, 3], 2), 1), (([], 1), -1), (([1], 1), 0), (([1, 1, 1, 1], 1), 0),
            (([1, 3, 5], 4), -1), (([1, 3, 5], 0), -1), (([1, 3, 5], 6), -1), (([2, 2], 2), 0),
            (([1, 2, 3, 3], 3), 2),
        ],
        "reference": '''
import bisect
def leftmost_index(a, x):
    i = bisect.bisect_left(a, x)
    return i if i < len(a) and a[i] == x else -1
''',
    },
    {
        "id": "t10_normalize_path",
        "func": "normalize_path",
        "spec": (
            "Implement `normalize_path(p: str) -> str` for Unix-style paths.\n"
            '- Split the path on "/". Ignore empty components and ".".\n'
            '- ".." removes the previous component.\n'
            '- For an absolute path (starting with "/"), ".." at the root is ignored. Any number of leading '
            'slashes means the same root "/".\n'
            '- For a relative path, leading ".." components that cannot be resolved are kept.\n'
            '- The result has no trailing slash, except for the root itself, which is "/".\n'
            '- An empty relative result is ".". The empty input string returns ".".\n'
            '- A component such as "..." is an ordinary name.'
        ),
        "no_mutate": False,
        "tests": [
            (("/a/b/../c",), "/a/c"), (("/../a",), "/a"), (("a/../../b",), "../b"), (("a/..",), "."),
            (("",), "."), (("/",), "/"), (("//a//b/",), "/a/b"), (("./a/./b",), "a/b"),
            (("../../a",), "../../a"), (("a/b/../../..",), ".."), (("/a/..",), "/"), (("...",), "..."),
            (("/.../..",), "/"), (("a/../b/",), "b"),
        ],
        "reference": '''
def normalize_path(p):
    absolute = p.startswith("/")
    stack = []
    for part in p.split("/"):
        if part == "" or part == ".":
            continue
        if part == "..":
            if stack and stack[-1] != "..":
                stack.pop()
            elif not absolute:
                stack.append("..")
        else:
            stack.append(part)
    if absolute:
        return "/" + "/".join(stack)
    return "/".join(stack) if stack else "."
''',
    },
    {
        "id": "t11_add_months",
        "func": "add_months",
        "spec": (
            "Implement `add_months(date_str: str, n: int) -> str`.\n"
            "- `date_str` is a valid date in the format YYYY-MM-DD. `n` is an integer and may be negative or zero.\n"
            "- Add n calendar months. If the resulting month has fewer days than the original day of month, "
            "clamp to the last day of that month (2024-01-31 plus 1 month is 2024-02-29).\n"
            "- Return the result in the format YYYY-MM-DD."
        ),
        "no_mutate": False,
        "tests": [
            (("2024-01-31", 1), "2024-02-29"), (("2023-01-31", 1), "2023-02-28"),
            (("2024-03-31", -1), "2024-02-29"), (("2024-12-15", 1), "2025-01-15"),
            (("2024-01-15", -1), "2023-12-15"), (("2024-01-31", 13), "2025-02-28"),
            (("2024-05-31", 0), "2024-05-31"), (("2024-01-31", -14), "2022-11-30"),
            (("2000-02-29", 12), "2001-02-28"), (("2000-02-29", 48), "2004-02-29"),
            (("1900-01-31", 1), "1900-02-28"),
        ],
        "reference": '''
import calendar
def add_months(date_str, n):
    y, m, d = int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10])
    y2, m2 = divmod(y * 12 + (m - 1) + n, 12)
    m2 += 1
    d2 = min(d, calendar.monthrange(y2, m2)[1])
    return f"{y2:04d}-{m2:02d}-{d2:02d}"
''',
    },
    {
        "id": "t12_parse_csv_line",
        "func": "parse_csv_line",
        "spec": (
            "Implement `parse_csv_line(line: str)` that splits one CSV line (no newline characters) into a list of strings.\n"
            "- Fields are separated by commas. An empty line is one empty field.\n"
            "- An unquoted field is taken literally, may be empty, and must not contain a double quote. "
            "Whitespace is preserved.\n"
            '- A quoted field starts with a double quote as the very first character of the field and ends '
            "with a double quote that is immediately followed by a comma or the end of the line. Inside a "
            'quoted field, two double quotes ("") represent one double quote, and commas are literal.\n'
            "- Raise ValueError if a double quote appears inside an unquoted field (this includes a field "
            "that has any character, even a space, before its opening quote), if a quoted field is not "
            "terminated, or if any character other than a comma follows the closing quote."
        ),
        "no_mutate": False,
        "tests": [
            (("a,b,c",), ["a", "b", "c"]), (("",), [""]), (("a,,c",), ["a", "", "c"]),
            (('a,"b,c",d',), ["a", "b,c", "d"]), (('a,"b""c",',), ["a", 'b"c', ""]),
            (('"",x',), ["", "x"]), ((" a , b ",), [" a ", " b "]), ((",",), ["", ""]),
            (('"a""",""""',), ['a"', '"']), (('a,"b',), VE), (('a,"b"c',), VE), (('a,b"c',), VE),
            ((' "a"',), VE),
        ],
        "reference": '''
def parse_csv_line(line):
    fields, i, n = [], 0, len(line)
    while True:
        if i < n and line[i] == '"':
            i += 1
            buf = []
            while True:
                if i >= n:
                    raise ValueError("unterminated")
                if line[i] == '"':
                    if i + 1 < n and line[i + 1] == '"':
                        buf.append('"')
                        i += 2
                    else:
                        i += 1
                        break
                else:
                    buf.append(line[i])
                    i += 1
            if i < n and line[i] != ",":
                raise ValueError("text after quote")
            fields.append("".join(buf))
        else:
            j = line.find(",", i)
            if j == -1:
                j = n
            field = line[i:j]
            if '"' in field:
                raise ValueError("quote in unquoted field")
            fields.append(field)
            i = j
        if i >= n:
            break
        i += 1
        if i == n:
            fields.append("")
            break
    return fields
''',
    },
    {
        "id": "t13_round_half_up",
        "func": "round_half_up",
        "spec": (
            "Implement `round_half_up(x: str, ndigits: int) -> str` for exact decimal rounding.\n"
            '- `x` is a decimal number written as: an optional leading "-", one or more ASCII digits, and '
            'optionally a "." followed by one or more ASCII digits. Examples: "2.675", "-0.5", "10".\n'
            "- Round to `ndigits` digits after the decimal point. Ties are rounded away from zero "
            '("2.675" with 2 digits is "2.68"; "-2.5" with 0 digits is "-3"). The rounding must be exact '
            "decimal arithmetic, not binary floating point.\n"
            "- Return a string with exactly `ndigits` digits after the decimal point, and no decimal point "
            'when ndigits is 0 ("10" with 2 digits is "10.00").\n'
            '- Never return a negative zero: "-0.004" with 2 digits is "0.00".\n'
            '- Raise ValueError if `x` is not in the format above (for example "1e3", ".5", "1.", "+1.5") '
            "or if ndigits is negative."
        ),
        "no_mutate": False,
        "tests": [
            (("2.675", 2), "2.68"), (("2.665", 2), "2.67"), (("1.005", 2), "1.01"), (("0.5", 0), "1"),
            (("1.5", 0), "2"), (("2.5", 0), "3"), (("-0.5", 0), "-1"), (("-2.5", 0), "-3"),
            (("10", 2), "10.00"), (("-0.004", 2), "0.00"), (("0.125", 2), "0.13"),
            (("999.995", 2), "1000.00"), (("0.045", 2), "0.05"), (("-0.0", 1), "0.0"),
            (("1e3", 1), VE), (("abc", 1), VE), (("1.", 1), VE), ((".5", 1), VE),
            (("1.2", -1), VE), (("+1.5", 0), VE),
        ],
        "reference": '''
import re
from decimal import Decimal, ROUND_HALF_UP
def round_half_up(x, ndigits):
    if ndigits < 0:
        raise ValueError("negative ndigits")
    if not re.fullmatch(r"-?[0-9]+(\\.[0-9]+)?", x):
        raise ValueError("bad number")
    q = Decimal(x).quantize(Decimal(1).scaleb(-ndigits), rounding=ROUND_HALF_UP)
    if q == 0:
        q = abs(q)
    return format(q, "f")
''',
    },
    {
        "id": "t14_wrap_text",
        "func": "wrap_text",
        "spec": (
            "Implement `wrap_text(text: str, width: int)` that returns a list of lines.\n"
            "- Words are runs of characters separated by one or more space characters (U+0020 only).\n"
            "- Wrap greedily: each line holds as many words as fit, joined by single spaces, with length at most `width`.\n"
            "- A word longer than `width` always starts on a new line and is split into consecutive pieces of "
            "exactly `width` characters. Its last piece (which may be shorter) starts a line that can continue "
            "with the following words if they fit.\n"
            "- Lines have no leading or trailing spaces. Empty or space-only text returns an empty list.\n"
            "- Raise ValueError if width < 1."
        ),
        "no_mutate": False,
        "tests": [
            (("the quick brown fox", 10), ["the quick", "brown fox"]), (("a  b   c", 3), ["a b", "c"]),
            (("", 5), []), (("   ", 5), []), (("abcdefgh", 3), ["abc", "def", "gh"]),
            (("hi abcdefgh yo", 3), ["hi", "abc", "def", "gh", "yo"]),
            (("hi abcdefg x", 3), ["hi", "abc", "def", "g x"]), (("abc def", 3), ["abc", "def"]),
            (("abc def", 7), ["abc def"]), (("ab cd", 2), ["ab", "cd"]),
            (("a bcdef", 3), ["a", "bcd", "ef"]), (("abcdef", 3), ["abc", "def"]), (("x", 0), VE),
        ],
        "reference": '''
def wrap_text(text, width):
    if width < 1:
        raise ValueError("width")
    lines, cur = [], ""
    for word in [w for w in text.split(" ") if w]:
        if len(word) > width:
            if cur:
                lines.append(cur)
                cur = ""
            while len(word) > width:
                lines.append(word[:width])
                word = word[width:]
            cur = word
        elif not cur:
            cur = word
        elif len(cur) + 1 + len(word) <= width:
            cur += " " + word
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines
''',
    },
    {
        "id": "t15_first_bracket_error",
        "func": "first_bracket_error",
        "spec": (
            "Implement `first_bracket_error(s: str) -> int` for the brackets ( ) [ ] { }. All other characters are ignored.\n"
            "- Scan left to right. Return the index of the first closing bracket that does not match the "
            "most recent unclosed opening bracket, or that has no opening bracket at all.\n"
            "- If there is no such closing bracket but some opening brackets are still unclosed at the end, "
            "return the index of the leftmost opening bracket that is still unclosed.\n"
            "- If the brackets are balanced, return -1."
        ),
        "no_mutate": False,
        "tests": [
            (("()",), -1), (("",), -1), (("a(b)c",), -1), (("{[()]}",), -1), (("(]",), 1),
            (("([)]",), 2), (("(((",), 0), (("(()",), 0), (("()(",), 2), ((")",), 0),
            (("x)y(",), 1), (("(a[b]",), 0), (("[(])",), 2), (("(()(",), 0),
        ],
        "reference": '''
def first_bracket_error(s):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for i, ch in enumerate(s):
        if ch in "([{":
            stack.append((ch, i))
        elif ch in pairs:
            if not stack or stack[-1][0] != pairs[ch]:
                return i
            stack.pop()
    return stack[0][1] if stack else -1
''',
    },
    {
        "id": "t16_dedupe_keep_order",
        "func": "dedupe_keep_order",
        "spec": (
            "Implement `dedupe_keep_order(items)`.\n"
            "- Return a new list with duplicates removed, keeping the first occurrence of each item and the original order.\n"
            "- Two items are duplicates when they compare equal with ==. Note that 1, 1.0 and True are equal under ==.\n"
            "- Items may be unhashable (for example lists or dicts).\n"
            "- Do not modify the input list."
        ),
        "no_mutate": True,
        "tests": [
            (([1, 2, 1, 3, 2],), [1, 2, 3]), (([],), []), (([[1], [1], [2]],), [[1], [2]]),
            (([{"a": 1}, {"a": 1}],), [{"a": 1}]), (([1, 1.0, True, 2],), [1, 2]),
            ((["a", "A", "a"],), ["a", "A"]), (([[1, 2], (1, 2)],), [[1, 2], (1, 2)]),
            (([0, False, 0.0, ""],), [0, ""]),
        ],
        "reference": '''
def dedupe_keep_order(items):
    out = []
    for x in items:
        if not any(x == y for y in out):
            out.append(x)
    return out
''',
    },
    {
        "id": "t17_compare_versions",
        "func": "compare_versions",
        "spec": (
            "Implement `compare_versions(a: str, b: str) -> int` returning -1, 0 or 1.\n"
            '- A version is one or more dot-separated parts of ASCII digits (leading zeros allowed, compared '
            'numerically), optionally followed by "-" and a tag of one or more ASCII letters or digits. '
            'Examples: "1.2.10", "1.0-rc1".\n'
            '- Compare the numeric parts first. Missing parts count as zero, so "1.0" equals "1".\n'
            "- If the numeric parts are equal: a version with a tag is lower than the same version without a tag; "
            "two tags are compared as plain strings; equal tags (or no tags) mean the versions are equal.\n"
            "- Raise ValueError if either argument is not a valid version (empty string, empty part, "
            "non-digit part, empty tag)."
        ),
        "no_mutate": False,
        "tests": [
            (("1.2.10", "1.2.9"), 1), (("1.0", "1"), 0), (("1.0.0", "1.0.1"), -1), (("2", "10"), -1),
            (("1.0-rc1", "1.0"), -1), (("1.0-rc1", "1.0-rc2"), -1), (("1.0-beta", "1.0-alpha"), 1),
            (("1.0.0-x", "1-x"), 0), (("01.2", "1.2"), 0), (("1.2-rc1", "1.3-alpha"), -1),
            (("1.0", "1.0-rc1"), 1), (("1..2", "1"), VE), (("", "1"), VE), (("1.a", "1"), VE),
            (("1.0-", "1.0"), VE),
        ],
        "reference": '''
import re
def compare_versions(a, b):
    def parse(v):
        m = re.fullmatch(r"([0-9]+(?:\\.[0-9]+)*)(?:-([0-9A-Za-z]+))?", v)
        if not m:
            raise ValueError("bad version")
        nums = [int(x) for x in m.group(1).split(".")]
        while len(nums) > 1 and nums[-1] == 0:
            nums.pop()
        return nums, m.group(2)
    na, ta = parse(a)
    nb, tb = parse(b)
    if na != nb:
        return -1 if na < nb else 1
    if ta == tb:
        return 0
    if ta is None:
        return 1
    if tb is None:
        return -1
    return -1 if ta < tb else 1
''',
    },
    {
        "id": "t18_flatten",
        "func": "flatten",
        "spec": (
            "Implement `flatten(nested, depth=None)`.\n"
            "- `nested` is a list. Flatten nested lists up to `depth` levels. depth=None flattens completely; "
            "depth=0 returns a shallow copy of the top-level list.\n"
            "- Only objects whose type is exactly `list` are flattened. Tuples, strings, dicts and everything "
            "else are kept as single items.\n"
            "- Return a new list and do not modify the input.\n"
            "- Raise ValueError if depth is negative."
        ),
        "no_mutate": True,
        "tests": [
            (([1, [2, [3, [4]]]], None), [1, 2, 3, 4]), (([1, [2, [3, [4]]]], 1), [1, 2, [3, [4]]]),
            (([1, [2, [3, [4]]]], 0), [1, [2, [3, [4]]]]), (([], None), []),
            ((["ab", ["cd"]], None), ["ab", "cd"]), (([(1, [2]), [3]], None), [(1, [2]), 3]),
            (([[[]]], None), []), (([[1, [2]], [3]], 2), [1, 2, 3]), (([[], [[]]], 1), [[]]),
            (([1, [2]], -1), VE),
        ],
        "reference": '''
def flatten(nested, depth=None):
    if depth is not None and depth < 0:
        raise ValueError("depth")
    out = []
    for x in nested:
        if type(x) is list and (depth is None or depth > 0):
            out.extend(flatten(x, None if depth is None else depth - 1))
        else:
            out.append(x)
    return out
''',
    },
    {
        "id": "t19_next_weekday",
        "func": "next_weekday",
        "spec": (
            "Implement `next_weekday(date_str: str, weekday: int) -> str`.\n"
            "- `date_str` is a valid date in the format YYYY-MM-DD. `weekday` uses 0 for Monday through 6 for Sunday.\n"
            "- Return the first date strictly after `date_str` that falls on `weekday`, in the format YYYY-MM-DD. "
            "If `date_str` itself falls on that weekday, the answer is 7 days later.\n"
            "- Raise ValueError if weekday is not in the range 0 to 6."
        ),
        "no_mutate": False,
        "tests": [
            (("2024-01-01", 0), "2024-01-08"), (("2024-01-01", 1), "2024-01-02"),
            (("2024-01-01", 6), "2024-01-07"), (("2024-02-28", 3), "2024-02-29"),
            (("2024-02-29", 4), "2024-03-01"), (("2023-12-31", 0), "2024-01-01"),
            (("2024-01-07", 6), "2024-01-14"), (("2024-01-01", 7), VE), (("2024-01-01", -1), VE),
        ],
        "reference": '''
import datetime
def next_weekday(date_str, weekday):
    if not 0 <= weekday <= 6:
        raise ValueError("weekday")
    d = datetime.date(int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10]))
    delta = (weekday - d.weekday() - 1) % 7 + 1
    return (d + datetime.timedelta(days=delta)).isoformat()
''',
    },
    {
        "id": "t20_mask_email",
        "func": "mask_email",
        "spec": (
            "Implement `mask_email(s: str) -> str`.\n"
            '- The string must contain exactly one "@" with a non-empty local part before it and a non-empty '
            "domain after it; otherwise raise ValueError.\n"
            '- Mask the local part with "*": keep its first and last characters and replace every character '
            'between them with "*" ("john" becomes "j**n").\n'
            '- A local part of length 1 becomes "*". A local part of length 2 keeps its first character and '
            'masks the second ("ab" becomes "a*").\n'
            "- The domain is returned unchanged."
        ),
        "no_mutate": False,
        "tests": [
            (("john@example.com",), "j**n@example.com"), (("ab@x.io",), "a*@x.io"), (("a@x.io",), "*@x.io"),
            (("abc@x",), "a*c@x"), (("alice.smith@mail.ru",), "a*********h@mail.ru"),
            (("no-at",), VE), (("a@@b",), VE), (("@x.io",), VE), (("a@",), VE), (("a@b@c",), VE),
        ],
        "reference": '''
def mask_email(s):
    if s.count("@") != 1:
        raise ValueError("need exactly one @")
    local, domain = s.split("@")
    if not local or not domain:
        raise ValueError("empty part")
    n = len(local)
    if n == 1:
        masked = "*"
    elif n == 2:
        masked = local[0] + "*"
    else:
        masked = local[0] + "*" * (n - 2) + local[-1]
    return masked + "@" + domain
''',
    },
]
