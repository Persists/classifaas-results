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
    clean = re.sub(r"\(R\)|\(TM\)|CPU|Processor|Platinum|(?:\d+\s*[- ]?\s*Core)|Gen\s+\d+|APU|@| T ", "", cpu_name, flags=re.IGNORECASE)
    clean = " ".join(clean.split())
    if clean == "Intel Xeon 8370C 2.80GHz":
        clean = "Intel Xeon 8370C"
    
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
    # --- AWS ---
    "aws:Intel Xeon 2.50GHz":              COLORS[0],
    "aws:Intel Xeon 2.90GHz":              COLORS[1],
    "aws:Intel Xeon 3.00GHz":              COLORS[2],
    "aws:AMD EPYC 2.25GHz":                COLORS[3],
    "aws:AMD EPYC 2.65GHz":                COLORS[18],
    # --- AZURE ---
    "azure:Intel Xeon 8370C":              COLORS[4],
    "azure:AMD EPYC 7763":                 COLORS[5],
    "azure:AMD EPYC 9V74":                 COLORS[6],
    # --- GCP ---
    "gcp:Model 1 (AMD)":                   COLORS[7],
    "gcp:Model 17 (AMD)":                  COLORS[8],
    "gcp:Model 85 (Intel)":                COLORS[9],
    "gcp:Model 106 (Intel)":               COLORS[10],
    "gcp:Model 143 (Intel)":               COLORS[11],
    "gcp:Model 173 (Intel)":               COLORS[12],
    # --- ALIBABA ---
    "alibaba:Intel Xeon 2.50GHz":          COLORS[13],
    "alibaba:Intel Xeon 2.90GHz":          COLORS[14],
    "alibaba:Intel Xeon 8163 2.50GHz":     COLORS[15],
    "alibaba:Intel Xeon 8269CY 2.50GHz":   COLORS[16],
    "alibaba:Intel Xeon 8269CY 3.10GHz":   COLORS[17],
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
    hash_val = int(hashlib.md5(s.encode()).hexdigest(), 16)
    return COLORS[hash_val % len(COLORS)]

def get_cpu_palette(cpu_list, provider=None):
    """
    Returns a dictionary {cpu_name: color} for the provided list.
    """
    unique_cpus = sorted(list(set(cpu_list)))
    return {cpu: get_cpu_color(cpu, provider) for cpu in unique_cpus}


# ==============================================================================
# CPU HATCH PATTERNS
# ==============================================================================
# Each CPU gets a distinct hatch within its provider, making it easier to tell
# bars apart at a glance (and in print/grayscale). Patterns are reused across
# providers because no figure mixes CPUs from different providers in one axis.
#
# Pool ordered roughly by visual weight, lightest first.
HATCH_POOL = ["", "//", "\\\\", "..", "xx", "++", "oo", "**"]

MANUAL_HATCHES = {
    # --- AWS (5 CPUs) ---
    "aws:Intel Xeon 2.50GHz":              "",
    "aws:Intel Xeon 2.90GHz":              "//",
    "aws:Intel Xeon 3.00GHz":              "\\\\\\\\\\\\",
    "aws:AMD EPYC 2.25GHz":                "..",
    "aws:AMD EPYC 2.65GHz":                "xx",
    # --- AZURE (3 CPUs) ---
    "azure:Intel Xeon 8370C":              "",
    "azure:AMD EPYC 7763":                 "//",
    "azure:AMD EPYC 9V74":                 "\\\\",
    # --- GCP (6 CPUs) ---
    "gcp:Model 1 (AMD)":                   "",
    "gcp:Model 17 (AMD)":                  "//",
    "gcp:Model 85 (Intel)":                "\\\\",
    "gcp:Model 106 (Intel)":               "..",
    "gcp:Model 143 (Intel)":               "xx",
    "gcp:Model 173 (Intel)":               "++",
    # --- ALIBABA (5 CPUs) ---
    "alibaba:Intel Xeon 2.50GHz":          "",
    "alibaba:Intel Xeon 2.90GHz":          "//",
    "alibaba:Intel Xeon 8163 2.50GHz":     "\\\\",
    "alibaba:Intel Xeon 8269CY 2.50GHz":   "..",
    "alibaba:Intel Xeon 8269CY 3.10GHz":   "xx",
}


def get_cpu_hatch(cpu_name, provider=None):
    """
    Returns the matplotlib hatch pattern for the CPU.
    Provider-aware so the same CPU label under different providers can map to
    different hatches (mirrors get_cpu_color). Falls back to deterministic
    assignment from HATCH_POOL for unknown CPUs.
    """
    s = clean_cpu_string(str(cpu_name)).strip()

    if provider:
        prov_key = f"{provider.lower()}:{s}"
        if prov_key in MANUAL_HATCHES:
            return MANUAL_HATCHES[prov_key]

    if s in MANUAL_HATCHES:
        return MANUAL_HATCHES[s]

    hash_val = int(hashlib.md5(s.encode()).hexdigest(), 16)
    return HATCH_POOL[hash_val % len(HATCH_POOL)]


def get_cpu_hatches(cpu_list, provider=None):
    """
    Returns a dictionary {cpu_name: hatch} for the provided list.
    """
    unique_cpus = sorted(list(set(cpu_list)))
    return {cpu: get_cpu_hatch(cpu, provider) for cpu in unique_cpus}