"""Build reproducible deployment packages without local credentials.

The expanded easy-deploy folder is managed output. Rebuilds refuse unexpected or
modified files instead of deleting a user's files from that folder.
"""

import ast
import base64
import hashlib
import io
import json
import stat
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "bundles"
SKIP_PARTS = {"__pycache__", ".build", ".cache", ".venv", "runs"}
RUNTIME_SUFFIXES = {
    ".py",
    ".txt",
    ".html",
    ".css",
    ".js",
    ".json",
    ".svg",
    ".png",
    ".ico",
    ".webp",
    ".woff",
    ".woff2",
}
PACKAGE_NAME = "t2d-compass-easy-deploy"
PACKAGE_MANIFEST = "PACKAGE_MANIFEST.json"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
THREE_FILE_NAME = "t2d-compass-three-files"


def is_link(path):
    # OneDrive placeholders can also be reparse points; they are not links.
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def select(folder, suffixes=None):
    return sorted(
        p
        for p in (ROOT / folder).rglob("*")
        if p.is_file()
        and not is_link(p)
        and not SKIP_PARTS.intersection(p.parts)
        and p.suffix != ".pyc"
        and p.name != ".env"
        and not p.name.startswith(".env.")
        and (suffixes is None or p.suffix in suffixes)
    )


