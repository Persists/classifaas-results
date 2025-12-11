import numpy as np

def calculate_cost(provider: str, memory_mb: int, duration_ms: float) -> float:
    """
    Calculates the cost (in USD) for a SINGLE invocation.
    
    Args:
        provider: 'aws', 'azure', 'gcp', or 'alibaba'
        memory_mb: The configured memory size in MB (e.g., 128, 512, 2048)
        duration_ms: The execution time in milliseconds.
                     (Pass the raw execution time; the function handles rounding rules)
    
    Returns:
        float: Cost in USD for this specific run.
    """
    
    # --- CONSTANTS & CONFIGURATION ---
    
    # AWS: $0.20 per 1M requests, $0.0000166667 per GB-second
    AWS_REQ_PRICE = 0.20 / 1_000_000
    AWS_GB_SEC = 0.0000166667

    # AZURE: $0.20 per 1M requests, $0.000037 per GB-second (User specific)
    AZURE_REQ_PRICE = 0.20 / 1_000_000
    AZURE_GB_SEC = 0.000037

    # GCP (Gen 1): $0.40 per 1M requests, Tier 1 Pricing per 100ms
    GCP_REQ_PRICE = 0.40 / 1_000_000
    GCP_TIER1_100MS = {
        128:  0.000000231,
        256:  0.000000463,
        512:  0.000000925,
        1024: 0.000001650,
        2048: 0.000002900,
        4096: 0.000005800,
        8192: 0.000006800
    }

    # ALIBABA: Tier 1 Pricing ($0.000020 per CU), Request = 75 CU / 10k
    ALI_CU_PRICE = 0.000020
    ALI_REQ_CU = 0.0075  # 75 / 10,000
    # Map Memory -> vCPU count (based on your specific config)
    ALI_VCPU_MAP = {
        128:  0.1,
        512:  0.4,
        2048: 1.6
    }

    # --- CALCULATION LOGIC ---

    provider = provider.lower()
    
    # 1. AWS
    if provider == "aws":
        duration_sec = duration_ms / 1000.0
        memory_gb = memory_mb / 1024.0
        compute_cost = duration_sec * memory_gb * AWS_GB_SEC
        return compute_cost + AWS_REQ_PRICE

    # 2. AZURE
    elif provider == "azure":
        duration_sec = duration_ms / 1000.0
        memory_gb = memory_mb / 1024.0
        compute_cost = duration_sec * memory_gb * AZURE_GB_SEC
        return compute_cost + AZURE_REQ_PRICE

    # 3. GCP (Gen 1)
    elif provider == "gcp":
        # Rule: Round UP to nearest 100ms
        billed_units = np.ceil(duration_ms / 100.0)
        
        # Get price for this memory tier (default to linear approx if missing)
        unit_price = GCP_TIER1_100MS.get(memory_mb)
        if unit_price is None:
            # Fallback: Approx $0.0000014 per GB per 100ms
            unit_price = (memory_mb / 1024.0) * 0.0000014
            
        compute_cost = billed_units * unit_price
        return compute_cost + GCP_REQ_PRICE

    # 4. ALIBABA
    elif provider == "alibaba":
        # Rule: Duration is in seconds for the formula
        duration_sec = duration_ms / 1000.0
        memory_gb = memory_mb / 1024.0
        
        # Get vCPU count
        vcpu = ALI_VCPU_MAP.get(memory_mb)
        if vcpu is None:
            # Fallback logic if you add new sizes later
            # (Alibaba generally scales vCPU with memory)
            vcpu = memory_gb * 0.75 
            
        # CU Formula: vCPU + (MemoryGB * 0.15)
        # Note: vCPU factor is 1.0
        resource_cu = (vcpu * 1.0) + (memory_gb * 0.15)
        
        compute_cost = resource_cu * duration_sec * ALI_CU_PRICE
        request_cost = ALI_REQ_CU * ALI_CU_PRICE
        
        return compute_cost + request_cost

    return 0.0