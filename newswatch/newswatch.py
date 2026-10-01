"""公式サイトのお知らせ一覧を見張り、条件に合う新着記事のタイトルとURLをDiscordに投稿する。
外部ライブラリなし（Python標準ライブラリのみ）。

見張る対象（ソース）は sources.json / sources.custom.json に書く。
ソースごとに Secret「NEWSWATCH_WEBHOOK_<ID>」が登録されているものだけ動く。

使い方:
  python newswatch/newswatch.py                     # 通常実行
  python newswatch/newswatch.py --dry-run           # 投稿も状態保存もせず、全ソースの判定結果を表示
  python newswatch/newswatch.py --dry-run --source globallab --since 19800
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_FILES = [os.path.join(HERE, "sources.json"), os.path.join(HERE, "sources.custom.json")]
STATE_FILE = os.path.join(HERE, "state.json")
WEBHOOK_PREFIX = "NEWSWATCH_WEBHOOK_"
UA = "Mozilla/5.0 (compatible; bdo-guild-tools/newswatch)"


class ListParser(HTMLParser):
    """記事リンク（id_param を含む<a>）と、その中の title_class 要素のテキストを集める。

    同じ記事が一覧の複数か所に出ることがあるため、番号で重複を除く。
    <a> 内の全テキストを使うとカテゴリ名や日付が混ざるので、title_class の要素だけを読む。
    リンク内に title_class の要素が複数ある場合（副題にも同じクラスが付く等）は最初の1つだけ読む。
    link_attr を指定すると、その属性を持つ <a> だけを記事リンクとみなす（全ページ共通の枠を除くため）。
    """

    def __init__(self, base_url, id_param, title_class, link_attr=None):
        super().__init__()  # convert_charrefs=True: &#xC5C5; などの数値参照はここでデコードされる
        self.base_url = base_url
        self.id_param = id_param
        self.title_class = title_class
        self.link_attr = link_attr
        self.items = {}  # 記事番号 -> (url, title)
        self._href = None
        self._title_tag = None  # title 要素の中にいる間、そのタグ名
        self._title_done = False
        self._buf = []

    def _article_no(self, href):
        values = parse_qs(urlparse(href).query).get(self.id_param)
        if values and values[0].isdigit():
            return int(values[0])
        return None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        href = a.get("href") or ""
        if (tag == "a" and self._article_no(href) is not None
                and (not self.link_attr or self.link_attr in a)):
            self._href = href
            self._title_tag = None
            self._title_done = False
            self._buf = []
        elif (self._href is not None and not self._title_done
              and self.title_class in (a.get("class") or "").split()):
            self._title_tag = tag

    def handle_data(self, data):
        if self._title_tag:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if self._href is None:
            return
        if tag == self._title_tag:
            self._title_tag = None
            self._title_done = True
        if tag != "a":
            return
        title = " ".join("".join(self._buf).split())
        if title:
            no = self._article_no(self._href)
            self.items.setdefault(no, (urljoin(self.base_url, self._href), title))
        self._href = None
        self._title_tag = None


def load_sources():
    """sources.json（配布分）に sources.custom.json（利用者分）を重ねる。同じ id は custom が上書き。"""
    sources = {}
    for path in SOURCE_FILES:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for s in json.load(f):
                sources[s["id"]] = s
    return list(sources.values())


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def webhook_for(source):
    name = WEBHOOK_PREFIX + source["id"].upper().replace("-", "_")
    return name, os.environ.get(name)


def post(webhook, content):
    body = json.dumps({"content": content, "flags": 4}).encode("utf-8")  # 4 = 埋め込みプレビュー抑制
    req = urllib.request.Request(
        webhook, data=body,
        headers={"Content-Type": "application/json", "User-Agent": UA},
    )
    urllib.request.urlopen(req, timeout=30).read()


class Maintenance(Exception):
    """公式サイトがメンテナンス中らしい（取得失敗とは分けて、すぐには警告しない）。"""


def _path(url):
    return urlparse(url).path.rstrip("/").lower()


def fetch_items(source):
    req = urllib.request.Request(source["list_url"], headers={"User-Agent": UA})
    resp = urllib.request.urlopen(req, timeout=30)
    html = resp.read().decode("utf-8", "replace")
    # メンテナンス中は一覧ではなく案内ページに転送される（日本公式で確認：/ja-JP/shutdown/closetime）
    if _path(resp.geturl()) != _path(source["list_url"]):
        raise Maintenance(f"別のページに転送されました: {urlparse(resp.geturl()).path}")
    for marker in source.get("maintenance_markers") or []:
        if marker in html:
            raise Maintenance(f"メンテナンスページの目印 {marker} があります")
    parser = ListParser(source["list_url"], source["id_param"], source["title_class"],
                        source.get("link_attr"))
    parser.feed(html)
    if not parser.items:
        raise RuntimeError("一覧から記事を1件も読み取れませんでした")
    return parser.items


def is_target(source, title):
    include = source.get("include") or []
    exclude = source.get("exclude") or []
    if include and not any(x in title for x in include):
        return False
    return not any(x in title for x in exclude)


def message(source, url, title):
    lines = [f"📢 **{source['name']}**", title, url]
    if source.get("note"):
        lines.append(source["note"])
    return "\n".join(lines)


def dry_run(sources, since):
    for source in sources:
        name, webhook = webhook_for(source)
        print(f"== {source['id']}（{source['name']}） Secret {name}: {'登録あり' if webhook else '未登録'}")
        try:
            items = fetch_items(source)
        except Maintenance as m:
            print(f"   メンテナンス中と判定: {m}")
            continue
        except Exception as e:
            print(f"   取得失敗: {e}")
            continue
        print(f"   取得: {len(items)} 件（最新 {max(items)}）")
        for no in sorted(items):
            if since is not None and no <= since:
                continue
            url, title = items[no]
            mark = "投稿" if is_target(source, title) else "除外"
            print(f"   [{mark}] {no} {title}\n          {url}")


MAINT_WARN_HOURS = 12  # メンテナンス判定がこれ以上続いたら一度だけ知らせる
FAIL_WARN_HOURS = 2    # 取得失敗がこれ以上続いたら一度だけ知らせる


def now():
    return datetime.now(timezone.utc)


def today():
    return now().date()


def handle_maintenance(source, webhook, st, reason):
    """メンテナンス中の回。黙って次の回に回すが、長く続いたら一度だけ知らせる。書き換えたら True。

    メンテナンスのたびに警告が出ないようにするため。判定が外れて（ページの作りが変わる等）
    黙り続けることのないよう、MAINT_WARN_HOURS 時間続いたら知らせる。
    """
    sid = source["id"]
    dirty = False
    if "maint_since" not in st:
        st["maint_since"] = now().isoformat(timespec="minutes")
        dirty = True
    hours = (now() - datetime.fromisoformat(st["maint_since"])).total_seconds() / 3600
    print(f"[{sid}] メンテナンス中と判定（{hours:.1f} 時間目）: {reason}")
    if hours < MAINT_WARN_HOURS or st.get("maint_notified"):
        return dirty
    try:
        post(webhook,
             f"⚠️ {source['name']}：公式サイトがメンテナンス中の状態が {int(hours)} 時間続いています。\n"
             "長時間のメンテナンスでなければ、公式サイトの作りが変わった可能性があります。\n"
             f"<{source['list_url']}>")
    except Exception as e:
        print(f"[{sid}] メンテナンス長期化の警告の投稿に失敗: {e}")
        return dirty
    st["maint_notified"] = True
    return True


def handle_failure(source, webhook, st, err):
    """取得に失敗した回。FAIL_WARN_HOURS 時間続いたら一度だけ知らせる。書き換えたら True。

    公式サイトが一時的に重い（タイムアウト等）だけで警告が出ないようにするため。
    ワークフロー自体は失敗にしない。
    """
    sid = source["id"]
    dirty = False
    if "fail_since" not in st:
        st["fail_since"] = now().isoformat(timespec="minutes")
        dirty = True
    hours = (now() - datetime.fromisoformat(st["fail_since"])).total_seconds() / 3600
    print(f"[{sid}] 取得失敗（{hours:.1f} 時間目）: {err}")
    if hours < FAIL_WARN_HOURS or st.get("error_notified"):
        return dirty
    try:
        post(webhook,
             f"⚠️ {source['name']} の取得に {int(hours)} 時間失敗し続けています（公式サイトの仕様変更の可能性）\n"
             f"<{source['list_url']}>\n詳細: {err}")
    except Exception as pe:
        print(f"[{sid}] 警告の投稿にも失敗: {pe}")
        return dirty
    st["error_notified"] = True
    return True


def check_quiet(source, webhook, st):
    """投稿対象が quiet_days 日以上見つかっていなければ、一度だけ警告する。書き換えたら True。

    告知タイトルの書き方が変わって include の語を含まなくなると、取得は成功し続けるので
    取得失敗の警告では気づけない。その「黙って止まる」壊れ方を拾うための見張り。
    """
    days = source.get("quiet_days") or 0
    last = st.get("last_target_date")
    if not days or not last or st.get("quiet_notified"):
        return False
    quiet = (today() - date.fromisoformat(last)).days
    if quiet < days:
        return False
    try:
        post(webhook,
             f"⚠️ {source['name']}：{quiet} 日間、投稿対象の告知が見つかっていません。\n"
             "告知が出ていないだけかもしれませんが、公式の告知タイトルの書き方が変わった可能性もあります。\n"
             f"<{source['list_url']}>")
    except Exception as e:
        print(f"[{source['id']}] 無投稿警告の投稿に失敗: {e}")
        return False
    print(f"[{source['id']}] 無投稿警告: {quiet} 日")
    st["quiet_notified"] = True
    return True


def run_source(source, webhook, st):
    """1ソース分を処理する。st はそのソースの状態（dict）で、書き換えたら True を返す。"""
    sid = source["id"]
    try:
        items = fetch_items(source)
    except Maintenance as m:
        return handle_maintenance(source, webhook, st, m)
    except Exception as e:
        return handle_failure(source, webhook, st, e)

    dirty = st.pop("error_notified", None) is not None
    for key in ("maint_since", "maint_notified", "fail_since"):
        if st.pop(key, None) is not None:
            dirty = True
    last = st.get("last_no")

    if last is None:
        # 初回は過去分を流さず、現在地だけ記録する
        st["last_no"] = max(items)
        st["last_target_date"] = today().isoformat()
        print(f"[{sid}] 初期化: last_no = {st['last_no']}")
        return True

    if "last_target_date" not in st:
        # 無投稿警告を入れる前の状態ファイル。今日を起点にする
        st["last_target_date"] = today().isoformat()
        dirty = True

    for no in sorted(items):
        if no <= last:
            continue
        url, title = items[no]
        if is_target(source, title):
            try:
                post(webhook, message(source, url, title))
            except Exception as e:
                # Webhook 削除（=利用停止）や一時障害。番号を進めずに終える（次回再試行）
                print(f"[{sid}] 投稿失敗 {no}: {e}")
                break
            print(f"[{sid}] 投稿: {no} {title}")
            st["last_target_date"] = today().isoformat()
            st.pop("quiet_notified", None)
        st["last_no"] = no
        dirty = True

    if check_quiet(source, webhook, st):
        dirty = True
    return dirty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="投稿・状態保存をせず判定結果を表示")
    ap.add_argument("--source", help="このIDのソースだけ処理する")
    ap.add_argument("--since", type=int, help="--dry-run 時、この番号より後だけ表示")
    args = ap.parse_args()

    try:
        sources = load_sources()
    except Exception as e:
        # 設定ファイルの書き間違いは利用者の編集直後に起きるので、ワークフローを失敗させて知らせる
        print(f"設定ファイルを読めません: {e}")
        sys.exit(1)
    if args.source:
        sources = [s for s in sources if s["id"] == args.source]

    if args.dry_run:
        dry_run(sources, args.since)
        return

    state = load_state()
    dirty = False
    for source in sources:
        name, webhook = webhook_for(source)
        if not webhook:
            # Secret 未登録 = このソースは使っていない
            continue
        st = state.setdefault(source["id"], {})
        if run_source(source, webhook, st):
            dirty = True

    if dirty:
        save_state(state)
    else:
        print("変更なし")


if __name__ == "__main__":
    main()