def content_map(paths):
    contents = {}
    for path in sorted(set(paths)):
        if is_link(path) or not path.resolve().is_relative_to(ROOT.resolve()):
            raise RuntimeError(f"Refusing linked or external package source: {path}")
        contents[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    return contents


def file_manifest(contents):
    return [
        {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in sorted(contents.items())
    ]


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def project_version():
    source = (ROOT / "src/alz_compass/__init__.py").read_text(encoding="utf-8")
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__version__"
            for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            if isinstance(value, str):
                return value
    raise RuntimeError("Package version was not found")


def validate_contents(contents):
    for name in contents:
        path = PurePosixPath(name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or "\\" in name
            or path.name == ".env"
            or ".venv" in path.parts
        ):
            raise RuntimeError(f"Unsafe package path: {name}")


def write_archive(name, contents):
    validate_contents(contents)
    archive = OUTPUT / name
    if archive.exists() and is_link(archive):
        raise RuntimeError(f"Refusing linked archive output: {archive}")
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zipped:
        for entry, data in sorted(contents.items()):
            info = ZipInfo(entry, ZIP_TIMESTAMP)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = ZIP_DEFLATED
            zipped.writestr(info, data, compresslevel=9)
    with ZipFile(archive) as zipped:
        if zipped.testzip() is not None:
            raise RuntimeError("Archive integrity failed")
        entries = zipped.namelist()
        if entries != sorted(contents):
            raise RuntimeError("Archive entries do not match the package")
    return {
        "file": archive.name,
        "files": len(entries),
        "bytes": archive.stat().st_size,
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }


def write_expanded(contents):
    validate_contents(contents)
    folder = OUTPUT / PACKAGE_NAME
    if folder.exists():
        if (
            is_link(folder)
            or not folder.is_dir()
            or folder.resolve() != OUTPUT.resolve() / PACKAGE_NAME
        ):
            raise RuntimeError(f"Refusing invalid package output: {folder}")
        existing = {}
        for path in folder.rglob("*"):
            if is_link(path) or not path.resolve().is_relative_to(folder.resolve()):
                raise RuntimeError(f"Refusing linked package path: {path}")
            if path.is_file():
                existing[path.relative_to(folder).as_posix()] = path
        if existing:
            if PACKAGE_MANIFEST not in existing:
                raise RuntimeError(f"Existing folder has no package manifest: {folder}")
            previous = json.loads(
                existing[PACKAGE_MANIFEST].read_text(encoding="utf-8")
            )
            if previous.get("package") != PACKAGE_NAME:
                raise RuntimeError(f"Existing folder is not managed output: {folder}")
            recorded = {item["path"]: item["sha256"] for item in previous["files"]}
            if set(existing) != set(recorded) | {PACKAGE_MANIFEST}:
                raise RuntimeError(
                    f"Unexpected or missing files in {folder}; "
                    "preserve them before rebuilding"
                )
            if set(existing) - set(contents):
                raise RuntimeError(
                    f"Obsolete files in {folder}; preserve the folder before rebuilding"
                )
            for name, expected_hash in recorded.items():
                if (
                    hashlib.sha256(existing[name].read_bytes()).hexdigest()
                    != expected_hash
                ):
                    raise RuntimeError(
                        "Modified output file must be preserved before rebuilding: "
                        f"{existing[name]}"
                    )
    folder.mkdir(exist_ok=True)
    for name, data in sorted(contents.items()):
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return {"directory": folder.name, "files": len(contents)}


def write_three_files(runtime_contents, version):
    """Make a text-only upload that cannot lose nested application folders."""
    embedded = {
        name.removeprefix("src/"): data
        for name, data in runtime_contents.items()
        if name.startswith("src/alz_compass/")
    }
    validate_contents(embedded)
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for name, data in sorted(embedded.items()):
            info = ZipInfo(name, ZIP_TIMESTAMP)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, data, compresslevel=9)
    payload = buffer.getvalue()
    encoded = base64.b64encode(payload).decode("ascii")
    chunks = "\n".join(
        f'    "{encoded[index : index + 76]}"' for index in range(0, len(encoded), 76)
    )
    launcher = (ROOT / "deploy/three_file_main.py.in").read_text(encoding="utf-8")
    launcher = launcher.replace(
        "@@PAYLOAD_SHA256@@", hashlib.sha256(payload).hexdigest()
    )
    launcher = launcher.replace("@@PAYLOAD_BASE64@@", chunks)
    compile(launcher, "main.py", "exec")
    contents = {
        "app.yaml": runtime_contents["app.yaml"],
        "requirements.txt": runtime_contents["requirements.txt"],
        "main.py": launcher.encode("utf-8"),
    }
    folder = OUTPUT / THREE_FILE_NAME
    manifest_path = OUTPUT / f"{THREE_FILE_NAME}-manifest.json"
    if is_link(folder) or is_link(manifest_path):
        raise RuntimeError("Refusing linked three-file package output")
    if folder.exists():
        if not folder.is_dir() or not manifest_path.is_file():
            raise RuntimeError("Existing three-file output is not managed")
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        recorded = {item["path"]: item["sha256"] for item in previous["files"]}
        if previous.get("package") != THREE_FILE_NAME or set(recorded) != set(contents):
            raise RuntimeError("Existing three-file manifest is not recognized")
        if {path.name for path in folder.iterdir()} != set(recorded):
            raise RuntimeError("Unexpected three-file package contents; preserved")
        for name, expected in recorded.items():
            path = folder / name
            if (
                path.parent != folder
                or is_link(path)
                or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != expected
            ):
                raise RuntimeError("Modified three-file package contents; preserved")
    folder.mkdir(exist_ok=True)
    for name, data in contents.items():
        (folder / name).write_bytes(data)
    manifest = {
        "package": THREE_FILE_NAME,
        "version": version,
        "data_mode": "live",
        "files": file_manifest(contents),
        "embedded_files": file_manifest(embedded),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
    }
    manifest_path.write_bytes(json_bytes(manifest))
    return {"directory": folder.name, "files": 3, "manifest": manifest_path.name}


def main():
    OUTPUT.mkdir(exist_ok=True)
    if is_link(OUTPUT) or OUTPUT.resolve() != ROOT.resolve() / "bundles":
        raise RuntimeError(f"Refusing linked output directory: {OUTPUT}")
    version = project_version()
    runtime = [ROOT / name for name in ("main.py", "app.yaml", "requirements.txt")]
    runtime += select("src", RUNTIME_SUFFIXES)
    runtime_contents = content_map(runtime)
    three_file = write_three_files(runtime_contents, version)
    easy_contents = {
        **runtime_contents,
        "START_HERE.md": (ROOT / "docs/EASY_DEPLOY.md").read_bytes(),
    }
    package_manifest = {
        "package": PACKAGE_NAME,
        "version": version,
        "data_mode": "live",
        "entry_point": "python main.py",
        "files": file_manifest(easy_contents),
    }
    easy_contents[PACKAGE_MANIFEST] = json_bytes(package_manifest)
    expanded = write_expanded(easy_contents)
    source = runtime + [
        ROOT / name
        for name in (
            "README.md",
            "QUICKSTART.md",
            "SECURITY.md",
            "LICENSE",
            "pyproject.toml",
            "uv.lock",
            ".gitignore",
            ".env.example",
            ".python-version",
        )
    ]
    for folder in (
        "tests", "docs", "data", "upstream", "scripts", "deploy", "assets",
        ".github", "presentation",
    ):
        source += select(folder)
    source += select("eval/results")
    source += select("eval/obesity")
    source += select("eval/type2diabetes")
    source += [
        p
        for p in (ROOT / "eval").iterdir()
        if p.is_file() and p.suffix in {".json", ".md"}
    ]
    # The presentation directory contains this submission's T2D deck.
    reports = [
        write_archive(f"{PACKAGE_NAME}.zip", easy_contents),
        write_archive("t2d-compass-databricks.zip", runtime_contents),
        write_archive("t2d-compass-source.zip", content_map(source)),
    ]
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": version,
        "starter_commit": "6e5fb39b4de044de4f39950ded44fa128416f11a",
        "deployment": "Package build only; no cloud deployment or execution performed",
        "primary_package": f"{PACKAGE_NAME}.zip",
        "expanded": expanded,
        "three_file_upload": three_file,
        "runtime_files": file_manifest(easy_contents),
        "archives": reports,
    }
    manifest_path = OUTPUT / "t2d-manifest.json"
    if manifest_path.exists() and is_link(manifest_path):
        raise RuntimeError(f"Refusing linked manifest output: {manifest_path}")
    manifest_path.write_bytes(json_bytes(manifest))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
