"""Streamlit frontend for BA-Agent."""

from __future__ import annotations

import streamlit as st  # type: ignore[import-not-found]

from .config import Settings
from .index import IndexBuilder
from .ingest import DocumentIngestor
from .query import QueryEngine


def render() -> None:
    st.set_page_config(page_title="BA-Agent", layout="wide")
    settings = Settings()
    st.title("BA-Agent – IEEE-konforme Literaturarbeit")

    with st.sidebar:
        st.header("Quellenverwaltung")
        uploaded_files = st.file_uploader(
            "Quellen hochladen", type=["pdf", "txt", "docx"], accept_multiple_files=True
        )
        if uploaded_files:
            dest_dir = settings.source_dir
            dest_dir.mkdir(parents=True, exist_ok=True)
            for uploaded in uploaded_files:
                target = dest_dir / uploaded.name
                target.write_bytes(uploaded.getvalue())
            st.success("Dateien gespeichert. Bitte Ingestion starten.")
        if st.button("Ingestion starten"):
            ingestor = DocumentIngestor(settings)
            count = len(ingestor.ingest())
            st.success(f"Ingestion abgeschlossen mit {count} Einträgen.")
        if st.button("Index erstellen"):
            builder = IndexBuilder(settings)
            chunks = builder.build()
            st.success(f"Index erstellt mit {len(chunks)} Chunks.")

    st.header("Fragen und Kapitel")
    question = st.text_input("Fragestellung", "Wie beeinflusst KI die Hochschullehre?")
    if st.button("Frage beantworten"):
        try:
            engine = QueryEngine(settings)
            result = engine.ask(question)
        except FileNotFoundError as error:
            st.error(str(error))
        else:
            st.subheader("Antwort")
            st.write(result["answer"])
            st.subheader("Literaturverzeichnis")
            for entry in result["bibliography"]:
                st.markdown(entry)

    st.header("Kapitel generieren")
    title = st.text_input("Kapitelüberschrift", "Einführung")
    topic = st.text_input("Kapitelthema", "KI in der Hochschullehre")
    if st.button("Kapitel generieren"):
        try:
            engine = QueryEngine(settings)
            result = engine.chapter(title, topic)
        except FileNotFoundError as error:
            st.error(str(error))
        else:
            st.markdown(result["text"])
            st.subheader("Literaturverzeichnis")
            for entry in result["bibliography"]:
                st.markdown(entry)


if __name__ == "__main__":  # pragma: no cover
    render()
