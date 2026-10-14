"""Tell IndexNow search engines (Bing, Yandex, Seznam, Naver) that the site changed.

    python tools/indexnow.py
"""

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_docs import INDEXNOW_KEY, SITE, TEXT  # noqa: E402


def main() -> int:
    host = SITE.split("/")[2]
    urls = [SITE + TEXT[k]["path"] for k in ("en", "ja")] + [SITE + "sitemap.xml"]
    body = json.dumps({"host": host, "key": INDEXNOW_KEY,
                       "keyLocation": f"{SITE}{INDEXNOW_KEY}.txt", "urlList": urls}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f"IndexNow: HTTP {resp.status} for {len(urls)} URLs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
