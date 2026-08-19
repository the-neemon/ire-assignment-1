"""Download and extract the raw EB-NeRD and MIND bundles.

Idempotent: a bundle is skipped if its extract directory already holds a .done marker,
so re-running costs nothing.

    python -m pipeline.download
    python -m pipeline.download ebnerd_small
"""

import argparse
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"

EBNERD_BASE = "https://ebnerd-dataset.s3.eu-west-1.amazonaws.com"
EBNERD_BUNDLES = ("ebnerd_demo", "ebnerd_small", "ebnerd_testset", "articles_large_only")
# Article embeddings ship separately from the impression bundles, under an artifacts/ prefix,
# and each one covers the full article set (so they apply to demo as well as large).
EBNERD_ARTIFACTS = (
    "Ekstra_Bladet_contrastive_vector",
    "Ekstra_Bladet_word2vec",
    "Ekstra_Bladet_image_embeddings",
    "FacebookAI_xlm_roberta_base",
    "google_bert_base_multilingual_cased",
)

MIND_REPO = "yjw1029/MIND"
MIND_BUNDLES = (
    "MINDsmall_train",
    "MINDsmall_dev",
    "MINDlarge_train",
    "MINDlarge_dev",
    "MINDlarge_test",
)
MIND_GATE_URL = f"https://huggingface.co/datasets/{MIND_REPO}"

# Both EB-NeRD encoders the assignment names: word2vec is what the pipeline uses,
# bert_base_multilingual_cased is needed only to reproduce the ablation that chose it.
DEFAULT_BUNDLES = (
    "ebnerd_demo",
    "Ekstra_Bladet_word2vec",
    "google_bert_base_multilingual_cased",
    "MINDsmall_train",
    "MINDsmall_dev",
)


def _fetch_ebnerd(name: str) -> Path:
    dest = RAW / "ebnerd" / f"{name}.zip"
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    prefix = "artifacts/" if name in EBNERD_ARTIFACTS else ""
    url = f"{EBNERD_BASE}/{prefix}{name}.zip"
    print(f"  downloading {url}")
    # Download to .part and rename only on success. rename is atomic, so an interrupted
    # download can never leave a truncated file that looks complete on the next run.
    tmp = dest.with_suffix(".zip.part")
    with urllib.request.urlopen(url) as response, open(tmp, "wb") as fh:
        # copyfileobj streams in chunks, so a 1.6 GB bundle never sits in memory at once.
        shutil.copyfileobj(response, fh)
    tmp.rename(dest)
    return dest


def _fetch_mind(name: str) -> Path:
    from huggingface_hub import hf_hub_download
    from huggingface_hub.errors import GatedRepoError, HfHubHTTPError

    print(f"  downloading {MIND_REPO}/{name}.zip")
    try:
        return Path(
            hf_hub_download(
                repo_id=MIND_REPO,
                repo_type="dataset",
                filename=f"{name}.zip",
                cache_dir=RAW / "mind",
            )
        )
    except (GatedRepoError, HfHubHTTPError) as exc:
        raise SystemExit(
            f"Could not fetch {name}.zip from the gated repo {MIND_REPO}.\n"
            f"Log in with `huggingface-cli login`, then open {MIND_GATE_URL} and click\n"
            f'"Agree and access repository" — access is granted automatically.\n'
            f"Original error: {exc}"
        ) from exc


def _extract(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(dest)
    # The marker is written last, so it can only exist if extraction finished. This is what
    # `fetch` checks, which is what makes "one command rebuilds from raw" cheap to re-run.
    (dest / ".done").touch()


def fetch(name: str, force: bool = False) -> None:
    dest = INTERIM / name
    if (dest / ".done").exists() and not force:
        print(f"{name}: already extracted, skipping")
        return

    print(f"{name}:")
    if name in EBNERD_BUNDLES or name in EBNERD_ARTIFACTS:
        archive = _fetch_ebnerd(name)
    elif name in MIND_BUNDLES:
        archive = _fetch_mind(name)
    else:
        raise SystemExit(f"unknown bundle {name!r}")

    print(f"  extracting to {dest}")
    _extract(archive, dest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundles", nargs="*", default=list(DEFAULT_BUNDLES))
    parser.add_argument("--force", action="store_true", help="re-extract even if done")
    args = parser.parse_args()

    for name in args.bundles:
        fetch(name, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
