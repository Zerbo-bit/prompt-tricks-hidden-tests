#!/usr/bin/env python3
"""把 results/<目录>/raw.jsonl 整理成给人看的分析稿（中文），输出到同目录的 分析.md。

用法：python3 analyze.py results/main

2026-10-19 审稿后的修订：
- 取样规则改为「每个实验单元取文件里第一条完整记录；没有完整记录时取最后一条」，并报告与「最后一条胜出」规则的差异。
- Newcombe 区间上下尾公式修正。
- 新增按题目聚类的推断：按题配对的符号置换检验、按题 bootstrap 区间。
- 输出 token 缺失（None 或 0）按缺失处理，不再当作 0；报告可用样本数。
"""
import json
import math
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

from run import VARIANTS, VARIANT_ORDER, fisher_two_sided, is_complete
from tasks import TASKS

LABEL = {v: VARIANTS[v]["label"] for v in VARIANT_ORDER}
TIPS = [v for v in VARIANT_ORDER if v != "baseline"]
ONE_LINERS = [v for v in TIPS if v != "doublecheck"]
SEED = 20261019
N_PERM = 20000
N_BOOT = 10000
UNITS_PER_VARIANT = len(TASKS) * 3


def read_all(out_dir):
    """读取全部原始记录（不去重），附带行号。解析失败的行跳过并计数。"""
    recs, bad = [], 0
    for i, line in enumerate(Path(out_dir, "raw.jsonl").read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            bad += 1
            continue
        r["_line"] = i
        recs.append(r)
    return recs, bad


def key_of(r):
    return (r["model"], r["task"], r["variant"], r["run"])


def select(records, rule):
    """按规则为每个实验单元选一条记录。
    first_complete：文件顺序里第一条完整记录；没有完整记录就取最后一条（重试只对未完成的单元进行，
    完整记录之后再出现的记录属于并发产生的重复运行，不采用）。
    last：最后一条胜出（修订前的规则）。两种规则都不看回答是否通过。"""
    by = defaultdict(list)
    for r in records:
        by[key_of(r)].append(r)
    chosen = {}
    for k, v in by.items():
        if rule == "last":
            chosen[k] = v[-1]
        else:
            chosen[k] = next((r for r in v if is_complete(r)), v[-1])
    return chosen, by


def wilson(p, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def newcombe(p1, n1, p2, n2):
    """独立比例之差 p2 - p1 的 95% 区间（Newcombe 第 10 法）。2026-10-19 修正：下界用 (p2-l2) 与 (u1-p1)，上界用 (u2-p2) 与 (p1-l1)。"""
    l1, u1 = wilson(p1, n1)
    l2, u2 = wilson(p2, n2)
    d = p2 - p1
    return (d - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2), d + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2))


