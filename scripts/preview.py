#!/usr/bin/env python3
"""Serve the site on loopback and simulate Netlify form submissions locally."""

import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import re
import threading
import time
from urllib.parse import parse_qs, unquote, urlsplit


PUBLIC_DIR = Path(__file__).resolve().parents[1] / "public"
SUBMISSIONS_FILE = Path("/tmp/huddlehub-local-submissions.jsonl")
MAX_BODY_BYTES = 64 * 1024
FORM_NAMES = frozenset({"term4-registration"})


def byte_range(header, size):
    """Return an inclusive single range, or None for an unsupported range unit.

    Multiple ranges are deliberately ignored rather than returning multipart
    content. Malformed or unsatisfiable single byte ranges raise ValueError.
    """
    unit, separator, value = header.strip().partition("=")
    if unit.lower() != "bytes":
        return None
    if "," in value:
        return None
    match = re.fullmatch(r"([0-9]*)-([0-9]*)", value) if separator else None
    if not match or not any(match.groups()) or size == 0:
        raise ValueError("Invalid byte range")
    first, last = match.groups()
    if not first:
        suffix = int(last)
        if suffix == 0:
            raise ValueError("Empty suffix range")
        return max(0, size - suffix), size - 1
    start = int(first)
    end = int(last) if last else size - 1
    if start >= size or end < start:
        raise ValueError("Unsatisfiable byte range")
    return start, min(end, size - 1)


class PreviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port=5173, directory=PUBLIC_DIR,
                 submissions_file=SUBMISSIONS_FILE, delay_post=0):
        self.public_dir = Path(directory).resolve()
        self.submissions_file = Path(submissions_file)
        self.delay_post = delay_post
        self.record_lock = threading.Lock()
        self.failure_lock = threading.Lock()
        self.fail_next_submission = False
        handler = partial(PreviewHandler, directory=str(self.public_dir))
        # Deliberately no configurable host: test records must remain local.
        super().__init__(("127.0.0.1", port), handler)

    def open_records(self, write=False):
        flags = (os.O_WRONLY | os.O_APPEND | os.O_CREAT) if write else os.O_RDONLY
        flags |= getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.submissions_file, flags, 0o600)
        if write:
            os.fchmod(fd, 0o600)
        return os.fdopen(fd, "a" if write else "r", encoding="utf-8")


class PreviewHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_head(self):
        # Always read the current local file after an edit, even when a browser
        # sends validators for its cached copy.
        for name in ("If-Modified-Since", "If-None-Match"):
            if name in self.headers:
                del self.headers[name]
        self._range_remaining = None
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        try:
            source = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None
        try:
            stat = os.fstat(source.fileno())
            selected = None
            # Range is defined only for GET. HEAD describes a full GET response
            # without transferring its body, regardless of a Range header.
            header = self.headers.get("Range") if self.command == "GET" else None
            validator = self.headers.get("If-Range")
            if header and (not validator or self.range_validator_matches(validator, stat.st_mtime)):
                try:
                    selected = byte_range(header, stat.st_size)
                except ValueError:
                    source.close()
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{stat.st_size}")
                    self.send_header("Content-Length", "0")
                    self.send_header("Accept-Ranges", "bytes")
                    self.end_headers()
                    return None
            self.send_response(206 if selected else 200)
            self.send_header("Content-Type", self.guess_type(path))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Last-Modified", self.date_time_string(stat.st_mtime))
            if selected:
                start, end = selected
                self._range_remaining = end - start + 1
                self.send_header("Content-Range", f"bytes {start}-{end}/{stat.st_size}")
                self.send_header("Content-Length", str(self._range_remaining))
                source.seek(start)
            else:
                self.send_header("Content-Length", str(stat.st_size))
            self.end_headers()
            return source
        except Exception:
            source.close()
            raise

    @staticmethod
    def range_validator_matches(validator, modified):
        # The preview does not issue ETags. Only an exact Last-Modified date can
        # validate an If-Range request; unknown/stale validators get a full file.
        try:
            date = parsedate_to_datetime(validator)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            return date.timestamp() == int(modified)
        except (TypeError, ValueError, OverflowError):
            return False

    def copyfile(self, source, outputfile):
        remaining = self._range_remaining
        if remaining is None:
            return super().copyfile(source, outputfile)
        while remaining:
            chunk = source.read(min(64 * 1024, remaining))
            if not chunk:
                break
            try:
                outputfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                break
            remaining -= len(chunk)

    def log_message(self, _format, *_args):
        # URLs and request bodies can contain names, email addresses or notes.
        # Avoid printing any of them to the console.
        pass

    def json_response(self, status, payload):
        data = json.dumps({"localPreview": True, **payload}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def local_request(self):
        port = self.server.server_port
        allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if self.headers.get("Host", "").lower() not in allowed_hosts:
            self.json_response(403, {"ok": False, "error": "Loopback requests only."})
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://{host}" for host in allowed_hosts}:
            self.json_response(403, {"ok": False, "error": "Use the local preview origin."})
            return False
        return True

    def safe_static_path(self):
        try:
            path = unquote(urlsplit(self.path).path, errors="strict")
            if "\x00" in path or "\\" in path or ".." in path.split("/"):
                return False
            resolved = (self.server.public_dir / path.lstrip("/")).resolve()
            return resolved.is_relative_to(self.server.public_dir)
        except (ValueError, UnicodeError):
            return False

    def do_GET(self):
        if not self.local_request():
            return
        path = urlsplit(self.path).path
        if path == "/__preview/submissions":
            try:
                with self.server.record_lock:
                    with self.server.open_records() as records:
                        submissions = [json.loads(line) for line in records if line.strip()]
            except FileNotFoundError:
                submissions = []
            except (OSError, ValueError):
                self.json_response(500, {"ok": False, "error": "Could not read local test records."})
                return
            self.json_response(200, {"ok": True, "submissions": submissions})
            return
        if path.startswith("/__preview/"):
            self.json_response(404, {"ok": False, "error": "Unknown preview route."})
            return
        if not self.safe_static_path():
            self.json_response(403, {"ok": False, "error": "Path is outside the public directory."})
            return
        super().do_GET()

    def do_HEAD(self):
        if not self.local_request():
            return
        if not self.safe_static_path():
            self.send_error(403)
            return
        super().do_HEAD()

    def do_POST(self):
        if not self.local_request():
            return
        path = urlsplit(self.path).path
        if path == "/__preview/fail-next":
            with self.server.failure_lock:
                self.server.fail_next_submission = True
            self.json_response(200, {"ok": True, "nextSubmissionWillFail": True})
            return
        if path != "/":
            self.json_response(404, {"ok": False, "error": "Unknown submission route."})
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/x-www-form-urlencoded":
            self.json_response(415, {"ok": False, "error": "Use an URL-encoded form body."})
            return
        if self.headers.get("Transfer-Encoding"):
            self.json_response(400, {"ok": False, "error": "Use Content-Length for local submissions."})
            return
        try:
            size = int(self.headers["Content-Length"])
        except (KeyError, TypeError, ValueError):
            self.json_response(411, {"ok": False, "error": "A valid Content-Length is required."})
            return
        if size < 0:
            self.json_response(400, {"ok": False, "error": "Invalid Content-Length."})
            return
        if size > MAX_BODY_BYTES:
            self.json_response(413, {"ok": False, "error": "Test submission exceeds 64 KB."})
            return
        try:
            body = self.rfile.read(size).decode("utf-8")
            fields = parse_qs(body, keep_blank_values=True, errors="strict", max_num_fields=256)
        except (UnicodeError, ValueError):
            self.json_response(400, {"ok": False, "error": "Invalid URL-encoded form body."})
            return
        form_names = fields.get("form-name", [])
        if len(form_names) != 1 or form_names[0] not in FORM_NAMES:
            self.json_response(400, {"ok": False, "error": "Unknown or missing form name."})
            return
        if self.server.delay_post:
            time.sleep(self.server.delay_post)
        with self.server.failure_lock:
            fail = self.server.fail_next_submission
            self.server.fail_next_submission = False
        if fail:
            self.json_response(503, {"ok": False, "error": "Simulated local submission failure."})
            return
        record = {
            "submittedAt": datetime.now(timezone.utc).isoformat(),
            "formName": form_names[0],
            "fields": fields,
        }
        try:
            with self.server.record_lock:
                with self.server.open_records(write=True) as records:
                    records.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            self.json_response(500, {"ok": False, "error": "Could not save local test submission."})
            return
        self.json_response(200, {"ok": True, "delivery": "local-only"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5173, help="Loopback port (default: 5173)")
    parser.add_argument("--delay-post", type=float, default=0,
                        help="Delay accepted submissions to test the sending state")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    if not math.isfinite(args.delay_post) or not 0 <= args.delay_post <= 60:
        parser.error("delay-post must be between 0 and 60 seconds")
    with PreviewServer(port=args.port, delay_post=args.delay_post) as server:
        print(f"Local preview: http://127.0.0.1:{server.server_port}", flush=True)
        print(f"Test submissions only: {SUBMISSIONS_FILE}. No external submission or email delivery.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
