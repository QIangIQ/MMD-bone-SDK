"""Generate the GitHub Pages site in docs/ from the bone table.

    python tools/build_docs.py          # write docs/
    python tools/build_docs.py --check  # fail if docs/ is out of date
"""

from __future__ import annotations

import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mmd_bone_tools import __version__  # noqa: E402
from mmd_bone_tools import dictionary as d  # noqa: E402

SITE = "https://qiangiq.github.io/MMD-bone-SDK/"
REPO = "https://github.com/QIangIQ/MMD-bone-SDK"
RELEASE = REPO + "/releases/latest"
DATE = "2026-10-14"

TEXT = {
    "en": {
        "path": "", "lang": "en",
        "title": "MMD Bone Tools: translate Japanese MMD bone names to English, retarget VMD motions",
        "desc": ("Free MMD tool that translates Japanese bone names in PMX, PMD and VMD files to "
                 "English, converts bones between MMD, Blender, Unity Humanoid, VRM and Mixamo, "
                 "and retargets VMD motions to any model. Windows app, CLI and Python library."),
        "h1": "MMD Bone Tools",
        "tag": ("Translate Japanese MMD bone names to English, map bones between MMD, Blender, "
                "Unity, VRM and Mixamo, and make any VMD motion fit any model."),
        "dl": "Download for Windows", "gh": "Source on GitHub", "other": "日本語",
        "pip": "Any OS with Python 3.10+:",
        "free": f"Free and open source (MIT) · version {__version__} · no install needed",
        "feat_h": "What it does",
        "feats": [
            ("Japanese → English bone names",
             "Translates bone, morph, material, display frame, rigid body and joint names in "
             "PMX/PMD models and VMD motions. 左腕 → arm_L, 右スカート前２ → skirt_front2_R."),
            ("Convert between rigs",
             "Renames 110 standard bones between Japanese MMD, English MMD, Blender (arm.L), "
             "Unity Humanoid, VRM 1.0 and Mixamo."),
            ("Retarget VMD motions",
             "Renames motion tracks to match a model and corrects A-pose / T-pose rest-pose "
             "differences, with automatic scaling."),
            ("Batch and zip downloads",
             "Translates whole folders and extracts Japanese zip files without garbled "
             "(文字化け) file names."),
            ("Safe on your files",
             "Only names change; everything else is written back byte for byte. Long names are "
             "fitted to VMD's 15-byte limit."),
            ("App, command line, library",
             "A desktop app in English and Japanese, the mmdbt command, and a Python API."),
        ],
        "how_h": "How to use it",
        "how": [
            "Download the Windows zip from the latest release and unzip it.",
            "Run MMDBoneTools.exe, or drop .pmx/.pmd/.vmd files onto it.",
            "Pick Translate, Convert or Retarget and press the button. Results are saved next "
            "to the originals with an _en suffix.",
        ],
        "cli_h": "Command line",
        "faq_h": "FAQ",
        "faq": [
            ("How do I translate MMD bone names from Japanese to English?",
             "Open MMD Bone Tools, add the .pmx, .pmd or .vmd file and press Translate. On the "
             "command line run: mmdbt translate model.pmx --rename"),
            ("Why doesn't my VMD motion move my model?",
             "MMD applies motions by bone name. A motion with Japanese names (左腕) does not move "
             "a model with English names (arm_L). Run: mmdbt retarget motion.vmd --model model.pmx"),
            ("How do I use MMD models and motions in Blender, Unity, VRChat or with Mixamo?",
             "Convert the bone names with mmdbt convert model.pmx --to blender (or unity, vrm, "
             "mixamo), or export a bone map with mmdbt map model.pmx --to unity."),
            ("What are the English names of センター, 上半身, 下半身 and 足ＩＫ?",
             "center, upper body, lower body and leg IK_L / leg IK_R. The full table is below."),
            ("Is it free?", "Yes. It is open source under the MIT license."),
        ],
        "table_h": "MMD bone name table",
        "table_p": ("Standard MMD bones in every supported naming convention. Left side shown; "
                    "right side uses 右 / _R / .R / Right."),
    },
    "ja": {
        "path": "ja/", "lang": "ja",
        "title": "MMDボーンツール｜MMDのボーン名を日本語から英語へ自動翻訳・VMDモーションのリターゲット",
        "desc": ("PMX・PMD・VMDのボーン名を日本語から英語へ自動翻訳し、Blender・Unity Humanoid・"
                 "VRM・Mixamo のボーン名へ変換、VMDモーションを別のモデルへリターゲットできる無料ツール。"
                 "Windowsアプリ・コマンド・Pythonライブラリ。"),
        "h1": "MMDボーンツール",
        "tag": ("MMDのボーン名を日本語から英語へ翻訳し、Blender・Unity・VRM・Mixamo と相互変換。"
                "どのVMDモーションもどのモデルにも合わせられます。"),
        "dl": "Windows版をダウンロード", "gh": "GitHubでソースを見る", "other": "English",
        "pip": "Python 3.10以上がある環境:",
        "free": f"無料・オープンソース（MIT）· バージョン {__version__} · インストール不要",
        "feat_h": "できること",
        "feats": [
            ("ボーン名の英語化",
             "PMX/PMD/VMDのボーン名・モーフ名・材質名・表示枠・剛体・ジョイント名を英語に翻訳。"
             "左腕 → arm_L、右スカート前２ → skirt_front2_R。"),
            ("命名規則の相互変換",
             "日本語MMD・英語MMD・Blender（arm.L）・Unity Humanoid・VRM 1.0・Mixamo の間で"
             "準標準ボーン110本を変換。"),
            ("モーションのリターゲット",
             "VMDのボーン名をモデルに合わせ、Aポーズ⇔Tポーズなど初期姿勢の違いを補正。移動量も自動調整。"),
            ("一括処理・zip展開",
             "フォルダごとまとめて翻訳。日本語ファイル名のzipも文字化けせずに展開。"),
            ("データは名前だけ変更",
             "名前以外はバイト単位でそのまま保存。長い名前はVMDの15バイト制限に合わせて短縮。"),
            ("アプリ・コマンド・ライブラリ",
             "日英表示のデスクトップアプリ、mmdbt コマンド、Python API。"),
        ],
        "how_h": "使い方",
        "how": [
            "最新リリースから Windows 用 zip をダウンロードして展開します。",
            "MMDBoneTools.exe を起動するか、.pmx/.pmd/.vmd ファイルをドラッグ＆ドロップします。",
            "「翻訳」「変換」「リターゲット」を選んでボタンを押します。結果は元ファイルの隣に _en 付きで保存されます。",
        ],
        "cli_h": "コマンドライン",
        "faq_h": "よくある質問",
        "faq": [
            ("MMDのボーン名を日本語から英語に変換するには？",
             "MMDボーンツールで .pmx / .pmd / .vmd を追加して「翻訳する」を押します。"
             "コマンドでは mmdbt translate モデル.pmx --rename です。"),
            ("モーションを読み込んでもモデルが動かないのはなぜ？",
             "MMDはボーン名でモーションを適用します。日本語名（左腕）のモーションは英語名（arm_L）の"
             "モデルを動かせません。mmdbt retarget モーション.vmd --model モデル.pmx で合わせられます。"),
            ("MMDモデルやモーションを Blender・Unity・VRChat・Mixamo で使うには？",
             "mmdbt convert モデル.pmx --to blender（unity / vrm / mixamo）でボーン名を変換するか、"
             "mmdbt map モデル.pmx --to unity で対応表を書き出します。"),
            ("センター・上半身・下半身・足ＩＫの英語名は？",
             "center、upper body、lower body、leg IK_L / leg IK_R です。下の対応表をご覧ください。"),
            ("無料ですか？", "はい。MITライセンスのオープンソースです。"),
        ],
        "table_h": "MMDボーン名 対応表",
        "table_p": "準標準ボーンの各命名規則での名前（左側のみ表示。右側は 右 / _R / .R / Right）。",
    },
}

