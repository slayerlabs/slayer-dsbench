#!/usr/bin/env python3
"""Push slayer-pl-8x3b -> SlayerLab/slayer-pl-8x3b. Resumowalny upload_folder.
Nowe repo zakladane jako prywatne; widocznosci istniejacego repo skrypt nie zmienia."""
import sys
from huggingface_hub import HfApi, create_repo
from paths import data_root

REPO = "SlayerLab/slayer-pl-8x3b"

if __name__ == "__main__":
    DS = str(data_root() / "slayer-pl-8x3b")
    api = HfApi()
    create_repo(REPO, repo_type="dataset", private=True, exist_ok=True)
    print("repo OK:", REPO)
    api.upload_folder(folder_path=DS, repo_id=REPO, repo_type="dataset",
                      ignore_patterns=["*.tmp", "**/.reg.json", "**/*.tmp"],
                      commit_message="slayer-pl-8x3b v0.1.0 (8x3B PL, wstepnie przeczyszczony)")
    info = api.dataset_info(REPO)
    print("PUSHED private=%s files=%d" % (info.private, len(info.siblings)))
