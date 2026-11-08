#!/usr/bin/env python3
"""Menggambar kartu bahasa dari repositori GitHub sendiri.

Dipanggil oleh .github/workflows/languages.yml setiap kali ada push dan sekali
sehari, lalu hasilnya disimpan sebagai assets/languages-dark.svg dan
assets/languages-light.svg di repositori ini. Tidak memakai layanan luar, jadi
kartunya tidak pernah kena batas pemakaian orang lain.

Jalankan sendiri:

    GITHUB_TOKEN=... python3 scripts/langcard.py khaichi11

Tanpa token pun jalan, hanya saja batas permintaan GitHub lebih kecil.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date

API = "https://api.github.com"
TOP = 6
SKIP_LANGS = {"Makefile", "Dockerfile", "Shell", "Batchfile", "CMake"}
SKIP_REPOS = set()          # nama repositori yang tidak ingin ikut dihitung

# Warna resmi GitHub untuk bahasa yang sering dipakai; sisanya memakai daftar
# cadangan di bawah supaya setiap bahasa tetap punya warna sendiri.
COLORS = {
    "Python": "#3572A5", "C": "#555555", "C++": "#f34b7d", "C#": "#178600",
    "Dart": "#00B4AB", "Java": "#b07219", "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6", "HTML": "#e34c26", "CSS": "#563d7c",
    "Shell": "#89e051", "Jupyter Notebook": "#DA5B0B", "Kotlin": "#A97BFF",
    "Swift": "#F05138", "Go": "#00ADD8", "Rust": "#dea584", "Ruby": "#701516",
    "PHP": "#4F5D95", "Lua": "#000080", "Vue": "#41b883", "Svelte": "#ff3e00",
    "CMake": "#DA3434", "Makefile": "#427819", "Dockerfile": "#384d54",
    "GLSL": "#5686a5", "Cuda": "#3A4E3A", "MATLAB": "#e16737", "R": "#198CE7",
    "Objective-C": "#438eff", "Assembly": "#6E4C13", "QML": "#44a51c",
}
SPARE = ["#8b7cf6", "#f59e0b", "#10b981", "#38bdf8", "#f472b6", "#a3e635"]

THEMES = {
    "dark": {"bg": "#0d1117", "edge": "#30363d", "title": "#e6edf3",
             "text": "#c9d1d9", "muted": "#8b949e", "track": "#21262d"},
    "light": {"bg": "#ffffff", "edge": "#d0d7de", "title": "#1f2328",
              "text": "#1f2328", "muted": "#59636e", "track": "#eaeef2"},
}


def get(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "langcard",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def repos(user):
    out, page = [], 1
    while True:
        batch = get(f"{API}/users/{user}/repos?per_page=100&page={page}&type=owner")
        out += batch
        if len(batch) < 100:
            return out
        page += 1


def collect(user):
    """Jumlah byte per bahasa, dari repositori sendiri yang bukan fork."""
    total = {}
    counted = 0
    for repo in repos(user):
        if repo.get("fork") or repo.get("archived") or repo["name"] in SKIP_REPOS:
            continue
        try:
            langs = get(repo["languages_url"])
        except urllib.error.HTTPError:
            continue
        if not langs:
            continue
        counted += 1
        for name, size in langs.items():
            if name in SKIP_LANGS:
                continue
            total[name] = total.get(name, 0) + size
    return total, counted


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def card(data, counted, theme, user):
    c = THEMES[theme]
    order = sorted(data.items(), key=lambda kv: -kv[1])
    ranked = order[:TOP]
    rest = sum(v for _, v in order[TOP:])
    grand = sum(data.values()) or 1
    if rest:
        ranked.append(("Other", rest))

    width, row_h, pad = 470, 30, 22
    head = 64
    height = head + row_h * len(ranked) + 20

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Languages used across {esc(user)} repositories">',
        "<style>",
        "  .t{font:600 15px ui-sans-serif,-apple-system,Segoe UI,Helvetica,Arial,sans-serif}",
        "  .s{font:400 11px ui-sans-serif,-apple-system,Segoe UI,Helvetica,Arial,sans-serif}",
        "  .n{font:500 12.5px ui-sans-serif,-apple-system,Segoe UI,Helvetica,Arial,sans-serif}",
        "  .bar{transform-origin:left center;animation:grow .9s cubic-bezier(.22,.8,.25,1) both}",
        "  @keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}",
        "  @media (prefers-reduced-motion:reduce){.bar{animation:none}}",
        "</style>",
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" '
        f'fill="{c["bg"]}" stroke="{c["edge"]}"/>',
        f'<text x="{pad}" y="32" class="t" fill="{c["title"]}">Most used languages</text>',
        f'<text x="{pad}" y="49" class="s" fill="{c["muted"]}">'
        f'across {counted} public repositories, updated {date.today().isoformat()}</text>',
    ]

    bar_x = pad + 112
    bar_w = width - bar_x - pad - 52
    for i, (name, size) in enumerate(ranked):
        y = head + i * row_h
        share = size / grand
        color = "#6e7681" if name == "Other" else COLORS.get(name, SPARE[i % len(SPARE)])
        parts += [
            f'<text x="{pad}" y="{y + 14}" class="n" fill="{c["text"]}">{esc(name)}</text>',
            f'<rect x="{bar_x}" y="{y + 4}" width="{bar_w}" height="10" rx="5" fill="{c["track"]}"/>',
            f'<rect class="bar" style="animation-delay:{i * 0.07:.2f}s" x="{bar_x}" '
            f'y="{y + 4}" width="{max(6, bar_w * share):.1f}" height="10" rx="5" fill="{color}"/>',
            f'<text x="{width - pad}" y="{y + 14}" class="s" fill="{c["muted"]}" '
            f'text-anchor="end">{share * 100:.1f}%</text>',
        ]
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    user = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_REPOSITORY_OWNER")
    if not user:
        sys.exit("pemakaian: langcard.py <nama-pengguna>")
    data, counted = collect(user)
    if not data:
        sys.exit("tidak ada bahasa yang terbaca")
    os.makedirs("assets", exist_ok=True)
    for theme in THEMES:
        with open(f"assets/languages-{theme}.svg", "w") as f:
            f.write(card(data, counted, theme, user))
    grand = sum(data.values())
    print(f"{counted} repositori, {len(data)} bahasa")
    for name, size in sorted(data.items(), key=lambda kv: -kv[1])[:TOP]:
        print(f"  {name:<20} {size / grand * 100:5.1f}%")


if __name__ == "__main__":
    main()
