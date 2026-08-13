from utils.logger import setup_logger


def test_setup_logger_returns_application_logger():
    logger = setup_logger()

    assert logger.name == "documentation_pipeline"
