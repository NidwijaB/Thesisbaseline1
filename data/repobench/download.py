"""
data/repobench/download.py
---------------------------
Downloads RepoBench (Python, v1.1) from HuggingFace and saves it locally.

RepoBench provides repository-level code completion tasks with cross-file
context already attached — this is what makes it useful for evaluating
retrieval (RAG) quality, not just raw completion accuracy.

Dataset: https://huggingface.co/datasets/tianyang/repobench_python_v1.1
Configs (pick one, or download all three — see main() below):
    - "cross_file_first"  : next line depends on a cross-file symbol used
                             for the first time in the current file
    - "cross_file_random" : next line depends on a cross-file symbol used
                             elsewhere already (harder retrieval case)
    - "in_file"           : next line only needs in-file context (no
                             retrieval benefit expected — useful as a
                             control group)

Run once:
    python data/repobench/download.py
"""

from __future__ import annotations
from pathlib import Path
from datasets import load_dataset

# Configs to pull. cross_file_first + cross_file_random are the ones that
# actually exercise retrieval; in_file is kept as a control/ablation set.
CONFIGS = ["cross_file_first", "cross_file_random", "in_file"]

OUTPUT_DIR = Path(__file__).parent  # data/repobench/


def download():
    for config_name in CONFIGS:
        print(f"Downloading RepoBench config: {config_name} ...")
        dataset = load_dataset("tianyang/repobench_python_v1.1", config_name)
        dest = OUTPUT_DIR / config_name
        dataset.save_to_disk(str(dest))
        print(f"  -> saved to {dest}")

    print("RepoBench download complete.")
    print("Next step: run src/preprocessing/prepare_datasets.py")


if __name__ == "__main__":
    download()