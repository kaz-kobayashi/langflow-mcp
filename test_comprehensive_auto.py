#!/usr/bin/env python
"""
COMPREHENSIVE_TEST_EXAMPLES.mdの入力例を自動実行するスクリプト

使い方:
  # Railway本番環境でテスト
  python test_comprehensive_auto.py --url https://web-production-1ed39.up.railway.app/api/chat

  # ローカルでテスト
  python test_comprehensive_auto.py

  # 範囲指定
  python test_comprehensive_auto.py --url https://web-production-1ed39.up.railway.app/api/chat --start 1 --end 10

オプション:
  --url URL        完全なURL（例: https://web-production-1ed39.up.railway.app/api/chat）
  --host HOST      FastAPIサーバーのホスト（デフォルト: localhost、--url指定時は無視）
  --port PORT      FastAPIサーバーのポート（デフォルト: 8000、--url指定時は無視）
  --output OUTPUT  結果の出力ファイル（デフォルト: test_results.txt）
  --start N        開始テストケース番号（デフォルト: 1）
  --end N          終了テストケース番号（デフォルト: すべて）
  --verbose        詳細な出力を表示
"""

import argparse
import json
import re
import requests
import sys
import time
from datetime import datetime
from pathlib import Path


def parse_test_examples(md_file_path: str) -> list[dict]:
    """
    COMPREHENSIVE_TEST_EXAMPLES.mdから入力例を抽出

    Returns:
        list of dict with keys: category, tool_name, description, input_text
    """
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    test_cases = []
    current_category = None

    # セクションごとに分割
    sections = re.split(r'^## (\d+\. .+)$', content, flags=re.MULTILINE)

    for i in range(1, len(sections), 2):
        if i + 1 >= len(sections):
            break

        category = sections[i].strip()
        section_content = sections[i + 1]

        # ツールごとに分割
        tool_sections = re.split(r'^### ([\d.]+) (.+)$', section_content, flags=re.MULTILINE)

        for j in range(1, len(tool_sections), 3):
            if j + 2 >= len(tool_sections):
                break

            tool_number = tool_sections[j].strip()
            tool_name = tool_sections[j + 1].strip()
            tool_content = tool_sections[j + 2]

            # **入力例**:のブロックを抽出
            input_match = re.search(
                r'\*\*入力例\*\*:\s*```(.*?)```',
                tool_content,
                re.DOTALL
            )

            if input_match:
                input_text = input_match.group(1).strip()

                # **目的**:を抽出
                purpose_match = re.search(r'\*\*目的\*\*:\s*(.+?)(?:\n\n|\*\*)', tool_content, re.DOTALL)
                description = purpose_match.group(1).strip() if purpose_match else ""

                test_cases.append({
                    'category': category,
                    'tool_number': tool_number,
                    'tool_name': tool_name,
                    'description': description,
                    'input_text': input_text
                })

    return test_cases


def send_chat_message(message: str, url: str = None, host: str = "localhost", port: int = 8000) -> dict:
    """
    /api/chatエンドポイントにメッセージを送信

    Args:
        message: チャットメッセージ
        url: 完全なURL（指定時はhost/portを無視）
        host: サーバーホスト
        port: サーバーポート

    Returns:
        レスポンスJSON
    """
    if url is None:
        url = f"http://{host}:{port}/api/chat"

    headers = {"Content-Type": "application/json"}
    payload = {"message": message}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": f"リクエストエラー: {str(e)}"
        }


def format_response(response: dict, verbose: bool = False) -> str:
    """
    レスポンスを読みやすい形式にフォーマット
    """
    if verbose:
        return json.dumps(response, ensure_ascii=False, indent=2)

    # 簡潔な出力
    status = response.get("status", "unknown")

    if status == "success":
        message = response.get("message", "")
        if len(message) > 200:
            message = message[:200] + "..."
        return f"✓ SUCCESS: {message}"
    else:
        error_msg = response.get("message", "不明なエラー")
        return f"✗ ERROR: {error_msg}"