CLI = """mmdbt translate model.pmx --rename
mmdbt translate dance.vmd
mmdbt retarget dance.vmd --model model_en.pmx
mmdbt convert model.pmx --to unity
mmdbt lookup 上半身2
mmdbt unpack download.zip
mmdbt batch ~/Downloads/mmd"""

CSS = """
:root{--bg:#f7f7fa;--fg:#1b1f2a;--mut:#5b6374;--card:#fff;--line:#e2e4ea;--acc:#e0485f;--accfg:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#181c28;--fg:#eceff4;--mut:#aab3c5;--card:#212636;--line:#323a4f;--acc:#ff7a8c;--accfg:#181c28}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,"Segoe UI","Hiragino Sans","Yu Gothic UI",Meiryo,sans-serif}
main{max-width:980px;margin:0 auto;padding:24px 16px 64px}
header{display:flex;gap:20px;align-items:center;flex-wrap:wrap;padding:24px 0}
header img{width:88px;height:88px}
h1{font-size:2.2rem;margin:0;line-height:1.2}h2{margin-top:2.4em;font-size:1.5rem}
.tag{font-size:1.15rem;color:var(--mut);margin:.4em 0 0}
.lang{margin-left:auto;align-self:flex-start}
a{color:var(--acc)}
.btns{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0 4px}
.btn{display:inline-block;padding:12px 20px;border-radius:10px;text-decoration:none;font-weight:600;border:1px solid var(--acc)}
.btn.primary{background:var(--acc);color:var(--accfg)}
.small{color:var(--mut);font-size:.92rem}
.shot{width:100%;height:auto;border-radius:10px;border:1px solid var(--line);margin-top:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.card h3{margin:0 0 6px;font-size:1.05rem}.card p{margin:0;color:var(--mut)}
p code{overflow-wrap:anywhere}
pre,code{font-family:ui-monospace,Consolas,"Cascadia Mono",monospace}
pre{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;overflow-x:auto}
details{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:8px 0}
summary{cursor:pointer;font-weight:600}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:.92rem;background:var(--card)}
th,td{padding:6px 10px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}
th{position:sticky;top:0;background:var(--card)}
footer{margin-top:48px;color:var(--mut);font-size:.9rem}
"""

