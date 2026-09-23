from pathlib import Path

from smart_pr_review_workflow.rag import load_knowledge_documents


def test_knowledge_documents_exist():
    docs = load_knowledge_documents()
    names = {doc.metadata["source"] for doc in docs}

    assert {"security-policy.md", "dependency-policy.md", "code-quality.md", "operational-policy.md"} <= names


def test_rag_files_exist():
    package = Path(__file__).parents[1] / "src" / "smart_pr_review_workflow"
    assert (package / "rag.py").exists()
