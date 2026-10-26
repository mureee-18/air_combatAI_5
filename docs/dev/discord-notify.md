# PR のコメント・レビューを Discord に通知する

`.github/workflows/discord-pr-comments.yml` が、PR にコメントやレビューが付いたときに Discord へ 1 件ずつ投稿します。本文は `scripts/discord_pr_notify.py` が組み立てます。

## 通知の例

```
💬 mureee-18 さんが PR #18「H9: Red 側だけ護衛を早める」にコメントしました
> 良さそうです。EH 相手の Red が少し下がっている点だけ次で見てください。
<https://github.com/mureee-18/air_combatAI_5/pull/18#issuecomment-...>
```

| イベント | 1 行目 |
|---|---|
| PR の会話欄へのコメント | 💬 〇〇 さんが PR #N「タイトル」にコメントしました |
| レビュー（承認） | ✅ 〇〇 さんが PR #N「タイトル」を承認しました |
| レビュー（変更リクエスト） | 📝 〇〇 さんが PR #N「タイトル」に変更をリクエストしました |
| レビュー（コメント、本文あり） | 💬 〇〇 さんが PR #N「タイトル」をレビューしました |
| 差分の行へのコメント | 💬 〇〇 さんが PR #N「タイトル」の `path` にコメントしました |

- 本文は先頭 300 文字までを引用し、その下にコメントへのリンクを付けます。
- 本文が空の「コメントのみ」レビューは通知しません。その中の行コメントは 1 件ずつ通知されるので、重複を避けるためです。
- Issue（PR ではないもの）へのコメントと、ボット（`github-actions[bot]` など）の投稿は通知しません。
- `allowed_mentions` を空にしているので、本文に `@everyone` などがあっても通知は飛びません。

## 設定手順

1. Discord で通知先チャンネルの設定を開き、「連携サービス」→「ウェブフック」→「新しいウェブフック」で Webhook を作り、URL をコピーします。
2. リポジトリの持ち主が GitHub の Settings → Secrets and variables → Actions → New repository secret を開き、名前 `DISCORD_WEBHOOK_URL`、値にコピーした URL を登録します。

Secret が未設定のあいだ、ワークフローは notice を出して何もせずに成功します。Webhook URL を知っていれば誰でも投稿できるので、チャットやコミットには貼らないでください。

## 注意

- `issue_comment` のワークフローは既定ブランチ（master）の定義で動くため、この PR がマージされるまでは通知されません。
- fork からの PR では Secret が渡らないため通知されません。
- コメント本文はスクリプトがイベントの JSON から直接読み、シェルには展開しません（スクリプトインジェクション対策）。

## ローカルでの確認

```bash
python scripts/discord_pr_notify.py --event-name issue_comment --event-path sample_event.json --dry-run
uvx --with pytest pytest tests/test_discord_pr_notify.py
```

`--dry-run` は Discord に送らず、送信する JSON を表示します。
