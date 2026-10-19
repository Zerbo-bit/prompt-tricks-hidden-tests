#!/usr/bin/env python3
"""实测：流行的编码提示词技巧，哪些真的让代码更能通过隐藏测试。

在同一批题（30 道）、同一套隐藏测试上，只改提示词里的一句话，比较通过率、自评、输出长度。

用法：
    python3 run.py selftest                        # 自检：参考答案必须全部通过隐藏测试（不联网）
    python3 run.py variants                        # 列出所有提示词变体和它们的原文
    python3 run.py setkey                          # 保存密钥（先在控制台复制密钥再运行）
    python3 run.py ping --models A,B               # 每个模型发一句话，看通不通
    python3 run.py run --models A,B --runs 3       # 正式运行（默认跑全部变体）
    python3 run.py run --models A --runs 1 --limit-tasks 1 --variants baseline,doublecheck   # 试跑
    python3 run.py report results/<目录>            # 重新生成汇总

接口密钥用 `python3 run.py setkey` 保存到本机私有文件 ~/.llm_api_key（或用环境变量 LLM_API_KEY），
不会打印，也不会写进结果文件。用完后 `python3 run.py delkey` 删除。
"""
import argparse
import concurrent.futures
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from math import comb
from pathlib import Path

from tasks import TASKS

HERE = Path(__file__).resolve().parent
DEFAULT_BASE = "https://api.example.com/v1"  # 把这里换成你自己的 OpenAI 兼容接口地址 / replace with your OpenAI-compatible endpoint
SHUFFLE_SEED = 20261015

# 基线提示词，和上一篇完全一样。每个变体只在它前面加一句，或者在拿到回答后追问一句。
PROMPT = """Write a Python function. Target: Python 3.9, standard library only.

{spec}

Reply with exactly one Python code block containing the complete solution (imports included).
After the code block, write one final line, exactly one of:
CONFIDENCE: SURE
CONFIDENCE: UNSURE
Write SURE only if you are certain the function meets every requirement above and would pass strict hidden tests that cover all of them."""

VARIANTS = {
    "baseline": {
        "label": "基线（不加任何技巧）",
        "prefix": "",
        "followup": None,
    },
    "role": {
        "label": "角色设定：资深工程师",
        "prefix": "You are a senior Python engineer with 15 years of experience, known for writing bug-free, production-grade code.\n\n",
        "followup": None,
    },
    "stepbystep": {
        "label": "先一步步思考",
        "prefix": "Before writing any code, think step by step: list the requirements and the edge cases, then write the code.\n\n",
        "followup": None,
    },
    "stakes": {
        "label": "施压：上生产、会被开除",
        "prefix": "This code goes straight to production today. If it has a bug, I will lose my job. Please be extremely careful.\n\n",
        "followup": None,
    },
    "testsfirst": {
        "label": "先写测试再写实现",
        "prefix": "Use test-driven development: first write unit tests that cover the requirements and the edge cases, then write the implementation that passes them. Put the tests in their own code block and the final implementation in a separate, final code block.\n\n",
        "followup": None,
    },
    "codeonly": {
        "label": "只要代码，不要解释",
        "prefix": "Reply with code only. Do not explain anything: no text before or after the code block, except the CONFIDENCE line required below.\n\n",
        "followup": None,
    },
    "doublecheck": {
        "label": "追问：你确定吗？再检查一遍",
        "prefix": "",
        "followup": "Are you sure? Double-check your code against every requirement and edge case in the task. If you find any problem, reply with the corrected complete solution in one Python code block; if you find none, say so and do not repeat the code. Then write the CONFIDENCE line again.",
    },
}
VARIANT_ORDER = list(VARIANTS)

