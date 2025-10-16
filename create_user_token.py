#!/usr/bin/env python3
"""
管理者用: ユーザーアカウントとトークンを発行するスクリプト

使用例:
    # 対話モード
    python create_user_token.py

    # コマンドライン引数で指定
    python create_user_token.py --email user@example.com --username myuser --password mypass123

    # 既存ユーザーのトークンを再発行
    python create_user_token.py --email user@example.com --reissue
"""

import argparse
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from database import get_db, User
from auth import get_password_hash, create_access_token
from sqlalchemy.orm import Session


def create_user_and_token(
    email: str,
    username: str,
    password: str,
    db: Session
) -> tuple[User, str]:
    """
    新規ユーザーを作成してトークンを発行

    Args:
        email: メールアドレス
        username: ユーザー名
        password: パスワード
        db: データベースセッション

    Returns:
        (User, token): 作成されたユーザーとJWTトークン

    Raises:
        ValueError: メールアドレスまたはユーザー名が既に使用されている場合
    """
    # 重複チェック
    if db.query(User).filter(User.email == email).first():
        raise ValueError(f"メールアドレス '{email}' は既に登録されています")

    if db.query(User).filter(User.username == username).first():
        raise ValueError(f"ユーザー名 '{username}' は既に使用されています")

    # ユーザー作成
    hashed_password = get_password_hash(password)
    user = User(
        email=email,
        username=username,
        hashed_password=hashed_password
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # トークン生成
    token = create_access_token(data={"sub": str(user.id)})

    return user, token


def reissue_token(email: str, db: Session) -> tuple[User, str]:
    """
    既存ユーザーのトークンを再発行

    Args:
        email: メールアドレス
        db: データベースセッション

    Returns:
        (User, token): ユーザーと新しいJWTトークン

    Raises:
        ValueError: ユーザーが存在しない場合
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise ValueError(f"メールアドレス '{email}' のユーザーが見つかりません")

    # トークン生成
    token = create_access_token(data={"sub": str(user.id)})

    return user, token


def list_users(db: Session):
    """登録済みユーザー一覧を表示"""
    users = db.query(User).all()
    if not users:
        print("登録済みユーザーはいません")
        return

    print(f"\n登録済みユーザー ({len(users)}人):")
    print("-" * 80)
    print(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Created At'}")
    print("-" * 80)
    for user in users:
        print(f"{user.id:<5} {user.username:<20} {user.email:<30} {user.created_at}")
    print("-" * 80)


def interactive_mode(db: Session):
    """対話モードでユーザー作成またはトークン再発行"""
    print("\n=== ユーザートークン管理 ===\n")
    print("1. 新規ユーザー作成とトークン発行")
    print("2. 既存ユーザーのトークン再発行")
    print("3. 登録済みユーザー一覧を表示")
    print("4. 終了")

    choice = input("\n選択してください (1-4): ").strip()

    if choice == "1":
        print("\n--- 新規ユーザー作成 ---")
        email = input("メールアドレス: ").strip()
        username = input("ユーザー名: ").strip()
        password = input("パスワード: ").strip()

        try:
            user, token = create_user_and_token(email, username, password, db)
            print("\n✅ ユーザー作成成功！")
            print(f"\nユーザーID: {user.id}")
            print(f"ユーザー名: {user.username}")
            print(f"メールアドレス: {user.email}")
            print(f"\n🔑 JWTトークン:")
            print(token)
            print("\n※このトークンは7日間有効です")
            print("※ユーザーにこのトークンを安全に共有してください")

        except ValueError as e:
            print(f"\n❌ エラー: {e}")

    elif choice == "2":
        print("\n--- トークン再発行 ---")
        email = input("メールアドレス: ").strip()

        try:
            user, token = reissue_token(email, db)
            print("\n✅ トークン再発行成功！")
            print(f"\nユーザーID: {user.id}")
            print(f"ユーザー名: {user.username}")
            print(f"メールアドレス: {user.email}")
            print(f"\n🔑 新しいJWTトークン:")
            print(token)
            print("\n※このトークンは7日間有効です")

        except ValueError as e:
            print(f"\n❌ エラー: {e}")

    elif choice == "3":
        list_users(db)

    elif choice == "4":
        print("\n終了します")
        sys.exit(0)

    else:
        print("\n❌ 無効な選択です")


def main():
    parser = argparse.ArgumentParser(
        description="ユーザーアカウントとトークンを管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 対話モード
  python create_user_token.py

  # 新規ユーザー作成
  python create_user_token.py --email user@example.com --username myuser --password mypass123

  # 既存ユーザーのトークン再発行
  python create_user_token.py --email user@example.com --reissue

  # ユーザー一覧表示
  python create_user_token.py --list
        """
    )

    parser.add_argument("--email", help="メールアドレス")
    parser.add_argument("--username", help="ユーザー名（新規作成時のみ）")
    parser.add_argument("--password", help="パスワード（新規作成時のみ）")
    parser.add_argument("--reissue", action="store_true", help="既存ユーザーのトークンを再発行")
    parser.add_argument("--list", action="store_true", help="登録済みユーザー一覧を表示")

    args = parser.parse_args()

    # データベースセッション取得
    db = next(get_db())

    try:
        # ユーザー一覧表示
        if args.list:
            list_users(db)
            return

        # トークン再発行
        if args.reissue:
            if not args.email:
                print("❌ エラー: --email を指定してください")
                sys.exit(1)

            try:
                user, token = reissue_token(args.email, db)
                print(f"\n✅ トークン再発行成功！")
                print(f"\nユーザー: {user.username} ({user.email})")
                print(f"\n🔑 新しいJWTトークン:")
                print(token)
                print("\n※このトークンは7日間有効です")

            except ValueError as e:
                print(f"❌ エラー: {e}")
                sys.exit(1)

            return

        # 新規ユーザー作成
        if args.email and args.username and args.password:
            try:
                user, token = create_user_and_token(
                    args.email,
                    args.username,
                    args.password,
                    db
                )
                print(f"\n✅ ユーザー作成成功！")
                print(f"\nユーザーID: {user.id}")
                print(f"ユーザー名: {user.username}")
                print(f"メールアドレス: {user.email}")
                print(f"\n🔑 JWTトークン:")
                print(token)
                print("\n※このトークンは7日間有効です")
                print("※ユーザーにこのトークンを安全に共有してください")

            except ValueError as e:
                print(f"❌ エラー: {e}")
                sys.exit(1)

        # 引数が不足している場合は対話モード
        else:
            while True:
                interactive_mode(db)
                print()

    finally:
        db.close()


if __name__ == "__main__":
    main()
