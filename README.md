# bdo-guild-tools

黒い砂漠（Black Desert）のギルド運営で使える小さな便利ツール集です。

- 費用：無料（公開リポジトリの GitHub Actions で動きます）
- 外部ライブラリ：なし（Python 標準ライブラリのみ）
- 使いたいツールだけ有効化できます。Secrets を登録していないツールは何もしません

## ツール一覧

| ツール | 内容 | 必要な Secret |
|---|---|---|
| [グローバルラボ更新通知](#グローバルラボ更新通知globallab) | グローバルラボ（テスト鯖）の週次アップデート告知を Discord に投稿 | `GLOBALLAB_WEBHOOK_URL` |

## 導入手順（共通）

このリポジトリを**フォーク**して、自分たちのフォークで動かします。

1. 右上の **Fork** からフォークを作る
2. フォークの **Actions** タブを開き、「I understand my workflows, go ahead and enable them」を押す
   （フォーク直後は定期実行が無効になっています）
3. **Settings → Actions → General → Workflow permissions** を
   「**Read and write permissions**」にして Save
   （ツールが状態ファイルをコミットするために必要です）
4. 使いたいツールの Secret を登録する（各ツールの項目を参照）
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

## グローバルラボ更新通知（globallab）

黒い砂漠グローバルラボの週次アップデート告知（업데이트 안내）を検知して、
タイトルと原文 URL を Discord チャンネルに投稿します。翻訳はしません。

- 取得元：<https://blackdesert.pearlabyss.com/GlobalLab/en-US/News/Notice?_categoryNo=2>
- 実行頻度：毎時（告知が無い週もあり、その場合は何も投稿されません）
- セキュリティモジュール更新（보안 모듈）の告知は投稿しません
- 投稿例：
  > 📢 **グローバルラボ更新**<br>
  > 9월 18일(금) 업데이트 안내<br>
  > https://blackdesert.pearlabyss.com/GlobalLab/en-US/News/Notice/Detail?_boardNo=19837<br>
  > ※原文は韓国語です。ブラウザの翻訳機能で読めます。テスト鯖の情報のため、日本鯖への適用時期・内容は未定です。

### 設定

1. Discord で投稿先チャンネルの Webhook URL を作る
   （チャンネルの編集 → 連携サービス → ウェブフック → 新しいウェブフック → URL をコピー）
2. `GLOBALLAB_WEBHOOK_URL` という名前で Secret に登録
3. Actions タブ → **Global Lab Notifier** → **Run workflow** で一度手動実行

初回は過去の告知を流さず、現在の最新記事番号を `globallab/state.json` に記録するだけです。
以降、毎時チェックして新しい告知があれば投稿します。

### 動作確認したいとき

初回実行でできた `globallab/state.json` の `last_board_no` を少し小さい数字
（例：記録されている番号 − 100）に書き換えてコミットし、手動実行すると、その間の告知が投稿されます。

### 異常時の動き

- 取得に失敗した場合（公式サイトの仕様変更など）、同じチャンネルに**一度だけ**警告を投稿します。
  復旧すると自動で通常運転に戻ります
- 失敗してもワークフローは失敗扱いにしません（オーナーへの失敗メールが毎時届くのを避けるため）

### 補足

- 公開リポジトリでは、60 日間リポジトリに動きがないと定期実行が自動停止されます。
  新着のたびに `globallab/state.json` がコミットされるので、告知が続く限り止まりません。
  止まってしまった場合は Actions タブから再度有効化してください

## 開発者向け

```
python globallab/notify.py --dry-run               # 投稿・状態保存をせず、一覧の検出結果を表示
python globallab/notify.py --dry-run --since 19800 # 記事番号 19800 より後だけ表示
```

### 規約

- ツールごとにフォルダを分け、コードと状態ファイルはフォルダ内で閉じる（例：`globallab/`）
- ワークフローは `.github/workflows/<ツール名>.yml`
- Secret 名にはツール名を入れる（例：`GLOBALLAB_WEBHOOK_URL`）。未登録なら何もせず正常終了する
- 依存は Python 標準ライブラリのみ
- 異常は投稿先に一度だけ警告し、ワークフローは失敗扱いにしない

## ライセンス

MIT。現状のまま提供します。サポートはありません。
