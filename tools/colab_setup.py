"""
tools/colab_setup.py
--------------------
One-command Colab setup. Run it from the project root AFTER cloning the repo and
mounting Google Drive (see docs/colab_steps.md):

    python tools/colab_setup.py                       # CrossCodeEval only (pilot)
    python tools/colab_setup.py --datasets crosscodeeval repobench

What it does:
  1. Checks that Drive is mounted and a GPU is present.
  2. Installs the pinned libraries (torch is NOT touched; Colab ships its own).
  3. Links experiments/finetuned_model and results/ to Google Drive, so adapters,
     checkpoints and results survive a disconnect.
  4. Gets the data: restores it from a Drive cache if one exists; otherwise downloads
     the public benchmarks, rebuilds splits / corpora / indexes with the same seeds as
     the local run, and saves a cache to Drive. So the slow part happens only once.

No secrets are read or written here. Standard library only, so it runs before pip.
"""

from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

DRIVE = Path("/content/drive/MyDrive/thesis")
CACHE = DRIVE / "cache"
OUTPUTS = DRIVE / "outputs"

# Pinned to the versions the local runs used (see docs/progress_log.md). If one of
# these pins fails on Colab, relax that pin and note it in the log.
PIP_PACKAGES = [
    "transformers==5.15.0",
    "peft==0.20.0",
    "accelerate==1.14.0",
    "datasets==5.0.1",
    "sentence-transformers==5.7.0",
    "bitsandbytes",
    "faiss-cpu==1.15.0",
    "rank_bm25==0.2.2",
    "Levenshtein==0.27.4",
    "nltk",
    "psutil",
    "pyyaml",
    "matplotlib",
]
# CodeBLEU is installed separately and is not fatal if it fails: it brings its own
# tree-sitter requirement, which could clash with the pins above. Evaluation raises a clear
# error if it is missing, or you can run it with --skip-codebleu.
OPTIONAL_PIP_PACKAGES = ["codebleu", "tree-sitter-python"]

# Steps that rebuild each dataset, in order. All are seeded in the scripts.
BUILD_STEPS = {
    "crosscodeeval": [
        ["data/crosscodeeval/download.py"],
        ["-m", "src.preprocessing.build_crosscodeeval_split"],
        ["-m", "src.preprocessing.build_crosscodeeval_finetune"],
        ["-m", "src.preprocessing.build_crosscodeeval_pilot"],
        ["-m", "src.retrieval.build_indexes"],
    ],
    "repobench": [
        ["data/repobench/download.py"],
        ["-m", "src.preprocessing.build_repobench_split"],
        ["-m", "src.preprocessing.build_repobench_finetune"],
        ["-m", "src.preprocessing.build_repobench_sample"],
        ["-m", "src.retrieval.build_repobench_indexes", "--sample-repos"],
    ],
}

# What gets cached per dataset (all gitignored, so GitHub never holds them).
CACHE_PATHS = {
    "crosscodeeval": [
        "data/crosscodeeval/python",
        "data/processed/crosscodeeval",
        "data/embeddings/crosscodeeval",
    ],
    "repobench": [
        "data/repobench/cross_file_first",
        "data/repobench/cross_file_random",
        "data/repobench/in_file",
        "data/processed/repobench",
        "data/embeddings/repobench",
    ],
}

# Sizes recorded in docs/progress_log.md. A mismatch is a warning, not a failure.
EXPECTED_LINES = {
    "data/processed/crosscodeeval/finetune/train.jsonl": 9378,
    "data/processed/crosscodeeval/finetune/val.jsonl": 1059,
    "data/processed/repobench/finetune/train.jsonl": 10800,
    "data/processed/repobench/finetune/val.jsonl": 1200,
}


# Other facts from the log that a stale or partial cache would break. (path, what to count, expected)
EXPECTED_OTHER = {
    "crosscodeeval": [
        ("data/processed/crosscodeeval/pilot_ids.json", "json_list", 50),       # Entry 13
        ("data/embeddings/crosscodeeval", "subfolders", 206),                    # Entry 12
        ("data/processed/crosscodeeval/examples.jsonl", "lines", 2018),         # Entries 3, 7: examples in repos with >= 3 files
    ],
    "repobench": [
        ("data/processed/repobench/sample_repos.json", "json_list", 446),       # Entry 24
    ],
}


