# ebnerd_small — test

244,647 impressions, 244,647 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5107 [0.5094, 0.5120] | 0.3257 [0.3245, 0.3269] | 0.3577 [0.3563, 0.3591] | 0.4409 [0.4397, 0.4421] |
| emb | 0.5305 [0.5293, 0.5319] | 0.3365 [0.3354, 0.3377] | 0.3711 [0.3697, 0.3725] | 0.4518 [0.4507, 0.4530] |
| fused | 0.5291 [0.5277, 0.5304] | 0.3360 [0.3348, 0.3372] | 0.3705 [0.3690, 0.3719] | 0.4512 [0.4500, 0.4524] |
| fused+popularity | 0.5731 [0.5718, 0.5744] | 0.3573 [0.3560, 0.3585] | 0.3991 [0.3976, 0.4005] | 0.4745 [0.4733, 0.4756] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.7968 | 16.9664 | 0.2067 |
| emb | 0.7911 | 16.9687 | 0.2058 |
| fused | 0.7922 | 16.9651 | 0.2059 |
| fused+popularity | 0.7948 | 16.9934 | 0.1978 |

## AUC by slice

cold = history length <= 34; head = clicked article with >= 349 train clicks

| slice | n | bm25 | emb | fused | fused+popularity |
|---|---|---|---|---|---|
| cold | 25,105 | 0.5103 [0.5059, 0.5142] | 0.5341 [0.5303, 0.5383] | 0.5321 [0.5281, 0.5359] | 0.5794 [0.5757, 0.5833] |
| warm | 219,542 | 0.5108 [0.5094, 0.5123] | 0.5301 [0.5287, 0.5315] | 0.5288 [0.5274, 0.5301] | 0.5724 [0.5711, 0.5738] |
| head | 803 | 0.5852 [0.5626, 0.6066] | 0.6801 [0.6597, 0.6995] | 0.6762 [0.6537, 0.6961] | 0.7177 [0.6959, 0.7367] |
| tail | 243,844 | 0.5105 [0.5091, 0.5118] | 0.5300 [0.5287, 0.5313] | 0.5286 [0.5273, 0.5299] | 0.5726 [0.5713, 0.5739] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0072 [0.0069, 0.0075] | 0.0133 [0.0128, 0.0138] | 0.0247 [0.0241, 0.0253] |
| emb | 0.0043 [0.0041, 0.0046] | 0.0081 [0.0077, 0.0085] | 0.0150 [0.0145, 0.0155] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 25,105 | 0.0257 [0.0239, 0.0277] | 0.0169 [0.0153, 0.0186] | -0.0088 [-0.0111, -0.0066] | yes |
| warm | 219,542 | 0.0245 [0.0240, 0.0252] | 0.0147 [0.0142, 0.0153] | -0.0098 [-0.0106, -0.0091] | yes |
| head | 803 | 0.0791 [0.0604, 0.0984] | 0.0598 [0.0448, 0.0772] | -0.0193 [-0.0405, +0.0000] | no |
| tail | 243,844 | 0.0245 [0.0239, 0.0251] | 0.0148 [0.0143, 0.0153] | -0.0097 [-0.0105, -0.0089] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | +0.0198 [+0.0182, +0.0215] | yes |
| emb - bm25 (ndcg@10) | +0.0109 [+0.0097, +0.0122] | yes |
| fused - emb (auc) | -0.0014 [-0.0022, -0.0007] | yes |
| fused - emb (ndcg@10) | -0.0006 [-0.0013, +0.0001] | no |
| fused - bm25 (auc) | +0.0184 [+0.0172, +0.0195] | yes |
| fused - bm25 (ndcg@10) | +0.0103 [+0.0095, +0.0112] | yes |
| fused+popularity - fused (auc) | +0.0440 [+0.0431, +0.0449] | yes |
| fused+popularity - fused (ndcg@10) | +0.0232 [+0.0226, +0.0239] | yes |
| emb - bm25 (recall@50) | -0.0029 [-0.0032, -0.0024] | yes |
| emb - bm25 (recall@100) | -0.0052 [-0.0058, -0.0047] | yes |
| emb - bm25 (recall@200) | -0.0097 [-0.0105, -0.0090] | yes |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.
