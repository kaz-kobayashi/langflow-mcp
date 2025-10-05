"""
Test MCP integration with chat agent
"""

import requests
import json

# テスト用のトークン（実際の環境に合わせて変更）
API_URL = "http://localhost:8000"

def test_eoq_calculation():
    """EOQ計算のテスト"""
    print("=== EOQ計算のテスト ===")

    # ユーザー登録（既に登録済みの場合はスキップ）
    register_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "password123"
    }

    response = requests.post(f"{API_URL}/api/register", json=register_data)
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✓ 登録成功: トークン取得")
    else:
        # ログイン試行
        login_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        response = requests.post(f"{API_URL}/api/login", json=login_data)
        token = response.json()["access_token"]
        print(f"✓ ログイン成功: トークン取得")

    # チャットリクエスト
    chat_data = {
        "messages": [
            {
                "role": "user",
                "content": "発注固定費用が1000円、平均需要量が100個/日、在庫保管費用が1円/個/日、品切れ費用が100円/個/日の場合の経済発注量を計算してください。"
            }
        ],
        "model": "gpt-3.5-turbo"
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print("\nチャットリクエスト送信中...")
    response = requests.post(f"{API_URL}/api/chat", json=chat_data, headers=headers, stream=True)

    print("\n応答:")
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data_str = line_str[6:]
                if data_str == '[DONE]':
                    break
                try:
                    data = json.loads(data_str)
                    if 'content' in data:
                        print(data['content'], end='', flush=True)
                    elif 'function_call' in data:
                        print(f"\n\n🔧 Function Call: {data['function_call']['name']}")
                        print(f"Result: {json.dumps(data['function_call']['result'], indent=2, ensure_ascii=False)}\n")
                except:
                    pass
    print("\n")


def test_safety_stock_calculation():
    """安全在庫計算のテスト"""
    print("\n=== 安全在庫計算のテスト ===")

    # ログイン
    login_data = {
        "email": "test@example.com",
        "password": "password123"
    }
    response = requests.post(f"{API_URL}/api/login", json=login_data)
    token = response.json()["access_token"]

    # チャットリクエスト
    chat_data = {
        "messages": [
            {
                "role": "user",
                "content": "平均需要量が100個/日、需要の標準偏差が10、リードタイムが3日、品切れ費用が100円/個/日、在庫保管費用が1円/個/日の場合の安全在庫レベルを計算してください。"
            }
        ],
        "model": "gpt-3.5-turbo"
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print("\nチャットリクエスト送信中...")
    response = requests.post(f"{API_URL}/api/chat", json=chat_data, headers=headers, stream=True)

    print("\n応答:")
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data_str = line_str[6:]
                if data_str == '[DONE]':
                    break
                try:
                    data = json.loads(data_str)
                    if 'content' in data:
                        print(data['content'], end='', flush=True)
                    elif 'function_call' in data:
                        print(f"\n\n🔧 Function Call: {data['function_call']['name']}")
                        print(f"Result: {json.dumps(data['function_call']['result'], indent=2, ensure_ascii=False)}\n")
                except:
                    pass
    print("\n")


if __name__ == "__main__":
    test_eoq_calculation()
    test_safety_stock_calculation()
