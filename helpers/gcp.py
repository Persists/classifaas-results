import os
import pandas as pd


def load_billed_gcp(csv_path: str) -> pd.DataFrame:
    billed_df = pd.read_csv(csv_path, dtype=str)

    # Extract billed duration (ms) from textPayload
    billed_df["billed_duration_ms"] = (
        billed_df["textPayload"]
        .astype(str)
        .str.extract(r"Function execution took\s+(\d+)\s+ms")[0]
        .astype(float)
    )

    # Clean and normalize fields
    billed_df["gcp_execution_id"] = billed_df["labels.execution_id"]

    # Keep only relevant and valid entries
    billed_df = billed_df.dropna(subset=["gcp_execution_id", "billed_duration_ms"])
    billed_df = billed_df[["gcp_execution_id", "billed_duration_ms"]]

    return billed_df


def load_all_billed_gcp(root_dir: str) -> pd.DataFrame:
    """
    Recursively find and load all GCP billed CSVs under `root_dir`.
    Returns a concatenated DataFrame.
    """
    all_records = []

    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".csv") and "billed" in file.lower():
                csv_path = os.path.join(root, file)
                df = load_billed_gcp(csv_path)
                if not df.empty:
                    all_records.append(df)

    combined_df = pd.concat(all_records, ignore_index=True)
    print(f"📥 Loaded {len(combined_df)} billed GCP records from {len(all_records)} files.")

    return combined_df


def inject_billed_gcp(df: pd.DataFrame, billed_df: pd.DataFrame) -> pd.DataFrame:
    # Only operate on GCP rows
    mask = df["provider"] == "gcp"

    # Build lookup table
# Detect duplicate execution IDs
    dupes = billed_df[billed_df["gcp_execution_id"].duplicated(keep=False)]

    if not dupes.empty:
        print("⚠️ Found duplicate gcp_execution_id entries in billed_df:")
        print(dupes.sort_values("gcp_execution_id").to_string(index=False))

    # Option 1: drop duplicates (keep the first)
    billed_df = billed_df.drop_duplicates(subset="gcp_execution_id", keep="first")

    # Now build the lookup table
    billed_indexed = billed_df.set_index("gcp_execution_id")

    # Fill all matching columns dynamically
    for col in billed_indexed.columns:
        if col == "gcp_execution_id":
            continue
        df.loc[mask, col] = df.loc[mask, "gcp_execution_id"].map(billed_indexed[col])

    # Check for unmatched entries (no billed_duration_ms)
    unmatched = df.loc[mask & df["billed_duration_ms"].isna()]
    if len(unmatched) > 0:
        print(f"⚠️ {len(unmatched)} GCP entries have no billed duration match.")
    else:
        print(f"✅ All GCP entries matched billed durations.")

    return df
