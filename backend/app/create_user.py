"""Command-line helper to create (or reset the password of) a user.

Usage (from the backend folder):
    python -m app.create_user some_username
The password is typed at a hidden prompt, so it never appears in shell history.
"""

import getpass
import sys

from . import database, security


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m app.create_user <username>")
        sys.exit(1)

    username = sys.argv[1].strip()
    password = getpass.getpass("Password: ")
    if len(password) < 8:
        print("Password must be at least 8 characters.")
        sys.exit(1)

    database.create_tables()
    database.create_or_update_user(username, security.hash_password(password))
    print(f"User '{username}' saved.")


if __name__ == "__main__":
    main()
