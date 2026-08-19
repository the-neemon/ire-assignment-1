# ebnerd_small — test

244,647 impressions, 244,647 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5107 [0.5094, 0.5120] | 0.3257 [0.3245, 0.3269] | 0.3577 [0.3563, 0.3591] | 0.4409 [0.4397, 0.4421] |
| emb | 0.4948 [0.4935, 0.4961] | 0.3216 [0.3204, 0.3227] | 0.3503 [0.3491, 0.3517] | 0.4355 [0.4345, 0.4367] |
| fused | 0.5110 [0.5096, 0.5122] | 0.3255 [0.3243, 0.3266] | 0.3579 [0.3565, 0.3592] | 0.4408 [0.4396, 0.4419] |
| fused+popularity | 0.5612 [0.5599, 0.5624] | 0.3496 [0.3484, 0.3508] | 0.3893 [0.3879, 0.3907] | 0.4667 [0.4655, 0.4678] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.7968 | 16.9664 | 0.2067 |
| emb | 0.8004 | 16.9620 | 0.2057 |
| fused | 0.7969 | 16.9656 | 0.2060 |
| fused+popularity | 0.7969 | 16.9969 | 0.1969 |

## AUC by slice

cold = history length <= 34; head = clicked article with >= 349 train clicks

| slice | n | bm25 | emb | fused | fused+popularity |
|---|---|---|---|---|---|
| cold | 25,105 | 0.5103 [0.5059, 0.5142] | 0.5003 [0.4963, 0.5045] | 0.5122 [0.5080, 0.5162] | 0.5664 [0.5626, 0.5702] |
| warm | 219,542 | 0.5108 [0.5094, 0.5123] | 0.4941 [0.4927, 0.4955] | 0.5108 [0.5095, 0.5123] | 0.5606 [0.5593, 0.5619] |
| head | 803 | 0.5852 [0.5626, 0.6066] | 0.5924 [0.5698, 0.6144] | 0.5919 [0.5698, 0.6121] | 0.6678 [0.6482, 0.6880] |
| tail | 243,844 | 0.5105 [0.5091, 0.5118] | 0.4944 [0.4931, 0.4958] | 0.5107 [0.5094, 0.5121] | 0.5608 [0.5596, 0.5621] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0072 [0.0069, 0.0075] | 0.0133 [0.0128, 0.0138] | 0.0247 [0.0241, 0.0253] |
| emb | 0.0044 [0.0042, 0.0047] | 0.0088 [0.0085, 0.0092] | 0.0179 [0.0174, 0.0184] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 25,105 | 0.0257 [0.0239, 0.0277] | 0.0189 [0.0172, 0.0206] | -0.0068 [-0.0094, -0.0042] | yes |
| warm | 219,542 | 0.0245 [0.0240, 0.0252] | 0.0178 [0.0172, 0.0183] | -0.0068 [-0.0076, -0.0060] | yes |
| head | 803 | 0.0791 [0.0604, 0.0984] | 0.0149 [0.0075, 0.0237] | -0.0641 [-0.0847, -0.0423] | yes |
| tail | 243,844 | 0.0245 [0.0239, 0.0251] | 0.0179 [0.0174, 0.0184] | -0.0066 [-0.0074, -0.0058] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | -0.0159 [-0.0177, -0.0141] | yes |
| emb - bm25 (ndcg@10) | -0.0054 [-0.0068, -0.0040] | yes |
| fused - emb (auc) | +0.0162 [+0.0145, +0.0178] | yes |
| fused - emb (ndcg@10) | +0.0053 [+0.0039, +0.0066] | yes |
| fused - bm25 (auc) | +0.0003 [-0.0002, +0.0008] | no |
| fused - bm25 (ndcg@10) | -0.0001 [-0.0003, +0.0001] | no |
| fused+popularity - fused (auc) | +0.0502 [+0.0493, +0.0511] | yes |
| fused+popularity - fused (ndcg@10) | +0.0259 [+0.0252, +0.0265] | yes |
| emb - bm25 (recall@50) | -0.0028 [-0.0032, -0.0023] | yes |
| emb - bm25 (recall@100) | -0.0045 [-0.0051, -0.0039] | yes |
| emb - bm25 (recall@200) | -0.0068 [-0.0076, -0.0059] | yes |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.
