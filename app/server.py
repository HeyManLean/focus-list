#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""专注清单 · 本地服务器 + SQLite 数据库

使用方法:
    python3 server.py
    然后浏览器打开 http://localhost:8765

数据保存在同目录下的 focuslist.db (SQLite)。
"""
import json
import os
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(BASE, "index.html")
DB = os.path.join(BASE, "focuslist.db")
PORT = int(os.environ.get("PORT", "8765"))
HOST = "127.0.0.1"
TIMER_FILE = os.path.join(BASE, "timer-state.json")

write_lock = threading.Lock()


def read_timer_state():
    try:
        with open(TIMER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"mode": "work", "status": "idle", "endAt": 0, "startedAt": 0, "remaining": 1500}


def write_timer_state(state):
    state["updatedAt"] = int(time.time() * 1000)
    with write_lock:
        with open(TIMER_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)


def connect():
    conn = sqlite3.connect(DB, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS groups(
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              color TEXT DEFAULT '',
              sort INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS settings(
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks(
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              notes TEXT DEFAULT '',
              priority INTEGER DEFAULT 1,
              estimate INTEGER DEFAULT 1,
              due TEXT DEFAULT '',
              created INTEGER DEFAULT 0,
              completed INTEGER DEFAULT 0,
              completed_at INTEGER DEFAULT 0,
              pomos INTEGER DEFAULT 0,
              last_focused INTEGER DEFAULT 0,
              group_id TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS sessions(
              id TEXT PRIMARY KEY,
              type TEXT NOT NULL,
              task_id TEXT,
              start INTEGER NOT NULL,
              end INTEGER NOT NULL,
              mins INTEGER NOT NULL
            );
            """
        )
        cols = [r[1] for r in conn.execute("PRAGMA table_info(tasks)")]
        if "group_id" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN group_id TEXT DEFAULT ''")
        conn.commit()
    finally:
        conn.close()


def read_state():
    conn = connect()
    try:
        tasks = []
        for r in conn.execute("SELECT * FROM tasks"):
            tasks.append({
                "id": r["id"], "title": r["title"], "notes": r["notes"],
                "priority": r["priority"], "estimate": r["estimate"], "due": r["due"],
                "created": r["created"], "completed": bool(r["completed"]),
                "completedAt": r["completed_at"], "pomos": r["pomos"],
                "lastFocused": r["last_focused"],
                "groupId": r["group_id"] or "",
            })
        sessions = []
        for r in conn.execute("SELECT * FROM sessions"):
            sessions.append({
                "id": r["id"], "type": r["type"], "taskId": r["task_id"],
                "start": r["start"], "end": r["end"], "mins": r["mins"],
            })
        settings = {}
        row = conn.execute("SELECT value FROM settings WHERE key='settings'").fetchone()
        if row:
            try:
                settings = json.loads(row["value"])
            except Exception:
                settings = {}
        groups = []
        for r in conn.execute("SELECT * FROM groups ORDER BY sort"):
            groups.append({
                "id": r["id"], "name": r["name"],
                "color": r["color"], "sort": r["sort"],
            })
        return {"tasks": tasks, "sessions": sessions, "settings": settings, "groups": groups}
    finally:
        conn.close()


def write_state(data):
    tasks = data.get("tasks") or []
    sessions = data.get("sessions") or []
    settings = data.get("settings") or {}
    groups = data.get("groups") or []
    conn = connect()
    try:
        with write_lock:
            conn.execute("DELETE FROM tasks")
            conn.execute("DELETE FROM sessions")
            conn.execute("DELETE FROM settings")
            conn.execute("DELETE FROM groups")
            conn.executemany(
                "INSERT INTO tasks(id,title,notes,priority,estimate,due,created,completed,completed_at,pomos,last_focused,group_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                [(
                    t.get("id") or "", str(t.get("title") or ""), str(t.get("notes") or ""),
                    int(t.get("priority", 1)), int(t.get("estimate", 1)), str(t.get("due") or ""),
                    int(t.get("created", 0) or 0), 1 if t.get("completed") else 0,
                    int(t.get("completedAt", 0) or 0), int(t.get("pomos", 0) or 0),
                    int(t.get("lastFocused", 0) or 0),
                ) for t in tasks],
            )
            conn.executemany(
                "INSERT INTO sessions(id,type,task_id,start,end,mins) VALUES(?,?,?,?,?,?)",
                [(
                    s.get("id") or "", s.get("type") or "work", s.get("taskId"),
                    int(s.get("start", 0) or 0), int(s.get("end", 0) or 0),
                    int(s.get("mins", 0) or 0),
                ) for s in sessions],
            )
            conn.execute(
                "INSERT OR REPLACE INTO settings(key,value) VALUES('settings',?)",
                (json.dumps(settings, ensure_ascii=False),),
            )
            conn.executemany(
                "INSERT OR REPLACE INTO groups(id,name,color,sort) VALUES(?,?,?,?)",
                [(g.get("id") or "", str(g.get("name") or ""), str(g.get("color") or ""),
                  int(g.get("sort", 0) or 0)) for g in groups],
            )
            conn.commit()
    finally:
        conn.close()


