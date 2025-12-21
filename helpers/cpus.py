import re

import seaborn as sns
import hashlib
import colorcet as cc



def clean_cpu_string(cpu_name):
    """
    Normalizes CPU names but PRESERVES frequency differences.
    merges 'Intel(R) ... @ 2.50GHz' -> 'Intel ... 2.50GHz'
    """
    if not isinstance(cpu_name, str):
        return "Unknown"
    
    # 1. Basic Cleanup (Remove trademark symbols, generic words, @)
    clean = re.sub(r"\(R\)|\(TM\)|CPU|Processor|(?:\d+\s*[- ]?\s*Core)|Gen\s+\d+|APU|@| T ", "", cpu_name, flags=re.IGNORECASE)
    clean = " ".join(clean.split())
    
    return clean

# ==============================================================================
# 2. SHORTENING HELPER (For Legend)
# ==============================================================================
def shorten_cpu_name(cpu_name):
    """
    Robust shortening for legends.
    """
    if not isinstance(cpu_name, str): return "Unknown"
    
    # We reuse the cleaning logic to ensure consistency
    # (Since clean_cpu_string is now producing the exact output we want for the legend too)
    return clean_cpu_string(cpu_name)[:45] 


# ==============================================================================
# CONSISTENT COLOR GENERATION
# ==============================================================================

# ==============================================================================
# 2. MANUAL COLOR MAPPING (TAB20 PALETTE)
# ==============================================================================

# Get 20 distinct colors from Seaborn's official 'tab20' palette
# We convert them to Hex immediately for consistency

# Kelly's 20 colors - scientifically chosen for maximum distinction
KELLY_COLORS = [
    '#F99379',  # Strong Yellowish Pink
    '#8DB600',  # Vivid Yellowish Green
    '#A1CAF1',  # Very Light Blue
    '#654522',  # Deep Yellowish Brown
    '#BE0032',  # Vivid Red
    '#875692',  # Strong Purple
    '#F3C300',  # Vivid Yellow
    '#C2B280',  # Grayish Yellow
    '#E68FAC',  # Strong Purplish Pink
    '#604E97',  # Strong Violet
    '#2B3D26',  # Dark Olive Green
    '#F6A600',  # Vivid Orange Yellow
    '#E25822',  # Vivid Reddish Orange
    '#B3446C',  # Strong Purplish Red
    '#0067A5',  # Strong Blue
    '#882D17',  # Strong Reddish Brown
    '#008856',  # Vivid Green
    '#F38400',  # Vivid Orange
    "#292920",  # Medium Gray
    '#DCD300',  # Vivid Greenish Yellow
]

COLORS = KELLY_COLORS

# Distinct Assignments
MANUAL_COLORS = {
    # --- AWS (Blues/Oranges) ---
    "aws:Intel Xeon 2.50GHz":        COLORS[0],  
    "aws:Intel Xeon 2.90GHz":        COLORS[1],  
    "aws:Intel Xeon 3.00GHz":        COLORS[2], 
    "aws:AMD EPYC 2.25GHz":                  COLORS[3], 
    "aws:AMD EPYC 2.65GHz":                COLORS[18], 
    # --- AZURE (Greens/Reds) ---
    "azure:Intel Xeon Platinum 8370C 2.80GHz": COLORS[4],  
    "azure:AMD EPYC 7763":                     COLORS[5],  
    "azure:AMD EPYC 9V74":                     COLORS[6],  
    # --- GCP (Purples/Browns - Microarchitecture Codes) ---
    "gcp:Model 1 (AMD)":   COLORS[7],   
    "gcp:Model 17 (AMD)":  COLORS[8],  
    "gcp:Model 85 (Intel)":  COLORS[9],  
    "gcp:Model 106 (Intel)": COLORS[10],  
    "gcp:Model 143 (Intel)": COLORS[11],  
    "gcp:Model 173 (Intel)": COLORS[12],  
    # --- ALIBABA (Greys/Olives/Cyans - Distinct from AWS) ---
    "alibaba:Intel Xeon 2.50GHz":                   COLORS[13],  
    "alibaba:Intel Xeon 2.90GHz":                   COLORS[14],  
    "alibaba:Intel Xeon Platinum 8163 2.50GHz":     COLORS[15],  
    "alibaba:Intel Xeon Platinum 8269CY 2.50GHz":   COLORS[16],  
    "alibaba:Intel Xeon Platinum 8269CY 3.10GHz":   COLORS[17],  
}

def get_cpu_color(cpu_name, provider=None):
    """
    Returns a unique color for the CPU using Kelly's maximum contrast palette.
    Prioritizes 'provider:cpu_name' lookup to distinguish AWS vs Alibaba.
    """
    s = clean_cpu_string(str(cpu_name)).strip()
    
    # 1. Try Provider-Specific Key (Priority)
    if provider:
        prov_key = f"{provider.lower()}:{s}"
        if prov_key in MANUAL_COLORS:
            return MANUAL_COLORS[prov_key]
    
    # 2. Try Generic Key (Fallback if provider not passed or not found)
    if s in MANUAL_COLORS:
        return MANUAL_COLORS[s]
    
    # 3. Fallback: Hash to Kelly palette (For unknown CPUs)
    # This ensures new/unknown CPUs still get a valid color
    hash_val = int(hashlib.md5(s.encode()).hexdigest(), 16)
    return COLORS[hash_val % len(COLORS)]

def get_cpu_palette(cpu_list, provider=None):
    """
    Returns a dictionary {cpu_name: color} for the provided list.
    """
    unique_cpus = sorted(list(set(cpu_list)))
    return {cpu: get_cpu_color(cpu, provider) for cpu in unique_cpus}

