from __future__ import annotations

import json as json_module
from typing import Any, Dict, List, Optional

import pandas as pd


SALES_PIPELINE_PROMPT = """You are a sales analyst. Analyze pipeline data to compute win rates, forecast revenue, identify bottlenecks, and recommend stage optimization. Provide clear metrics on conversion and deal velocity."""


def analyze_sales_pipeline(csv_content: str, prompt: Optional[str] = None) -> Dict[str, Any]:
    """Analyze sales pipeline CSV with columns: Deal, Stage, Amount, Rep, Close_Date."""
    try:
        df = pd.read_csv(pd.io.common.StringIO(csv_content))
        
        results: Dict[str, Any] = {
            "rows": len(df),
            "columns": df.columns.tolist(),
        }
        
        # Stage analysis
        if 'Stage' in df.columns:
            stage_counts = df['Stage'].value_counts().to_dict()
            results["stage_distribution"] = stage_counts
        
        # Amount analysis
        if 'Amount' in df.columns:
            amounts = pd.to_numeric(df['Amount'], errors='coerce')
            results["financial_summary"] = {
                "total_pipeline": float(amounts.sum()),
                "average_deal_size": float(amounts.mean()),
                "deal_count": len(df),
                "largest_deal": float(amounts.max()),
            }
        
        # Rep analysis
        if 'Rep' in df.columns and 'Amount' in df.columns:
            rep_summary = {}
            for rep in df['Rep'].unique():
                rep_df = df[df['Rep'] == rep]
                amounts = pd.to_numeric(rep_df['Amount'], errors='coerce')
                rep_summary[str(rep)] = {
                    "deals": len(rep_df),
                    "total_amount": float(amounts.sum()),
                }
            results["rep_performance"] = rep_summary
        
        return results
    except Exception as e:
        return {"error": str(e)}


def run_sales_pipeline_analyst(csv_content: Optional[str], table_json: Optional[List[Dict[str, Any]]], prompt: str) -> Dict[str, Any]:
    if csv_content:
        return analyze_sales_pipeline(csv_content, prompt)
    if table_json is not None:
        df = pd.DataFrame(table_json)
        return {"rows": len(df), "columns": df.columns.tolist()}
    return {"error": "sales-pipeline requires CSV or table JSON input."}