def wipe_state():
    conn = connect()
    try:
        with write_lock:
            conn.execute("DELETE FROM tasks")
            conn.execute("DELETE FROM sessions")
            conn.execute("DELETE FROM settings")
            conn.commit()
    finally:
        conn.close()



def task_to_row(t):
    return (
        t.get("id") or "", str(t.get("title") or ""), str(t.get("notes") or ""),
        int(t.get("priority", 1)), int(t.get("estimate", 1)), str(t.get("due") or ""),
        int(t.get("created", 0) or 0), 1 if t.get("completed") else 0,
        int(t.get("completedAt", 0) or 0), int(t.get("pomos", 0) or 0),
        int(t.get("lastFocused", 0) or 0),
        str(t.get("groupId") or ""),
    )


def session_to_row(s):
    return (
        s.get("id") or "", s.get("type") or "work", s.get("taskId"),
        int(s.get("start", 0) or 0), int(s.get("end", 0) or 0),
        int(s.get("mins", 0) or 0),
    )


def upsert_task(task):
    conn = connect()
    try:
        with write_lock:
            conn.execute(
                "INSERT OR REPLACE INTO tasks(id,title,notes,priority,estimate,due,created,completed,completed_at,pomos,last_focused,group_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                task_to_row(task),
            )
            conn.commit()
    finally:
        conn.close()


def delete_task(task_id):
    conn = connect()
    try:
        with write_lock:
            conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            conn.commit()
    finally:
        conn.close()


def upsert_session(session):
    conn = connect()
    try:
        with write_lock:
            conn.execute(
                "INSERT OR REPLACE INTO sessions(id,type,task_id,start,end,mins) VALUES(?,?,?,?,?,?)",
                session_to_row(session),
            )
            conn.commit()
    finally:
        conn.close()



def upsert_group(group):
    conn = connect()
    try:
        with write_lock:
            conn.execute(
                "INSERT OR REPLACE INTO groups(id,name,color,sort) VALUES(?,?,?,?)",
                (group.get("id") or "", str(group.get("name") or ""),
                 str(group.get("color") or ""), int(group.get("sort", 0) or 0)),
            )
            conn.commit()
    finally:
        conn.close()


def delete_group(group_id):
    conn = connect()
    try:
        with write_lock:
            conn.execute("DELETE FROM groups WHERE id=?", (group_id,))
            conn.commit()
    finally:
        conn.close()


def put_settings(settings):
    conn = connect()
    try:
        with write_lock:
            conn.execute(
                "INSERT OR REPLACE INTO settings(key,value) VALUES('settings',?)",
                (json.dumps(settings, ensure_ascii=False),),
            )
            conn.commit()
    finally:
        conn.close()



def ai_chat(data):
    """Proxy an OpenAI-compatible chat completion request."""
    base = (data.get("baseUrl") or "").strip().rstrip("/")
    key = (data.get("apiKey") or "").strip()
    model = (data.get("model") or "").strip()
    messages = data.get("messages")
    if not base or not model or not messages:
        raise ValueError("缺少 Base URL / 模型 / 消息配置")
    url = base
    if not url.endswith("/chat/completions"):
        url = url + "/chat/completions"
    payload = {"model": model, "messages": messages, "temperature": 0.7}
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST"
    )
    req.add_header("Content-Type", "application/json")
    if key:
        req.add_header("Authorization", "Bearer " + key)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        return content
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", "replace")[:500]
        raise RuntimeError("API 返回 %s：%s" % (e.code, err))
    except Exception as e:
        raise RuntimeError("请求失败：" + str(e))


