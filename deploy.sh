#!/bin/bash
# 本番環境へのデプロイスクリプト

echo "========================================="
echo "本番環境へのデプロイを開始します"
echo "========================================="
echo ""

# .envが本番用か確認
if grep -q "localhost:11434" .env; then
    echo "✗ エラー: .envがローカル開発用の設定になっています"
    echo "  本番用の.envに切り替えてください"
    exit 1
fi

echo "✓ .envが本番用設定であることを確認しました"
echo ""

# テストを実行
echo "テストを実行中..."
python -m pytest test_phase*.py -v
if [ $? -ne 0 ]; then
    echo "✗ テストが失敗しました"
    read -p "デプロイを続行しますか？ (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "✓ テストが完了しました"
echo ""

# Git push
echo "Gitリポジトリにpushします..."
git push

echo ""
echo "========================================="
echo "✓ デプロイが完了しました"
echo "Railwayで自動デプロイが開始されます"
echo "========================================="
