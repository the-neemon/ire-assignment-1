# One command rebuilds everything from raw files.
#
#   make data                    Q1: raw archives -> feature store, nothing else
#   make all                     data + retrieval + evaluation, every dataset
#   make DATASETS=mind_small all just one
#   make results                 re-evaluate without recomputing scores
#   make test                    anti-leakage checks on the built artifacts
#   make submissions             Codabench leaderboard files (downloads the test sets)
#   make encoder-ablation        re-run the EB-NeRD encoder comparison

PY := .venv/bin/python
DATASETS ?= ebnerd_demo ebnerd_small mind_small
# Both EB-NeRD encoders the assignment names are fetched: word2vec is the one the pipeline
# uses, bert_base_multilingual_cased is needed only to reproduce the ablation that chose it.
BUNDLES ?= ebnerd_demo ebnerd_small Ekstra_Bladet_word2vec \
	google_bert_base_multilingual_cased MINDsmall_train MINDsmall_dev

W2V := data/interim/Ekstra_Bladet_word2vec/Ekstra_Bladet_word2vec/document_vector.parquet
MBERT := data/interim/google_bert_base_multilingual_cased/google_bert_base_multilingual_cased/bert_base_multilingual_cased.parquet

.PHONY: all data venv download split retrieve results test submissions encoder-ablation clean-processed

all: results

# Q1's deliverable on its own: raw archives in, feature store out, one command.
# `all` continues past this into retrieval and evaluation.
data: split

venv:
	uv venv --python 3.11 .venv
	# CPU-only torch first: the default resolves to CUDA wheels (~2.5GB) that this
	# machine cannot use, and pulling them stalls the install.
	VIRTUAL_ENV=.venv uv pip install torch --index-url https://download.pytorch.org/whl/cpu
	VIRTUAL_ENV=.venv uv pip install polars pyarrow bm25s PyStemmer faiss-cpu \
		sentence-transformers huggingface_hub numpy scipy scikit-learn tqdm pyyaml pytest

download:
	$(PY) -m pipeline.download $(BUNDLES)

split: download
	$(PY) -m pipeline.split $(DATASETS)

retrieve: split
	$(PY) -m retrieval.bm25 $(DATASETS)
	$(PY) -m retrieval.embeddings $(DATASETS)
	$(PY) -m retrieval.fuse $(DATASETS)

results: retrieve
	$(PY) -m eval.run $(DATASETS)

# Anti-leakage checks against the built artifacts. Runs in seconds; needs `make split`
# to have run, and skips any dataset that has not been built.
test:
	$(PY) -m pytest tests/ -v

# Codabench leaderboard files. Separate from `all` because these score the competitions'
# held-out test sets (EB-NeRD 13.5M impressions, MIND-large 2.4M), not our splits, and
# need those bundles downloaded first.
submissions:
	$(PY) -m pipeline.download ebnerd_testset MINDlarge_test
	$(PY) -m pipeline.submit ebnerd
	$(PY) -m pipeline.submit mind

# Which EB-NeRD encoder to use is the one modelling choice the assignment leaves open, so it
# is settled by measurement rather than assertion. Runs the identical pipeline once per
# encoder — only the article vectors differ — and leaves both reports under
# results/encoder_ablation/. The winner is read off **val**; test is reported, never chosen on.
# Overwrites results/ebnerd_*, so `make results` afterwards restores the configured encoder.
encoder-ablation:
	@set -e; for enc in word2vec:$(W2V) bert_multilingual:$(MBERT); do \
		tag=$${enc%%:*}; path=$${enc#*:}; \
		echo "=== $$tag ==="; \
		$(PY) -m retrieval.embeddings ebnerd_demo ebnerd_small --splits val test --embeddings $$path; \
		$(PY) -m retrieval.fuse ebnerd_demo ebnerd_small --splits val test; \
		$(PY) -m eval.run ebnerd_demo ebnerd_small --splits val test; \
		mkdir -p results/encoder_ablation/$$tag; \
		cp results/ebnerd_demo_*.md results/ebnerd_demo_*.json \
		   results/ebnerd_small_*.md results/ebnerd_small_*.json results/encoder_ablation/$$tag/; \
	done

clean-processed:
	rm -rf data/processed results