def json_response(handler, obj, status=200):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def error_response(handler, msg, status=400):
    json_response(handler, {"ok": False, "error": msg}, status)


class Handler(BaseHTTPRequestHandler):
    server_version = "FocusList/1.0"

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/state":
            json_response(self, read_state())
        elif path == "/api/info":
            json_response(self, {"db": DB, "storage": "sqlite"})
        elif path == "/api/timer":
            json_response(self, read_timer_state())
        elif path in ("/", "/index.html"):
            self.serve_index()
        else:
            error_response(self, "not found", 404)

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return None

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/state":
            if self.headers.get("X-Client-Version") != "2":
                return error_response(self, "页面版本过旧，请刷新页面后重试", 400)
            data = self.read_json()
            if data is None:
                return error_response(self, "invalid JSON")
            try:
                write_state(data)
                json_response(self, {"ok": True})
            except Exception as e:
                error_response(self, str(e), 500)
        elif path == "/api/task":
            data = self.read_json()
            if data is None or not data.get("id"):
                return error_response(self, "invalid task")
            try:
                upsert_task(data)
                json_response(self, {"ok": True})
            except Exception as e:
                error_response(self, str(e), 500)
        elif path == "/api/session":
            data = self.read_json()
            if data is None or not data.get("id"):
                return error_response(self, "invalid session")
            try:
                upsert_session(data)
                json_response(self, {"ok": True})
            except Exception as e:
                error_response(self, str(e), 500)
        elif path == "/api/group":
            data = self.read_json()
            if data is None or not data.get("id"):
                return error_response(self, "invalid group")
            try:
                upsert_group(data)
                json_response(self, {"ok": True})
            except Exception as e:
                error_response(self, str(e), 500)
        elif path == "/api/ai/chat":
            data = self.read_json()
            if data is None:
                return error_response(self, "invalid JSON")
            try:
                content = ai_chat(data)
                json_response(self, {"ok": True, "content": content})
            except Exception as e:
                error_response(self, str(e), 400)
        elif path == "/api/timer":
            data = self.read_json()
            if data is None or not isinstance(data, dict):
                return error_response(self, "invalid timer state")
            try:
                write_timer_state({k: data.get(k) for k in ("mode", "status", "endAt", "startedAt", "remaining")})
                json_response(self, {"ok": True})
            except Exception as e:
                error_response(self, str(e), 500)
        elif path == "/api/settings":
            data = self.read_json()
            if data is None:
                return error_response(self, "invalid settings")
            try:
                put_settings(data)
                json_response(self, {"ok": True})
            except Exception as e:
                error_response(self, str(e), 500)
        else:
            return error_response(self, "not found", 404)

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path == "/api/state":
            try:
                wipe_state()
                json_response(self, {"ok": True})
            except Exception as e:
                error_response(self, str(e), 500)
        elif path == "/api/group":
            from urllib.parse import parse_qs
            qs = parse_qs(urlparse(self.path).query)
            group_id = (qs.get("id") or [None])[0]
            if not group_id:
                return error_response(self, "missing id")
            try:
                delete_group(group_id)
                json_response(self, {"ok": True})
            except Exception as e:
                error_response(self, str(e), 500)
        elif path == "/api/task":
            from urllib.parse import parse_qs
            qs = parse_qs(urlparse(self.path).query)
            task_id = (qs.get("id") or [None])[0]
            if not task_id:
                return error_response(self, "missing id")
            try:
                delete_task(task_id)
                json_response(self, {"ok": True})
            except Exception as e:
                error_response(self, str(e), 500)
        else:
            return error_response(self, "not found", 404)

    def serve_index(self):
        try:
            with open(INDEX, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except FileNotFoundError:
            error_response(self, "index.html not found", 500)

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))


def main():
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.daemon_threads = True
    url = "http://%s:%d" % (HOST, PORT)
    print("=" * 54)
    print("  专注清单 · 本地服务器已启动")
    print("  数据库文件 : %s" % DB)
    print("  访问地址   : %s" % url)
    print("  停止服务   : Ctrl + C")
    print("=" * 54)
    if not os.environ.get("FL_SKIP_BROWSER"):
        try:
            threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止服务")


if __name__ == "__main__":
    main()
