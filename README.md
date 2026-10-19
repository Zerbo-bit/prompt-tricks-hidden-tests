# Prompt-tricks experiment: reproduction package / Пакет для воспроизведения

Contents (all files are local copies; no API keys or personal data are included):

- `tasks_base.py`, `tasks_hard.py`, `tasks.py` — the 30 tasks: specification text shown to the model, hidden test cases (493 in total), reference solutions.
- `run.py` — runner and judge. `python3 run.py variants` prints the seven prompt variants verbatim; `python3 run.py selftest` runs the reference solutions against the hidden tests; the judge executes each candidate in an isolated subprocess (`python -I`) with a 30-second limit.
- `analyze.py` — produces `results/main/分析.md` from `results/main/raw.jsonl` (`python3 analyze.py results/main`). Includes the record-selection rule, the corrected Newcombe interval, task-clustered permutation test and bootstrap interval.
- `results/main/raw.jsonl` — the final raw log: 2,195 records covering 1,890 experiment units (3 models × 30 tasks × 7 variants × 3 runs). A unit can have several records (retries after truncation, re-runs after the INI spec clarification, and a few duplicates produced when two runner processes overlapped). Selection rule: for each unit the first complete record in file order; if none is complete, the last one. The rule never looks at whether the answer passed.
- `results/main/raw.pass1.jsonl` — snapshot after the first full pass (output cap 16,000 tokens), before the 63 INI-task records were voided and re-run under the clarified spec. `results/main/raw.before-rejudge.jsonl` — snapshot before the one gpt cron answer was re-judged with longer limits.
- `results/main/paired_by_task.csv` — per task × run × variant: baseline result vs variant result (pass / fail / truncated), the paired view behind the McNemar counts.
- `results/main/config.json` — models, prompt template, variant texts, shuffle seed, Python version (3.9.6), start time.
- `实验设计.md` — pre-registered questions, rules and the full run log (Chinese).

Model identifiers as sent to the API: `gpt-6.1-sol`, `claude-haiku-5-5`, `glm-5.3-flash`, via one third-party OpenAI-compatible endpoint; not re-verified on vendors' official APIs. Run parameters: temperature left at the endpoint default; output cap 16,000 tokens in the first pass, 32,000 for retries of truncated units; per-request timeout 360 s in the first pass, 900 s in the final retry pass; judge limit 30 s per candidate.

Not yet done: a public location for this package. Until it is published, the article must not claim "reproducible in one command from a link".
