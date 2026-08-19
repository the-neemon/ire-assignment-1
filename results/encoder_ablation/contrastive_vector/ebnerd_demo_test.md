# ebnerd_demo — test

25,356 impressions, 25,356 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5125 [0.5088, 0.5166] | 0.3273 [0.3241, 0.3308] | 0.3591 [0.3551, 0.3632] | 0.4418 [0.4387, 0.4453] |
| emb | 0.5418 [0.5377, 0.5457] | 0.3489 [0.3451, 0.3525] | 0.3830 [0.3786, 0.3870] | 0.4629 [0.4592, 0.4664] |
| fused | 0.5384 [0.5343, 0.5423] | 0.3455 [0.3420, 0.3490] | 0.3803 [0.3760, 0.3845] | 0.4600 [0.4566, 0.4634] |
| fused+popularity | 0.5793 [0.5755, 0.5831] | 0.3664 [0.3629, 0.3702] | 0.4086 [0.4043, 0.4129] | 0.4823 [0.4790, 0.4858] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.7964 | 13.9755 | 0.2178 |
| emb | 0.7801 | 13.9926 | 0.2169 |
| fused | 0.7820 | 13.9901 | 0.2177 |
| fused+popularity | 0.7882 | 13.9802 | 0.2120 |

## AUC by slice

cold = history length <= 40; head = clicked article with >= 72 train clicks

| slice | n | bm25 | emb | fused | fused+popularity |
|---|---|---|---|---|---|
| cold | 2,725 | 0.5102 [0.4987, 0.5225] | 0.5438 [0.5314, 0.5560] | 0.5447 [0.5329, 0.5573] | 0.5954 [0.5835, 0.6073] |
| warm | 22,631 | 0.5128 [0.5087, 0.5171] | 0.5416 [0.5373, 0.5457] | 0.5376 [0.5333, 0.5420] | 0.5773 [0.5729, 0.5816] |
| head | 57 | 0.5908 [0.5141, 0.6607] | 0.6279 [0.5581, 0.6930] | 0.6368 [0.5577, 0.7084] | 0.8116 [0.7593, 0.8596] |
| tail | 25,299 | 0.5123 [0.5085, 0.5165] | 0.5416 [0.5376, 0.5456] | 0.5382 [0.5341, 0.5422] | 0.5787 [0.5748, 0.5825] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0108 [0.0095, 0.0122] | 0.0216 [0.0199, 0.0234] | 0.0390 [0.0368, 0.0413] |
| emb | 0.0110 [0.0097, 0.0123] | 0.0245 [0.0226, 0.0263] | 0.0462 [0.0435, 0.0488] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 2,725 | 0.0360 [0.0294, 0.0429] | 0.0448 [0.0371, 0.0532] | +0.0088 [-0.0004, +0.0183] | no |
| warm | 22,631 | 0.0394 [0.0368, 0.0420] | 0.0463 [0.0436, 0.0489] | +0.0069 [+0.0035, +0.0104] | yes |
| head | 57 | 0.1078 [0.0351, 0.1930] | 0.0351 [0.0000, 0.1053] | -0.0727 [-0.1629, +0.0175] | no |
| tail | 25,299 | 0.0389 [0.0366, 0.0411] | 0.0462 [0.0436, 0.0489] | +0.0073 [+0.0041, +0.0106] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | +0.0293 [+0.0237, +0.0343] | yes |
| emb - bm25 (ndcg@10) | +0.0210 [+0.0169, +0.0247] | yes |
| fused - emb (auc) | -0.0035 [-0.0054, -0.0016] | yes |
| fused - emb (ndcg@10) | -0.0028 [-0.0047, -0.0009] | yes |
| fused - bm25 (auc) | +0.0259 [+0.0211, +0.0300] | yes |
| fused - bm25 (ndcg@10) | +0.0182 [+0.0149, +0.0212] | yes |
| fused+popularity - fused (auc) | +0.0409 [+0.0380, +0.0437] | yes |
| fused+popularity - fused (ndcg@10) | +0.0223 [+0.0200, +0.0245] | yes |
| emb - bm25 (recall@50) | +0.0001 [-0.0017, +0.0018] | no |
| emb - bm25 (recall@100) | +0.0029 [+0.0005, +0.0053] | yes |
| emb - bm25 (recall@200) | +0.0071 [+0.0040, +0.0104] | yes |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.