# 在独立子进程里执行模型写的代码并跑隐藏测试。子进程拿不到密钥，工作目录是临时目录。
CHILD = r'''
import ast, copy, json, sys
payload = ast.literal_eval(sys.stdin.read())

def norm(v):
    if isinstance(v, (list, tuple)):
        return [norm(x) for x in v]
    if isinstance(v, dict):
        return {k: norm(x) for k, x in v.items()}
    return v

results = []
try:
    ns = {}
    source = payload["code"]
    if "from __future__" not in source:
        # 让 3.10+ 写法的类型标注（如 int | None）在 3.9 上也能加载，避免因为标注误判成失败
        source = "from __future__ import annotations\n" + source
    exec(compile(source, "<candidate>", "exec"), ns)
    fn = ns[payload["func"]]
except BaseException as e:
    print(json.dumps({"load_error": type(e).__name__ + ": " + str(e)[:200]}))
    sys.exit(0)

for args, expected in payload["tests"]:
    call_args = copy.deepcopy(args)
    item = {"ok": False}
    wants_raise = isinstance(expected, tuple) and len(expected) == 2 and expected[0] == "__raises__"
    try:
        got = fn(*call_args)
        if wants_raise:
            item["why"] = "expected " + expected[1] + ", returned " + repr(got)[:120]
        elif norm(got) != norm(expected) or type(got) is bool and type(expected) is not bool:
            item["why"] = "returned " + repr(got)[:160]
        elif payload["no_mutate"] and call_args != args:
            item["why"] = "mutated its input"
        else:
            item["ok"] = True
    except BaseException as e:
        if wants_raise and type(e).__name__ == expected[1]:
            item["ok"] = True
        else:
            item["why"] = "raised " + type(e).__name__ + ": " + str(e)[:120]
    results.append(item)
print(json.dumps({"results": results}))
'''


def run_hidden_tests(task, code, timeout=30):
    payload = repr({"code": code, "func": task["func"], "tests": task["tests"], "no_mutate": task["no_mutate"]})
    with tempfile.TemporaryDirectory() as tmp:
        child = Path(tmp) / "child.py"
        child.write_text(CHILD, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(child)], input=payload, text=True, capture_output=True,
                timeout=timeout, cwd=tmp, env={"PATH": os.environ.get("PATH", "")},
            )
        except subprocess.TimeoutExpired:
            return {"passed": False, "failed_cases": [], "detail": "timeout"}
    try:
        out = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"passed": False, "failed_cases": [], "detail": "crashed: " + proc.stderr.strip()[-200:]}
    if "load_error" in out:
        return {"passed": False, "failed_cases": [], "detail": "load_error: " + out["load_error"]}
    failed = [
        {"case": i, "args": repr(task["tests"][i][0])[:120], "why": r.get("why", "")}
        for i, r in enumerate(out["results"]) if not r["ok"]
    ]
    return {"passed": not failed, "failed_cases": failed, "detail": ""}


def extract_code(text, func):
    """取回答里定义了目标函数的最后一个代码块（「先写测试」变体会先给测试块，实现在后面）。"""
    blocks = re.findall(r"```(?:python|py|Python)?[ \t]*\n(.*?)```", text or "", flags=re.S)
    with_def = [b for b in blocks if re.search(r"def\s+" + re.escape(func) + r"\s*\(", b)]
    if with_def:
        return with_def[-1]
    return blocks[-1] if blocks else None


def extract_confidence(text):
    found = re.findall(r"CONFIDENCE:\s*(SURE|UNSURE)\b", text or "", flags=re.I)
    return found[-1].upper() if found else "MISSING"


STREAM_MODELS = set()   # 普通方式拿不到完整响应的模型，记下来，之后直接用流式方式调用
LIMIT_PARAM = {}        # 每个模型接受哪种「输出上限」参数名
MAX_OUTPUT_TOKENS = 32000  # 给足输出额度，避免带思考过程的模型把额度用光、正文被截断。正式跑第一遍是 16000，补跑无效记录时提高到 32000


class Incomplete(Exception):
    """响应没有正常结束（被截断、连接中断）。"""


def _open(base, key, payload, timeout):
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
    )
    return urllib.request.urlopen(req, timeout=timeout)


def _post(base, key, model, payload, timeout):
    """带上输出上限参数发送请求；参数名不被接受时依次换另一种写法。"""
    names = [LIMIT_PARAM[model]] if model in LIMIT_PARAM else ["max_tokens", "max_completion_tokens", None]
    for i, name in enumerate(names):
        body = dict(payload)
        if name:
            body[name] = MAX_OUTPUT_TOKENS
        try:
            resp = _open(base, key, body, timeout)
            LIMIT_PARAM[model] = name
            return resp
        except urllib.error.HTTPError as e:
            if e.code != 400 or i == len(names) - 1:
                raise


