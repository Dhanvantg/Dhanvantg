"""Refresh public-only profile metrics using the standard library."""
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
USER = "Dhanvantg"
START = "<!--START_SECTION:github-context-->"
END = "<!--END_SECTION:github-context-->"


def api(path):
    headers = {"User-Agent": "Dhanvantg-profile", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request("https://api.github.com/" + path, headers=headers), timeout=30) as response:
        return json.load(response)


def fetch_public_data():
    user = api(f"users/{USER}")
    repos = []
    for page in range(1, 101):
        batch = api(f"users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos.extend(repo for repo in batch if not repo.get("private") and repo["owner"]["login"].lower() == USER.lower())
        if len(batch) < 100:
            return user, repos
    raise RuntimeError("Repository pagination limit reached; keeping previous assets")


def summarize(repos):
    original = [repo for repo in repos if not repo.get("fork")]
    languages = Counter(repo["language"] for repo in original if repo.get("language"))
    return original, languages


def context_markdown(user, repos, updated):
    original, languages = summarize(repos)
    lines = []
    if languages:
        # A primary-language count is not a measure of time spent or skill.
        lines += ["**Public repositories by primary language**", "", "```text"]
        total = sum(languages.values())
        for language, count in sorted(languages.items(), key=lambda pair: (-pair[1], pair[0])):
            fraction = count / total
            filled = round(fraction * 20)
            bar = "█" * filled + "░" * (20 - filled)
            lines.append(f"{language:<14} {count:>2} repos  {bar}  {fraction * 100:>5.1f}%")
        lines += ["```", "", "<sub>Owned, non-fork public repositories with a detected primary language. Private and organization work is not included.</sub>"]
    else:
        lines.append("No detected primary languages in the public repository sample yet.")
    lines += ["", f"<sub>On GitHub since {user['created_at'][:4]} · Updated {updated} UTC</sub>"]
    return "\n".join(lines)


def overview_svg(user, repos, updated):
    original, _ = summarize(repos)
    stars = sum(repo.get("stargazers_count", 0) for repo in original)
    stats = [(len(repos), "PUBLIC REPOSITORIES"), (stars, "STARS ON ORIGINAL REPOS"), (user["followers"], "FOLLOWERS")]
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="720" height="218" viewBox="0 0 720 218" role="img" aria-labelledby="title desc">
<title id="title">Dhanvant's public GitHub overview</title><desc id="desc">{len(repos)} public repositories, {stars} stars on original repositories, {user["followers"]} followers. Updated {escape(updated)} UTC.</desc>
<style>text{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;fill:#302d26}}.muted{{fill:#736b5d}}.value{{fill:#b95330;font-size:37px;font-weight:700}}.panel{{fill:#faf8f1;stroke:#e2dccd}}@media(prefers-color-scheme:dark){{text{{fill:#e8e1d7}}.muted{{fill:#afa697}}.value{{fill:#f19a74}}.panel{{fill:#161b22;stroke:#30363d}}}}</style>
<rect class="panel" x="1" y="1" width="718" height="216" rx="14"/>
<text x="30" y="40" font-size="18" font-weight="600">@Dhanvantg</text><text class="muted" x="690" y="40" text-anchor="end" font-size="13">Building since {user['created_at'][:4]}</text>
''']
    for index, (value, label) in enumerate(stats):
        x = 120 + index * 240
        parts.append(f'<text class="value" x="{x}" y="113" text-anchor="middle">{value}</text><text class="muted" x="{x}" y="144" text-anchor="middle" font-size="10.5" letter-spacing=".5">{escape(label)}</text>')
    parts.append(f'<text class="muted" x="360" y="191" text-anchor="middle" font-size="12">Public activity snapshot · {escape(updated)} UTC</text></svg>')
    return "".join(parts)


def replace_context(readme, body):
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError("README must contain exactly one profile context marker pair")
    before, tail = readme.split(START, 1)
    _, after = tail.split(END, 1)
    return before + START + "\n" + body + "\n" + END + after


def main():
    user, repos = fetch_public_data()  # No partial write if a request fails.
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    result = replace_context(readme, context_markdown(user, repos, updated))
    graphic = overview_svg(user, repos, updated)
    (ROOT / "assets/github-overview.svg").write_text(graphic, encoding="utf-8")
    (ROOT / "README.md").write_text(result, encoding="utf-8")
    print(f"Refreshed public profile snapshot: {len(repos)} repositories")


if __name__ == "__main__":
    try:
        main()
    except (urllib.error.URLError, ValueError, KeyError, RuntimeError) as exc:
        raise SystemExit(f"Profile refresh failed ({type(exc).__name__}); inspect the API availability and input schema") from None
