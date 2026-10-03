"""Validate deployment inputs and archive contents using temporary fixtures."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare_deploy.py"
SPEC = importlib.util.spec_from_file_location("prepare_deploy", SCRIPT)
deploy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy)


class PrepareDeployTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="huddlehub-deploy-test-")
        self.root = Path(self.temp.name)
        self.public = self.root / "public"
        for folder in ("assets/css", "assets/fonts", "assets/js", "assets/images", "assets/videos"):
            (self.public / folder).mkdir(parents=True, exist_ok=True)
        self.html = '''<!doctype html><html><head>
          <link rel="stylesheet" href="assets/css/site.css"></head><body>
          <a href="#book">Book</a><section id="book">
          <img src="assets/images/poster.jpg"><video poster="assets/images/poster.jpg">
          <source src="assets/videos/this-week.mp4"></video>
          <script src="assets/js/booking.js"></script>
          <form name="term4-registration" method="POST" action="/" data-netlify="true" netlify-honeypot="bot-field">
          <input type="hidden" name="form-name" value="term4-registration">
          <input name="parent-name"><input name="phone"><input name="email"><input name="bot-field">
          <input type="hidden" name="children-and-groups"><textarea name="message"></textarea>
          </form></section></body></html>'''
        self.write_index()
        (self.public / "assets/css/site.css").write_text('@import "fonts.css"; body { background: url("../images/poster.jpg"); }')
        (self.public / "assets/css/fonts.css").write_text('@font-face { src: url("../fonts/local.woff2"); }')
        for name in ("assets/images/poster.jpg", "assets/fonts/local.woff2", "assets/videos/this-week.mp4", "assets/js/booking.js"):
            (self.public / name).write_bytes(b"local-test-file")

    def tearDown(self):
        self.temp.cleanup()

    def write_index(self):
        (self.public / "index.html").write_text(self.html, encoding="utf-8")

    def test_recursive_assets_and_netlify_fields_validate(self):
        checks = deploy.validate_site(self.public)
        self.assertEqual(checks["netlifyForm"], "term4-registration")
        self.assertEqual(checks["netlifyFields"], sorted(deploy.EXPECTED_FIELDS))
        self.assertEqual(checks["hashAnchorsChecked"], 1)
        self.assertGreaterEqual(checks["localReferencesChecked"], 8)

    def test_missing_css_font_and_video_are_blockers(self):
        for name in ("assets/css/site.css", "assets/fonts/local.woff2", "assets/videos/this-week.mp4"):
            with self.subTest(asset=name):
                path = self.public / name
                content = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(deploy.ValidationError, "Missing asset"):
                    deploy.validate_site(self.public)
                path.write_bytes(content)

    def test_unresolved_anchor_and_duplicate_id_are_blockers(self):
        self.html = self.html.replace('href="#book"', 'href="#missing"')
        self.write_index()
        with self.assertRaisesRegex(deploy.ValidationError, "Unresolved hash anchors"):
            deploy.validate_site(self.public)
        self.html = self.html.replace('href="#missing"', 'href="#book"') + '<div id="book"></div>'
        self.write_index()
        with self.assertRaisesRegex(deploy.ValidationError, "Duplicate HTML ids"):
            deploy.validate_site(self.public)

    def test_missing_field_and_incorrect_form_name_are_blockers(self):
        self.html = self.html.replace('<input type="hidden" name="children-and-groups">', '')
        self.write_index()
        with self.assertRaisesRegex(deploy.ValidationError, "Missing static Netlify fields"):
            deploy.validate_site(self.public)
        self.html = self.html.replace('value="term4-registration"', 'value="other-form"') + '<input name="children-and-groups">'
        self.write_index()
        with self.assertRaises(deploy.ValidationError):
            deploy.validate_site(self.public)

    def test_asset_traversal_and_symlink_are_blockers(self):
        (self.root / "outside.jpg").write_bytes(b"outside")
        self.html = self.html.replace('src="assets/images/poster.jpg"', 'src="../outside.jpg"')
        self.write_index()
        with self.assertRaisesRegex(deploy.ValidationError, "escapes public"):
            deploy.validate_site(self.public)
        self.html = self.html.replace('src="../outside.jpg"', 'src="assets/images/poster.jpg"')
        self.write_index()
        (self.public / "linked.jpg").symlink_to(self.root / "outside.jpg")
        with self.assertRaisesRegex(deploy.ValidationError, "symbolic link"):
            deploy.prepare_deploy(self.public, self.root / "site.zip", self.root / "manifest.json")

    def test_complete_archive_and_exact_sha256_manifest(self):
        (self.public / ".DS_Store").write_text("junk")
        (self.public / "assets/.env").write_text("not-for-upload")
        (self.public / "robots.txt").write_text("User-agent: *")
        archive, manifest_file = self.root / "site.zip", self.root / "manifest.json"
        manifest = deploy.prepare_deploy(self.public, archive, manifest_file)
        self.assertEqual(manifest, json.loads(manifest_file.read_text()))
        self.assertEqual(manifest["archive"]["sha256"], deploy.file_hash(archive))
        with zipfile.ZipFile(archive) as package:
            self.assertEqual(set(package.namelist()), {record["path"] for record in manifest["files"]})
            self.assertIn("assets/videos/this-week.mp4", package.namelist())
            self.assertIn("robots.txt", package.namelist())
            self.assertNotIn(".DS_Store", package.namelist())
            self.assertNotIn("assets/.env", package.namelist())
            for record in manifest["files"]:
                self.assertEqual(record["bytes"], len(package.read(record["path"])))
        self.assertEqual(manifest["excluded"], [".DS_Store", "assets/.env"])


if __name__ == "__main__":
    unittest.main()
