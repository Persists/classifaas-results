import os
import json
import pandas as pd
from datetime import datetime

from helpers.cpus import clean_cpu_string



def parse_log_file(benchmark_file: str) -> list[dict]:
    """
    Parse a benchmark log file and extract invocation records.
    Each log file starts with a metadata line followed by multiple JSON lines
    representing individual invocation records.
    """

    records = []
    with open(benchmark_file, 'r') as f:
        lines = f.readlines()
        if not lines:
            return []

        # Parse metadata (first line)
        try:
            meta = json.loads(lines[0])
        except json.JSONDecodeError:
            print(f"Invalid metadata line in {benchmark_file}")
            return []

        # Extract common meta info
        timestamp = datetime.fromisoformat(meta["timestamp"].replace("Z", "+00:00"))
        provider = meta.get("provider", "unknown").lower()
        region = meta.get("region", "unknown")
        memory = int(meta.get('memorySize', 'unknown'))
        function = meta.get("function", "unknown")
        parallel = int(meta.get("parallel-requests", 0))
        iterations = int(meta.get("iterationsPerBenchmark", 0))
        retries = int(meta.get("retries", 0))

        # Parse each invocation record
        for line in lines[1:]:
            try:
                data = json.loads(line)
                body = data["body"]
                benchmark = body.get("benchmark", {})
                cpu_field = body.get("cpuType", "unknown")
                cpu_frequency_mhz = body.get("cpuFrequencyMHz", None)

                if provider == "gcp":
                    model = body.get("cpuModel", "unknown")
                    GCP_CPU_MAPPING = {
                        "1": "Model 1 (AMD)",
                        "17": "Model 17 (AMD)",
                        "85": "Model 85 (Intel)",
                        "106": "Model 106 (Intel)",
                        "143": "Model 143 (Intel)",
                        "173": "Model 173 (Intel)",
                    }
                    cpu_field = GCP_CPU_MAPPING.get(
                        str(model), 
                        f"Model {model} (Unknown)"
                    )  

                if "AMD" in cpu_field and provider == "aws":
                    if cpu_frequency_mhz and cpu_frequency_mhz >= 2640 and cpu_frequency_mhz <= 2660:
                        cpu_field = "AMD EPYC 2.65GHz"
                    elif cpu_frequency_mhz and cpu_frequency_mhz >= 2240 and cpu_frequency_mhz <= 2260:
                        cpu_field = "AMD EPYC 2.25GHz"
                    else :
                        print(f"Unknown AMD CPU frequency {cpu_frequency_mhz} MHz on AWS, defaulting to generic name.")
                        cpu_field = "AMD EPYC unknown"

                record = {
                    "timestamp": timestamp,
                    "provider": provider,
                    "region": region,
                    "function": function,
                    "memory_size_mb": memory,
                    "parallel_requests": parallel,
                    "iterations_per_benchmark": iterations,
                    "retries": retries,

                    # CPU/system info
                    "cpu_type": cpu_field,
                    "cpu_model_number": body.get("cpuModel", "unknown"),

                    # Performance metrics
                    "runtime_ms": body.get("runtime", None),
                    "user_runtime_ms": body.get("userRuntime", None),
                    "framework_runtime_ms": body.get("frameworkRuntime", None),

                    # Container info
                    "container_id": body.get("containerID", "unknown"),
                    "new_container": body.get("newcontainer", None),
                    "invocation_count": body.get("invocationCount", None),
                    "instance_id": body.get("instanceId", "unknown"),
                    "uuid": body.get("uuid", "unknown"),

                    # Benchmark-specific
                    "benchmark_type": benchmark.get("type", "unknown"),
                    "flags": body.get("cpuFlags", []),
                    "cpu_frequency": cpu_frequency_mhz,
                }

                header = data.get("header", {})
                if provider == "azure":
                    record["azure_invocation_id"] = header.get("azure-invocation-id", "unknown")
                elif provider == "gcp":
                    record["gcp_execution_id"] = header.get("function-execution-id", "unknown")
                elif provider == "aws":
                    record["aws_request_id"] = header.get("aws-request-id", "unknown")
                elif provider == "alibaba":
                    record["alibaba_request_id"] = header.get("ali-request-id", "unknown")
                else:
                    print(f"Unknown provider '{provider}' in {benchmark_file}")



                # Depending on benchmark type, include additional fields
                if benchmark.get("type") == "gemm":
                    record["matrix_size"] = benchmark.get("matrixSize")
                    record["multiplication_time_ms"] = benchmark.get("multiplicationTimeMs")

                elif benchmark.get("type") == "aesCtr":
                    record["key_size"] = benchmark.get("keySize")
                    record["encrypt_size_mb"] = benchmark.get("encryptSizeMB")
                    record["encrypt_time_ms"] = benchmark.get("encryptTimeMs")

                elif benchmark.get("type") == "gzip":
                    record["compress_size_mb"] = benchmark.get("compressSizeMB")
                    record["compress_time_ms"] = benchmark.get("compressTimeMS")

                elif benchmark.get("type") == "sha256":
                    record["hash_size_mb"] = benchmark.get("hashSizeMB")
                    record["hash_time_ms"] = benchmark.get("hashTimeMs")
                
                elif benchmark.get("type") == "json":
                    record["json_time_ms"] = benchmark.get("jsonTimeMs")

                records.append(record)

            except json.JSONDecodeError:
                # skip invalid JSON lines (like stray '{')
                continue
            except Exception as e:
                print(f"Error parsing line in {benchmark_file}: {e}")
                continue

    return records


