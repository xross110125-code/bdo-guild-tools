# newswatch セットアップ

公式サイトの新着告知を、ギルドの Discord に自動で投稿できるようにするまでの手順です。
設定が済んだ後の使い方は [manual.md](manual.md)、仕組みの詳細は [design.md](design.md) を参照してください。

## 必要なもの

- GitHub のアカウント（無料）
- 投稿先の Discord チャンネルの**管理権限**（Webhook を作るため）
- （任意）Google アカウント。起動を安定させる GAS を使う場合のみ

費用はかかりません（公開リポジトリの GitHub Actions は無料）。

## 全体の流れ

1. リポジトリをフォークして、Actions を使えるようにする
2. Discord で Webhook を作る
3. GitHub に Webhook の URL を登録する（Secret）
4. 1回目の実行をする
5. 動作確認をする
6. （任意）GAS で起動を安定させる

以下の手順では、あなたのフォークを `<owner>/bdo-guild-tools` と書きます。`<owner>` は自分の GitHub のアカウント名に読み替えてください。

## 1. フォークして Actions を使えるようにする

1. <https://github.com/xross110125-code/bdo-guild-tools> を開き、右上の **Fork** → **Create fork**
2. できたフォークの **Actions** タブを開き、**I understand my workflows, go ahead and enable them** を押す
   （フォーク直後は定期実行が無効になっています）
3. **Settings**（タブの一番右）→ 左メニュー **Actions** → **General** を開く
4. 一番下の **Workflow permissions** で **Read and write permissions** を選び、**Save**
   （ツールが状態ファイルをコミットするために必要です）
5. **Code** タブで `newswatch/state.json` を開き、右上の **…** → **Delete file** → **Commit changes**
   （フォーク元の記録がコピーされているため。消しておくと、1回目の実行で自分用に作り直されます）

## 2. Discord で Webhook を作る

監視対象（下の表）ごとに1つずつ作るのがおすすめです。
Webhook の名前が投稿者名として表示されるので、どの告知か見分けやすくなり、1つだけ止めることもできます。

| 監視対象 | 内容 | Webhook の名前の例 |
|---|---|---|
| `globallab` | グローバルラボ（韓国テスト鯖）の週次アップデート告知 | グローバルラボ |
| `jp-update` | 日本公式のアップデート告知 | 黒い砂漠 アップデート |
| `jp-event` | 日本公式のイベント告知 | 黒い砂漠 イベント |

要らないものは作らなくて構いません。Webhook（と次の Secret）を用意したものだけが動きます。

作り方：

1. 投稿先のチャンネル名にマウスを乗せ、右に出る **⚙️（チャンネルの編集）** を押す
   （または、サーバー名 → **サーバー設定** → **連携サービス**）
2. 左メニューの **連携サービス** → **ウェブフック** → **新しいウェブフック**
3. できた Webhook を開き、**お名前** を変え、**チャンネル** が投稿先になっているか確認する
4. 必要な数だけ繰り返す。画面下に **変更を保存** が出ていれば押す

⚙️ や「連携サービス」が見当たらない場合は、管理権限がありません。サーバーの管理者に頼んでください。

> **Webhook の URL は合言葉です。** 知っている人は誰でもそのチャンネルに投稿できます。
> チャットに貼ったり、URL が写ったスクリーンショットを共有したりしないでください。
> 漏れた場合は、その Webhook を削除して作り直してください。

## 3. GitHub に Webhook の URL を登録する（Secret）

1. `https://github.com/<owner>/bdo-guild-tools/settings/secrets/actions` を開く
   （**Settings** → 左メニュー **Secrets and variables** → **Actions**）
2. **New repository secret** を押す
3. **Name** に下の表の名前、**Secret** に Discord でコピーした URL を貼り、**Add secret**

| 監視対象 | Name |
|---|---|
| `globallab` | `NEWSWATCH_WEBHOOK_GLOBALLAB` |
| `jp-update` | `NEWSWATCH_WEBHOOK_JP_UPDATE` |
| `jp-event` | `NEWSWATCH_WEBHOOK_JP_EVENT` |

Discord で **ウェブフックURLをコピー** → GitHub に貼る、を1つずつ繰り返すと取り違えません。

「Secret names can only contain alphanumeric characters ...」と出たら、Name の前後に空白が入っているか、
`_`（アンダースコア）が `-`（ハイフン）になっています。打ち直してください。

## 4. 1回目の実行をする

1. **Actions** タブ → 左の **News Watch** → 右の **Run workflow** → 緑の **Run workflow**
2. 1分ほど待ち、実行に緑のチェックが付けば成功