def run_tests(
    test_cases: list[dict],
    url: str = None,
    host: str = "localhost",
    port: int = 8000,
    output_file: str = "test_results.txt",
    start: int = 1,
    end: int = None,
    verbose: bool = False
):
    """
    テストケースを順次実行
    """
    if end is None:
        end = len(test_cases)

    # 範囲チェック
    start = max(1, min(start, len(test_cases)))
    end = max(start, min(end, len(test_cases)))

    selected_tests = test_cases[start-1:end]

    server_info = url if url else f"http://{host}:{port}"

    print(f"=" * 80)
    print(f"テスト実行開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"対象: {start}～{end}番 (全{len(test_cases)}個中)")
    print(f"サーバー: {server_info}")
    print(f"出力ファイル: {output_file}")
    print(f"=" * 80)
    print()

    results = []
    success_count = 0
    error_count = 0

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"テスト実行結果\n")
        f.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"対象範囲: {start}～{end}番\n")
        f.write(f"=" * 80 + "\n\n")

        for idx, test_case in enumerate(selected_tests, start=start):
            category = test_case['category']
            tool_name = test_case['tool_name']
            input_text = test_case['input_text']

            print(f"[{idx}/{len(test_cases)}] {category} - {tool_name}")
            print(f"  入力文字数: {len(input_text)} 文字")

            # ファイルに書き込み
            f.write(f"[{idx}] {category}\n")
            f.write(f"ツール: {tool_name}\n")
            f.write(f"説明: {test_case['description']}\n")
            f.write(f"{'-' * 80}\n")
            f.write(f"入力:\n{input_text}\n\n")

            # APIリクエスト送信
            start_time = time.time()
            response = send_chat_message(input_text, url=url, host=host, port=port)
            elapsed = time.time() - start_time

            # 結果の記録
            status = response.get("status", "unknown")
            formatted_response = format_response(response, verbose)

            print(f"  {formatted_response}")
            print(f"  実行時間: {elapsed:.2f}秒")
            print()

            f.write(f"結果 ({elapsed:.2f}秒):\n")
            f.write(json.dumps(response, ensure_ascii=False, indent=2))
            f.write(f"\n\n{'=' * 80}\n\n")

            # 統計を更新
            if status == "success":
                success_count += 1
            else:
                error_count += 1

            results.append({
                'test_number': idx,
                'tool_name': tool_name,
                'status': status,
                'elapsed': elapsed
            })

            # サーバーへの負荷を考慮して少し待機
            time.sleep(0.5)

        # サマリー
        total = len(selected_tests)
        success_rate = (success_count / total * 100) if total > 0 else 0

        summary = f"""
{'=' * 80}
テスト実行サマリー
{'=' * 80}
総テスト数: {total}
成功: {success_count} ({success_rate:.1f}%)
失敗: {error_count} ({100 - success_rate:.1f}%)
{'=' * 80}
"""
        print(summary)
        f.write(summary)

        # 失敗したテストのリスト
        if error_count > 0:
            failed_tests = [r for r in results if r['status'] != 'success']
            f.write("\n失敗したテスト:\n")
            for r in failed_tests:
                f.write(f"  [{r['test_number']}] {r['tool_name']}\n")

    print(f"\n結果は {output_file} に保存されました。")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="COMPREHENSIVE_TEST_EXAMPLES.mdの入力例を自動実行",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--url',
        default=None,
        help='完全なURL（例: https://web-production-1ed39.up.railway.app/api/chat）'
    )

    parser.add_argument(
        '--host',
        default='localhost',
        help='FastAPIサーバーのホスト（デフォルト: localhost、--url指定時は無視）'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='FastAPIサーバーのポート（デフォルト: 8000、--url指定時は無視）'
    )

    parser.add_argument(
        '--output',
        default='test_results.txt',
        help='結果の出力ファイル（デフォルト: test_results.txt）'
    )

    parser.add_argument(
        '--start',
        type=int,
        default=1,
        help='開始テストケース番号（デフォルト: 1）'
    )

    parser.add_argument(
        '--end',
        type=int,
        default=None,
        help='終了テストケース番号（デフォルト: すべて）'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='詳細な出力を表示'
    )

    args = parser.parse_args()

    # COMPREHENSIVE_TEST_EXAMPLES.mdのパスを取得
    md_file = Path(__file__).parent / "COMPREHENSIVE_TEST_EXAMPLES.md"

    if not md_file.exists():
        print(f"エラー: {md_file} が見つかりません", file=sys.stderr)
        sys.exit(1)

    # サーバーの接続チェック
    if args.url:
        # 完全URLの場合、/healthエンドポイントをチェック
        health_url = args.url.replace('/api/chat', '/health')
        try:
            response = requests.get(health_url, timeout=5)
            response.raise_for_status()
            print(f"✓ サーバー接続確認: {args.url}")
        except requests.exceptions.RequestException as e:
            print(f"✗ サーバーに接続できません: {e}", file=sys.stderr)
            print(f"  URL: {args.url}", file=sys.stderr)
            sys.exit(1)
    else:
        # host/portの場合
        try:
            response = requests.get(f"http://{args.host}:{args.port}/health", timeout=5)
            response.raise_for_status()
            print(f"✓ サーバー接続確認: http://{args.host}:{args.port}")
        except requests.exceptions.RequestException as e:
            print(f"✗ サーバーに接続できません: {e}", file=sys.stderr)
            print(f"  サーバーが起動しているか確認してください: ./run_local.sh", file=sys.stderr)
            sys.exit(1)

    # テストケースをパース
    print(f"テストケースを抽出中: {md_file}")
    test_cases = parse_test_examples(str(md_file))
    print(f"✓ {len(test_cases)}個のテストケースを抽出しました\n")

    # テスト実行
    results = run_tests(
        test_cases=test_cases,
        url=args.url,
        host=args.host,
        port=args.port,
        output_file=args.output,
        start=args.start,
        end=args.end,
        verbose=args.verbose
    )

    # 終了コード
    error_count = sum(1 for r in results if r['status'] != 'success')
    sys.exit(0 if error_count == 0 else 1)


if __name__ == "__main__":
    main()
