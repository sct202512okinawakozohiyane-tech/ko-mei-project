# TOEIC Study Lab

ローカルLLM「孔明」を活用したTOEIC学習支援アプリです。

## 概要

TOEIC Part 5形式の英文法問題を自動生成し、SQLiteに保存します。
学習者はWeb画面上で問題を解き、正誤・解説・学習履歴を確認できます。

## 主な機能

- TOEIC Part 5形式の問題生成
- JSON形式での問題管理
- SQLiteによる学習履歴保存
- 正答率・苦手分野の記録
- Flaskによる簡易Web UI

## 技術構成

- Python
- Flask
- SQLite
- HTML/CSS
- ローカルLLM

## 問題データのインポート

`questions/approved/questions.json` に置いた問題データを `questions` テーブルへ一括INSERTする。

```bash
python3 scripts/import_questions.py
```

- 入力ファイル: `questions/approved/questions.json`（JSON配列、1要素が1問）
- 各要素のキー: `part`（整数）, `question_text`, `choice_a`〜`choice_d`, `correct_answer`（"A"〜"D"の文字列）, `explanation`, `difficulty`（文字列）
- 実行するたびにJSON内の全件が新規行としてINSERTされる（重複チェックなし）

## note
- SQlite の実行コマンド
sqlite3 data/toeic.db

- 初回の作問のコマンドは「地」のターミナルから、
cd ko-mei-project
docker exec -w /workspace/toeic-study-lab ko-mei python3 scripts/generate_question.py 10

- 初回レビューの実施方法
cd /home/koz/ko-mei-project/workspace/toeic-study-lab
docker exec ko-mei python3 /workspace/toeic-study-lab/scripts/review_question.py 10

- レビュー後のファイルの仕分け（フォルダの移動）コマンド
docker exec ko-mei python3 /workspace/toeic-study-lab/scripts/sort_reviewed.py

- レビューを反映して "need_fix"フォルダ内のファイルを修正するコマンド
docker exec ko-mei python3 /workspace/toeic-study-lab/scripts/rewrite_question.py

- 再レビューコマンド
docker exec ko-mei python3 /workspace/toeic-study-lab/scripts/rereview_question.py

- 再レビュー後のファイルの仕分け（フォルダの移動）コマンド
docker exec ko-mei python3 /workspace/toeic-study-lab/scripts/finalize_questions.py

## その他
# 1. DBマイグレーション（初回のみ）
docker exec ko-mei python3 /workspace/toeic-study-lab/scripts/migrate_add_grammar_category.py

# 2. カテゴリ指定で問題生成
docker exec ko-mei python3 /workspace/toeic-study-lab/scripts/generate_question.py 5 participle
docker exec ko-mei python3 /workspace/toeic-study-lab/scripts/generate_question.py 5 relative_clause

# 3. カテゴリ別分布確認（DB投入後）
docker exec ko-mei python3 /workspace/toeic-study-lab/scripts/question_distribution.py
docker exec ko-mei python3 /workspace/toeic-study-lab/scripts/question_distribution.py --threshold 10
