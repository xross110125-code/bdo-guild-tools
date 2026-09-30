/**
 * News Watch ワークフローを外部から起動する（Google Apps Script 用）。
 *
 * GitHub Actions の定期実行（schedule）は抜けやすいため、GAS の時間主導トリガーから
 * workflow_dispatch を叩いて補う。GitHub 側の定期実行はそのまま残るので、
 * これが止まっても「定期実行だけで動く状態」に戻るだけで、監視は止まらない。
 *
 * 使い方（詳しくは docs/newswatch/setup.md「6. （任意）GAS で起動を安定させる」）:
 *   1. 下の OWNER / REPO を、起動したいリポジトリ（自分のフォーク）に合わせる
 *   2. スクリプトプロパティ GITHUB_TOKEN にアクセストークンを保存する
 *   3. setup() を1回実行する（トリガーが作られる）
 *
 * トークンはこのファイルに書かないこと。
 */

const OWNER = 'xross110125-code';
const REPO = 'bdo-guild-tools';
const WORKFLOW = 'newswatch.yml';
const REF = 'main';
const EVERY_MINUTES = 15; // GAS で選べるのは 1 / 5 / 10 / 15 / 30

/** ワークフローを1回起動する。トリガーから呼ばれる。 */
function dispatch() {
  const token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  if (!token) {
    throw new Error('スクリプトプロパティ GITHUB_TOKEN が未設定です');
  }
  const url = `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}/dispatches`;
  const res = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
    },
    payload: JSON.stringify({ ref: REF }),
    muteHttpExceptions: true,
  });
  const code = res.getResponseCode();
  if (code < 200 || code >= 300) {
    // 失敗はエラーにして、GAS のトリガー失敗通知メールで気づけるようにする
    throw new Error(`起動に失敗しました: HTTP ${code} ${res.getContentText()}`);
  }
}

/** dispatch を EVERY_MINUTES 分ごとに呼ぶトリガーを作る。何度実行しても1つだけになる。 */
function setup() {
  ScriptApp.getProjectTriggers()
    .filter((t) => t.getHandlerFunction() === 'dispatch')
    .forEach((t) => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('dispatch').timeBased().everyMinutes(EVERY_MINUTES).create();
}

/** トリガーを消して、外部からの起動をやめる。 */
function teardown() {
  ScriptApp.getProjectTriggers()
    .filter((t) => t.getHandlerFunction() === 'dispatch')
    .forEach((t) => ScriptApp.deleteTrigger(t));
}
