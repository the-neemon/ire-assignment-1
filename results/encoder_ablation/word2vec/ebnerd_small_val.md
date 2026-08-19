# ebnerd_small — val

64,365 impressions, 64,365 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5205 [0.5177, 0.5230] | 0.3418 [0.3393, 0.3443] | 0.3794 [0.3766, 0.3823] | 0.4607 [0.4585, 0.4630] |
| emb | 0.5098 [0.5073, 0.5124] | 0.3385 [0.3362, 0.3409] | 0.3708 [0.3682, 0.3736] | 0.4550 [0.4529, 0.4573] |
| fused | 0.5236 [0.5208, 0.5262] | 0.3427 [0.3404, 0.3450] | 0.3810 [0.3782, 0.3838] | 0.4616 [0.4593, 0.4638] |
| fused+popularity | 0.5611 [0.5586, 0.5635] | 0.3575 [0.3551, 0.3597] | 0.4023 [0.3996, 0.4050] | 0.4787 [0.4766, 0.4808] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8039 | 16.3525 | 0.1142 |
| emb | 0.7995 | 16.3308 | 0.1146 |
| fused | 0.8030 | 16.3414 | 0.1140 |
| fused+popularity | 0.8031 | 16.3388 | 0.1098 |

## AUC by slice

cold = history length <= 42; head = clicked article with >= 379 train clicks

| slice | n | bm25 | emb | fused | fused+popularity |
|---|---|---|---|---|---|
| cold | 6,463 | 0.5281 [0.5206, 0.5366] | 0.5158 [0.5077, 0.5241] | 0.5334 [0.5264, 0.5416] | 0.5635 [0.5565, 0.5709] |
| warm | 57,902 | 0.5196 [0.5169, 0.5222] | 0.5091 [0.5065, 0.5116] | 0.5225 [0.5199, 0.5250] | 0.5609 [0.5584, 0.5633] |
| head | 1,094 | 0.5091 [0.4903, 0.5266] | 0.6256 [0.6046, 0.6454] | 0.5408 [0.5222, 0.5585] | 0.6285 [0.6131, 0.6426] |
| tail | 63,271 | 0.5207 [0.5180, 0.5233] | 0.5078 [0.5050, 0.5104] | 0.5233 [0.5208, 0.5258] | 0.5600 [0.5576, 0.5624] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0052 [0.0047, 0.0058] | 0.0110 [0.0101, 0.0118] | 0.0214 [0.0202, 0.0225] |
| emb | 0.0025 [0.0022, 0.0029] | 0.0065 [0.0059, 0.0071] | 0.0153 [0.0144, 0.0163] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 6,463 | 0.0284 [0.0245, 0.0323] | 0.0158 [0.0130, 0.0189] | -0.0127 [-0.0176, -0.0080] | yes |
| warm | 57,902 | 0.0206 [0.0195, 0.0218] | 0.0153 [0.0142, 0.0162] | -0.0054 [-0.0069, -0.0039] | yes |
| head | 1,094 | 0.0229 [0.0137, 0.0320] | 0.1060 [0.0868, 0.1243] | +0.0832 [+0.0631, +0.1042] | yes |
| tail | 63,271 | 0.0214 [0.0203, 0.0226] | 0.0137 [0.0128, 0.0146] | -0.0076 [-0.0092, -0.0063] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | -0.0107 [-0.0140, -0.0071] | yes |
| emb - bm25 (ndcg@10) | -0.0057 [-0.0082, -0.0031] | yes |
| fused - emb (auc) | +0.0138 [+0.0106, +0.0167] | yes |
| fused - emb (ndcg@10) | +0.0066 [+0.0041, +0.0089] | yes |
| fused - bm25 (auc) | +0.0031 [+0.0020, +0.0043] | yes |
| fused - bm25 (ndcg@10) | +0.0009 [+0.0002, +0.0016] | yes |
| fused+popularity - fused (auc) | +0.0375 [+0.0357, +0.0394] | yes |
| fused+popularity - fused (ndcg@10) | +0.0171 [+0.0158, +0.0185] | yes |
| emb - bm25 (recall@50) | -0.0027 [-0.0034, -0.0020] | yes |
| emb - bm25 (recall@100) | -0.0045 [-0.0055, -0.0034] | yes |
| emb - bm25 (recall@200) | -0.0061 [-0.0075, -0.0046] | yes |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.
