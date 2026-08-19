# ebnerd_demo — test

25,356 impressions, 25,356 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5125 [0.5088, 0.5166] | 0.3273 [0.3241, 0.3308] | 0.3591 [0.3551, 0.3632] | 0.4418 [0.4387, 0.4453] |
| emb | 0.4966 [0.4924, 0.5006] | 0.3214 [0.3179, 0.3249] | 0.3500 [0.3457, 0.3543] | 0.4351 [0.4317, 0.4384] |
| fused | 0.5125 [0.5088, 0.5166] | 0.3273 [0.3241, 0.3308] | 0.3591 [0.3551, 0.3632] | 0.4418 [0.4387, 0.4453] |
| fused+popularity | 0.5610 [0.5572, 0.5648] | 0.3488 [0.3456, 0.3525] | 0.3878 [0.3838, 0.3921] | 0.4657 [0.4625, 0.4692] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.7964 | 13.9755 | 0.2178 |
| emb | 0.8004 | 13.9748 | 0.2157 |
| fused | 0.7964 | 13.9755 | 0.2178 |
| fused+popularity | 0.7966 | 13.9723 | 0.2113 |

## AUC by slice

cold = history length <= 40; head = clicked article with >= 72 train clicks

| slice | n | bm25 | emb | fused | fused+popularity |
|---|---|---|---|---|---|
| cold | 2,725 | 0.5102 [0.4987, 0.5225] | 0.4976 [0.4846, 0.5103] | 0.5102 [0.4987, 0.5225] | 0.5714 [0.5594, 0.5829] |
| warm | 22,631 | 0.5128 [0.5087, 0.5171] | 0.4964 [0.4922, 0.5009] | 0.5128 [0.5087, 0.5171] | 0.5597 [0.5555, 0.5638] |
| head | 57 | 0.5908 [0.5141, 0.6607] | 0.7142 [0.6621, 0.7603] | 0.5908 [0.5141, 0.6607] | 0.7667 [0.7155, 0.8125] |
| tail | 25,299 | 0.5123 [0.5085, 0.5165] | 0.4961 [0.4921, 0.5004] | 0.5123 [0.5085, 0.5165] | 0.5605 [0.5565, 0.5643] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0108 [0.0095, 0.0122] | 0.0216 [0.0199, 0.0234] | 0.0390 [0.0368, 0.0413] |
| emb | 0.0089 [0.0078, 0.0101] | 0.0188 [0.0172, 0.0205] | 0.0347 [0.0326, 0.0369] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 2,725 | 0.0360 [0.0294, 0.0429] | 0.0371 [0.0301, 0.0440] | +0.0011 [-0.0081, +0.0114] | no |
| warm | 22,631 | 0.0394 [0.0368, 0.0420] | 0.0345 [0.0322, 0.0368] | -0.0049 [-0.0084, -0.0016] | yes |
| head | 57 | 0.1078 [0.0351, 0.1930] | 0.0526 [0.0000, 0.1228] | -0.0551 [-0.1604, +0.0353] | no |
| tail | 25,299 | 0.0389 [0.0366, 0.0411] | 0.0347 [0.0324, 0.0370] | -0.0042 [-0.0074, -0.0011] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | -0.0160 [-0.0219, -0.0104] | yes |
| emb - bm25 (ndcg@10) | -0.0067 [-0.0109, -0.0027] | yes |
| fused - emb (auc) | +0.0160 [+0.0104, +0.0219] | yes |
| fused - emb (ndcg@10) | +0.0067 [+0.0027, +0.0109] | yes |
| fused - bm25 (auc) | +0.0000 [+0.0000, +0.0000] | no |
| fused - bm25 (ndcg@10) | +0.0000 [+0.0000, +0.0000] | no |
| fused+popularity - fused (auc) | +0.0485 [+0.0454, +0.0513] | yes |
| fused+popularity - fused (ndcg@10) | +0.0238 [+0.0218, +0.0258] | yes |
| emb - bm25 (recall@50) | -0.0019 [-0.0037, -0.0002] | yes |
| emb - bm25 (recall@100) | -0.0028 [-0.0052, -0.0005] | yes |
| emb - bm25 (recall@200) | -0.0043 [-0.0073, -0.0013] | yes |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.
