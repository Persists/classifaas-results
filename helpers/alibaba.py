import os
import pandas as pd


def load_billed_alibaba(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype=str, on_bad_lines="skip", engine="python")
    
    df = df.rename(columns={
        "requestId": "alibaba_request_id",
        "durationMs": "billed_duration_ms",
        "memoryMB": "memory_mb",
        "memoryUsageMB": "memory_used_mb",
        "coldStartLatencyMs": "cold_start_latency_ms",
        "runtimeInitializationMs": "runtime_init_ms",
        "invokeFunctionLatencyMs": "invoke_latency_ms",
        "isColdStart": "is_cold_start"
    })

    numeric_cols = [
        "billed_duration_ms",
        "memory_mb",
        "memory_used_mb",
        "cold_start_latency_ms",
        "runtime_init_ms",
        "invoke_latency_ms"
    ]

    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["is_cold_start"] = df["is_cold_start"].astype(str).str.lower().eq("true")

    df = df[
        [
            "alibaba_request_id",
            "billed_duration_ms",
            "memory_mb",
            "memory_used_mb",
            "cold_start_latency_ms",
            "runtime_init_ms",
            "invoke_latency_ms",
            "is_cold_start",
        ]
    ].dropna(subset=["alibaba_request_id"])

    return df


def load_all_billed_alibaba(root_dir: str) -> pd.DataFrame:
    all_records = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".csv") and "billed" in file.lower():
                csv_path = os.path.join(root, file)
                try:
                    df = load_billed_alibaba(csv_path)
                    all_records.append(df)
                except Exception as e:
                    print(f"❌ Failed to read {csv_path}: {e}")

    combined_df = pd.concat(all_records, ignore_index=True)
    print(f"📥 Loaded {len(combined_df)} billed Alibaba records from {len(all_records)} files.")
    return combined_df


def inject_billed_alibaba(df: pd.DataFrame, billed_df: pd.DataFrame) -> pd.DataFrame:
    mask = df["provider"] == "alibaba"
    billed_indexed = billed_df.set_index("alibaba_request_id")

    # Inject all billed fields into Alibaba rows
    for col in billed_indexed.columns:
        if col == "alibaba_request_id":
            continue
        df.loc[mask, col] = df.loc[mask, "alibaba_request_id"].map(billed_indexed[col])

    unmatched = df.loc[mask & df["billed_duration_ms"].isna()]
    if len(unmatched) > 0:
        print(f"⚠️ {len(unmatched)} Alibaba entries have no billed duration match.")
    else:
        print(f"✅ All Alibaba entries matched billed durations.")

    return df
