# mind_small — test

73,152 impressions, 73,152 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5645 [0.5624, 0.5668] | 0.3077 [0.3054, 0.3101] | 0.2838 [0.2813, 0.2865] | 0.3451 [0.3429, 0.3476] |
| emb | 0.6339 [0.6319, 0.6360] | 0.3486 [0.3462, 0.3512] | 0.3315 [0.3289, 0.3341] | 0.3911 [0.3889, 0.3936] |
| fused | 0.6353 [0.6334, 0.6375] | 0.3520 [0.3496, 0.3544] | 0.3343 [0.3318, 0.3370] | 0.3936 [0.3913, 0.3961] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8449 | 16.9256 | 0.0535 |
| emb | 0.8226 | 16.9257 | 0.0523 |
| fused | 0.8195 | 16.9240 | 0.0528 |

## AUC by slice

cold = history length <= 3; head = clicked article with >= 152 train clicks

| slice | n | bm25 | emb | fused |
|---|---|---|---|---|
| cold | 7,529 | 0.5196 [0.5127, 0.5266] | 0.5618 [0.5547, 0.5681] | 0.5606 [0.5534, 0.5670] |
| warm | 65,623 | 0.5697 [0.5674, 0.5722] | 0.6422 [0.6399, 0.6444] | 0.6438 [0.6416, 0.6461] |
| zero_history | 2,214 | 0.5125 [0.5003, 0.5253] | 0.5125 [0.5003, 0.5253] | 0.5125 [0.5003, 0.5253] |
| head | 860 | 0.6217 [0.6065, 0.6376] | 0.6199 [0.6037, 0.6351] | 0.6312 [0.6149, 0.6468] |
| tail | 72,292 | 0.5639 [0.5617, 0.5662] | 0.6340 [0.6321, 0.6363] | 0.6353 [0.6334, 0.6375] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0060 [0.0056, 0.0065] | 0.0124 [0.0117, 0.0132] | 0.0220 [0.0210, 0.0230] |
| emb | 0.0076 [0.0070, 0.0082] | 0.0138 [0.0130, 0.0146] | 0.0239 [0.0229, 0.0250] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 7,529 | 0.0129 [0.0107, 0.0152] | 0.0155 [0.0129, 0.0183] | +0.0026 [-0.0002, +0.0052] | no |
| warm | 65,623 | 0.0231 [0.0220, 0.0242] | 0.0249 [0.0239, 0.0261] | +0.0018 [+0.0006, +0.0031] | yes |
| zero_history | 2,214 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | +0.0000 [+0.0000, +0.0000] | no |
| head | 860 | 0.0868 [0.0705, 0.1037] | 0.0985 [0.0808, 0.1160] | +0.0118 [+0.0000, +0.0232] | yes |
| tail | 72,292 | 0.0213 [0.0203, 0.0223] | 0.0230 [0.0221, 0.0241] | +0.0018 [+0.0006, +0.0029] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | +0.0693 [+0.0668, +0.0718] | yes |
| emb - bm25 (ndcg@10) | +0.0460 [+0.0437, +0.0482] | yes |
| fused - emb (auc) | +0.0014 [+0.0009, +0.0020] | yes |
| fused - emb (ndcg@10) | +0.0025 [+0.0016, +0.0033] | yes |
| fused - bm25 (auc) | +0.0707 [+0.0684, +0.0730] | yes |
| fused - bm25 (ndcg@10) | +0.0485 [+0.0467, +0.0504] | yes |
| emb - bm25 (recall@50) | +0.0015 [+0.0009, +0.0021] | yes |
| emb - bm25 (recall@100) | +0.0013 [+0.0005, +0.0022] | yes |
| emb - bm25 (recall@200) | +0.0019 [+0.0008, +0.0031] | yes |
