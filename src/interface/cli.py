"""主命令行入口"""


def cli_main() -> None:
    """Main entrypoint for the deepagents CLI.

    This function is registered as a console script entrypoint in pyproject.toml.
    """
    print("I'm alive!")


if __name__ == "__main__":
    cli_main()
