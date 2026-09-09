from __future__ import annotations

import json as json_module
from typing import Any, Dict, List, Optional

import pandas as pd


JSON_ANALYST_PROMPT = """You are a JSON data analyst. Flatten nested structures, analyze keys, compute statistics, and detect data quality issues. Provide recommendations for data normalization."""


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """Recursively flatten nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        elif isinstance(v, list):
            items.append((new_key, str(v)))
        else:
            items.append((new_key, v))
    return dict(items)


def analyze_json_data(json_text: str, prompt: Optional[str] = None) -> Dict[str, Any]:
    """Analyze JSON data - flatten, compute stats, detect issues."""
    try:
        data = json_module.loads(json_text)
        
        # Handle both list of objects and single object
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            records = [data]
        else:
            return {"error": "JSON must be an object or array of objects."}
        
        # Flatten records
        flattened = [flatten_dict(r) for r in records]
        df = pd.DataFrame(flattened)
        
        return {
            "record_count": len(records),
            "columns": df.columns.tolist(),
            "dtypes": df.dtypes.apply(lambda dt: str(dt)).to_dict(),
            "null_counts": df.isna().sum().to_dict(),
            "sample": df.head(3).to_dict(orient="records"),
            "recommendation": f"Flattened {len(records)} records into {len(df.columns)} columns. Check null_counts for data quality.",
        }
    except json_module.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}


def run_json_analyst(json_text: Optional[str], prompt: str) -> Dict[str, Any]:
    if json_text:
        return analyze_json_data(json_text, prompt)
    return {"error": "json-analyst requires JSON input."}
