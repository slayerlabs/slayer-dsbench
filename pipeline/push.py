#!/usr/bin/env python3
"""Push slayer-pl-8x3b -> SlayerLab/slayer-pl-8x3b (dataset, private=True). Resumowalny upload_folder."""
import sys
from huggingface_hub import HfApi, create_repo

DS = "/mnt/c/Projekty/datasets/slayer-pl-8x3b"
REPO = "SlayerLab/slayer-pl-8x3b"

if __name__ == "__main__":
    api = HfApi()
    create_repo(REPO, repo_type="dataset", private=True, exist_ok=True)
    print("repo OK (private):", REPO)
    api.upload_folder(folder_path=DS, repo_id=REPO, repo_type="dataset",
                      ignore_patterns=["*.tmp", "**/.reg.json", "**/*.tmp"],
                      commit_message="slayer-pl-8x3b v0.1.0 (8x3B PL, wstepnie przeczyszczony)")
    info = api.dataset_info(REPO)
    print("PUSHED private=%s files=%d" % (info.private, len(info.siblings)))
