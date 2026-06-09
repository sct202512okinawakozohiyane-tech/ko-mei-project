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