HEADERS = {"jp": "Japanese MMD", "en": "English MMD", "blender": "Blender",
           "unity": "Unity Humanoid", "vrm": "VRM 1.0", "mixamo": "Mixamo"}


def table_html() -> str:
    rows = []
    for b in d.BONES:
        if b.side == "R":
            continue
        cells = []
        for c in d.CONVENTIONS:
            n = b.name(c) or ""
            if c == "jp" and n and d._uses_fullwidth(b):
                n = d.jp_display(n)
            cells.append(f"<td>{html.escape(n) or '–'}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    head = "".join(f"<th>{HEADERS[c]}</th>" for c in d.CONVENTIONS)
    return (f'<div class="tablewrap"><table><thead><tr>{head}</tr></thead><tbody>'
            + "\n".join(rows) + "</tbody></table></div>")


def page(key: str) -> str:
    t = TEXT[key]
    other = "ja" if key == "en" else "en"
    url = SITE + t["path"]
    other_url = SITE + TEXT[other]["path"]
    root = "" if key == "en" else "../"
    ld_app = {
        "@context": "https://schema.org", "@type": "SoftwareApplication",
        "name": "MMD Bone Tools", "alternateName": "MMDボーンツール",
        "applicationCategory": "MultimediaApplication", "operatingSystem": "Windows, macOS, Linux",
        "softwareVersion": __version__, "datePublished": DATE, "description": t["desc"],
        "url": url, "downloadUrl": RELEASE, "codeRepository": REPO, "license": "https://opensource.org/licenses/MIT",
        "image": SITE + "social-preview.png", "inLanguage": ["en", "ja"],
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "keywords": "MMD, MikuMikuDance, PMX, PMD, VMD, bone names, translate, Japanese, English, "
                    "retarget, Blender, Unity, VRM, Mixamo, ボーン名, 英語化",
    }
    ld_faq = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in t["faq"]],
    }
    feats = "".join(f'<div class="card"><h3>{html.escape(h)}</h3><p>{html.escape(p)}</p></div>'
                    for h, p in t["feats"])
    how = "".join(f"<li>{html.escape(s)}</li>" for s in t["how"])
    faq = "".join(f"<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>"
                  for q, a in t["faq"])
    return f"""<!doctype html>
<html lang="{t['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(t['title'])}</title>
<meta name="description" content="{html.escape(t['desc'])}">
<meta name="keywords" content="MMD, MikuMikuDance, PMX, PMD, VMD, bone, ボーン名, 英語化, 翻訳, retarget, リターゲット, Blender, Unity, VRM, VRChat, Mixamo">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="{t['lang']}" href="{url}">
<link rel="alternate" hreflang="{TEXT[other]['lang']}" href="{other_url}">
<link rel="alternate" hreflang="x-default" href="{SITE}">
<link rel="icon" href="{root}icon.png">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(t['title'])}">
<meta property="og:description" content="{html.escape(t['desc'])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}social-preview.png">
<meta property="og:locale" content="{'en_US' if key == 'en' else 'ja_JP'}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(t['title'])}">
<meta name="twitter:description" content="{html.escape(t['desc'])}">
<meta name="twitter:image" content="{SITE}social-preview.png">
<script type="application/ld+json">{json.dumps(ld_app, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(ld_faq, ensure_ascii=False)}</script>
<style>{CSS}</style>
</head>
<body>
<main>
<header>
<img src="{root}icon.png" alt="" width="88" height="88">
<div><h1>{html.escape(t['h1'])}</h1><p class="tag">{html.escape(t['tag'])}</p></div>
<a class="lang" href="{other_url}" hreflang="{TEXT[other]['lang']}">{t['other']}</a>
</header>
<div class="btns">
<a class="btn primary" href="{RELEASE}">{html.escape(t['dl'])}</a>
<a class="btn" href="{REPO}">{html.escape(t['gh'])}</a>
</div>
<p class="small">{html.escape(t['free'])} · {html.escape(t['pip'])} <code>pip install mmd-bone-tools</code></p>
<img class="shot" src="{root}screenshot.png" alt="MMD Bone Tools / MMDボーンツール" width="892" height="530">
<h2>{html.escape(t['feat_h'])}</h2>
<div class="grid">{feats}</div>
<h2>{html.escape(t['how_h'])}</h2>
<ol>{how}</ol>
<h2>{html.escape(t['cli_h'])}</h2>
<pre><code>{html.escape(CLI)}</code></pre>
<h2>{html.escape(t['faq_h'])}</h2>
{faq}
<h2 id="bones">{html.escape(t['table_h'])}</h2>
<p>{html.escape(t['table_p'])}</p>
{table_html()}
<footer>MMD Bone Tools {__version__} · MIT · <a href="{REPO}">GitHub</a> · <a href="{REPO}/issues">Issues</a></footer>
</main>
</body>
</html>
"""


