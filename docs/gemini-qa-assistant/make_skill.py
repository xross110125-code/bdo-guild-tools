"""instructions.md の指示文から Claude のスキル（zip）を作る。

使い方: python make_skill.py [出力先フォルダ]
出力先を省略するとこのフォルダに bdo-qa.zip を作る。zip は claude.ai の
「カスタマイズ → スキル」でアップロードする。正本は instructions.md なので、
スキルの中身を直接直さず、instructions.md を直してから作り直すこと。
"""
import re
import sys
import zipfile
from pathlib import Path

NAME = "bdo-qa"
DESCRIPTION = (
    "黒い砂漠（日本サーバー）の質問に、最新の公式告知・グローバルラボ・Wiki などを検索して"
    "出典と日付付きで答える。アップデート内容、アイテム、クラス、イベントなど黒い砂漠について聞かれたときに使う。"
)
PREFACE = (
    "以下は Gemini の Gem 用に書いた指示文と同じもの（正本は bdo-guild-tools の "
    "docs/gemini-qa-assistant/instructions.md）。「Google 検索」とある箇所は、"
    "使えるウェブ検索で読み替える。\n"
)

here = Path(__file__).resolve().parent
src = (here / "instructions.md").read_text(encoding="utf-8")
m = re.search(r"^```\n(.*?)^```", src, re.S | re.M)
if not m:
    sys.exit("instructions.md に指示文の枠（```）が見つからない")

skill = f"---\nname: {NAME}\ndescription: {DESCRIPTION}\n---\n\n{PREFACE}\n{m.group(1)}"
out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else here
out = out_dir / f"{NAME}.zip"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr(f"{NAME}/SKILL.md", skill.encode("utf-8"))
print(out)
