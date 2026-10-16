#!/usr/bin/env python3
"""Fetch only verified binary assets from the five latest published releases."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPOS = ("Archivist", "Tether", "Vigilant", "Portalview", "Scry")
BASE_URL = "https://seth-reee.github.io/omarchy-packages"

def gh(*args):
    return subprocess.check_output(["gh", *args], text=True)

def collect():
    releases = {}
    state = {"fingerprint": (ROOT / "keys/fingerprint").read_text().strip(), "releases": {}}
    for repo in REPOS:
        release = json.loads(gh("api", f"repos/seth-reee/{repo}/releases/latest"))
        assert not release["draft"] and not release["prerelease"]
        assert re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", release["tag_name"])
        releases[repo] = release
        state["releases"][repo] = {
            "tag": release["tag_name"], "id": release["id"],
            "assets": [{"name": a["name"], "id": a["id"], "size": a["size"]}
                       for a in release["assets"]],
        }
    try:
        with urllib.request.urlopen(BASE_URL + "/manifest.json", timeout=30) as response:
            previous = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        previous = None
    changed = state != previous or os.environ.get("FORCE_REFRESH") == "true"
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a") as file:
            file.write(f"changed={str(changed).lower()}\n")
    if not changed:
        print("All published packages are current; no deployment needed.")
        return
    dist = ROOT / "dist"
    for arch in ("x86_64", "aarch64"):
        (dist / arch).mkdir(parents=True, exist_ok=True)
    for repo, release in releases.items():
        slug = repo.lower()
        version = release["tag_name"][1:]
        with tempfile.TemporaryDirectory() as temporary:
            for arch in ("x86_64", "aarch64"):
                pattern = re.compile(re.escape(f"{slug}-{version}-") + r"[0-9]+-" + arch + r"\.pkg\.tar\.zst")
                assets = [a for a in release["assets"] if pattern.fullmatch(a["name"])]
                if len(assets) != 1:
                    raise RuntimeError(f"Expected exactly one {repo} {arch} package")
                name = assets[0]["name"]
                sums = f"SHA256SUMS-{arch}"
                gh("release", "download", release["tag_name"], "--repo", f"seth-reee/{repo}",
                   "--pattern", name, "--pattern", sums, "--dir", temporary)
                hashes = {}
                for line in (Path(temporary) / sums).read_text().splitlines():
                    digest, filename = line.split(maxsplit=1)
                    if not re.fullmatch(r"[0-9a-f]{64}", digest):
                        raise RuntimeError("Invalid release checksum")
                    hashes[filename.lstrip("*")] = digest
                package = Path(temporary) / name
                digest = hashlib.sha256(package.read_bytes()).hexdigest()
                if hashes.get(name) != digest:
                    raise RuntimeError(f"Release checksum mismatch: {name}")
                info = gh("api", f"repos/seth-reee/{repo}/releases/assets/{assets[0]['id']}")
                asset_digest = json.loads(info).get("digest")
                if asset_digest and asset_digest != "sha256:" + digest:
                    raise RuntimeError(f"GitHub asset digest mismatch: {name}")
                metadata = subprocess.check_output(["bsdtar", "-xOf", str(package), ".PKGINFO"], text=True)
                for expected in (f"pkgname = {slug}", f"pkgver = {version}-" + name[len(f"{slug}-{version}-"):].split("-")[0], f"arch = {arch}"):
                    if expected not in metadata.splitlines():
                        raise RuntimeError(f"Incorrect package metadata: {expected}")
                shutil.copy2(package, dist / arch / name)
                print(f"Verified {repo} {release['tag_name']} ({arch})")
    (dist / "manifest.json").write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    shutil.copy2(ROOT / "keys/seth-reee.asc", dist / "seth-reee.asc")
    shutil.copy2(ROOT / "scripts/install.sh", dist / "install.sh")
    rows = "".join(f'<li><a href="https://github.com/seth-reee/{repo}/releases/tag/{entry["tag"]}">{repo} {entry["tag"]}</a></li>' for repo, entry in state["releases"].items())
    (dist / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>Seth Reee packages</title><h1>Seth Reee packages</h1><p>Signed Arch Linux packages for x86_64 and aarch64.</p><ul>' + rows + '</ul><p><a href="https://github.com/seth-reee/omarchy-packages#installation">Installation instructions</a></p><p>Signing key: <code>' + state["fingerprint"] + '</code></p>')

if __name__ == "__main__":
    collect()
