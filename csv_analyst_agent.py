from __future__ import annotations

import base64
import os
from io import StringIO
from typing import Any, Dict

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_experimental.agents import create_pandas_dataframe_agent

load_dotenv()

DEFAULT_MODEL = os.environ.get("DEEPSEEK_MODEL", os.environ.get("LLM_MODEL", "deepseek-chat"))
DEFAULT_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEFAULT_API_BASE = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")

CSV_AGENT_PROMPT = """You are an expert data analyst. You have access to a pandas dataframe called df.

INSTRUCTIONS FOR ALL ANALYSIS:
1. Always explore data first (shape, columns, dtypes)
2. Provide numerical insights and statistics
3. VISUALIZATION RULE: When asked about plots, charts, histograms, distributions, or visual analysis:
   - Always create matplotlib visualizations
   - Execute this exact code pattern:
     import matplotlib.pyplot as plt
     import matplotlib
     matplotlib.use('Agg')
     plt.figure(figsize=(10, 6))
     # [your plotting code]
     plt.tight_layout()
     plt.savefig('chart.png', dpi=100, bbox_inches='tight')
     plt.close()
   - Save MUST use filename: 'chart.png' (not chart_temp.png or other names)
   - Always close with plt.close()
   - Never use plt.show() - it will not work

4. IMPORTANT: If the user asks for visualization, MUST create chart.png file
5. Return clear text summary of findings
6. If any code fails, show the error and fix it

CRITICAL RULES:
- EVERY chart request must result in saving 'chart.png'
- Chart must be saved with exactly this filename
- Always end chart code with plt.close()
- The file 'chart.png' in current directory is how charts are displayed
"""


def _build_llm() -> ChatOpenAI:
    kwargs: Dict[str, Any] = {
        "model": DEFAULT_MODEL,
        "temperature": 0,
    }
    if DEFAULT_API_KEY:
        kwargs["api_key"] = DEFAULT_API_KEY
    if DEFAULT_API_BASE:
        kwargs["base_url"] = DEFAULT_API_BASE
    return ChatOpenAI(**kwargs)


def _parse_csv(csv_text: str) -> pd.DataFrame:
    return pd.read_csv(StringIO(csv_text))


def create_csv_analyst(df: pd.DataFrame):
    llm = _build_llm()
    return create_pandas_dataframe_agent(
        llm=llm,
        df=df,
        verbose=False,
        agent_type="tool-calling",
        allow_dangerous_code=True,
        number_of_head_rows=5,
        prefix=CSV_AGENT_PROMPT,
    )


def run_csv_analyst(csv_text: str, prompt: str) -> Dict[str, Any]:
    if not csv_text:
        raise ValueError("CSV text is required for csv-analyst.")

    df = _parse_csv(csv_text)
    agent = create_csv_analyst(df)
    if hasattr(agent, "invoke"):
        answer = agent.invoke(prompt)
    else:
        answer = agent.run(prompt)

    chart_path = os.path.abspath("chart.png")
    chart_created = os.path.exists(chart_path)
    chart_png_base64 = None
    if chart_created:
        with open(chart_path, "rb") as fh:
            chart_png_base64 = base64.b64encode(fh.read()).decode("utf-8")

    return {
        "answer": answer,
        "chart_created": chart_created,
        "chart_png_base64": chart_png_base64,
    }
