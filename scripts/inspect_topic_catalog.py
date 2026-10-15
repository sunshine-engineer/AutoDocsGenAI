from scripts.catalog_cli import run


def main() -> int:
    return run("inspect")


if __name__ == "__main__":
    raise SystemExit(main())
