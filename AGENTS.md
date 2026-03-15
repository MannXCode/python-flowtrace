# Sandbox Debugger — Project Context for AI Agents

> Drop this file in the root of your project. The AI agent will read it before doing anything.
> Keep it updated as the project evolves.

---

## What This Project Is

A browser-based Python debugging tool that records every action performed during a program's execution and lets the developer replay, rewind, pause, and inspect that execution visually. Think of it as a "time machine" for your Python code — you run your program once, and then you can explore what happened at any point without re-running manually.

The closest existing tool was **Cyberbrain** (github.com/laike9m/Cyberbrain, ~2.5k stars, now abandoned). This project learns from its mistakes:
- Cyberbrain was VS Code-only and hard to install. This is browser-based — just open a URL.
- Cyberbrain could only trace one function at a time. This traces the whole program.
- Cyberbrain had no rewind, no memory tracking, no DB sandboxing.

---

## Core Philosophy

- **Ship something that works first.** A simple ugly version that runs beats a perfect version that doesn't exist.
- **The tracer is the foundation.** If the data coming out of `sys.settrace()` is wrong, everything else is wrong. Get this right before touching the UI.
- **Browser-based, not CLI.** The target user is a developer who wants a visual, interactive experience — not another terminal tool.
- **Modular by stage.** Each stage is independently useful. Stage 1 alone (the tracer) has value even without a UI.

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Backend | Python + Flask | Lightweight. Django is overkill for this. |
| Real-time comms | Flask-SocketIO | Streams trace events to the browser live |
| Core tracer | `sys.settrace()` | Python built-in. Powers everything. |
| Memory tracking | `tracemalloc` + `sys.getsizeof()` | Built-in. No extra deps. |
| DB sandboxing | `unittest.mock` | Intercepts and mocks DB/CRUD calls |
| Code editor in UI | Monaco Editor (CDN) | Same editor as VS Code. Highlights current line. |
| Charts | Chart.js (CDN) | Memory graphs, line count stats |
| Frontend | HTML + CSS + Vanilla JS | No React. Keep it simple. |
| Subprocess execution | Python `subprocess` | Runs user's code in isolation |

---

## Project Structure (Target)

```
sandbox-debugger/
├── AGENTS.md                  ← You are here
├── README.md
├── requirements.txt
├── run.py                     ← Entry point. Starts Flask server.
│
├── core/
│   ├── __init__.py
│   ├── tracer.py              ← sys.settrace() hook. The most important file.
│   ├── recorder.py            ← Records inputs, function calls, variable states
│   ├── replayer.py            ← Replays a recorded session
│   └── memory.py              ← tracemalloc integration
│
├── server/
│   ├── __init__.py
│   ├── app.py                 ← Flask app + SocketIO setup
│   ├── routes.py              ← REST endpoints (upload file, start/stop session)
│   └── events.py              ← SocketIO event handlers (pause, step, rewind)
│
├── sandbox/
│   ├── __init__.py
│   └── db_mock.py             ← unittest.mock patches for DB calls
│
└── ui/
    ├── index.html             ← Main UI
    ├── style.css
    └── main.js                ← SocketIO client + UI logic
```

---

## Build Stages

### Stage 1 — Core Tracer *(build this first, no UI)*
**Files:** `core/tracer.py`, `core/recorder.py`

The tracer hooks into Python's `sys.settrace()` to intercept every line executed. For every event it records:
- Which file and line number executed
- Which function was entered or exited
- The name, value, and type of every local variable at that moment
- Any exception that was raised

Output is a structured JSON log written to disk. Run from the terminal, inspect the JSON. Do NOT move to Stage 2 until this data is accurate and complete.

