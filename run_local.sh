#!/bin/bash
# ローカル開発用の起動スクリプト

echo "========================================="
echo "ローカル開発環境を起動します"
echo "========================================="
echo ""

# .env.localを.envにコピー
if [ -f .env.local ]; then
    echo "✓ .env.localから環境変数を読み込みます"
    cp .env.local .env
else
    echo "✗ .env.localが見つかりません"
    exit 1
fi

# Ollamaが起動しているか確認
echo ""
echo "Ollamaの状態を確認中..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✓ Ollamaが起動しています"

    # gpt-oss:latestモデルが存在するか確認
    if curl -s http://localhost:11434/api/tags | grep -q "gpt-oss:latest"; then
        echo "✓ gpt-oss:latestモデルが利用可能です"
    else
        echo "⚠ gpt-oss:latestモデルが見つかりません"
        echo "  以下のコマンドでモデルをプルしてください："
        echo "  ollama pull gpt-oss:latest"
        exit 1
    fi
else
    echo "✗ Ollamaが起動していません"
    echo "  以下のコマンドでOllamaを起動してください："
    echo "  ollama serve"
    exit 1
fi

echo ""
echo "========================================="
echo "FastAPIサーバーを起動します"
echo "ポート: 8000"
echo "========================================="
echo ""

# FastAPIサーバーを起動
uvicorn main:app --reload --host 0.0.0.0 --port 8000
