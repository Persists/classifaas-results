import os
import json
import pandas as pd
from datetime import datetime

from helpers.cpus import shorten_cpu_name



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
                    "cpu_type": shorten_cpu_name(cpu_field),
                    "cpu_model_number": body.get("cpuModel", "unknown"),

                    # Context switches
                    "context_switches": body.get("contextSwitches", None),
                    "context_switches_delta": body.get("contextSwitchesDelta", None),

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
                if benchmark.get("type") == "matmul":
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
        "matmul": "multiplication_time_ms",
        "aesCtr": "encrypt_time_ms",
        "gzip": "compress_time_ms",
        "sha256": "hash_time_ms",
        "json": "json_time_ms"
    }
    return mapping.get(benchmark_type, "runtime_ms")


def trim_on_benchmark(df: pd.DataFrame, group_on_timestamp: bool, benchmark: str) -> pd.DataFrame:
    """
    Trim outliers from the DataFrame for a specific benchmark type.
    Optionally group by timestamp to only trim within each timestamp group.
    """

    metric = metric_for_benchmark(benchmark)

    def trim_outliers(series: pd.Series) -> pd.Series:
        high = series.quantile(0.99)
        return (series <= high)
    
    group_by = ["cpu_type"]
    if group_on_timestamp:
        group_by.append("timestamp")

    mask = df.groupby(group_by)[metric].transform(trim_outliers)
    trimmed_df = df[mask].copy()


    return trimmed_df




def filter_full_lifecycle(df: pd.DataFrame, remove_cold: bool = False) -> pd.DataFrame:
    """
    Filter the DataFrame for a specific provider, memory size, benchmark type, and optionally region.
    Optionally remove cold start invocations.
    """
    subset = df.copy()

    grouped = subset.groupby("instance_id")
    valid_ids = [
        inst_id
        for inst_id, group in grouped
        if len(group) == 4
    ]
    subset = subset[subset["instance_id"].isin(valid_ids)]

    if remove_cold:
        subset = subset[subset["invocation_count"] > 1]

    return subset

def remove_cold_starts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove cold start invocations from the DataFrame.
    Cold starts are identified as records where 'invocation_count' is 1.
    """
    return df[~(df["invocation_count"] == 1)].copy()


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

