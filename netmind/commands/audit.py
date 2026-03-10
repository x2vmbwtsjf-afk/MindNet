"""Mock audit command for local CLI behavior testing."""


def handle_audit(args: list[str]) -> None:
    """Handle audit command."""
    if args:
        print("Usage: audit")
        return

    print("Running local audit (mock)...")
    print("- Interface status: OK")
    print("- Route table: OK")
    print("- CDP neighbors: OK")
    print("Audit complete.")
