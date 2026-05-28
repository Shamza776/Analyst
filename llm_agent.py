import os
import google.generativeai as genai
from utils import get_schema
import pandas as pd


# ── Configure Gemini ──────────────────────────────────────────────────────────
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
for model in genai.list_models():
    if "generateContent" in model.supported_generation_methods:
        print(model.name)
model = genai.GenerativeModel("gemini-2.5-flash")


# ── Prompt Templates ──────────────────────────────────────────────────────────

def _code_generation_prompt(question: str, schema_a: str, schema_b: str, key: str) -> str:
    return f"""
You are a Python/pandas expert. The user has uploaded two Excel files loaded as DataFrames.

{schema_a}

{schema_b}

The key column used for comparison is: `{key}`

The user's question is:
\"{question}\"

Write Python/pandas code to answer this question.
RULES:
- You have access to: df_a, df_b, and pd (pandas)
- Always store your final output in a variable called `result`
- result must be a DataFrame, a dict, a number, or a string
- Do NOT import anything — pandas is already available as `pd`
- Do NOT use print() — just store output in `result`
- Write clean, concise code only. No explanation, no markdown, no code fences.
"""


def _synthesis_prompt(question: str, result_str: str) -> str:
    return f"""
You are a helpful data analyst assistant. The user asked:
\"{question}\"

The pandas computation returned this result:
{result_str}

Write a clear, concise response to the user in plain English.
- Summarize the key findings
- If it's a DataFrame, describe what the rows represent
- Keep it under 5 sentences unless the data is complex
- Do not repeat the raw data back verbatim
"""


def _summary_synthesis_prompt(summary: dict, key: str) -> str:
    return f"""
You are a data analyst. Two Excel files were compared using the key column `{key}`.
Here are the comparison results:

{summary}

Write a brief, friendly summary for a business user explaining:
- How many records match
- What's missing in each file
- Whether there are any value mismatches
- One sentence on what this might mean practically

Keep it under 6 sentences. Be direct and clear.
"""


# ── Public Functions ──────────────────────────────────────────────────────────

def generate_pandas_code(question: str, df_a: pd.DataFrame, df_b: pd.DataFrame, key: str) -> str:
    """Ask Gemini to write pandas code that answers the user's question."""
    schema_a = get_schema(df_a, "df_a (File A)")
    schema_b = get_schema(df_b, "df_b (File B)")
    prompt = _code_generation_prompt(question, schema_a, schema_b, key)
    response = model.generate_content(prompt)
    # Strip any accidental markdown code fences
    code = response.text.strip()
    code = code.replace("```python", "").replace("```", "").strip()
    return code


def synthesize_result(question: str, result) -> str:
    """Ask Gemini to explain a pandas result in plain English."""
    if isinstance(result, pd.DataFrame):
        result_str = result.to_string(index=False) if len(result) <= 20 else (
            result.head(10).to_string(index=False) + f"\n... ({len(result)} rows total)"
        )
    else:
        result_str = str(result)

    prompt = _synthesis_prompt(question, result_str)
    response = model.generate_content(prompt)
    return response.text.strip()


def synthesize_summary(summary: dict, key: str) -> str:
    """Ask Gemini to narrate the high-level comparison summary."""
    prompt = _summary_synthesis_prompt(summary, key)
    response = model.generate_content(prompt)
    return response.text.strip()