from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from novel_agent.workflows import build_chapter_workflow


def test_chapter_workflow_runs_without_nervus() -> None:
    index = {
        "chapters": [
            {
                "chapter_id": "ch001",
                "title": "Test",
                "summary": "Summary",
                "time_markers": [],
                "references": [],
            }
        ],
        "characters": [],
        "references": [],
    }
    dummy_model = RunnableLambda(lambda _: AIMessage(content="dummy"))
    workflow = build_chapter_workflow(dummy_model, continuity_index=index)
    result = workflow.invoke({"prompt": "Hello"})
    assert result["draft"] == "dummy"
    assert "issues" in result
