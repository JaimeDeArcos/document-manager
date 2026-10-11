# Ask your PDFs locally

A small, runnable companion to [**“Part 1/3: Chat with Your PDFs Locally”**](https://blog.jaimedearcos.com/chat-with-pdfs-locally-part-1/). Upload PDFs, ask questions in a browser, and inspect the document, section, page, and excerpt behind each answer. The app uses local models and stores its data on your machine.

This is an educational single-user application. It handles PDFs with selectable text, up to 25 MB each. Scanned image-only PDFs need OCR and are reserved for Part 3 of the series.

## What runs where

| Component | Purpose | Where it runs |
|---|---|---|
| [Streamlit](https://docs.streamlit.io/develop/tutorials/chat-and-llm-apps/build-conversational-apps) | Browser chat and PDF uploads | `127.0.0.1:8501` |
| [PyMuPDF4LLM](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) | Extract page-aware Markdown from PDFs | In the Python process |
| [Chroma](https://docs.trychroma.com/reference/python) | Persist vectors, text, and source metadata | Embedded, in `data/chroma/` |
| [Ollama](https://ollama.com/download) + `embeddinggemma` | Embed chunks and questions | Local Ollama service |
| Ollama + `gemma3:4b` | Write an answer from retrieved excerpts | Local Ollama service |

No Chroma server, cloud API key, or LangChain installation is needed. The first installation and model pulls need internet access; afterwards the default app talks to Ollama at `http://127.0.0.1:11434`. `gemma3:4b` is about 3.3 GB and `embeddinggemma` about 622 MB to download, so allow disk space and expect slower responses on modest CPUs. Model sizes and requirements are listed in the [Gemma 3](https://ollama.com/library/gemma3) and [EmbeddingGemma](https://ollama.com/library/embeddinggemma) model pages.

## Prerequisites

Install **Python 3.11–3.14**, [uv](https://docs.astral.sh/uv/getting-started/installation/), [Ollama](https://ollama.com/download), and `make`. Start the Ollama app, or run `ollama serve` in another terminal. Verify that `python3.11`, `uv`, `ollama`, and `make` are on your `PATH`.

On macOS or Linux:

```bash
git clone https://github.com/JaimeDeArcos/document-manager.git
cd document-manager
make setup       # creates .venv and installs locked Python dependencies
make models      # downloads embeddinggemma and gemma3:4b into Ollama
make doctor      # checks the local Ollama service and both models
make run         # opens the app at http://127.0.0.1:8501
```

If your Python executable has another name, use `make setup PYTHON=python3.12`. To choose a different local port, use `make run PORT=8502`. The Makefile binds Streamlit to `127.0.0.1` so the demo is available only on your own computer by default.

Want a PDF before using your own? Run `make demo-pdf`, then upload `data/demo-handbook.pdf` in the sidebar. Ask **“How long are project notes kept?”**. The answer should mention 90 days and cite *Retention*, page 1. Ask **“What is the holiday policy?”** to probe an unsupported question. The intended response says the documents do not support an answer; always inspect the cited excerpt, because a local model can still make an unsupported claim.

## How an answer is built

```text
PDF upload → page-aware text extraction → chunks with section and page
           → embeddinggemma vectors → local Chroma index

Question → embeddinggemma vector → closest chunks → gemma3:4b
         → answer + validated source IDs → excerpts in the UI
```

Each indexed chunk keeps its filename, one-based page number, and a section label. The section comes from the PDF table of contents or a heading found during Markdown extraction. If neither exists, the label is simply `Page N`; the app does not invent a section. The model receives numbered excerpts and must choose which ones support its answer. The application rejects citation numbers that were not retrieved and shows the underlying excerpt so you can check the claim. A local model can still make mistakes, so read the source before relying on an answer.

Re-uploading identical bytes is a no-op. Uploading a changed PDF under the same filename replaces the old vectors. You can remove an indexed document with the **✕** button in the sidebar. The chat history stays in the browser session and clears with **Clear chat**.

## Files, configuration, and checks

Uploaded PDFs are copied to `data/pdfs/`; Chroma writes vectors and metadata to `data/chroma/`. The demo PDF is written to `data/demo-handbook.pdf`. The whole `data/` directory is ignored by Git. To start over, stop the app and remove `data/` yourself; doing so deletes uploaded PDFs and the index.

You can override defaults through environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `DOCUMENT_MANAGER_DATA_DIR` | `./data` | Local PDFs and Chroma files |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama API address |
| `DOCUMENT_MANAGER_EMBED_MODEL` | `embeddinggemma` | Embedding model; re-index after changing it |
| `DOCUMENT_MANAGER_CHAT_MODEL` | `gemma3:4b` | Answer model |

Run `make test` for the extraction, replacement, and citation tests. `make doctor` checks the live Ollama service; the automated tests use fakes and do not download models. The example was built for a single local user, so it has no accounts or network-facing deployment configuration.

## Troubleshooting

- **Ollama unavailable:** Start the Ollama app or `ollama serve`, then run `make doctor`. Check `OLLAMA_HOST` if you changed it.
- **Model not found:** Run `make models`. Pulls are the only large setup downloads.
- **No selectable text:** Open the PDF and try to select a sentence. Image-only scans require OCR, which this first part deliberately does not perform.
- **Wrong or vague answer:** Inspect the cited excerpts. Try a more specific question or a PDF with clearer text. A nearest-neighbor result is a candidate, not proof that the answer exists.
- **Different embedding model:** Clear and rebuild the index before querying it. Mixing embedding spaces makes retrieval meaningless.

The complete flow is small enough to follow in [`pdf.py`](src/document_manager/pdf.py), [`store.py`](src/document_manager/store.py), [`llm.py`](src/document_manager/llm.py), and [`service.py`](src/document_manager/service.py).