def mcnemar_p(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2.0 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def pct(a, b):
    return "—" if not b else "%.1f%%" % (100.0 * a / b)


def tokens_of(r):
    """接口报告的输出 token（追问变体为两轮之和）。None 或 0 视为缺失，返回 None。"""
    c = r.get("completion_tokens")
    if not c:
        return None
    if r["variant"] == "doublecheck":
        f = r.get("first_completion_tokens")
        if not f:
            return None
        return c + f
    return c


def secs_of(r):
    return (r.get("seconds") or 0) + (r.get("first_seconds") or 0)


def task_counts(rows):
    """按题汇总：task -> [通过数, 有效数]"""
    tc = defaultdict(lambda: [0, 0])
    for r in rows:
        tc[r["task"]][0] += 1 if r["passed"] else 0
        tc[r["task"]][1] += 1
    return tc


def clustered_tests(full, v):
    """按题目聚类的推断，只用 7 个变体都完整的共同单元 full（{variant: record} 的列表）。
    每题的统计量 = 该题各次 (变体通过 − 基线通过) 的平均；总体统计量 = 各题等权平均（百分点）。
    置换：随机翻转每题差值的符号（双侧）；bootstrap：按题重抽样后算同一个等权平均。
    返回 (题数, 等权差值, 置换 p, 区间下, 区间上)。"""
    per_task = defaultdict(list)
    for c in full:
        per_task[c["baseline"]["task"]].append((1 if c[v]["passed"] else 0) - (1 if c["baseline"]["passed"] else 0))
    tasks = sorted(per_task)
    if not tasks:
        return (0, None, None, None, None)
    diffs = [sum(x) / len(x) for x in (per_task[t] for t in tasks)]
    obs = sum(diffs) / len(diffs)
    rng = random.Random(SEED)
    hits = 0
    for _ in range(N_PERM):
        sm = sum(d if rng.random() < 0.5 else -d for d in diffs) / len(diffs)
        if abs(sm) >= abs(obs) - 1e-12:
            hits += 1
    p = (hits + 1) / (N_PERM + 1)
    boots = []
    for _ in range(N_BOOT):
        sample = [diffs[rng.randrange(len(diffs))] for _ in diffs]
        boots.append(sum(sample) / len(sample))
    boots.sort()
    return (len(tasks), obs, p, boots[int(0.025 * N_BOOT)], boots[int(0.975 * N_BOOT) - 1])


def main(out_dir):
    out_dir = Path(out_dir)
    all_recs, bad = read_all(out_dir)
    chosen, by_unit = select(all_recs, "first_complete")
    alt, _ = select(all_recs, "last")
    records = list(chosen.values())
    ok = [r for r in records if is_complete(r)]
    models = sorted({r["model"] for r in records})
    L = []
    L += ["# 提示词技巧实测：分析稿", "",
          "数据：`%s`，原始记录 %d 条（解析失败 %d 行），覆盖 %d 个实验单元（模型 × 题 × 变体 × 次）。按取样规则每个单元取 1 条，其中完整 %d 条（无效 = 输出被截断或接口错误，不计入分母）。" % (
              out_dir / "raw.jsonl", len(all_recs), bad, len(chosen), len(ok)), ""]

    # ---- 取样规则与敏感性 ----
    multi = {k: v for k, v in by_unit.items() if len(v) > 1}
    pat = Counter("".join("C" if is_complete(r) else "i" for r in v) for v in multi.values())
    diff_units = []
    for k in chosen:
        a, b = chosen[k], alt[k]
        if a is b:
            continue
        if is_complete(a) != is_complete(b) or (is_complete(a) and a.get("passed") != b.get("passed")):
            diff_units.append((k, a, b))
    L += ["## 取样规则", "",
          "规则：每个实验单元取文件顺序里的第一条完整记录；没有完整记录时取最后一条。理由：按协议只对未完成的单元重试，完整记录之后再出现的记录来自并发进程的重复运行，不采用。规则只看记录是否完整，不看是否通过。", "",
          "有多条记录的单元 %d 个；记录序列分布（C = 完整，i = 不完整，按文件顺序）：%s。" % (len(multi), "，".join("%s %d" % kv for kv in pat.most_common())), "",
          "与修订前「最后一条胜出」规则相比，结果不同的单元 %d 个：" % len(diff_units)]
    for k, a, b in diff_units:
        L.append("- %s | %s | 第%d次：本规则取第 %d 行（%s，%s），旧规则取第 %d 行（%s，%s）" % (
            k[0], k[1], k[3], a["_line"], "完整" if is_complete(a) else "不完整", "通过" if a.get("passed") else "未通过",
            b["_line"], "完整" if is_complete(b) else "不完整", "通过" if b.get("passed") else "未通过"))
    ok_alt = [r for r in alt.values() if is_complete(r)]
    L += ["", "合计：本规则完整 %d / 无效 %d；旧规则完整 %d / 无效 %d。" % (len(ok), len(chosen) - len(ok), len(ok_alt), len(alt) - len(ok_alt)), ""]

    # ---- 无效记录分布 ----
    inval = [r for r in records if not is_complete(r)]
    L += ["## 无效记录", ""]
    if inval:
        c = Counter((r["model"], r["variant"]) for r in inval)
        L += ["| 模型 | 变体 | 无效条数 |", "| --- | --- | ---: |"]
        for (m, v), n in sorted(c.items()):
            L.append("| %s | %s | %d |" % (m, LABEL[v], n))
        ct = Counter(r["task"] for r in inval)
        L += ["", "按题：" + "，".join("%s %d" % kv for kv in ct.most_common(10)), "",
              "原因：finish=length（输出到上限被截断）%d 条，其中 completion_tokens 等于 32000 的 %d 条；接口错误 %d 条；正文为空 %d 条、非空 %d 条。" % (
                  sum(r.get("finish") == "length" or r.get("first_finish") == "length" for r in inval),
                  sum(r.get("completion_tokens") == 32000 for r in inval), sum(bool(r.get("api_error")) for r in inval),
                  sum(not (r.get("response") or "").strip() for r in inval), sum(bool((r.get("response") or "").strip()) for r in inval))]
    else:
        L.append("（没有）")
    L.append("")

    # ---- 主表 ----
    L += ["## 主表：通过率、推断、自评、输出长度", "",
          "每个变体满额 %d 个单元（%d 题 × 3 次）。「通过/满额」把无效单元算作未通过，是保守口径。差值 = 变体通过率 − 基线通过率（有效单元口径，百分点）。" % (UNITS_PER_VARIANT, len(TASKS)),
          "这里的区间和 p 是独立比例口径：Newcombe 95% 区间与 Fisher 精确检验，把每个变体的有效单元当作独立样本，忽略同一题 3 次重复的相关性，而且各变体的有效集合不同。只作对照；文中引用的推断见下一节「配对口径」（共同单元、按题聚类）。",
          "输出 token = 接口报告的 completion_tokens（追问变体为两轮之和）；缺失（None 或 0）不计入，括号里是可用样本数。耗时只含最终保留的那次请求，不含重试与等待。", ""]
    cells = {}
    for m in models:
        L += ["### %s" % m, "",
              "| 变体 | 有效 | 通过 | 通过率 | 通过/满额 | 差值 | Newcombe 区间(独立) | Fisher p | SURE | SURE 但没过 | UNSURE | 输出 token 中位数 (n) | 耗时中位数(秒) |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        base = [r for r in ok if r["model"] == m and r["variant"] == "baseline"]
        pb, nb = (sum(r["passed"] for r in base) / len(base)) if base else 0, len(base)
        for v in VARIANT_ORDER:
            rs = [r for r in ok if r["model"] == m and r["variant"] == v]
            if not rs:
                continue
            passed = sum(r["passed"] for r in rs)
            sure = [r for r in rs if r["confidence"] == "SURE"]
            toks = [t for t in (tokens_of(r) for r in rs) if t is not None]
            secs = [secs_of(r) for r in rs]
            cells[(m, v)] = {"n": len(rs), "passed": passed, "tok": statistics.median(toks) if toks else None, "ntok": len(toks), "sec": statistics.median(secs)}
            if v == "baseline" or not base:
                delta = ci = p = "—"
            else:
                pv = passed / len(rs)
                lo, hi = newcombe(pb, nb, pv, len(rs))
                delta = "%+.1f" % (100 * (pv - pb))
                ci = "[%+.1f, %+.1f]" % (100 * lo, 100 * hi)
                p = "%.3f" % fisher_two_sided(sum(r["passed"] for r in base), nb - sum(r["passed"] for r in base), passed, len(rs) - passed)
            L.append("| %s | %d | %d | %s | %d/%d | %s | %s | %s | %d | %d | %d | %s (%d) | %.0f |" % (
                LABEL[v], len(rs), passed, pct(passed, len(rs)), passed, UNITS_PER_VARIANT, delta, ci, p, len(sure),
                sum(not r["passed"] for r in sure), sum(r["confidence"] == "UNSURE" for r in rs),
                ("%.0f" % cells[(m, v)]["tok"]) if cells[(m, v)]["tok"] is not None else "—", cells[(m, v)]["ntok"], cells[(m, v)]["sec"]))
        L.append("")

    # ---- 配对口径 ----
    L += ["## 配对口径：只算 7 个变体都有效的「题 × 次」单元（文中引用的推断）", "",
          "无效记录集中在难题和个别变体，按有效记录直接算通过率会让缺项多的模型显得偏好。这里只保留同一道题、同一次里 7 个变体都有效的单元（满额 90）。两种推断都在这个共同集合上做：(1) McNemar 精确检验，逐单元配对，只看结果不一致的单元；(2) 按题聚类：每题统计量 = 该题各次 (变体通过 − 基线通过) 的平均，总体 = 各题等权平均（百分点），符号置换 %d 次（双侧）与按题 bootstrap %d 次用同一个统计量。注意「通过/配对单元」按单元汇总，「按题等权差值」按题平均，两者含义不同、数值可以不等。这个口径只回答「在所有变体都写得完的子集里有没有差别」，不代表全部单元的使用效果。" % (N_PERM, N_BOOT), ""]
    for m in models:
        cell = defaultdict(dict)
        for r in ok:
            if r["model"] == m:
                cell[(r["task"], r["run"])][r["variant"]] = r
        full = [c for c in cell.values() if all(v in c for v in VARIANT_ORDER)]
        valid_per_task = Counter(r["task"] for r in ok if r["model"] == m)
        full_tasks = sum(1 for t in TASKS if valid_per_task[t["id"]] == 3 * len(VARIANT_ORDER))
        L += ["### %s：配对单元 %d/90；%d 题里 21 条全有效的题 %d 道" % (m, len(full), len(TASKS), full_tasks), ""]
        if not full:
            L += ["（没有可配对的单元）", ""]
            continue
        ntasks_full = len({c["baseline"]["task"] for c in full})
        L += ["共同单元覆盖 %d 道题。" % ntasks_full, "",
              "| 变体 | 通过/配对单元 | 通过率 | 差值(按单元) | 基线过·它没过 | 基线没过·它过 | McNemar p | 按题等权差值 | 置换 p(按题) | bootstrap 区间(按题) |",
              "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        n = len(full)
        base_pass = sum(c["baseline"]["passed"] for c in full)
        for v in VARIANT_ORDER:
            pv = sum(c[v]["passed"] for c in full)
            if v == "baseline":
                L.append("| %s | %d/%d | %s | — | — | — | — | — | — | — |" % (LABEL[v], pv, n, pct(pv, n)))
            else:
                b = sum(bool(c["baseline"]["passed"] and not c[v]["passed"]) for c in full)
                cc = sum(bool((not c["baseline"]["passed"]) and c[v]["passed"]) for c in full)
                nt, obs, pperm, blo, bhi = clustered_tests(full, v)
                L.append("| %s | %d/%d | %s | %+.1f | %d | %d | %.3f | %+.2f | %.3f | [%+.1f, %+.1f] |" % (
                    LABEL[v], pv, n, pct(pv, n), 100.0 * (pv - base_pass) / n, b, cc, mcnemar_p(b, cc), 100 * obs, pperm, 100 * blo, 100 * bhi))
        L += ["", "共同单元上的输出 token 与耗时（同一批题、同一批次，可直接比较；token 缺失不计入，括号为可用样本数）：", "",
              "| 变体 | 输出 token 中位数 (n) | 相对基线 | 耗时中位数(秒) |", "| --- | ---: | ---: | ---: |"]
        base_tok = [t for t in (tokens_of(c["baseline"]) for c in full) if t is not None]
        base_med = statistics.median(base_tok) if base_tok else None
        for v in VARIANT_ORDER:
            toks = [t for t in (tokens_of(c[v]) for c in full) if t is not None]
            med = statistics.median(toks) if toks else None
            rel = ("%.2f 倍" % (med / base_med)) if (med is not None and base_med) else "—"
            L.append("| %s | %s (%d) | %s | %.0f |" % (LABEL[v], ("%.0f" % med) if med is not None else "—", len(toks), rel if v != "baseline" else "—", statistics.median([secs_of(c[v]) for c in full])))
        L.append("")

    # ---- 追问 ----
    L += ["## 追问「你确定吗？」第二轮发生了什么", "",
          "| 模型 | 有效 | 第一轮未过 | 其中第二轮修对 | 第二轮给了新代码 | 改坏 | 最终未过 | 自评改口 SURE→UNSURE | 第二轮说「发现问题」但没给代码(关键词粗判) |",
          "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    claim_re = re.compile(r"\b(found|there is|there's|one|real|genuine)\b[^.\n]{0,40}\b(problem|issue|bug|defect|gap|hole|weakness)", re.I)
    deny_re = re.compile(r"\b(no|not|didn't|did not|don't|found no|without)\b[^.\n]{0,30}\b(problem|issue|bug|defect)", re.I)
    for m in models:
        rs = [r for r in ok if r["model"] == m and r["variant"] == "doublecheck" and "first_passed" in r]
        if not rs:
            continue
        gave = [r for r in rs if r.get("second_gave_code")]
        said = [r for r in rs if not r.get("second_gave_code") and claim_re.search((r.get("second_response") or "")[:500]) and not deny_re.search((r.get("second_response") or "")[:300])]
        L.append("| %s | %d | %d | %d | %d | %d | %d | %d | %d |" % (
            m, len(rs), sum(not r["first_passed"] for r in rs), sum((not r["first_passed"]) and r["passed"] for r in rs), len(gave),
            sum(r["first_passed"] and not r["passed"] for r in gave), sum(not r["passed"] for r in rs),
            sum(r["first_confidence"] == "SURE" and r["confidence"] == "UNSURE" for r in rs), len(said)))
    L += ["", "「说发现问题但没给代码」是按关键词粗判的；2026-10-18 人工核对，标出的 3 条都是在确认没问题，实际为 0。", ""]

    # ---- 自评校准 ----
    L += ["## 自评（SURE/UNSURE）和实际结果", "", "| 模型 | 有效 | SURE | 其中没过 | UNSURE | 其中其实通过 |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for m in models:
        rs = [r for r in ok if r["model"] == m]
        s = [r for r in rs if r["confidence"] == "SURE"]
        u = [r for r in rs if r["confidence"] == "UNSURE"]
        L.append("| %s | %d | %d | %d | %d | %d |" % (m, len(rs), len(s), sum(not r["passed"] for r in s), len(u), sum(r["passed"] for r in u)))
    L.append("")

    # ---- 难度 ----
    L += ["## 题目难度：上一篇的 20 题 vs 新加的 10 题（所有变体合计，有效记录口径）", "", "| 模型 | 旧 20 题通过率 | 新 10 题通过率 |", "| --- | ---: | ---: |"]
    for m in models:
        rs = [r for r in ok if r["model"] == m]
        old = [r for r in rs if r["task"] < "t21"]
        new = [r for r in rs if r["task"] >= "t21"]
        L.append("| %s | %s | %s |" % (m, pct(sum(r["passed"] for r in old), len(old)), pct(sum(r["passed"] for r in new), len(new))))
    L.append("")
    tc = defaultdict(lambda: [0, 0])
    for r in ok:
        tc[r["task"]][0] += r["passed"]
        tc[r["task"]][1] += 1
    L += ["最难的 8 题（所有模型所有变体合计）：" + "；".join("%s %d/%d" % (t, p, n) for t, (p, n) in sorted(tc.items(), key=lambda kv: kv[1][0] / kv[1][1])[:8]), ""]

    # ---- 每道题 × 变体 ----
    L += ["## 每道题的通过次数（按模型；每格 = 通过/有效）", ""]
    for m in models:
        L += ["### %s" % m, "", "| 题目 | " + " | ".join(LABEL[v] for v in VARIANT_ORDER) + " |", "| --- | " + " | ".join("---:" for _ in VARIANT_ORDER) + " |"]
        for t in [t["id"] for t in TASKS]:
            row = []
            for v in VARIANT_ORDER:
                rs = [r for r in ok if r["model"] == m and r["task"] == t and r["variant"] == v]
                row.append("%d/%d" % (sum(r["passed"] for r in rs), len(rs)))
            L.append("| %s | %s |" % (t, " | ".join(row)))
        L.append("")

    # ---- 合并五个技巧（探索性，不进文章）----
    L += ["## 附：五个「加一句」技巧合并 vs 基线（探索性，混合了不同干预，不进文章）", "", "| 模型 | 基线 | 五个技巧合并 | 差值 | Fisher p |", "| --- | ---: | ---: | ---: | ---: |"]
    for m in models:
        b = [r for r in ok if r["model"] == m and r["variant"] == "baseline"]
        t = [r for r in ok if r["model"] == m and r["variant"] in ONE_LINERS]
        if b and t:
            pb_, pt_ = sum(r["passed"] for r in b), sum(r["passed"] for r in t)
            L.append("| %s | %d/%d = %s | %d/%d = %s | %+.1f | %.3f |" % (
                m, pb_, len(b), pct(pb_, len(b)), pt_, len(t), pct(pt_, len(t)), 100 * (pt_ / len(t) - pb_ / len(b)),
                fisher_two_sided(pb_, len(b) - pb_, pt_, len(t) - pt_)))
    L.append("")

    # ---- 失败清单 ----
    L += ["## 所有未通过的有效回答（写稿时从这里挑例子）", ""]
    for r in sorted([r for r in ok if not r["passed"]], key=lambda r: (r["model"], r["variant"], r["task"], r["run"])):
        fc = r.get("failed_cases") or []
        first = fc[0] if fc else {"args": "", "why": r.get("detail", "")}
        L.append("- %s | %s | %s | 第%d次 | 自评 %s | 没过 %d 例 | 例：输入 %s → %s" % (
            r["model"], LABEL[r["variant"]], r["task"], r["run"], r["confidence"], len(fc), first["args"][:60], first["why"][:90]))
    L.append("")
    (out_dir / "分析.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("已写入", out_dir / "分析.md", "| 原始记录", len(all_recs), "单元", len(chosen), "有效", len(ok))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/main")
