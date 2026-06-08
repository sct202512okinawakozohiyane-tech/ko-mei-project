#!/bin/bash

# 生成回数を引数から取得する（引数がなければ 3 回）
COUNT=${1:-3}

# このスクリプトがある場所を基準に ask_komei_once.sh のパスを決める
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ONCE_SCRIPT="$SCRIPT_DIR/ask_komei_once.sh"

# 成功・失敗のカウンタを初期化する
SUCCESS=0
FAIL=0

for i in $(seq 1 "$COUNT"); do
    echo "========================================="
    echo "[$i/$COUNT] 問題を生成します..."
    echo "========================================="

    # ask_komei_once.sh を実行し、成否をカウントする
    if bash "$ONCE_SCRIPT"; then
        SUCCESS=$((SUCCESS + 1))
        echo "[$i/$COUNT] 成功しました"
    else
        FAIL=$((FAIL + 1))
        echo "[$i/$COUNT] 失敗しました（次の回に進みます）"
    fi

    # 最後の回の後は待機しない
    if [ "$i" -lt "$COUNT" ]; then
        echo "60秒待機します..."
        sleep 60
    fi
done

echo "========================================="
echo "完了: 成功 $SUCCESS 回 / 失敗 $FAIL 回"
echo "========================================="
