"""Local preview request tests; no external services or dependencies."""

from contextlib import redirect_stderr, redirect_stdout
import http.client
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.parse import urlencode


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "preview.py"
SPEC = importlib.util.spec_from_file_location("preview", SCRIPT)
preview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview)


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="huddlehub-preview-test-")
        self.root = Path(self.temp.name)
        self.public = self.root / "public"
        self.public.mkdir()
        (self.public / "index.html").write_text("<h1>Local test site</h1>")
        (self.public / "assets/videos").mkdir(parents=True)
        self.video = b"0123456789abcdefghijklmnopqrstuvwxyz"
        (self.public / "assets/videos/test.mp4").write_bytes(self.video)
        self.records = self.root / "submissions.jsonl"
        self.server = preview.PreviewServer(port=0, directory=self.public, submissions_file=self.records)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        status, content_type, data = response.status, response.getheader("Content-Type"), response.read()
        connection.close()
        payload = json.loads(data) if content_type and content_type.startswith("application/json") else data.decode()
        return status, payload

    def submit(self, name="term4-registration", **fields):
        return self.request("POST", "/", urlencode({"form-name": name, **fields}),
                            {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})

    def submissions(self):
        status, payload = self.request("GET", "/__preview/submissions")
        self.assertEqual(status, 200)
        return payload["submissions"]

    def media_request(self, headers=None, method="GET", path="/assets/videos/test.mp4"):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        connection.request(method, path, headers=headers or {})
        response = connection.getresponse()
        status, response_headers, data = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return status, response_headers, data

    def test_loopback_and_static_site(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        status, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("Local test site", body)
        self.assertEqual(self.submissions(), [])

    def test_static_edits_bypass_browser_cache(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        connection.request("GET", "/", headers={"If-Modified-Since": "Wed, 31 Dec 2099 23:59:59 GMT"})
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("Cache-Control"), "no-store")
        response.read()
        connection.close()
        (self.public / "index.html").write_text("Updated local page")
        self.assertEqual(self.request("GET", "/")[1], "Updated local page")
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        connection.request("GET", "/__preview/submissions")
        response = connection.getresponse()
        self.assertEqual(response.getheader("Cache-Control"), "no-store")
        response.read()
        connection.close()

    def test_static_video_full_response(self):
        status, headers, body = self.media_request()
        self.assertEqual(status, 200)
        self.assertEqual(body, self.video)
        self.assertEqual(headers["Content-Type"], "video/mp4")
        self.assertEqual(headers["Content-Length"], str(len(self.video)))
        self.assertEqual(headers["Accept-Ranges"], "bytes")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertNotIn("Content-Range", headers)

    def test_static_single_byte_ranges(self):
        cases = [("bytes=3-8", 3, 8), ("bytes=29-", 29, 35),
                 ("bytes=-4", 32, 35), ("bytes=30-999", 30, 35),
                 ("bytes=-999", 0, 35), ("bytes=0-0", 0, 0)]
        for requested, start, end in cases:
            with self.subTest(range=requested):
                status, headers, body = self.media_request({"Range": requested},
                                                          path="/assets/videos/test.mp4?v=changed")
                self.assertEqual(status, 206)
                self.assertEqual(body, self.video[start:end + 1])
                self.assertEqual(headers["Content-Range"], f"bytes {start}-{end}/{len(self.video)}")
                self.assertEqual(headers["Content-Length"], str(end - start + 1))
                self.assertEqual(headers["Accept-Ranges"], "bytes")

    def test_static_invalid_and_unsatisfiable_ranges(self):
        for requested in ("bytes=36-", "bytes=8-3", "bytes=-0", "bytes=-", "bytes=abc", "bytes=1-2-3"):
            with self.subTest(range=requested):
                status, headers, body = self.media_request({"Range": requested})
                self.assertEqual(status, 416)
                self.assertEqual(headers["Content-Range"], f"bytes */{len(self.video)}")
                self.assertEqual(headers["Content-Length"], "0")
                self.assertEqual(body, b"")
        (self.public / "assets/videos/empty.mp4").write_bytes(b"")
        status, headers, body = self.media_request({"Range": "bytes=0-"}, path="/assets/videos/empty.mp4")
        self.assertEqual(status, 416)
        self.assertEqual(headers["Content-Range"], "bytes */0")
        self.assertEqual(body, b"")

    def test_static_head_ignores_range(self):
        for requested in ("bytes=3-8", "bytes=999-"):
            with self.subTest(range=requested):
                status, headers, body = self.media_request({"Range": requested}, method="HEAD")
                self.assertEqual(status, 200)
                self.assertEqual(headers["Content-Length"], str(len(self.video)))
                self.assertEqual(headers["Accept-Ranges"], "bytes")
                self.assertNotIn("Content-Range", headers)
                self.assertEqual(body, b"")

    def test_static_unsupported_ranges_fall_back_to_full_file(self):
        for requested in ("bytes=1-2,5-6", "items=0-2"):
            with self.subTest(range=requested):
                status, headers, body = self.media_request({"Range": requested})
                self.assertEqual(status, 200)
                self.assertEqual(body, self.video)
                self.assertNotIn("Content-Range", headers)

    def test_static_if_range_requires_current_validator(self):
        _, full_headers, _ = self.media_request()
        status, _, body = self.media_request({"Range": "bytes=2-4", "If-Range": full_headers["Last-Modified"]})
        self.assertEqual(status, 206)
        self.assertEqual(body, self.video[2:5])
        for validator in ('"unknown-etag"', "Sat, 01 Jan 2000 00:00:00 GMT", "invalid-date"):
            with self.subTest(validator=validator):
                status, headers, body = self.media_request({"Range": "bytes=2-4", "If-Range": validator})
                self.assertEqual(status, 200)
                self.assertEqual(body, self.video)
                self.assertNotIn("Content-Range", headers)

    def test_static_ranges_do_not_bypass_path_guards(self):
        (self.root / "secret.mp4").write_bytes(b"outside-public")
        (self.public / "linked.mp4").symlink_to(self.root / "secret.mp4")
        for path in ("/../secret.mp4", "/%2e%2e/secret.mp4", "/linked.mp4", "/%00"):
            with self.subTest(path=path):
                status, _, body = self.media_request({"Range": "bytes=0-1"}, path=path)
                self.assertEqual(status, 403)
                self.assertNotIn(b"outside-public", body)

    def test_known_forms_save_local_records_only(self):
        for name in sorted(preview.FORM_NAMES):
            with self.subTest(form=name):
                status, payload = self.submit(name, **{"parent-name": "Test Parent", "phone": "0000000000"})
                self.assertEqual(status, 200)
                self.assertEqual(payload, {"localPreview": True, "ok": True, "delivery": "local-only"})
        records = self.submissions()
        self.assertEqual({r["formName"] for r in records}, preview.FORM_NAMES)
        self.assertEqual(records[0]["fields"]["parent-name"], ["Test Parent"])
        self.assertEqual(self.records.stat().st_mode & 0o777, 0o600)

    def test_invalid_form_names_do_not_save(self):
        status, _ = self.submit("unknown")
        self.assertEqual(status, 400)
        status, _ = self.request("POST", "/", "form-name=term4-registration&form-name=coach-application",
                                 {"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(status, 400)
        self.assertEqual(self.submissions(), [])

    def test_invalid_type_and_large_body_do_not_save(self):
        status, _ = self.request("POST", "/", "{}", {"Content-Type": "application/json"})
        self.assertEqual(status, 415)
        status, _ = self.request("POST", "/", "x" * (preview.MAX_BODY_BYTES + 1),
                                 {"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(status, 413)
        self.assertEqual(self.submissions(), [])

    def test_fail_next_once_then_recover(self):
        status, payload = self.request("POST", "/__preview/fail-next", "")
        self.assertEqual(status, 200)
        self.assertTrue(payload["nextSubmissionWillFail"])
        # Invalid submissions do not consume the requested failure.
        self.assertEqual(self.submit("unknown")[0], 400)
        self.assertEqual(self.submit()[0], 503)
        self.assertEqual(self.submissions(), [])
        self.assertEqual(self.submit()[0], 200)
        self.assertEqual(len(self.submissions()), 1)

    def test_traversal_and_symlink_are_denied(self):
        secret = self.root / "secret.txt"
        secret.write_text("outside-public")
        (self.public / "linked.txt").symlink_to(secret)
        for path in ["/../secret.txt", "/%2e%2e/secret.txt", "/linked.txt", "/%00"]:
            with self.subTest(path=path):
                status, _ = self.request("GET", path)
                self.assertEqual(status, 403)

    def test_foreign_host_and_origin_are_denied(self):
        status, _ = self.request("GET", "/__preview/submissions", headers={"Host": "example.com"})
        self.assertEqual(status, 403)
        status, _ = self.request("POST", "/__preview/fail-next", "", {"Origin": "https://example.com"})
        self.assertEqual(status, 403)

    def test_unknown_routes(self):
        self.assertEqual(self.request("POST", "/other", "")[0], 404)
        self.assertEqual(self.request("GET", "/__preview/other")[0], 404)

    def test_delay_and_no_personal_data_in_console(self):
        self.server.delay_post = 0.1
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            start = time.monotonic()
            self.assertEqual(self.submit(**{"parent-name": "Private Test Name"})[0], 200)
            self.assertGreaterEqual(time.monotonic() - start, 0.09)
            self.request("GET", "/?email=private-test@example.test")
        self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
