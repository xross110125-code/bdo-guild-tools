"""グローバルラボの「업데이트 안내」を検知して、タイトルとURLをDiscordに投稿する。
外部ライブラリなし（Python標準ライブラリのみ）。

使い方:
  python globallab/notify.py            # 通常実行（GLOBALLAB_WEBHOOK_URL が必要）
  python globallab/notify.py --dry-run  # 投稿も状態保存もせず、検出結果を表示するだけ
  python globallab/notify.py --dry-run --since 19800  # 記事番号 19800 より後を新着扱いにして表示
"""
import argparse
import json
import os
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin

LIST_URL = "https://blackdesert.pearlabyss.com/GlobalLab/en-US/News/Notice?_categoryNo=2"
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
WEBHOOK_ENV = "GLOBALLAB_WEBHOOK_URL"
INCLUDE = "업데이트 안내"          # 週次アップデートのお知らせ
EXCLUDE = ["보안 모듈"]            # セキュリティモジュール更新は除外
UA = "Mozilla/5.0 (compatible; bdo-guild-tools/globallab)"


class ListParser(HTMLParser):
    """記事リンク（_boardNo=を含む<a>）と、その中の <p class="title"> を集める。

    一覧ページには上部スライダーと本体一覧の2か所に同じ記事が出るため、番号で重複を除く。
    <a> 内の全テキストを使うとカテゴリ名や日付が混ざるので、title クラスの要素だけを読む。
    """

    def __init__(self):
        super().__init__()  # convert_charrefs=True: &#xC5C5; などの数値参照はここでデコードされる
        self.items = {}  # board_no -> (url, title)
        self._href = None
        self._title_tag = None  # title 要素の中にいる間、そのタグ名
        self._buf = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and "_boardNo=" in (a.get("href") or ""):
            self._href = a["href"]
            self._title_tag = None
            self._buf = []
        elif self._href is not None and "title" in (a.get("class") or "").split():
            self._title_tag = tag

    def handle_data(self, data):
        if self._title_tag:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if self._href is None:
            return
        if tag == self._title_tag:
            self._title_tag = None
        if tag != "a":
            return
        title = " ".join("".join(self._buf).split())
        try:
            no = int(self._href.split("_boardNo=")[1].split("&")[0])
        except ValueError:
            no = None
        if no is not None and title:
            self.items.setdefault(no, (urljoin(LIST_URL, self._href), title))
        self._href = None
        self._title_tag = None


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def post(webhook, content):
    body = json.dumps({"content": content, "flags": 4}).encode("utf-8")  # 4 = 埋め込みプレビュー抑制
    req = urllib.request.Request(
        webhook, data=body,
        headers={"Content-Type": "application/json", "User-Agent": UA},
    )
    urllib.request.urlopen(req, timeout=30).read()


def fetch_items():
    req = urllib.request.Request(LIST_URL, headers={"User-Agent": UA})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    parser = ListParser()
    parser.feed(html)
    if not parser.items:
        raise RuntimeError("一覧から記事を1件も読み取れませんでした")
    return parser.items


def is_target(title):
    return INCLUDE in title and not any(x in title for x in EXCLUDE)


def message(url, title):
    return (f"📢 **グローバルラボ更新**\n{title}\n{url}\n"
            "※原文は韓国語です。ブラウザの翻訳機能で読めます。"
            "テスト鯖の情報のため、日本鯖への適用時期・内容は未定です。")


def dry_run(since):
    items = fetch_items()
    print(f"取得: {len(items)} 件（最新 {max(items)}）")
    for no in sorted(items):
        url, title = items[no]
        if since is not None and no <= since:
            continue
        mark = "投稿" if is_target(title) else "除外"
        print(f"[{mark}] {no} {title}\n        {url}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="投稿・状態保存をせず検出結果を表示")
    ap.add_argument("--since", type=int, help="--dry-run 時、この番号より後だけ表示")
    args = ap.parse_args()

    if args.dry_run:
        dry_run(args.since)
        return

    webhook = os.environ.get(WEBHOOK_ENV)
    if not webhook:
        # Secrets 未登録 = このツールを使っていない。何もせず正常終了する
        print(f"{WEBHOOK_ENV} が未設定のためスキップ")
        return

    state = load_state()

    try:
        items = fetch_items()
    except Exception as e:
        print(f"取得失敗: {e}")
        # 失敗の通知は1回だけ（毎時スパムしない）。ワークフロー自体は失敗にしない
        if not state.get("error_notified"):
            try:
                post(webhook,
                     "⚠️ グローバルラボ更新の取得に失敗しました（公式サイトの仕様変更の可能性）\n"
                     f"<{LIST_URL}>\n詳細: {e}")
            except Exception as pe:
                print(f"警告の投稿にも失敗: {pe}")
                return
            state["error_notified"] = True
            save_state(state)
        return

    dirty = state.pop("error_notified", None) is not None
    newest = max(items)
    last = state.get("last_board_no")

    if last is None:
        # 初回は過去分を流さず、現在地だけ記録する
        state["last_board_no"] = newest
        save_state(state)
        print(f"初期化: last_board_no = {newest}")
        return

    for no in sorted(items):
        if no <= last:
            continue
        url, title = items[no]
        if is_target(title):
            try:
                post(webhook, message(url, title))
            except Exception as e:
                # Webhook 削除（=利用停止）や一時障害。番号を進めずに終える（次回再試行）
                print(f"投稿失敗 {no}: {e}")
                break
            print(f"投稿: {no} {title}")
        state["last_board_no"] = no
        dirty = True

    if dirty:
        save_state(state)


if __name__ == "__main__":
    main()
