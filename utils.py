import pandas as pd


def load_file(filepath: str) -> pd.DataFrame:
    """Load an Excel or CSV file into a DataFrame."""
    if filepath.endswith(".csv"):
        return pd.read_csv(filepath)
    return pd.read_excel(filepath)


def get_schema(df: pd.DataFrame, name: str = "dataframe") -> str:
    """
    Return a string description of a DataFrame's schema and sample rows.
    This is what we send to the LLM so it understands the data structure.
    """
    schema = f"DataFrame '{name}':\n"
    schema += f"  Shape: {df.shape[0]} rows x {df.shape[1]} columns\n"
    schema += f"  Columns: {list(df.columns)}\n"
    schema += f"  Dtypes:\n"
    for col, dtype in df.dtypes.items():
        schema += f"    - {col}: {dtype}\n"
    schema += f"\n  Sample (first 3 rows):\n{df.head(3).to_string(index=False)}\n"
    return schema


def detect_key_column(df_a: pd.DataFrame, df_b: pd.DataFrame) -> str | None:
    """
    Try to auto-detect the best column to use as the key for comparison.
    Looks for columns with 'id', 'code', 'key', or 'number' in the name
    that exist in both DataFrames.
    """
    common_cols = set(df_a.columns) & set(df_b.columns)
    priority_keywords = ["id", "code", "key", "number", "no", "ref"]
    for col in common_cols:
        if any(kw in col.lower() for kw in priority_keywords):
            return col
    # Fallback: return first common column
    return list(common_cols)[0] if common_cols else None