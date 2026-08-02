from utils.config_loader import load_config


def main():

    config = load_config()

    print(config)

    print()

    print(config.project.name)

    print(config.llm.model)

    print(config.output.directory)


if __name__ == "__main__":
    main()