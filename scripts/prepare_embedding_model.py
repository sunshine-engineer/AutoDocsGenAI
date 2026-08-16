from fastembed import TextEmbedding

from utils.config_loader import load_config


def main() -> None:
    config = load_config().embedding
    model = TextEmbedding(
        model_name=config.model,
        cache_dir=config.cache_directory,
        threads=2,
    )

    embeddings = iter(
        model.embed(
            ["model readiness check"],
            batch_size=1,
        )
    )

    try:
        vector = next(embeddings)
    except StopIteration as exc:
        raise RuntimeError("embedding model returned no vectors") from exc

    if len(vector) != config.dimension:
        raise RuntimeError(
            f"model returned {len(vector)} dimensions; expected {config.dimension}"
        )

    print(f"Embedding model ready: {config.model} ({len(vector)} dimensions)")


if __name__ == "__main__":
    main()
