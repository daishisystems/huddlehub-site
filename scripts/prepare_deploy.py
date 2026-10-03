#!/usr/bin/env python3
"""Validate the static site and prepare a complete archive without deploying it."""

import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import zipfile


PUBLIC_DIR = Path(__file__).resolve().parents[1] / "public"
ARCHIVE_PATH = Path("/tmp/huddlehub-term4-deploy.zip")
MANIFEST_PATH = Path("/tmp/huddlehub-term4-manifest.json")
EXPECTED_FORM = "term4-registration"
EXPECTED_FIELDS = frozenset({
    "form-name", "parent-name", "phone", "email", "children-and-groups", "message", "bot-field",
})
SITE_HOSTS = frozenset({"huddlehub.co.za", "www.huddlehub.co.za"})
JUNK_NAMES = frozenset({".DS_Store", "Thumbs.db", "desktop.ini", "__MACOSX", "__pycache__", ".git", ".netlify", "node_modules"})
CSS_URL = re.compile(r"url\(\s*(?:\"([^\"]*)\"|'([^']*)'|([^)]*?))\s*\)", re.IGNORECASE)
CSS_IMPORT = re.compile(r"@import\s+(?:\"([^\"]+)\"|'([^']+)')", re.IGNORECASE)


class ValidationError(Exception):
    pass


def is_junk(relative):
    return any(part in JUNK_NAMES or part.startswith("._") or part.startswith(".env")
               or part.endswith(("~", ".swp", ".swo", ".tmp", ".pyc", ".log"))
               for part in relative.parts)


class SiteHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.duplicate_ids = set()
        self.references = []
        self.anchors = []
        self.forms = []
        self.current_form = None
        self.styles = []
        self.in_style = False

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        element_id = attrs.get("id")
        if element_id:
            if element_id in self.ids:
                self.duplicate_ids.add(element_id)
            self.ids.add(element_id)
        for attr in ("src", "poster"):
            if attrs.get(attr):
                self.references.append(attrs[attr])
        if tag == "object" and attrs.get("data"):
            self.references.append(attrs["data"])
        if attrs.get("href"):
            reference = attrs["href"]
            if reference.startswith("#"):
                self.anchors.append(unquote(reference[1:]))
            else:
                self.references.append(reference)
        if attrs.get("srcset"):
            # Data URLs are embedded, so there is no file to validate.
            if not attrs["srcset"].lstrip().startswith("data:"):
                self.references.extend(item.strip().split()[0] for item in attrs["srcset"].split(",") if item.strip())
        if attrs.get("style"):
            self.styles.append(attrs["style"])
        if tag == "style":
            self.in_style = True
        if tag == "form":
            self.current_form = {"attributes": attrs, "fields": {}}
            self.forms.append(self.current_form)
        elif tag in {"input", "textarea", "select", "button"} and self.current_form is not None:
            if attrs.get("name"):
                self.current_form["fields"].setdefault(attrs["name"], []).append(attrs)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "form":
            self.current_form = None
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.styles.append(data)


