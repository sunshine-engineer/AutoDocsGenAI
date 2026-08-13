from utils.config_loader import load_config


def test_load_config():
    config = load_config()

    assert config.project.name == "Documentation Knowledge Pipeline"
    assert config.crawl.max_pages == 10
    assert config.chunking.max_characters == 4000
    assert config.chunking.overlap_characters < config.chunking.max_characters
    assert config.database.host == "postgres"
    assert config.database.port == 5432
    assert config.database.name == "autodocs"
    assert config.database.user == "autodocs"
    assert config.database.connect_timeout_seconds == 10