def run(cmd: list[str]) -> None:
    print("  $", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def check_environment() -> None:
    if not (DRIVE.parent).exists():
        sys.exit("Google Drive is not mounted. Run the 'mount Drive' cell first.")
    CACHE.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    print(f"Drive folder: {DRIVE}")


def install_packages() -> None:
    print("\n[2/5] Installing libraries")
    run([sys.executable, "-m", "pip", "install", "-q", *PIP_PACKAGES])
    result = subprocess.run([sys.executable, "-m", "pip", "install", "-q", *OPTIONAL_PIP_PACKAGES])
    if result.returncode != 0:
        print("  WARNING: CodeBLEU packages did not install. Evaluate with --skip-codebleu, "
              "or tell Claude Code the pip error.")


def check_gpu(allow_cpu: bool) -> None:
    print("\n[3/5] Checking the GPU")
    code = (
        "import torch, bitsandbytes;"
        "print('cuda:', torch.cuda.is_available());"
        "print('gpu:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else None);"
        "print('bitsandbytes:', bitsandbytes.__version__)"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    print(result.stdout + result.stderr[-500:])
    if "cuda: True" not in result.stdout and not allow_cpu:
        sys.exit("No GPU. Runtime > Change runtime type > T4 GPU, then restart and re-run.")


def link_outputs() -> None:
    """Make output folders live on Drive; the code keeps using its normal paths."""
    print("\n[4/5] Linking output folders to Drive")
    for local, remote in [
        ("experiments/finetuned_model", OUTPUTS / "finetuned_model"),
        ("results", OUTPUTS / "results"),
    ]:
        remote.mkdir(parents=True, exist_ok=True)
        local_path = Path(local)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        if local_path.is_symlink():
            local_path.unlink()
        elif local_path.exists():
            if any(local_path.iterdir()):
                sys.exit(f"{local} already has files; refusing to replace it.")
            local_path.rmdir()
        local_path.symlink_to(remote, target_is_directory=True)
        print(f"  {local} -> {remote}")


def restore_or_build(name: str, force_rebuild: bool) -> None:
    archive = CACHE / f"{name}_data.tar"
    if archive.exists() and not force_rebuild:
        print(f"  restoring {name} from {archive}")
        with tarfile.open(archive) as tar:
            tar.extractall(".", filter="data")  # 'data' filter blocks unsafe paths
        return
    print(f"  no cache for {name}: downloading and rebuilding (one-time, slow)")
    for step in BUILD_STEPS[name]:
        run([sys.executable, *step])
    tmp = archive.with_suffix(".tar.part")
    with tarfile.open(tmp, "w") as tar:
        for path in CACHE_PATHS[name]:
            if Path(path).exists():
                tar.add(path)
    tmp.rename(archive)  # only a complete archive ever gets the final name
    print(f"  cached to {archive}")


def verify_data(names: list[str]) -> None:
    print("\nChecking data against the sizes in the progress log")
    for rel, expected in EXPECTED_LINES.items():
        if not any(n in rel for n in names):
            continue
        path = Path(rel)
        if not path.exists():
            print(f"  MISSING  {rel}")
            continue
        with path.open(encoding="utf-8") as f:
            count = sum(1 for _ in f)
        status = "ok     " if count == expected else "DIFFERS"
        print(f"  {status} {rel}: {count} (log says {expected})")
    for name in names:
        for rel, kind, expected in EXPECTED_OTHER.get(name, []):
            path = Path(rel)
            if not path.exists():
                print(f"  MISSING  {rel}")
                continue
            if kind == "json_list":
                count = len(json.loads(path.read_text(encoding="utf-8")))
            elif kind == "subfolders":
                count = sum(1 for p in path.iterdir() if p.is_dir())
            else:
                with path.open(encoding="utf-8") as f:
                    count = sum(1 for _ in f)
            status = "ok     " if count == expected else "DIFFERS"
            print(f"  {status} {rel}: {count} (log says {expected})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="+", default=["crosscodeeval"],
                        choices=sorted(BUILD_STEPS))
    parser.add_argument("--rebuild", action="store_true", help="Ignore the Drive cache")
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--allow-cpu", action="store_true")
    args = parser.parse_args()

    if not Path("configs/config.yaml").exists():
        sys.exit("Run this from the project root (the folder containing configs/).")

    print("[1/5] Checking Drive")
    check_environment()
    if not args.skip_install:
        install_packages()
    check_gpu(args.allow_cpu)
    link_outputs()
    print("\n[5/5] Preparing data")
    for name in args.datasets:
        restore_or_build(name, args.rebuild)
    verify_data(args.datasets)
    print("\nSetup finished. Next: see 'Start training' in docs/colab_steps.md")


if __name__ == "__main__":
    main()