**1回目は Discord に何も投稿されません。** 過去の告知を一斉に流さないよう、
今の最新の記事番号を `newswatch/state.json` に記録するだけです。以降、新しい告知が出たら投稿されます。

## 5. 動作確認をする

次の告知を待たずに投稿を確かめたい場合は、記録した番号を少し戻します。

1. リポジトリの `newswatch/state.json` を開き、✏️（鉛筆）で編集する
2. 確かめたい監視対象の `last_no` を小さくする（例：記録されている番号 − 30）
3. **Commit changes** で保存し、**Actions** → **News Watch** → **Run workflow** で実行する

戻した番号から最新までの間にある告知が、Discord に投稿されます。数を増やしすぎるとたくさん流れるので注意してください。

## 6. （任意）GAS で起動を安定させる

GitHub の定期実行は抜けやすく、数時間に1回しか動かないことがあります（告知を取りこぼすことはなく、投稿が遅れるだけです）。
Google Apps Script（GAS）から 15 分ごとに起動させると、投稿の遅れを 15 分程度に抑えられます。
GAS が止まっても、GitHub の定期実行だけで動く状態に戻るだけです。

### 6-1. GitHub でアクセストークンを作る

1. <https://github.com/settings/personal-access-tokens/new> を開く
   （GitHub 右上のアイコン → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**）
2. 次のとおり設定する

| 項目 | 設定 |
|---|---|
| Token name | わかる名前（例：`newswatch-dispatch`） |
| Resource owner | 自分のアカウント |
| Expiration | **No expiration**（無期限）。期限を付けると、切れた時点で GAS からの起動が止まります |
| Repository access | **Only select repositories** → 自分のフォークだけを選ぶ |
| Permissions | **Add permissions** → **Actions** を **Read and write**。ほかは触らない（Metadata: Read-only が自動で付くのは正常） |

3. **Generate token** を押し、表示されたトークン（`github_pat_` で始まる文字列）をコピーする。
   **この画面を閉じると二度と表示されません。**

No expiration の下に「期限を付けることを強く推奨」という黄色い警告が出ますが、
手を離れても動き続けることを優先して無期限にしています。代わりに権限を最小限に絞っています。

> **トークンはリポジトリを操作できる鍵です。** チャットやスクリーンショットに出さないでください。
> 漏れた場合は <https://github.com/settings/personal-access-tokens> でそのトークンを削除して作り直してください。

### 6-2. GAS に設定する

1. <https://script.google.com/> で **新しいプロジェクト** を作る（名前は自由）
2. `コード.gs` の中身を、リポジトリの [`newswatch/gas/dispatch.gs`](../../newswatch/gas/dispatch.gs) の内容で丸ごと置き換え、保存する
3. 先頭の `OWNER` を自分の GitHub のアカウント名に書き換える（`REPO` はフォークの名前を変えていなければそのまま）
4. 左の ⚙️ **プロジェクトの設定** → 一番下の **スクリプト プロパティを追加**
   - プロパティ：`GITHUB_TOKEN`
   - 値：6-1 でコピーしたトークン
   - **スクリプト プロパティを保存**
5. 左の **<>（エディタ）** に戻り、上の関数の選択欄で **`dispatch`** を選んで **▷ 実行**
   - 初回は「承認が必要です」と出るので、**権限を確認** → 自分の Google アカウントを選ぶ
   - 「このアプリは Google で確認されていません」と出たら、**詳細** → **（プロジェクト名）に移動**（自分で作ったスクリプトなので問題ありません）
   - 外部サービスへの接続を **許可**
   - 実行ログに「実行完了」と出て、GitHub の **Actions** に「Manually run by …」の実行が1件増えれば成功
6. 関数の選択欄で **`setup`** を選んで **▷ 実行**。15 分ごとのトリガーが作られる
7. 左の ⏰ **トリガー** を開き、`dispatch`・時間主導型・15 分おき のトリガーが1つあることを確認する

エラーが出た場合は [manual.md「困ったとき」](manual.md#困ったとき) を参照してください。

## よく使うページ

`<owner>` は自分のアカウント名に読み替えてください。

| 用途 | URL |
|---|---|
| Actions（実行の一覧） | `https://github.com/<owner>/bdo-guild-tools/actions` |
| Secret の一覧 | `https://github.com/<owner>/bdo-guild-tools/settings/secrets/actions` |
| Actions の設定（書き込み権限など） | `https://github.com/<owner>/bdo-guild-tools/settings/actions` |
| アクセストークンの一覧 | <https://github.com/settings/personal-access-tokens> |
| GAS のプロジェクト一覧 | <https://script.google.com/home> |