def _call_plain(base, key, model, messages, timeout):
    payload = {"model": model, "messages": messages}
    with _post(base, key, model, payload, timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    choice = (data.get("choices") or [{}])[0]
    return (choice.get("message") or {}).get("content") or "", data.get("usage") or {}, choice.get("finish_reason")


def _call_stream(base, key, model, messages, timeout):
    """流式调用：一行行读，读到结束标记就停，不依赖服务端正确关闭连接。"""
    payload = {"model": model, "messages": messages, "stream": True, "stream_options": {"include_usage": True}}
    try:
        resp = _post(base, key, model, payload, timeout)
    except urllib.error.HTTPError as e:
        if e.code != 400:
            raise
        payload.pop("stream_options")
        resp = _post(base, key, model, payload, timeout)
    parts, usage, finish, done, deadline = [], {}, None, False, time.monotonic() + timeout
    with resp:
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError("stream exceeded %ss" % timeout)
            line = resp.readline()
            if not line:
                break
            line = line.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if chunk == "[DONE]":
                done = True
                break
            try:
                obj = json.loads(chunk)
            except ValueError:
                continue
            if obj.get("usage"):
                usage = obj["usage"]
            choice = (obj.get("choices") or [{}])[0]
            finish = choice.get("finish_reason") or finish
            parts.append((choice.get("delta") or {}).get("content") or (choice.get("message") or {}).get("content") or "")
    if not finish and not done:
        raise Incomplete("stream ended early after %d chars" % len("".join(parts)))
    return "".join(parts), usage, finish or "stop"


def call_api(base, key, model, messages, timeout=180):
    last, soft_failures = "", 0
    for wait in [0, 3, 10, 30, 60]:
        if soft_failures >= 4:
            break
        if wait:
            time.sleep(wait)
        began = time.monotonic()
        mode = "stream" if model in STREAM_MODELS else "plain"
        try:
            content, usage, finish = (_call_stream if mode == "stream" else _call_plain)(base, key, model, messages, timeout)
            return {"text": content, "seconds": round(time.monotonic() - began, 2), "mode": mode, "finish": finish or "stop",
                    "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens")}
        except urllib.error.HTTPError as e:
            last = "HTTP %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:200])
            if e.code not in (408, 409, 429) and e.code < 500:
                break
        except Exception as e:  # 响应不完整、超时等：改用流式方式再试
            last = type(e).__name__ + ": " + str(e)[:200]
            soft_failures += 1
            STREAM_MODELS.add(model)
    return {"api_error": last}


def is_complete(rec):
    """这条记录是不是一次完整、可以计入统计的回答（追问变体要求两轮都完整）。"""
    if rec.get("api_error"):
        return False
    if rec.get("finish") == "length" or rec.get("first_finish") == "length":
        return False
    return True


KEY_FILE = Path.home() / ".llm_api_key"


def looks_like_key(k):
    return k.startswith("sk-") and k.isascii() and 20 <= len(k) <= 200 and not any(c.isspace() for c in k)


def need_key():
    key = os.environ.get("LLM_API_KEY", "").strip()
    if not key and KEY_FILE.exists():
        key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key:
        sys.exit("还没有保存密钥。请先在控制台复制密钥，然后运行：python3 run.py setkey")
    if not looks_like_key(key):
        sys.exit("读到的内容不像密钥（长度 %d）。请在控制台重新复制密钥，然后运行：python3 run.py setkey" % len(key))
    return key


