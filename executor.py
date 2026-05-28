import pandas as pd
import traceback


def run_generated_code(code: str, df_a: pd.DataFrame, df_b: pd.DataFrame) -> tuple[bool, any, str]:
    """
    Safely execute LLM-generated pandas code.

    The LLM is instructed to always store its output in a variable called `result`.
    We provide df_a, df_b, and pd as the available context.

    Returns:
        (success: bool, result: any, error_message: str)
    """
    local_vars = {
        "df_a": df_a.copy(),
        "df_b": df_b.copy(),
        "pd": pd,
    }

    try:
        exec(code, {"__builtins__": {}}, local_vars)
        result = local_vars.get("result", None)

        if result is None:
            return False, None, "LLM code ran but did not set a `result` variable."

        return True, result, ""

    except Exception:
        error = traceback.format_exc()
        return False, None, error