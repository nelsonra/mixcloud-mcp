"""Generates a secure random API key for HTTP transport auth."""
import secrets


def run() -> None:
    print(secrets.token_hex(32))


if __name__ == "__main__":
    run()
