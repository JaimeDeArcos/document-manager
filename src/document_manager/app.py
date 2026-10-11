"""Streamlit UI: run with `make run` from the repository root."""

import streamlit as st

from document_manager.config import Settings
from document_manager.models import Answer
from document_manager.service import DocumentManager


st.set_page_config(page_title="Ask your PDFs · Local", page_icon="📚", layout="wide")


@st.cache_resource
def manager() -> DocumentManager:
    return DocumentManager(Settings.from_env())


def show_sources(answer: Answer, message_index: int) -> None:
    if not answer.sources:
        return
    with st.expander(f"Sources ({len(answer.sources)})", expanded=True):
        for index, source in enumerate(answer.sources, start=1):
            st.markdown(f"**{index}. {source.filename} · {source.section} · page {source.page}**")
            st.caption(source.text[:700] + ("…" if len(source.text) > 700 else ""))
            path = manager().pdf_path(source.filename)
            if path.exists():
                st.download_button(
                    f"Download {source.filename}",
                    data=path.read_bytes(),
                    file_name=source.filename,
                    mime="application/pdf",
                    key=f"download-{message_index}-{source.id}",
                )


app = manager()
st.title("Ask your PDFs")
st.caption("A small RAG app that keeps documents, vectors, and model calls on your machine.")

with st.sidebar:
    st.header("Documents")
    uploads = st.file_uploader("Add text-selectable PDFs", type="pdf", accept_multiple_files=True)
    if st.button("Index selected PDFs", disabled=not uploads, use_container_width=True):
        for upload in uploads or []:
            try:
                with st.spinner(f"Indexing {upload.name}…"):
                    document, changed = app.index_pdf(upload.name, upload.getvalue())
                action = "Indexed" if changed else "Already indexed"
                st.success(f"{action}: {document.filename} ({document.chunks} chunks)")
            except Exception as exc:
                st.error(f"{upload.name}: {exc}")

    documents = app.documents()
    if documents:
        st.divider()
        for document in documents:
            left, right = st.columns([4, 1])
            left.write(f"📄 {document.filename} · {document.chunks} chunks")
            if right.button("✕", key=f"delete-{document.filename}", help=f"Remove {document.filename}"):
                app.delete_document(document.filename)
                st.rerun()
    else:
        st.info("Add a PDF to begin. Try `make demo-pdf` if you need one.")

    st.divider()
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.caption("Runs on localhost. Your PDFs and vectors stay in `data/`.")

messages = st.session_state.setdefault("messages", [])
for index, message in enumerate(messages):
    with st.chat_message(message["role"]):
        st.markdown(message["text"])
        if message["role"] == "assistant":
            show_sources(message["answer"], index)

if question := st.chat_input("Ask something about your documents…", disabled=not documents):
    messages.append({"role": "user", "text": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        try:
            with st.spinner("Searching documents and asking the local model…"):
                answer = app.ask(question)
            st.markdown(answer.text)
            show_sources(answer, len(messages))
            messages.append({"role": "assistant", "text": answer.text, "answer": answer})
        except Exception as exc:
            st.error(f"Could not answer locally: {exc}. Check `make doctor` and Ollama.")
