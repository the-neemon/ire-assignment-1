# ebnerd_small — test

244,647 impressions, 244,647 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5107 [0.5094, 0.5120] | 0.3257 [0.3245, 0.3269] | 0.3577 [0.3563, 0.3591] | 0.4409 [0.4397, 0.4421] |
| emb | 0.5397 [0.5383, 0.5410] | 0.3492 [0.3480, 0.3504] | 0.3831 [0.3817, 0.3845] | 0.4627 [0.4615, 0.4638] |
| fused | 0.5380 [0.5367, 0.5394] | 0.3474 [0.3463, 0.3486] | 0.3813 [0.3800, 0.3826] | 0.4613 [0.4601, 0.4624] |
| fused+popularity | 0.5797 [0.5785, 0.5810] | 0.3688 [0.3676, 0.3701] | 0.4101 [0.4087, 0.4115] | 0.4841 [0.4830, 0.4852] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.7968 | 16.9664 | 0.2067 |
| emb | 0.7803 | 17.0072 | 0.2050 |
| fused | 0.7820 | 16.9992 | 0.2051 |
| fused+popularity | 0.7882 | 17.0144 | 0.1975 |

## AUC by slice

cold = history length <= 34; head = clicked article with >= 349 train clicks

| slice | n | bm25 | emb | fused | fused+popularity |
|---|---|---|---|---|---|
| cold | 25,105 | 0.5103 [0.5059, 0.5142] | 0.5481 [0.5442, 0.5519] | 0.5449 [0.5411, 0.5489] | 0.5906 [0.5868, 0.5944] |
| warm | 219,542 | 0.5108 [0.5094, 0.5123] | 0.5387 [0.5373, 0.5403] | 0.5372 [0.5359, 0.5387] | 0.5785 [0.5772, 0.5799] |
| head | 803 | 0.5852 [0.5626, 0.6066] | 0.6191 [0.5985, 0.6388] | 0.6353 [0.6148, 0.6556] | 0.6921 [0.6703, 0.7133] |
| tail | 243,844 | 0.5105 [0.5091, 0.5118] | 0.5394 [0.5381, 0.5406] | 0.5377 [0.5364, 0.5389] | 0.5793 [0.5782, 0.5806] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0072 [0.0069, 0.0075] | 0.0133 [0.0128, 0.0138] | 0.0247 [0.0241, 0.0253] |
| emb | 0.0073 [0.0069, 0.0076] | 0.0144 [0.0139, 0.0148] | 0.0277 [0.0271, 0.0283] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 25,105 | 0.0257 [0.0239, 0.0277] | 0.0292 [0.0272, 0.0314] | +0.0035 [+0.0008, +0.0060] | yes |
| warm | 219,542 | 0.0245 [0.0240, 0.0252] | 0.0275 [0.0269, 0.0282] | +0.0030 [+0.0020, +0.0038] | yes |
| head | 803 | 0.0791 [0.0604, 0.0984] | 0.0461 [0.0311, 0.0610] | -0.0330 [-0.0542, -0.0118] | yes |
| tail | 243,844 | 0.0245 [0.0239, 0.0251] | 0.0276 [0.0270, 0.0283] | +0.0031 [+0.0023, +0.0040] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | +0.0289 [+0.0272, +0.0308] | yes |
| emb - bm25 (ndcg@10) | +0.0218 [+0.0204, +0.0231] | yes |
| fused - emb (auc) | -0.0017 [-0.0023, -0.0011] | yes |
| fused - emb (ndcg@10) | -0.0014 [-0.0020, -0.0008] | yes |
| fused - bm25 (auc) | +0.0273 [+0.0257, +0.0288] | yes |
| fused - bm25 (ndcg@10) | +0.0204 [+0.0193, +0.0215] | yes |
| fused+popularity - fused (auc) | +0.0417 [+0.0408, +0.0426] | yes |
| fused+popularity - fused (ndcg@10) | +0.0228 [+0.0221, +0.0236] | yes |
| emb - bm25 (recall@50) | +0.0001 [-0.0004, +0.0006] | no |
| emb - bm25 (recall@100) | +0.0011 [+0.0005, +0.0017] | yes |
| emb - bm25 (recall@200) | +0.0030 [+0.0022, +0.0039] | yes |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.