def outputs() -> dict[str, str]:
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
               'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n')
    for key in ("en", "ja"):
        sitemap += f"  <url><loc>{SITE}{TEXT[key]['path']}</loc><lastmod>{DATE}</lastmod>"
        for alt in ("en", "ja"):
            sitemap += (f'<xhtml:link rel="alternate" hreflang="{alt}" '
                        f'href="{SITE}{TEXT[alt]["path"]}"/>')
        sitemap += "</url>\n"
    sitemap += "</urlset>\n"
    return {
        "index.html": page("en"),
        "ja/index.html": page("ja"),
        "sitemap.xml": sitemap,
        "robots.txt": f"User-agent: *\nAllow: /\nSitemap: {SITE}sitemap.xml\n",
        ".nojekyll": "",
    }


def main() -> int:
    docs = ROOT / "docs"
    check = "--check" in sys.argv
    stale = []
    for rel, content in outputs().items():
        p = docs / rel
        if check:
            if not p.exists() or p.read_text(encoding="utf-8") != content:
                stale.append(rel)
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8", newline="\n")
    for name in ("icon.png", "social-preview.png", "screenshot.png"):
        src, dst = ROOT / "assets" / name, docs / name
        if check:
            if not dst.exists() or dst.read_bytes() != src.read_bytes():
                stale.append(name)
        else:
            shutil.copyfile(src, dst)
    if stale:
        print("docs/ is out of date, run python tools/build_docs.py: " + ", ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
