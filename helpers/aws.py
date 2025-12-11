import os
import pandas as pd


def load_billed_aws(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype=str)

    # Normalize columns
    df = df.rename(columns={
        "@requestId": "aws_request_id",
        "@duration": "duration_ms",
        "@billedDuration": "billed_duration_ms",
        "@memorySize": "memory_bytes",
        "@maxMemoryUsed": "max_memory_used_bytes",
        "@initDuration": "init_duration_ms"

    })

    # Convert numeric fields
    df["billed_duration_ms"] = pd.to_numeric(df["billed_duration_ms"], errors="coerce")
    df["duration_ms"] = pd.to_numeric(df["duration_ms"], errors="coerce")
    df["memory_mb"] = (pd.to_numeric(df["memory_bytes"], errors="coerce") / 1_000_000).astype("float64")
    df["max_memory_used_mb"] = (pd.to_numeric(df["max_memory_used_bytes"], errors="coerce") / 1_000_000).astype("float64")
    df["init_duration_ms"] = pd.to_numeric(df["init_duration_ms"], errors="coerce")

    # Keep relevant subset
    df = df[["aws_request_id", "duration_ms", "billed_duration_ms", "memory_mb", "max_memory_used_mb", "init_duration_ms"]].dropna(subset=["aws_request_id"])

    return df


def load_all_billed_aws(root_dir: str) -> pd.DataFrame:
    all_records = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".csv") and "billed" in file.lower():
                csv_path = os.path.join(root, file)
                try:
                    df = load_billed_aws(csv_path)
                    all_records.append(df)
                except Exception as e:
                    print(f"❌ Failed to read {csv_path}: {e}")

    combined_df = pd.concat(all_records, ignore_index=True)
    print(f"📥 Loaded {len(combined_df)} billed AWS records from {len(all_records)} files.")
    return combined_df


def inject_billed_aws(df: pd.DataFrame, billed_df: pd.DataFrame) -> pd.DataFrame:
    mask = df["provider"] == "aws"
    billed_indexed = billed_df.set_index("aws_request_id")

    # Inject all billed fields into AWS rows
    for col in billed_indexed.columns:
        if col == "aws_request_id":
            continue
        df.loc[mask, col] = df.loc[mask, "aws_request_id"].map(billed_indexed[col])


    # Check for unmatched entries (no billed_duration_ms)
    unmatched = df.loc[mask & df["billed_duration_ms"].isna()]
    if len(unmatched) > 0:
        print(f"⚠️ {len(unmatched)} AWS entries have no billed duration match.")
    else:
        print(f"✅ All AWS entries matched billed durations.")

    return df