Key implementation notes:
- Use `sys.settrace()` at the global level and `frame.f_trace` for local tracing
- Filter by file path to separate user code from library code (check if `frame.f_code.co_filename` starts with the user's project directory)
- Serialize variable values safely — use `repr()` as a fallback for objects that can't be JSON serialized
- Track variable *changes* not just current state: compare current frame locals to previous frame locals on each `line` event

```python
# Minimal tracer skeleton
import sys, json

events = []

def tracer(frame, event, arg):
    if event in ('call', 'line', 'return', 'exception'):
        events.append({
            'event': event,
            'file': frame.f_code.co_filename,
            'line': frame.f_lineno,
            'function': frame.f_code.co_name,
            'locals': {k: repr(v) for k, v in frame.f_locals.items()}
        })
    return tracer

sys.settrace(tracer)
# ... run user code here ...
sys.settrace(None)
```

**Definition of done for Stage 1:**
- Run the tracer on a simple test script (e.g. a basic expense tracker with a loop and some conditionals)
- Inspect the JSON output manually
- Confirm: every line is recorded, variable values are correct, function calls/returns are captured, library internals are filtered out

---

### Stage 2 — Flask Backend + WebSockets
**Files:** `server/app.py`, `server/routes.py`, `server/events.py`, `run.py`

Wrap the tracer in a Flask server. The user uploads or points to a Python file. Flask runs it in a subprocess and streams trace events to the browser in real time via SocketIO.

Key implementation notes:
- Run user code in a `subprocess.Popen` call, NOT in the same process as Flask (isolation + safety)
- The tracer writes events to a queue or temp file; a background thread reads from it and emits SocketIO events
- REST endpoints needed: `POST /run` (start execution), `POST /stop` (kill subprocess)
- SocketIO events to emit: `trace_event` (each line/call/return), `execution_complete`, `execution_error`

**Definition of done for Stage 2:**
- Submit a Python file via a simple HTML form (no fancy UI yet)
- See trace events printing in the browser console in real time as the code runs

---

### Stage 3 — The UI (Four Panels)
**Files:** `ui/index.html`, `ui/style.css`, `ui/main.js`

Build the visual interface. Four panels:

1. **Code Viewer** (Monaco Editor): Shows the user's source code. Highlights the currently executing line in real time as SocketIO events come in. Use Monaco via CDN.

2. **Variables Panel**: Live-updating list of all variables in the current scope. Shows name, value, type, and how many times the variable has been changed so far.

3. **Flow Panel**: A collapsible tree of every function call. Shows which `if`/`else` branches executed and which were skipped. Color: green = executed, gray = skipped.

4. **Stats Panel**: Line count (user code vs library code), total memory usage (placeholder for Stage 5), execution time so far.

Key implementation notes:
- Load Monaco from CDN: `https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs/loader.min.js`
- On each `trace_event` SocketIO message, update the highlighted line in Monaco and re-render the variables panel
- Use CSS Grid for the four-panel layout

**Definition of done for Stage 3:**
- Run a test script and watch the Monaco editor highlight each line in real time
- See variables update live in the variables panel
- See the function call tree build up in the flow panel

---

### Stage 4 — Controls (Play / Pause / Step / Rewind)
**Files:** `server/events.py`, `core/replayer.py`, updates to `core/tracer.py`

Implement the debugger controls:

- **Pause**: Use a `threading.Event` to halt the subprocess between trace events. The tracer checks this event before processing each line.
- **Step Forward**: Unpause for exactly one event, then pause again.
- **Play**: Unpause fully and let execution continue.
- **Rewind**: This replays the entire execution from scratch using the recorded inputs. The replayer re-runs the user's file with the same stdin inputs, function arguments, and random seeds that were recorded in Stage 1. The user can modify their code before rewinding.
- **Variable editing mid-execution**: When paused, allow the user to type a new value for any variable in the UI. Inject it into the running frame using `ctypes` frame manipulation or a `pdb`-style hook.

Key implementation notes for rewind:
- Record ALL user inputs during execution (`builtins.input` patched to log every call and its return value)
- On rewind, patch `builtins.input` again to replay logged values automatically instead of waiting for user input
- Also patch `random.random()` and `random.randint()` to replay logged random values (deterministic replay)
- This approach (record inputs, replay from scratch) is the same strategy used by Mozilla's `rr` debugger

**Definition of done for Stage 4:**
- Pause mid-execution, change a variable's value in the UI, resume and confirm the new value is used
- Rewind a program that uses `input()` and confirm it replays the same inputs automatically

---

### Stage 5 — Memory Tracking
**Files:** `core/memory.py`, updates to UI stats panel

Add memory usage tracking using Python's built-in `tracemalloc`.

- Start `tracemalloc` before running user code
- On each trace event, snapshot current memory with `tracemalloc.take_snapshot()`
- Report: total memory in use, memory delta since last line, top 5 allocating lines, memory per variable (using `sys.getsizeof()` on each local)
- Display as a live Chart.js line graph in the Stats panel: x-axis = lines executed, y-axis = MB in use

Key implementation notes:
- `tracemalloc` has overhead — only take snapshots every N lines (configurable, default every 10 lines) to keep performance reasonable
- `sys.getsizeof()` does NOT recurse into containers — use a recursive size helper for accurate variable sizes
- Filter `tracemalloc` snapshots by filename to separate user code from library allocations

**Definition of done for Stage 5:**
- Run a script that builds a large list and watch memory usage climb in the Chart.js graph
- Confirm the top-allocating line is correctly identified

---

### Stage 6 — DB Sandboxing + Polish + Release
**Files:** `sandbox/db_mock.py`, `README.md`, packaging

**DB Sandboxing:**
Use `unittest.mock.patch` to intercept all DB calls so they only execute once even if the user rewinds and replays. Supported patterns:
- SQLAlchemy session methods (`session.add`, `session.commit`, `session.delete`)
- Django ORM (`Model.objects.create`, `Model.save`, `Model.delete`)
- Raw `psycopg2` / `sqlite3` cursor execute calls

On first run: execute the real DB call and log the result. On replay: return the logged result without hitting the DB.

**Polish checklist:**
- Error handling: what happens if the user's code crashes? Show the exception in the UI with the line highlighted in red.
- File size limit: reject files over 500 lines with a clear message (very large files will be slow to trace)
- Loading states: show a spinner while the code is starting up
- Dark mode support in the UI

**Release checklist:**
- Write `README.md` with a GIF demo, installation steps, and usage examples
- Publish to GitHub with a good description and topics: `python`, `debugger`, `developer-tools`, `flask`
- Publish to PyPI so users can `pip install sandbox-debugger` and run `sandbox-debugger myfile.py`
- Post on Reddit: r/Python, r/programming

---

## What NOT to Do

- **Do not use Django.** Flask is sufficient. Django adds unnecessary complexity.
- **Do not try to make rewind perfect on the first attempt.** Input replay covers 90% of use cases. Handle edge cases (threads, network calls) later.
- **Do not trace library internals by default.** Filter by the user's project directory in the tracer. The user doesn't need to see what's happening inside `requests` or `sqlalchemy`.
- **Do not try to support async/multithreaded programs in the first version.** Cyberbrain tried this and it killed the project. Add it later.
- **Do not serialize variables with `json.dumps()` directly.** Many Python objects are not JSON serializable. Always use `repr()` as a fallback.

---

## Key Files to Read First

If you're an AI agent picking this project up, read these files in this order:

1. `AGENTS.md` (this file) — project overview and intent
2. `core/tracer.py` — the most important file. Everything depends on this.
3. `server/app.py` — how Flask wraps the tracer
4. `ui/main.js` — how the frontend connects to the backend

---

## Current Status

| Stage | Status |
|---|---|
| Stage 1 — Core Tracer | Not started |
| Stage 2 — Flask + WebSockets | Not started |
| Stage 3 — UI | Not started |
| Stage 4 — Controls | Not started |
| Stage 5 — Memory Tracking | Not started |
| Stage 6 — DB Sandbox + Release | Not started |

> Update this table as stages are completed.

---

## Developer Notes

- Developer has experience with Flask, Django, Django REST, HTML, CSS, JS
- No prior experience with `sys.settrace()` or `tracemalloc` — keep explanations clear
- Target: learning + portfolio + open source community tool
- Inspired by Cyberbrain (abandoned 2021) — this project fills the gap it left
- Estimated timeline: 8–10 weeks part-time