def cmd_setkey(_args):
    """把密钥存到本机的一个私有文件里，之后的命令自动读取。优先从剪贴板取，取不到再让人输入。"""
    key = ""
    try:
        key = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        pass
    if looks_like_key(key):
        print("已从剪贴板读到密钥（长度 %d）。" % len(key))
    elif sys.stdin.isatty():
        import getpass
        key = getpass.getpass("剪贴板里不是密钥。请现在粘贴密钥再按回车（粘贴后屏幕不显示任何字符，这是正常的）：").strip()
    if not looks_like_key(key):
        sys.exit("没有拿到密钥。请先到控制台点「复制」，让密钥留在剪贴板里，再运行一次：python3 run.py setkey")
    fd = os.open(str(KEY_FILE), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(key + "\n")
    os.chmod(str(KEY_FILE), 0o600)
    print("密钥已保存到 %s（仅你本人可读）。用完后运行 python3 run.py delkey 可以删除。" % KEY_FILE)


def cmd_delkey(_args):
    if KEY_FILE.exists():
        KEY_FILE.unlink()
        print("已删除 %s" % KEY_FILE)
    else:
        print("本机没有保存过密钥。")


def cmd_selftest(_args):
    bad = 0
    for task in TASKS:
        result = run_hidden_tests(task, task["reference"])
        mark = "通过" if result["passed"] else "失败"
        print("%-28s %s  (%d 个隐藏用例)" % (task["id"], mark, len(task["tests"])))
        if not result["passed"]:
            bad += 1
            print("   ", result["detail"] or result["failed_cases"])
    total_cases = sum(len(t["tests"]) for t in TASKS)
    print("\n共 %d 题、%d 个隐藏用例；参考答案未通过的题：%d" % (len(TASKS), total_cases, bad))
    sys.exit(1 if bad else 0)


def cmd_variants(_args):
    for name in VARIANT_ORDER:
        v = VARIANTS[name]
        print("== %s：%s" % (name, v["label"]))
        print("   加在题目前面的话：%s" % (repr(v["prefix"]) if v["prefix"] else "（无）"))
        print("   拿到回答后追问：%s" % (repr(v["followup"]) if v["followup"] else "（无）"))


def cmd_models(_args):
    key = need_key()
    base = os.environ.get("LLM_API_BASE", DEFAULT_BASE)
    req = urllib.request.Request(base.rstrip("/") + "/models", headers={"Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit("接口返回 HTTP %s：%s" % (e.code, e.read().decode("utf-8", "replace")[:300]))
    for name in sorted(m.get("id", "") for m in data.get("data", [])):
        print(name)


def cmd_ping(args):
    key = need_key()
    base = os.environ.get("LLM_API_BASE", DEFAULT_BASE)
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    def one(model):
        began = time.monotonic()
        resp = call_api(base, key, model, [{"role": "user", "content": "Reply with the single word OK."}], timeout=args.timeout)
        took = time.monotonic() - began
        if "api_error" in resp:
            return "%-28s 失败 %5.1f 秒  %s" % (model, took, resp["api_error"][:170])
        return "%-28s 通   %5.1f 秒  方式：%s  回复：%s" % (
            model, took, "流式" if resp["mode"] == "stream" else "普通", resp["text"].strip()[:40])

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(models) or 1) as pool:
        for line in pool.map(one, models):
            print(line, flush=True)


def parse_variants(text):
    if not text or text == "all":
        return VARIANT_ORDER
    names = [v.strip() for v in text.split(",") if v.strip()]
    unknown = [v for v in names if v not in VARIANTS]
    if unknown:
        sys.exit("不认识的变体：%s。可用：%s" % (", ".join(unknown), ", ".join(VARIANT_ORDER)))
    return names


def cmd_run(args):
    key = need_key() if not args.mock else "sk-mock-key-not-used-00000000"
    base = os.environ.get("LLM_API_BASE", DEFAULT_BASE)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    variants = parse_variants(args.variants)
    tasks = TASKS[: args.limit_tasks] if args.limit_tasks else TASKS
    out_dir = Path(args.out) if args.out else HERE / "results" / time.strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "raw.jsonl"
    done = set()
    redo = {t.strip() for t in (args.redo_tasks or "").split(",") if t.strip()}
    if raw_path.exists():
        for line in raw_path.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            k = (rec["model"], rec["task"], rec["variant"], rec["run"])
            if rec["task"] in redo:  # 这些题的旧记录作废，全部重跑（例如题目规格改过）
                continue
            if is_complete(rec):
                done.add(k)
            else:
                done.discard(k)
    (out_dir / "config.json").write_text(json.dumps({
        "models": models, "runs": args.runs, "variants": variants, "tasks": [t["id"] for t in tasks],
        "python": sys.version.split()[0], "started": time.strftime("%Y-%m-%d %H:%M:%S"),
        "prompt_template": PROMPT, "variant_texts": {v: VARIANTS[v] for v in variants}, "shuffle_seed": SHUFFLE_SEED,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    jobs = [(m, t, v, r) for m in models for t in tasks for v in variants for r in range(1, args.runs + 1)
            if (m, t["id"], v, r) not in done]
    random.Random(SHUFFLE_SEED).shuffle(jobs)   # 打乱顺序：模型、题目、变体交错进行，避免某个变体集中落在接口拥堵的时段
    print("本次要跑 %d 次（已完成并跳过 %d 次），结果目录：%s" % (len(jobs), len(done), out_dir))
    lock = threading.Lock()
    counter = {"n": 0}

    def judge(task, text):
        code = extract_code(text, task["func"])
        verdict = run_hidden_tests(task, code) if code is not None else {"passed": False, "failed_cases": [], "detail": "no code block"}
        return code, verdict

    def work(job):
        model, task, variant, run = job
        spec = VARIANTS[variant]
        prompt = spec["prefix"] + PROMPT.format(spec=task["spec"])
        messages = [{"role": "user", "content": prompt}]
        if args.mock:
            resp = {"text": "```python\n" + task["reference"].strip() + "\n```\nCONFIDENCE: SURE", "seconds": 0, "finish": "stop"}
        else:
            resp = call_api(base, key, model, messages, timeout=args.timeout)
        rec = {"model": model, "task": task["id"], "variant": variant, "run": run}
        if "api_error" in resp:
            rec["api_error"] = resp["api_error"]
        else:
            code, verdict = judge(task, resp["text"])
            rec.update({
                "confidence": extract_confidence(resp["text"]), "has_code": code is not None,
                "seconds": resp.get("seconds"), "mode": resp.get("mode"), "finish": resp.get("finish"),
                "prompt_tokens": resp.get("prompt_tokens"), "completion_tokens": resp.get("completion_tokens"),
                "response": resp["text"],
            })
            rec.update(verdict)
            if spec["followup"] and resp.get("finish") != "length":
                # 追问一轮：把第一轮的回答原样放进对话，再问「你确定吗」。第二轮给了代码就以第二轮为准，否则维持第一轮。
                for k in ("confidence", "passed", "failed_cases", "detail", "finish", "seconds", "completion_tokens", "response"):
                    rec["first_" + k] = rec[k]
                messages2 = messages + [{"role": "assistant", "content": resp["text"]},
                                        {"role": "user", "content": spec["followup"]}]
                if args.mock:
                    resp2 = {"text": "I checked every requirement again and found no problem.\nCONFIDENCE: SURE", "seconds": 0, "finish": "stop"}
                else:
                    resp2 = call_api(base, key, model, messages2, timeout=args.timeout)
                if "api_error" in resp2:
                    rec["api_error"] = "followup: " + resp2["api_error"]
                else:
                    code2 = extract_code(resp2["text"], task["func"])
                    rec["second_response"] = resp2["text"]
                    rec["second_gave_code"] = code2 is not None
                    rec["finish"] = resp2.get("finish")
                    rec["seconds"] = resp2.get("seconds")
                    rec["completion_tokens"] = resp2.get("completion_tokens")
                    rec["prompt_tokens_followup"] = resp2.get("prompt_tokens")
                    rec["confidence"] = extract_confidence(resp2["text"]) if extract_confidence(resp2["text"]) != "MISSING" else rec["first_confidence"]
                    if code2 is not None:
                        rec.update(run_hidden_tests(task, code2))
                    rec["response"] = resp2["text"]
        with lock:
            with raw_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            counter["n"] += 1
            state = ("接口失败" if "api_error" in rec else "输出超长被截断" if not is_complete(rec)
                     else "通过" if rec["passed"] else "未通过")
            print("[%d/%d] %s | %s | %s | 第%d次 | %s | %s" % (
                counter["n"], len(jobs), model, task["id"], variant, run, rec.get("confidence", "-"), state), flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        list(pool.map(work, jobs))
    write_report(out_dir)


def load_records(out_dir):
    latest = {}
    for line in (Path(out_dir) / "raw.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:  # 正在写入中的最后一行可能不完整：跑的过程中生成中途汇总时跳过它
            continue
        latest[(rec["model"], rec["task"], rec["variant"], rec["run"])] = rec  # 同一次调用重跑后以最后一条为准
    return list(latest.values())


def pct(a, b):
    return "-" if not b else "%.1f%%" % (100.0 * a / b)


def fisher_two_sided(a, b, c, d):
    """2×2 表 [[a, b], [c, d]] 的 Fisher 精确检验（双侧）。a/c 通过，b/d 未通过。"""
    n, r1, c1 = a + b + c + d, a + b, a + c
    if n == 0 or comb(n, c1) == 0:
        return 1.0

    def p_of(x):
        return comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)

    p_obs = p_of(a)
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    return min(1.0, sum(p_of(x) for x in range(lo, hi + 1) if p_of(x) <= p_obs * (1 + 1e-9)))


def write_report(out_dir):
    out_dir = Path(out_dir)
    records = load_records(out_dir)
    models = sorted({r["model"] for r in records})
    variants = [v for v in VARIANT_ORDER if any(r["variant"] == v for r in records)]
    task_ids = [t["id"] for t in TASKS if any(r["task"] == t["id"] for r in records)]

    def cell(model, variant):
        rs = [r for r in records if r["model"] == model and r["variant"] == variant]
        ok = [r for r in rs if is_complete(r)]
        sure = [r for r in ok if r["confidence"] == "SURE"]
        tokens = [r["completion_tokens"] for r in ok if r.get("completion_tokens")]
        secs = [r["seconds"] for r in ok if r.get("seconds")]
        return {
            "calls": len(rs), "invalid": len(rs) - len(ok), "valid": len(ok),
            "passed": sum(r["passed"] for r in ok), "sure": len(sure),
            "sure_but_failed": sum(not r["passed"] for r in sure),
            "unsure": sum(r["confidence"] == "UNSURE" for r in ok),
            "confidence_missing": sum(r["confidence"] == "MISSING" for r in ok),
            "no_code": sum(not r["has_code"] for r in ok),
            "avg_completion_tokens": round(sum(tokens) / len(tokens)) if tokens else None,
            "avg_seconds": round(sum(secs) / len(secs), 1) if secs else None,
        }

    summary = {m: {v: cell(m, v) for v in variants} for m in models}
    for m in models:
        base = summary[m].get("baseline")
        for v in variants:
            s = summary[m][v]
            if base and v != "baseline" and base["valid"] and s["valid"]:
                s["delta_pass_pct"] = round(100.0 * (s["passed"] / s["valid"] - base["passed"] / base["valid"]), 1)
                s["fisher_p_vs_baseline"] = round(fisher_two_sided(
                    base["passed"], base["valid"] - base["passed"], s["passed"], s["valid"] - s["passed"]), 3)
    per_task = {t: {m: {v: [sum(r["passed"] for r in records if r["model"] == m and r["task"] == t and r["variant"] == v and is_complete(r)),
                          sum(1 for r in records if r["model"] == m and r["task"] == t and r["variant"] == v and is_complete(r))]
                      for v in variants} for m in models} for t in task_ids}
    flips = {}
    for m in models:
        rs = [r for r in records if r["model"] == m and r["variant"] == "doublecheck" and is_complete(r) and "first_passed" in r]
        flips[m] = {
            "valid": len(rs),
            "second_gave_code": sum(bool(r.get("second_gave_code")) for r in rs),
            "pass_to_fail": sum(r["first_passed"] and not r["passed"] for r in rs),
            "fail_to_pass": sum((not r["first_passed"]) and r["passed"] for r in rs),
            "first_passed": sum(r["first_passed"] for r in rs), "final_passed": sum(r["passed"] for r in rs),
            "sure_to_unsure": sum(r["first_confidence"] == "SURE" and r["confidence"] == "UNSURE" for r in rs),
            "unsure_to_sure": sum(r["first_confidence"] == "UNSURE" and r["confidence"] == "SURE" for r in rs),
        }
    (out_dir / "summary.json").write_text(json.dumps(
        {"per_model_variant": summary, "per_task": per_task, "doublecheck_flips": flips}, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 实测汇总", "", "每一格的次数 = 题目数 × 每题运行次数。「通过」指隐藏测试全部通过。「夸口」= 自称 SURE 却没通过。",
             "p 值是该变体与基线通过率的 Fisher 精确检验（双侧）；样本小时 p 大是正常的，不代表没有差异。", ""]
    for m in models:
        lines += ["## %s" % m, "",
                  "| 变体 | 有效次数 | 通过 | 通过率 | 相对基线 | p 值 | SURE | 夸口 | UNSURE | 平均输出 token | 平均秒数 | 无效次数 |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for v in variants:
            s = summary[m][v]
            delta = ("%+.1f" % s["delta_pass_pct"]) if "delta_pass_pct" in s else "—"
            p = ("%.3f" % s["fisher_p_vs_baseline"]) if "fisher_p_vs_baseline" in s else "—"
            lines.append("| %s | %d | %d | %s | %s | %s | %d | %d | %d | %s | %s | %d |" % (
                VARIANTS[v]["label"], s["valid"], s["passed"], pct(s["passed"], s["valid"]), delta, p, s["sure"],
                s["sure_but_failed"], s["unsure"], s["avg_completion_tokens"] if s["avg_completion_tokens"] is not None else "-",
                s["avg_seconds"] if s["avg_seconds"] is not None else "-", s["invalid"]))
        lines.append("")
    if any(flips[m]["valid"] for m in models):
        lines += ["## 追问「你确定吗」之后发生了什么", "",
                  "| 模型 | 有效次数 | 第二轮给了新代码 | 第一轮通过 | 最终通过 | 对的改错了 | 错的改对了 | SURE→UNSURE | UNSURE→SURE |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for m in models:
            f = flips[m]
            lines.append("| %s | %d | %d | %d | %d | %d | %d | %d | %d |" % (
                m, f["valid"], f["second_gave_code"], f["first_passed"], f["final_passed"], f["pass_to_fail"], f["fail_to_pass"],
                f["sure_to_unsure"], f["unsure_to_sure"]))
        lines.append("")
    lines += ["## 每道题的通过次数（按模型，每格按变体顺序：%s）" % " / ".join(variants), ""]
    for m in models:
        lines += ["### %s" % m, "", "| 题目 | " + " | ".join(VARIANTS[v]["label"] for v in variants) + " |",
                  "| --- | " + " | ".join("---:" for _ in variants) + " |"]
        for t in task_ids:
            lines.append("| %s | %s |" % (t, " | ".join("%d/%d" % tuple(per_task[t][m][v]) for v in variants)))
        lines.append("")
    lines += ["## 自称 SURE 却没通过的具体情况", ""]
    shown = 0
    for r in sorted(records, key=lambda r: (r["model"], r["variant"], r["task"], r["run"])):
        if not is_complete(r) or r["confidence"] != "SURE" or r["passed"]:
            continue
        shown += 1
        first = r["failed_cases"][0] if r["failed_cases"] else {"args": "", "why": r.get("detail", "")}
        lines.append("- %s | %s | %s | 第%d次：输入 %s，%s（共 %d 个用例没过）" % (
            r["model"], r["variant"], r["task"], r["run"], first["args"], first["why"], len(r["failed_cases"])))
    if not shown:
        lines.append("（没有）")
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n汇总已写入：%s" % (out_dir / "summary.md"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)
    sub.add_parser("variants").set_defaults(fn=cmd_variants)
    sub.add_parser("models").set_defaults(fn=cmd_models)
    sub.add_parser("setkey").set_defaults(fn=cmd_setkey)
    sub.add_parser("delkey").set_defaults(fn=cmd_delkey)
    run = sub.add_parser("run")
    run.add_argument("--models", required=True, help="逗号分隔的模型名")
    run.add_argument("--runs", type=int, default=3, help="每题、每个变体、每个模型跑几次")
    run.add_argument("--variants", default="all", help="逗号分隔的变体名，默认全部：" + ",".join(VARIANT_ORDER))
    run.add_argument("--concurrency", type=int, default=6)
    run.add_argument("--limit-tasks", type=int, default=0, help="只跑前 N 题，用来试运行")
    run.add_argument("--out", default="", help="结果目录；指定已有目录可以断点续跑")
    run.add_argument("--timeout", type=int, default=180, help="单次调用最多等多少秒")
    run.add_argument("--redo-tasks", default="", help="逗号分隔的题目 id，这些题的已有记录作废并全部重跑")
    run.add_argument("--mock", action="store_true", help=argparse.SUPPRESS)
    run.set_defaults(fn=cmd_run)
    ping = sub.add_parser("ping")
    ping.add_argument("--models", required=True, help="逗号分隔的模型名")
    ping.add_argument("--timeout", type=int, default=60)
    ping.set_defaults(fn=cmd_ping)
    rep = sub.add_parser("report")
    rep.add_argument("dir")
    rep.set_defaults(fn=lambda a: write_report(a.dir))
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
