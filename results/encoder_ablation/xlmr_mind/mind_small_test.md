# mind_small — test

73,152 impressions, 73,152 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5645 [0.5624, 0.5668] | 0.3077 [0.3054, 0.3101] | 0.2838 [0.2813, 0.2865] | 0.3451 [0.3429, 0.3476] |
| emb | 0.6364 [0.6343, 0.6385] | 0.3535 [0.3512, 0.3560] | 0.3361 [0.3335, 0.3387] | 0.3953 [0.3930, 0.3979] |
| fused | 0.6367 [0.6346, 0.6390] | 0.3547 [0.3523, 0.3572] | 0.3365 [0.3339, 0.3392] | 0.3962 [0.3939, 0.3988] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8449 | 16.9256 | 0.0535 |
| emb | 0.8228 | 16.9087 | 0.0523 |
| fused | 0.8223 | 16.9117 | 0.0533 |

## AUC by slice

cold = history length <= 3; head = clicked article with >= 152 train clicks

| slice | n | bm25 | emb | fused |
|---|---|---|---|---|
| cold | 7,529 | 0.5196 [0.5127, 0.5266] | 0.5702 [0.5626, 0.5767] | 0.5665 [0.5594, 0.5729] |
| warm | 65,623 | 0.5697 [0.5674, 0.5722] | 0.6440 [0.6419, 0.6464] | 0.6447 [0.6426, 0.6472] |
| zero_history | 2,214 | 0.5125 [0.5003, 0.5253] | 0.5125 [0.5003, 0.5253] | 0.5125 [0.5003, 0.5253] |
| head | 860 | 0.6217 [0.6065, 0.6376] | 0.6705 [0.6568, 0.6848] | 0.6764 [0.6624, 0.6902] |
| tail | 72,292 | 0.5639 [0.5617, 0.5662] | 0.6360 [0.6338, 0.6382] | 0.6362 [0.6341, 0.6383] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0060 [0.0056, 0.0065] | 0.0124 [0.0117, 0.0132] | 0.0220 [0.0210, 0.0230] |
| emb | 0.0067 [0.0062, 0.0072] | 0.0125 [0.0118, 0.0132] | 0.0233 [0.0224, 0.0244] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 7,529 | 0.0129 [0.0107, 0.0152] | 0.0154 [0.0129, 0.0178] | +0.0025 [-0.0005, +0.0053] | no |
| warm | 65,623 | 0.0231 [0.0220, 0.0242] | 0.0242 [0.0231, 0.0253] | +0.0011 [-0.0001, +0.0023] | no |
| zero_history | 2,214 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | +0.0000 [+0.0000, +0.0000] | no |
| head | 860 | 0.0868 [0.0705, 0.1037] | 0.0981 [0.0806, 0.1163] | +0.0114 [-0.0003, +0.0240] | no |
| tail | 72,292 | 0.0213 [0.0203, 0.0223] | 0.0224 [0.0214, 0.0234] | +0.0011 [-0.0000, +0.0022] | no |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | +0.0718 [+0.0691, +0.0744] | yes |
| emb - bm25 (ndcg@10) | +0.0502 [+0.0480, +0.0524] | yes |
| fused - emb (auc) | +0.0003 [-0.0004, +0.0010] | no |
| fused - emb (ndcg@10) | +0.0009 [+0.0000, +0.0019] | yes |
| fused - bm25 (auc) | +0.0721 [+0.0698, +0.0744] | yes |
| fused - bm25 (ndcg@10) | +0.0511 [+0.0493, +0.0529] | yes |
| emb - bm25 (recall@50) | +0.0006 [+0.0000, +0.0012] | yes |
| emb - bm25 (recall@100) | +0.0000 [-0.0008, +0.0009] | no |
| emb - bm25 (recall@200) | +0.0013 [+0.0002, +0.0024] | yes |
