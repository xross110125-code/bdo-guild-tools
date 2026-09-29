# bdo-guild-tools

黒い砂漠（Black Desert）のギルド運営で使える小さな便利ツール集です。

- 費用：無料（公開リポジトリの GitHub Actions で動きます）
- 外部ライブラリ：なし（Python 標準ライブラリのみ）
- 使いたいものだけ有効化できます。Secret を登録していないものは何もしません

## ツール一覧

| ツール | 内容 | 仕様書 |
|---|---|---|
| [ニュース監視（newswatch）](#ニュース監視newswatch) | 公式サイトのお知らせ一覧を見張り、新着を Discord に投稿 | [newswatch/README.md](newswatch/README.md) |

## 導入手順（共通）

このリポジトリを**フォーク**して、自分たちのフォークで動かします。

1. 右上の **Fork** からフォークを作る
2. フォークの **Actions** タブを開き、「I understand my workflows, go ahead and enable them」を押す
   （フォーク直後は定期実行が無効になっています）
3. **Settings → Actions → General → Workflow permissions** を
   「**Read and write permissions**」にして Save
   （ツールが状態ファイルをコミットするために必要です）
4. 使いたいものの Secret を登録する（各ツールの項目を参照）
   - **Settings → Secrets and variables → Actions → New repository secret**
5. Actions タブから対象のワークフローを選び、**Run workflow** で一度手動実行する

Webhook URL などの Secret は、コード・README・Issue などに**絶対に書かないでください**。
書いてしまった場合は Discord 側でその Webhook を削除して作り直してください。

### 更新の取り込み

フォークのトップにある **Sync fork → Update branch** で、このリポジトリの更新を取り込めます。
取り込まなくても、フォーク側はそのまま動き続けます。

### 止め方

Discord 側で Webhook を削除すれば投稿は止まります。リポジトリ側の操作は不要です。
完全に止めたい場合は、Actions タブでワークフローを無効化するか、フォークを削除してください。

## ニュース監視（newswatch）

公式サイトのお知らせ一覧を毎時チェックし、条件に合う新着記事のタイトルと URL を Discord に投稿します。
翻訳はしません。

最初から用意してある監視対象：

| ID | 内容 | Secret 名 |
|---|---|---|
| `globallab` | グローバルラボ（韓国テスト鯖）の週次アップデート告知。セキュリティモジュール更新は除く | `NEWSWATCH_WEBHOOK_GLOBALLAB` |
| `jp-update` | 日本公式のアップデート告知。セキュリティモジュール・公式ホームページ・「黒い砂漠+」の更新は除く | `NEWSWATCH_WEBHOOK_JP_UPDATE` |
| `jp-event` | 日本公式のイベント告知（イベントタブの新着すべて） | `NEWSWATCH_WEBHOOK_JP_EVENT` |

**Secret を登録したものだけが動きます。** 同じ Webhook URL を複数の Secret に登録すれば、同じチャンネルにまとめて流せます。

投稿例：

> 📢 **グローバルラボ更新**<br>
> 9월 18일(금) 업데이트 안내<br>
> https://blackdesert.pearlabyss.com/GlobalLab/ko-KR/News/Notice/Detail?_boardNo=19837<br>
> ※原文は韓国語です。ブラウザの翻訳機能で読めます。テスト鯖の情報のため、日本鯖への適用時期・内容は未定です。

### 設定

1. Discord で投稿先チャンネルの Webhook URL を作る
   （チャンネルの編集 → 連携サービス → ウェブフック → 新しいウェブフック → URL をコピー）
2. 上の表の Secret 名で、Webhook URL を登録
3. Actions タブ → **News Watch** → **Run workflow** で一度手動実行

初回は過去の告知を流さず、現在の最新記事番号を `newswatch/state.json` に記録するだけです。
以降、毎時チェックして新しい告知があれば投稿します。

監視対象を自分で増やすこともできます。方法は [仕様書](newswatch/README.md#新しいソースの足し方) を参照してください。

### 動作確認したいとき

初回実行でできた `newswatch/state.json` の `last_no` を少し小さい数字
（例：記録されている番号 − 100）に書き換えてコミットし、手動実行すると、その間の告知が投稿されます。

### 異常時の動き

- 取得に失敗した場合（公式サイトの仕様変更など）、同じチャンネルに**一度だけ**警告を投稿します。
  復旧すると自動で通常運転に戻ります
- 失敗してもワークフローは失敗扱いにしません（オーナーへの失敗メールが毎時届くのを避けるため）

### 補足

- 公開リポジトリでは、60 日間リポジトリに動きがないと定期実行が自動停止されます。
  新着のたびに `newswatch/state.json` がコミットされるので、告知が続く限り止まりません。
  止まってしまった場合は Actions タブから再度有効化してください
- 常設ページ（「今週のイベントは？」など）の中身の更新は検知しません。新しい記事が出たときだけ投稿します

## 開発者向け

### 規約

- ツールごとにフォルダを分け、コードと状態ファイルはフォルダ内で閉じる（例：`newswatch/`）
- ワークフローは `.github/workflows/<ツール名>.yml`
- Secret 名にはツール名を入れる（例：`NEWSWATCH_WEBHOOK_GLOBALLAB`）。未登録なら何もせず正常終了する
- 依存は Python 標準ライブラリのみ
- 異常は投稿先に一度だけ警告し、ワークフローは失敗扱いにしない
- 利用者が書き換えるファイル（状態・利用者設定）は配布元に置かない（Sync fork で衝突させないため）

## ライセンス

MIT。現状のまま提供します。サポートはありません。
