from __future__ import annotations

from typing import Any, Dict

from base_agent import BaseAgent


class ReportAgent(BaseAgent):
    SYSTEM_PROMPT = "Report specialist: generate Word and PDF reports from structured data."

    def perform_task(self, payload: Dict[str, Any]) -> Any:
        report_name = payload.get("report_name", "report.docx")
        sections = payload.get("sections", [])
        return {"report": report_name, "sections": len(sections), "status": "generated"}
