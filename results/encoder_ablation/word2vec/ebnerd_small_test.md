# ebnerd_small — test

244,647 impressions, 244,647 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5107 [0.5094, 0.5120] | 0.3257 [0.3245, 0.3269] | 0.3577 [0.3563, 0.3591] | 0.4409 [0.4397, 0.4421] |
| emb | 0.5036 [0.5022, 0.5049] | 0.3175 [0.3163, 0.3187] | 0.3476 [0.3461, 0.3489] | 0.4344 [0.4333, 0.4355] |
| fused | 0.5131 [0.5118, 0.5143] | 0.3254 [0.3243, 0.3266] | 0.3579 [0.3565, 0.3592] | 0.4414 [0.4402, 0.4424] |
| fused+popularity | 0.5644 [0.5632, 0.5657] | 0.3506 [0.3494, 0.3518] | 0.3913 [0.3899, 0.3928] | 0.4683 [0.4672, 0.4695] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.7968 | 16.9664 | 0.2067 |
| emb | 0.7929 | 16.9576 | 0.2068 |
| fused | 0.7957 | 16.9607 | 0.2068 |
| fused+popularity | 0.7962 | 16.9964 | 0.1965 |

## AUC by slice

cold = history length <= 34; head = clicked article with >= 349 train clicks

| slice | n | bm25 | emb | fused | fused+popularity |
|---|---|---|---|---|---|
| cold | 25,105 | 0.5103 [0.5059, 0.5142] | 0.5123 [0.5084, 0.5165] | 0.5163 [0.5120, 0.5203] | 0.5711 [0.5671, 0.5748] |
| warm | 219,542 | 0.5108 [0.5094, 0.5123] | 0.5026 [0.5012, 0.5040] | 0.5127 [0.5113, 0.5142] | 0.5637 [0.5624, 0.5650] |
| head | 803 | 0.5852 [0.5626, 0.6066] | 0.6349 [0.6145, 0.6531] | 0.6067 [0.5849, 0.6262] | 0.6801 [0.6607, 0.6998] |
| tail | 243,844 | 0.5105 [0.5091, 0.5118] | 0.5031 [0.5018, 0.5044] | 0.5128 [0.5114, 0.5141] | 0.5641 [0.5629, 0.5653] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0072 [0.0069, 0.0075] | 0.0133 [0.0128, 0.0138] | 0.0247 [0.0241, 0.0253] |
| emb | 0.0038 [0.0036, 0.0041] | 0.0081 [0.0077, 0.0085] | 0.0165 [0.0160, 0.0170] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 25,105 | 0.0257 [0.0239, 0.0277] | 0.0199 [0.0183, 0.0216] | -0.0058 [-0.0083, -0.0032] | yes |
| warm | 219,542 | 0.0245 [0.0240, 0.0252] | 0.0161 [0.0156, 0.0167] | -0.0084 [-0.0093, -0.0076] | yes |
| head | 803 | 0.0791 [0.0604, 0.0984] | 0.0286 [0.0174, 0.0399] | -0.0504 [-0.0729, -0.0299] | yes |
| tail | 243,844 | 0.0245 [0.0239, 0.0251] | 0.0165 [0.0160, 0.0170] | -0.0080 [-0.0088, -0.0073] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | -0.0072 [-0.0089, -0.0055] | yes |
| emb - bm25 (ndcg@10) | -0.0065 [-0.0079, -0.0052] | yes |
| fused - emb (auc) | +0.0095 [+0.0081, +0.0110] | yes |
| fused - emb (ndcg@10) | +0.0070 [+0.0058, +0.0082] | yes |
| fused - bm25 (auc) | +0.0024 [+0.0017, +0.0030] | yes |
| fused - bm25 (ndcg@10) | +0.0005 [+0.0001, +0.0009] | yes |
| fused+popularity - fused (auc) | +0.0514 [+0.0505, +0.0522] | yes |
| fused+popularity - fused (ndcg@10) | +0.0270 [+0.0263, +0.0276] | yes |
| emb - bm25 (recall@50) | -0.0033 [-0.0038, -0.0029] | yes |
| emb - bm25 (recall@100) | -0.0052 [-0.0058, -0.0046] | yes |
| emb - bm25 (recall@200) | -0.0082 [-0.0090, -0.0074] | yes |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.
