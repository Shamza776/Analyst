import pandas as pd
import traceback


# Safe builtins — allows set, len, abs, round, etc. but blocks open, exec, eval, import
SAFE_BUILTINS = {
    name: getattr(builtins, name)
    for name in [
        "abs", "all", "any", "bool", "dict", "dir", "divmod", "enumerate",
        "filter", "float", "format", "frozenset", "getattr", "hasattr",
        "hash", "int", "isinstance", "issubclass", "iter", "len", "list",
        "map", "max", "min", "next", "print", "range", "repr", "reversed",
        "round", "set", "slice", "sorted", "str", "sum", "tuple", "type",
        "zip", "True", "False", "None",
    ]
}

def run_generated_code(code: str, df_a: pd.DataFrame, df_b: pd.DataFrame) -> tuple[bool, any, str]:
    """
    Safely execute LLM-generated pandas code.

    The LLM is instructed to always store its output in a variable called `result`.
    We provide df_a, df_b, and pd as the available context.

    Returns:
        (success: bool, result: any, error_message: str)
    """

     # Strip accidental markdown fences the LLM may have included
    code = code.replace("```python", "").replace("```", "").strip()

    local_vars = {
        "df_a": df_a.copy(),
        "df_b": df_b.copy(),
        "pd": pd,
    }

    try:
        exec(code, {"__builtins__": {SAFE_BUILTINS}}, local_vars)
        result = local_vars.get("result", None)

        if result is None:
             # Last resort: return the last assigned variable that looks like data
            # Note: pandas operations return numpy types, not plain int/float
            import numpy as np
            candidates = {
                k: v for k, v in local_vars.items()
                if k not in ("df_a", "df_b", "pd")
                and not k.startswith("_")
                and isinstance(v, (pd.DataFrame, pd.Series, str, dict, list,
                                   int, float, np.integer, np.floating))
            }
            if candidates:
                result = list(candidates.values())[-1]
                return True, result, ""
            return False, None, "LLM code ran but did not set a `result` variable."

        return True, result, ""

    except Exception:
        error = traceback.format_exc()
        return False, None, error