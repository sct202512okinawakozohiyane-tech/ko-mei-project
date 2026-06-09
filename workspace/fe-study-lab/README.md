# FE（基本情報技術者試験）向けアルゴリズム問題の作問機能は、"ko-mei" の Docker 環境で作業する必要がある。

# project フォルダに移動する
cd ko-mei-project

# Docker に入る
docker exec -it ko-mei bash

# 作業フォルダ workspace/fe-study-lab へ移動
cd fe-study-lab

# テスト実施コマンド
bash scripts/run_quiz.sh

# 問題作成コマンド
bash scripts/generate_many.sh 10

# 問題レビューコマンド
## レビュー結果は feedback/reviews/ フォルダに格納される
scripts/review_pending.sh

# reject & fix 問題修正コマンド
## reject された問題ファイルとレビュー結果ファイルを questions/rejected フォルダへ格納してから以下を実施する
scripts/repair_rejected.sh