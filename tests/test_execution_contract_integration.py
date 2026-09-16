from backend_api import AgentExecutionResponse


def test_agent_execution_response_contains_execution_contract_fields():
    response = AgentExecutionResponse(
        agent_id="csv-analyst",
        mode="auto",
        answer="ok",
        execution_id="exec_123",
        trace_id="trace_123",
        status="queued",
    )

    assert response.execution_id == "exec_123"
    assert response.trace_id == "trace_123"
    assert response.status == "queued"
