"""Placeholder connect command."""


def handle_connect(args: list[str]) -> None:
    """Handle connect <ip> command."""
    if len(args) != 1:
        print("Usage: connect <ip>")
        return

    ip = args[0]
    print(f"[placeholder] connect to {ip}")
    print("SSH is not implemented yet.")
