from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import requests
import os
import time

BASE_URL = "https://mta.or.id/download-area/"
BROSUR_DIR = Path("../brosur/")


def get_year(filename: str) -> str:
    match = re.match(r'^(\d{2})', filename)

    if match:
        yy = int(match.group(1))
        year = 2000 + yy if yy < 50 else 1900 + yy
        return str(year)

    return "unknown"


def fetch_link() -> list[dict]:
    links = []
    page = 1

    while True:
        url = f"{BASE_URL}#undefined-undefined-p{page}" if page > 1 else BASE_URL

        res = requests.get(url, timeout=30)
        res.raise_for_status()

        soup = BeautifulSoup(res.text, "html.parser")

        found = False
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/download-brosur/" in href and href.endswith(".pdf"):
                filename = href.split("/")[-1]
                links.append({
                    "filename": filename,
                    "url": urljoin("https://mta.or.id", href),
                    "year": get_year(filename)
                })
                found = True

        next = soup.find("a", string=re.compile(
            r"next|Next|selanjutnya", re.I))

        if not next or not found:
            break
        page += 1

    return links


def get_exist() -> set[str]:
    return {p.name for p in BROSUR_DIR.rglob("*.pdf")}


def download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        res = requests.get(url, timeout=60, stream=True)
        res.raise_for_status()

        with open(dest, "wb") as f:
            for chunk in res.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        return False


def main():
    links = fetch_link()
    exist = get_exist()

    new = [l for l in links if l["filename"] not in exist]

    if not new:
        with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as f:
            f.write("new=false\n")
        return

    downloaded = 0
    for item in links:
        dest = BROSUR_DIR / item["year"] / item["filename"]
        if download(item["url"], dest):
            downloaded += 1
        time.sleep(1)

    with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as f:
        f.write("new={'true' if downloaded > 0 else 'false'}\n")
        f.write(f"count={downloaded}\n")


if __name__ == "__main__":
    main()
