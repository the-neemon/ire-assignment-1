# ebnerd_demo — test

25,356 impressions, 25,356 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5125 [0.5088, 0.5166] | 0.3273 [0.3241, 0.3308] | 0.3591 [0.3551, 0.3632] | 0.4418 [0.4387, 0.4453] |
| emb | 0.5041 [0.5000, 0.5079] | 0.3147 [0.3116, 0.3181] | 0.3457 [0.3417, 0.3496] | 0.4317 [0.4286, 0.4350] |
| fused | 0.5146 [0.5107, 0.5186] | 0.3260 [0.3228, 0.3296] | 0.3584 [0.3544, 0.3626] | 0.4424 [0.4392, 0.4457] |
| fused+popularity | 0.5649 [0.5611, 0.5689] | 0.3505 [0.3471, 0.3541] | 0.3906 [0.3866, 0.3947] | 0.4683 [0.4652, 0.4715] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.7964 | 13.9755 | 0.2178 |
| emb | 0.7929 | 13.9747 | 0.2165 |
| fused | 0.7947 | 13.9730 | 0.2171 |
| fused+popularity | 0.7953 | 13.9715 | 0.2115 |

## AUC by slice

cold = history length <= 40; head = clicked article with >= 72 train clicks

| slice | n | bm25 | emb | fused | fused+popularity |
|---|---|---|---|---|---|
| cold | 2,725 | 0.5102 [0.4987, 0.5225] | 0.5023 [0.4902, 0.5138] | 0.5107 [0.4983, 0.5229] | 0.5740 [0.5622, 0.5857] |
| warm | 22,631 | 0.5128 [0.5087, 0.5171] | 0.5043 [0.5003, 0.5088] | 0.5150 [0.5108, 0.5194] | 0.5638 [0.5595, 0.5678] |
| head | 57 | 0.5908 [0.5141, 0.6607] | 0.6807 [0.6259, 0.7325] | 0.6521 [0.5839, 0.7157] | 0.7961 [0.7479, 0.8412] |
| tail | 25,299 | 0.5123 [0.5085, 0.5165] | 0.5037 [0.4998, 0.5079] | 0.5143 [0.5103, 0.5183] | 0.5644 [0.5606, 0.5681] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0108 [0.0095, 0.0122] | 0.0216 [0.0199, 0.0234] | 0.0390 [0.0368, 0.0413] |
| emb | 0.0064 [0.0055, 0.0074] | 0.0133 [0.0119, 0.0146] | 0.0270 [0.0252, 0.0289] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 2,725 | 0.0360 [0.0294, 0.0429] | 0.0257 [0.0194, 0.0316] | -0.0103 [-0.0183, -0.0018] | yes |
| warm | 22,631 | 0.0394 [0.0368, 0.0420] | 0.0272 [0.0253, 0.0294] | -0.0122 [-0.0156, -0.0090] | yes |
| head | 57 | 0.1078 [0.0351, 0.1930] | 0.0351 [0.0000, 0.0877] | -0.0727 [-0.1604, +0.0000] | no |
| tail | 25,299 | 0.0389 [0.0366, 0.0411] | 0.0270 [0.0250, 0.0290] | -0.0118 [-0.0147, -0.0089] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | -0.0085 [-0.0140, -0.0033] | yes |
| emb - bm25 (ndcg@10) | -0.0101 [-0.0139, -0.0064] | yes |
| fused - emb (auc) | +0.0105 [+0.0065, +0.0147] | yes |
| fused - emb (ndcg@10) | +0.0106 [+0.0075, +0.0139] | yes |
| fused - bm25 (auc) | +0.0020 [-0.0003, +0.0044] | no |
| fused - bm25 (ndcg@10) | +0.0005 [-0.0010, +0.0020] | no |
| fused+popularity - fused (auc) | +0.0503 [+0.0475, +0.0532] | yes |
| fused+popularity - fused (ndcg@10) | +0.0259 [+0.0238, +0.0280] | yes |
| emb - bm25 (recall@50) | -0.0044 [-0.0061, -0.0028] | yes |
| emb - bm25 (recall@100) | -0.0083 [-0.0106, -0.0062] | yes |
| emb - bm25 (recall@200) | -0.0120 [-0.0148, -0.0090] | yes |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.
