import pandas as pd
import os

def load_billed_azure(csv_path: str) -> pd.DataFrame:
    billed_df = pd.read_csv(csv_path)

    # Standardize column names
    billed_df = billed_df.rename(columns={
            "customDimensions_InvocationId": "azure_invocation_id",
            "id": "request_id",
            "duration": "billed_duration_ms"
        })

    # Clean and convert
    billed_df["azure_invocation_id"] = billed_df["azure_invocation_id"].astype(str).str.strip()
    billed_df["request_id"] = billed_df["request_id"].astype(str).str.strip()
    billed_df["billed_duration_ms"] = pd.to_numeric(billed_df["billed_duration_ms"], errors="coerce")

    return billed_df

def load_all_billed_azure(root_dir: str) -> pd.DataFrame:
    all_records = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".csv") and "billed" in file.lower():
                csv_path = os.path.join(root, file)
                try:
                    df = load_billed_azure(csv_path)
                    all_records.append(df)
                except Exception as e:
                    print(f"⚠️ Failed to read {csv_path}: {e}")

    combined_df = pd.concat(all_records, ignore_index=True)
    print(f"📥 Loaded {len(combined_df)} billed Azure records from {len(all_records)} files.")
    return combined_df



def inject_billed_azure(df: pd.DataFrame, billed_df: pd.DataFrame) -> pd.DataFrame:
    mask = df["provider"] == "azure"
    billed_indexed = billed_df.set_index("azure_invocation_id")

    # Inject all billed fields into Azure rows
    for col in billed_indexed.columns:
        if col == "azure_invocation_id":
            continue
        df.loc[mask, col] = df.loc[mask, "azure_invocation_id"].map(billed_indexed[col])

    unmatched = df.loc[mask & df["billed_duration_ms"].isna()]
    if len(unmatched) > 0:
        print(f"⚠️ {len(unmatched)} Azure entries have no billed duration match.")
    else:
        print(f"✅ All Azure entries matched billed durations.")

    return df
