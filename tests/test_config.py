from utils.config_loader import load_config


def test_load_config():
    config = load_config()

    assert config.project.name == "Documentation Knowledge Pipeline"
    assert config.crawl.max_pages == 10
    assert config.chunking.max_characters == 4000
    assert config.chunking.overlap_characters < config.chunking.max_characters
