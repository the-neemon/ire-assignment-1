# mind_small — val

61,894 impressions, 61,894 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5801 [0.5775, 0.5827] | 0.3169 [0.3142, 0.3194] | 0.2892 [0.2865, 0.2920] | 0.3461 [0.3434, 0.3488] |
| emb | 0.6256 [0.6232, 0.6279] | 0.3362 [0.3337, 0.3389] | 0.3140 [0.3112, 0.3169] | 0.3730 [0.3705, 0.3757] |
| fused | 0.6293 [0.6270, 0.6318] | 0.3430 [0.3403, 0.3457] | 0.3204 [0.3176, 0.3234] | 0.3786 [0.3759, 0.3813] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8174 | 16.0012 | 0.0907 |
| emb | 0.7847 | 15.9808 | 0.0878 |
| fused | 0.7830 | 15.9637 | 0.0888 |

## AUC by slice

cold = history length <= 4; head = clicked article with >= 205 train clicks

| slice | n | bm25 | emb | fused |
|---|---|---|---|---|
| cold | 8,196 | 0.5348 [0.5273, 0.5416] | 0.5709 [0.5641, 0.5778] | 0.5708 [0.5638, 0.5774] |
| warm | 53,698 | 0.5870 [0.5844, 0.5896] | 0.6340 [0.6315, 0.6365] | 0.6383 [0.6357, 0.6407] |
| zero_history | 1,503 | 0.4929 [0.4766, 0.5081] | 0.4929 [0.4766, 0.5081] | 0.4929 [0.4766, 0.5081] |
| head | 3,340 | 0.6412 [0.6320, 0.6505] | 0.6697 [0.6606, 0.6781] | 0.6800 [0.6714, 0.6886] |
| tail | 58,554 | 0.5766 [0.5741, 0.5793] | 0.6231 [0.6207, 0.6254] | 0.6264 [0.6240, 0.6288] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0145 [0.0136, 0.0154] | 0.0237 [0.0227, 0.0249] | 0.0361 [0.0347, 0.0373] |
| emb | 0.0121 [0.0114, 0.0129] | 0.0194 [0.0184, 0.0203] | 0.0317 [0.0305, 0.0331] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 8,196 | 0.0217 [0.0188, 0.0249] | 0.0248 [0.0216, 0.0283] | +0.0031 [+0.0001, +0.0064] | yes |
| warm | 53,698 | 0.0383 [0.0368, 0.0398] | 0.0328 [0.0314, 0.0341] | -0.0055 [-0.0070, -0.0039] | yes |
| zero_history | 1,503 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | +0.0000 [+0.0000, +0.0000] | no |
| head | 3,340 | 0.0758 [0.0685, 0.0842] | 0.0716 [0.0640, 0.0798] | -0.0042 [-0.0101, +0.0017] | no |
| tail | 58,554 | 0.0338 [0.0324, 0.0352] | 0.0294 [0.0281, 0.0308] | -0.0044 [-0.0059, -0.0029] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | +0.0456 [+0.0426, +0.0486] | yes |
| emb - bm25 (ndcg@10) | +0.0269 [+0.0246, +0.0292] | yes |
| fused - emb (auc) | +0.0037 [+0.0030, +0.0045] | yes |
| fused - emb (ndcg@10) | +0.0056 [+0.0046, +0.0066] | yes |
| fused - bm25 (auc) | +0.0493 [+0.0466, +0.0519] | yes |
| fused - bm25 (ndcg@10) | +0.0325 [+0.0307, +0.0346] | yes |
| emb - bm25 (recall@50) | -0.0024 [-0.0032, -0.0014] | yes |
| emb - bm25 (recall@100) | -0.0044 [-0.0055, -0.0031] | yes |
| emb - bm25 (recall@200) | -0.0044 [-0.0057, -0.0029] | yes |
