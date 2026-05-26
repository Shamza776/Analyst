import pandas as pd


def find_missing_in_b(df_a: pd.DataFrame, df_b: pd.DataFrame, key: str) -> pd.DataFrame:
    """Rows that exist in File A but are NOT in File B."""
    merged = df_a.merge(df_b[[key]], on=key, how="left", indicator=True)
    return df_a[merged["_merge"] == "left_only"].reset_index(drop=True)


def find_missing_in_a(df_a: pd.DataFrame, df_b: pd.DataFrame, key: str) -> pd.DataFrame:
    """Rows that exist in File B but are NOT in File A."""
    merged = df_b.merge(df_a[[key]], on=key, how="left", indicator=True)
    return df_b[merged["_merge"] == "left_only"].reset_index(drop=True)


def find_common(df_a: pd.DataFrame, df_b: pd.DataFrame, key: str) -> pd.DataFrame:
    """Rows whose key value exists in BOTH files."""
    common_keys = set(df_a[key]) & set(df_b[key])
    return df_a[df_a[key].isin(common_keys)].reset_index(drop=True)


def find_value_mismatches(df_a: pd.DataFrame, df_b: pd.DataFrame, key: str) -> pd.DataFrame:
    """
    For rows present in both files, compare all shared columns and flag
    any rows where values differ. Returns a DataFrame showing the differences.
    """
    shared_cols = [c for c in df_a.columns if c in df_b.columns and c != key]
    merged = df_a.merge(df_b, on=key, suffixes=("_A", "_B"), how="inner")

    mismatch_rows = []
    for _, row in merged.iterrows():
        diffs = {}
        for col in shared_cols:
            val_a = row.get(f"{col}_A")
            val_b = row.get(f"{col}_B")
            if pd.notna(val_a) and pd.notna(val_b) and val_a != val_b:
                diffs[col] = {"file_A": val_a, "file_B": val_b}
        if diffs:
            mismatch_rows.append({
                key: row[key],
                "mismatched_columns": list(diffs.keys()),
                "details": str(diffs)
            })

    return pd.DataFrame(mismatch_rows) if mismatch_rows else pd.DataFrame(
        columns=[key, "mismatched_columns", "details"]
    )


def get_summary(df_a: pd.DataFrame, df_b: pd.DataFrame, key: str) -> dict:
    """High-level summary of the comparison — always the first thing we compute."""
    missing_in_b = find_missing_in_b(df_a, df_b, key)
    missing_in_a = find_missing_in_a(df_a, df_b, key)
    common = find_common(df_a, df_b, key)
    mismatches = find_value_mismatches(df_a, df_b, key)

    return {
        "total_in_A": len(df_a),
        "total_in_B": len(df_b),
        "common_records": len(common),
        "missing_in_B": len(missing_in_b),
        "missing_in_A": len(missing_in_a),
        "value_mismatches": len(mismatches),
        "match_rate_pct": round(len(common) / max(len(df_a), 1) * 100, 1),
    }