def css_references(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    for pattern in (CSS_URL, CSS_IMPORT):
        for match in pattern.finditer(css):
            yield next(part.strip() for part in match.groups() if part is not None)


def local_reference(reference, source, public):
    parsed = urlsplit(reference.strip())
    if parsed.scheme or parsed.netloc:
        if parsed.scheme not in {"http", "https", ""} or parsed.hostname not in SITE_HOSTS:
            return None
        base = public
    else:
        base = public if parsed.path.startswith("/") else source.parent
    if not parsed.path:
        return None
    if parsed.path == "/__preview/submissions" and not parsed.scheme and not parsed.netloc:
        # The hidden local receipt link names a preview API, not a static file.
        return None
    path = unquote(parsed.path)
    if "\x00" in path or "\\" in path:
        raise ValidationError(f"Invalid asset path in {source.relative_to(public)}: {reference}")
    candidate = (base / path.lstrip("/")).resolve()
    if not candidate.is_relative_to(public):
        raise ValidationError(f"Asset escapes public directory in {source.relative_to(public)}: {reference}")
    if candidate.is_dir():
        candidate /= "index.html"
    if is_junk(candidate.relative_to(public)):
        raise ValidationError(f"Referenced file would be excluded: {candidate.relative_to(public)}")
    if not candidate.is_file():
        raise ValidationError(f"Missing asset in {source.relative_to(public)}: {reference}")
    return candidate


def validate_site(public=PUBLIC_DIR):
    public = Path(public).resolve()
    index = public / "index.html"
    if not index.is_file():
        raise ValidationError("public/index.html is missing")
    inspected = set()
    documents = {}
    pending = [index]
    reference_count = 0
    while pending:
        source = pending.pop()
        if source in inspected:
            continue
        inspected.add(source)
        if source.suffix.lower() == ".html":
            parser = SiteHTML()
            parser.feed(source.read_text(encoding="utf-8"))
            documents[source] = parser
            if parser.duplicate_ids:
                raise ValidationError(f"Duplicate HTML ids: {', '.join(sorted(parser.duplicate_ids))}")
            missing = sorted(set(parser.anchors) - parser.ids - {""})
            if missing:
                raise ValidationError(f"Unresolved hash anchors in {source.relative_to(public)}: {', '.join(missing)}")
            references = parser.references + [ref for style in parser.styles for ref in css_references(style)]
        elif source.suffix.lower() == ".css":
            references = list(css_references(source.read_text(encoding="utf-8")))
        else:
            continue
        for reference in references:
            target = local_reference(reference, source, public)
            if target is not None:
                reference_count += 1
                if target.suffix.lower() in {".html", ".css"}:
                    pending.append(target)
    parser = documents[index]
    matches = [form for form in parser.forms if form["attributes"].get("name") == EXPECTED_FORM]
    if len(matches) != 1:
        raise ValidationError("Exactly one static term4-registration form is required")
    form = matches[0]
    attrs = form["attributes"]
    if attrs.get("method", "").upper() != "POST" or attrs.get("action") != "/":
        raise ValidationError("Term 4 form must POST to /")
    if attrs.get("data-netlify") != "true" or attrs.get("netlify-honeypot") != "bot-field":
        raise ValidationError("Term 4 form requires Netlify detection and its bot-field honeypot")
    missing_fields = sorted(EXPECTED_FIELDS - form["fields"].keys())
    if missing_fields:
        raise ValidationError(f"Missing static Netlify fields: {', '.join(missing_fields)}")
    names = form["fields"]["form-name"]
    if len(names) != 1 or names[0].get("type") != "hidden" or names[0].get("value") != EXPECTED_FORM:
        raise ValidationError("Hidden form-name must equal term4-registration")
    return {"localReferencesChecked": reference_count, "hashAnchorsChecked": len(parser.anchors),
            "netlifyForm": EXPECTED_FORM, "netlifyFields": sorted(EXPECTED_FIELDS)}


def inventory(public):
    files, excluded = [], []
    for path in sorted(public.rglob("*")):
        relative = path.relative_to(public)
        if is_junk(relative):
            if path.is_file():
                excluded.append(relative.as_posix())
            continue
        if path.is_symlink():
            raise ValidationError(f"Deployment contains a symbolic link: {relative}")
        if path.is_file():
            files.append(path)
    return files, excluded


def fingerprint(path):
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns, stat.st_ino


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as data:
        for chunk in iter(lambda: data.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_deploy(public=PUBLIC_DIR, archive=ARCHIVE_PATH, manifest_path=MANIFEST_PATH):
    public, archive, manifest_path = Path(public).resolve(), Path(archive), Path(manifest_path)
    files, excluded = inventory(public)
    fingerprints = {path: fingerprint(path) for path in files}
    checks = validate_site(public)
    records = []
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as package:
        for path in files:
            digest = hashlib.sha256()
            size = 0
            relative = path.relative_to(public).as_posix()
            info = zipfile.ZipInfo.from_file(path, arcname=relative)
            info.compress_type = zipfile.ZIP_DEFLATED
            with path.open("rb") as source, package.open(info, "w", force_zip64=True) as target:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    target.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            records.append({"path": relative, "bytes": size, "sha256": digest.hexdigest()})
    after_files, _ = inventory(public)
    if files != after_files or any(fingerprint(path) != fingerprints[path] for path in files):
        raise ValidationError("Public files changed during preparation; regenerate the archive")
    manifest = {
        "schemaVersion": 1,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "sourceDirectory": str(public),
        "archive": {"path": str(archive.resolve()), "bytes": archive.stat().st_size, "sha256": file_hash(archive)},
        "totalFiles": len(records), "totalBytes": sum(record["bytes"] for record in records),
        "checks": checks, "excluded": excluded, "files": records,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="Validate without creating an archive")
    args = parser.parse_args()
    try:
        if args.check_only:
            checks = validate_site()
            print(json.dumps(checks, indent=2))
        else:
            manifest = prepare_deploy()
            print(f"Prepared {manifest['totalFiles']} files ({manifest['totalBytes']:,} bytes); no deployment performed.")
            print(f"Archive: {ARCHIVE_PATH}")
            print(f"SHA256: {manifest['archive']['sha256']}")
            print(f"Exact contents and file hashes: {MANIFEST_PATH}")
    except (OSError, UnicodeError, ValueError, ValidationError) as error:
        print(f"Deployment preparation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
