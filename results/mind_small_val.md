# mind_small — val

61,894 impressions, 61,894 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5801 [0.5775, 0.5827] | 0.3169 [0.3142, 0.3194] | 0.2892 [0.2865, 0.2920] | 0.3461 [0.3434, 0.3488] |
| emb | 0.6338 [0.6312, 0.6362] | 0.3411 [0.3382, 0.3440] | 0.3188 [0.3159, 0.3216] | 0.3776 [0.3748, 0.3803] |
| fused | 0.6364 [0.6341, 0.6388] | 0.3449 [0.3423, 0.3477] | 0.3225 [0.3198, 0.3254] | 0.3811 [0.3784, 0.3840] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8174 | 16.0012 | 0.0907 |
| emb | 0.7783 | 15.9435 | 0.0883 |
| fused | 0.7765 | 15.9396 | 0.0893 |

## AUC by slice

cold = history length <= 4; head = clicked article with >= 205 train clicks

| slice | n | bm25 | emb | fused |
|---|---|---|---|---|
| cold | 8,196 | 0.5348 [0.5273, 0.5416] | 0.5759 [0.5694, 0.5829] | 0.5761 [0.5692, 0.5828] |
| warm | 53,698 | 0.5870 [0.5844, 0.5896] | 0.6426 [0.6403, 0.6450] | 0.6456 [0.6432, 0.6480] |
| zero_history | 1,503 | 0.4929 [0.4766, 0.5081] | 0.4929 [0.4766, 0.5081] | 0.4929 [0.4766, 0.5081] |
| head | 3,340 | 0.6412 [0.6320, 0.6505] | 0.7030 [0.6947, 0.7114] | 0.7059 [0.6976, 0.7147] |
| tail | 58,554 | 0.5766 [0.5741, 0.5793] | 0.6299 [0.6274, 0.6324] | 0.6324 [0.6299, 0.6350] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0145 [0.0136, 0.0154] | 0.0237 [0.0227, 0.0249] | 0.0361 [0.0347, 0.0373] |
| emb | 0.0131 [0.0123, 0.0139] | 0.0215 [0.0205, 0.0225] | 0.0343 [0.0330, 0.0356] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 8,196 | 0.0217 [0.0188, 0.0249] | 0.0243 [0.0212, 0.0275] | +0.0026 [-0.0003, +0.0054] | no |
| warm | 53,698 | 0.0383 [0.0368, 0.0398] | 0.0358 [0.0343, 0.0372] | -0.0025 [-0.0042, -0.0009] | yes |
| zero_history | 1,503 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | +0.0000 [+0.0000, +0.0000] | no |
| head | 3,340 | 0.0758 [0.0685, 0.0842] | 0.0825 [0.0745, 0.0910] | +0.0067 [+0.0002, +0.0134] | yes |
| tail | 58,554 | 0.0338 [0.0324, 0.0352] | 0.0315 [0.0302, 0.0329] | -0.0023 [-0.0038, -0.0008] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | +0.0537 [+0.0510, +0.0566] | yes |
| emb - bm25 (ndcg@10) | +0.0315 [+0.0293, +0.0337] | yes |
| fused - emb (auc) | +0.0026 [+0.0020, +0.0032] | yes |
| fused - emb (ndcg@10) | +0.0035 [+0.0027, +0.0044] | yes |
| fused - bm25 (auc) | +0.0564 [+0.0538, +0.0590] | yes |
| fused - bm25 (ndcg@10) | +0.0350 [+0.0330, +0.0369] | yes |
| emb - bm25 (recall@50) | -0.0015 [-0.0024, -0.0006] | yes |
| emb - bm25 (recall@100) | -0.0022 [-0.0034, -0.0011] | yes |
| emb - bm25 (recall@200) | -0.0018 [-0.0033, -0.0004] | yes |
