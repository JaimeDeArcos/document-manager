"""Check the local services and models before launching the UI."""

from ollama import Client

from .config import Settings


def main() -> int:
    settings = Settings.from_env()
    print(f"PDFs:    {settings.pdf_dir}")
    print(f"Vectors: {settings.vector_dir}")
    print(f"Ollama:  {settings.ollama_host}")
    try:
        models = Client(host=settings.ollama_host).list().models
    except Exception as exc:
        print(f"Ollama is unavailable: {exc}")
        print("Start the Ollama app or run `ollama serve`, then retry.")
        return 1

    available = {model.model for model in models}
    missing = [
        name for name in (settings.embedding_model, settings.chat_model)
        if name not in available and f"{name}:latest" not in available
    ]
    if missing:
        print(f"Missing models: {', '.join(missing)}. Run `make models`.")
        return 1
    print("Ollama and both models are ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