def metric_for_benchmark(benchmark_type: str) -> str:
    """
    Given a benchmark type, return the corresponding performance metric field name.
    """
    mapping = {
        "gemm": "multiplication_time_ms",
        "aesCtr": "encrypt_time_ms",
        "gzip": "compress_time_ms",
        "sha256": "hash_time_ms",
        "json": "json_time_ms"
    }
    return mapping.get(benchmark_type, "runtime_ms")



def filter_cpu_data(df: pd.DataFrame, provider: str, memory_size: int, benchmark: str, group_on_timestamp: bool, region: str | None = None, remove_cold: bool = True, no_outlier_filter: bool = False) -> pd.DataFrame:
    """
    Filter the DataFrame for specific CPU/system configurations based on provider, memory size, region, and benchmark type.
    Optionally group by timestamp to ensure complete sets of invocations.
    """

    subset = df[
        (df["provider"] == provider) &
        (df["memory_size_mb"] == memory_size) &
        (df["benchmark_type"] == benchmark) & 
        ((region is None) | (df["region"] == region))
    ].copy()

    if subset.empty:
        print(f"No data found for {provider} - {memory_size}MB - {benchmark} - region: {region}")
        return subset
    
    # --- CPU Normalization ---
    subset["cpu_type"] = subset["cpu_type"].apply(clean_cpu_string)

    # Filter only instances with 4 invocations (1 cold start + 3 warm)
    grouped = subset.groupby("instance_id")
    valid_ids = [
        inst_id
        for inst_id, group in grouped
        if len(group) == 4
    ]
    subset = subset[subset["instance_id"].isin(valid_ids)]

    if remove_cold:
        subset = subset[subset["invocation_count"] > 1]

    # --- Tukey Outlier Removal on Instance Means ---    
    metric_field = metric_for_benchmark(benchmark)
    
    # Calculate mean per instance (include timestamp since it's constant per instance)
    group_cols = ["cpu_type"] + (["timestamp"] if group_on_timestamp else [])
    instance_means = subset.groupby(["instance_id"] + group_cols)[metric_field].mean().reset_index()
    instance_means.columns = ["instance_id"] + group_cols + ["instance_mean"]


    def is_outlier_percentile(series: pd.Series, lower_q: float = 0.01, upper_q: float = 0.99) -> pd.Series:
        """
        Flags values outside [lower_q, upper_q] percentiles as outliers.
        Example: lower_q=0.01, upper_q=0.99 removes the bottom/top 1%.
        """
        low = series.quantile(lower_q)
        high = series.quantile(upper_q)
        return (series < low) | (series > high)

    if no_outlier_filter == False:
        outlier_mask = instance_means.groupby(group_cols)["instance_mean"].transform(
            lambda s: is_outlier_percentile(s, lower_q=0.05, upper_q=0.95)
        )
        bad_instances = instance_means.loc[outlier_mask, "instance_id"].unique()
        subset = subset[~subset["instance_id"].isin(bad_instances)]

        
    # # Tukey on instance means, grouped by CPU type
    # def is_outlier_tukey(series: pd.Series) -> pd.Series:
    #     Q1 = series.quantile(0.25)
    #     Q3 = series.quantile(0.75)
    #     IQR = Q3 - Q1
    #     lower_bound = Q1 - 3 * IQR
    #     upper_bound = Q3 + 3 * IQR
    #     return (series < lower_bound) | (series > upper_bound)


    # if no_outlier_filter == False:
    #     outlier_mask = instance_means.groupby(group_cols)["instance_mean"].transform(is_outlier_tukey)
    #     bad_instances = instance_means.loc[outlier_mask, "instance_id"].unique()
    #     subset = subset[~subset["instance_id"].isin(bad_instances)]

    return subset


def load_records_from_directory(log_dir: str) -> pd.DataFrame:   
    """
    Aggregate benchmark records from multiple log files into a single DataFrame.
    Each log file is parsed to extract invocation records.
    """

    all_records = []

    for root, _, files in os.walk(log_dir):
        if "logs" in root.split(os.sep):
            continue  # skip the 'logs' directory
        for file in files:
            if file.endswith(".log"):
                log_path = os.path.join(root, file)
                records = parse_log_file(log_path)
                all_records.extend(records)

    return pd.DataFrame(all_records)

