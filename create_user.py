"""
Quick script to create a new user for the Maltese Law RAG system.

Usage:
    python create_user.py

This will prompt for username, password, email, and notes, then create
the user and display their API token.
"""

from user_tracking import tracker
import sys


def main():
    print("=" * 60)
    print("Create New User - Maltese Law RAG")
    print("=" * 60)
    print()

    # Get user details
    username = input("Username: ").strip()
    if not username:
        print("Error: Username is required")
        return

    password = input("Password: ").strip()
    if not password:
        print("Error: Password is required")
        return

    email = input("Email (optional): ").strip()
    notes = input("Notes (e.g. 'Free trial - Company XYZ'): ").strip()

    print()
    print("Creating user...")

    # Create the user
    result = tracker.create_user(
        username=username,
        password=password,
        email=email,
        notes=notes
    )

    if result.get('success'):
        print()
        print("✓ User created successfully!")
        print()
        print("=" * 60)
        print("API TOKEN (save this - give it to the client):")
        print("=" * 60)
        print(result['api_token'])
        print("=" * 60)
        print()
        print(f"User ID: {result['user_id']}")
        print(f"Username: {result['username']}")
        print()
        print("The client should:")
        print("1. Open the chat interface")
        print("2. Click the 'No Token' button in the header")
        print("3. Enter this token and click 'Save Token'")
        print("4. Start asking questions!")
        print()
        if tracker.telegram_bot_token:
            print("✓ Telegram notification sent to admin")
        else:
            print("⚠ Telegram notifications not configured (set TELEGRAM_BOT_TOKEN in .env)")
        print()
    else:
        print(f"✗ Error: {result.get('error')}")
        sys.exit(1)


if __name__ == '__main__':
    main()
