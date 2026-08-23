# mind_small — val

61,894 impressions, 61,894 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5840 [0.5814, 0.5865] | 0.3204 [0.3177, 0.3230] | 0.2924 [0.2897, 0.2954] | 0.3494 [0.3468, 0.3522] |
| emb | 0.6356 [0.6331, 0.6380] | 0.3422 [0.3394, 0.3452] | 0.3202 [0.3172, 0.3231] | 0.3789 [0.3762, 0.3819] |
| fused | 0.6390 [0.6366, 0.6415] | 0.3478 [0.3450, 0.3505] | 0.3248 [0.3218, 0.3277] | 0.3836 [0.3809, 0.3865] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8154 | 15.9960 | 0.0901 |
| emb | 0.7771 | 15.9426 | 0.0880 |
| fused | 0.7755 | 15.9383 | 0.0895 |

## AUC by slice

cold = history length <= 4; head = clicked article with >= 205 train clicks

| slice | n | bm25 | emb | fused |
|---|---|---|---|---|
| cold | 8,196 | 0.5348 [0.5273, 0.5416] | 0.5759 [0.5694, 0.5829] | 0.5764 [0.5696, 0.5832] |
| warm | 53,698 | 0.5915 [0.5889, 0.5941] | 0.6447 [0.6423, 0.6470] | 0.6486 [0.6462, 0.6509] |
| zero_history | 1,503 | 0.4929 [0.4766, 0.5081] | 0.4929 [0.4766, 0.5081] | 0.4929 [0.4766, 0.5081] |
| head | 3,340 | 0.6474 [0.6387, 0.6568] | 0.7040 [0.6958, 0.7124] | 0.7081 [0.6996, 0.7166] |
| tail | 58,554 | 0.5804 [0.5779, 0.5831] | 0.6317 [0.6291, 0.6342] | 0.6351 [0.6325, 0.6377] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0157 [0.0148, 0.0167] | 0.0247 [0.0236, 0.0258] | 0.0371 [0.0357, 0.0384] |
| emb | 0.0131 [0.0123, 0.0139] | 0.0216 [0.0205, 0.0226] | 0.0342 [0.0330, 0.0355] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 8,196 | 0.0217 [0.0188, 0.0249] | 0.0243 [0.0212, 0.0275] | +0.0026 [-0.0003, +0.0054] | no |
| warm | 53,698 | 0.0394 [0.0379, 0.0409] | 0.0357 [0.0343, 0.0372] | -0.0037 [-0.0054, -0.0022] | yes |
| zero_history | 1,503 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | +0.0000 [+0.0000, +0.0000] | no |
| head | 3,340 | 0.0786 [0.0711, 0.0868] | 0.0835 [0.0755, 0.0918] | +0.0049 [-0.0017, +0.0114] | no |
| tail | 58,554 | 0.0347 [0.0333, 0.0361] | 0.0314 [0.0301, 0.0327] | -0.0033 [-0.0048, -0.0018] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | +0.0516 [+0.0488, +0.0543] | yes |
| emb - bm25 (ndcg@10) | +0.0295 [+0.0274, +0.0317] | yes |
| fused - emb (auc) | +0.0034 [+0.0027, +0.0041] | yes |
| fused - emb (ndcg@10) | +0.0047 [+0.0037, +0.0057] | yes |
| fused - bm25 (auc) | +0.0550 [+0.0526, +0.0574] | yes |
| fused - bm25 (ndcg@10) | +0.0342 [+0.0323, +0.0361] | yes |
| emb - bm25 (recall@50) | -0.0027 [-0.0036, -0.0017] | yes |
| emb - bm25 (recall@100) | -0.0031 [-0.0043, -0.0019] | yes |
| emb - bm25 (recall@200) | -0.0029 [-0.0043, -0.0015] | yes |
