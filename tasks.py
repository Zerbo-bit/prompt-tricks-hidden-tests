"""题库：上一篇的 20 道题（tasks_base）+ 这次新加的 10 道更难的题（tasks_hard）。"""
from tasks_base import TASKS as _BASE
from tasks_hard import HARD

TASKS = _BASE + HARD
