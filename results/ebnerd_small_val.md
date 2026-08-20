# ebnerd_small — val

64,365 impressions, 64,365 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5205 [0.5177, 0.5230] | 0.3418 [0.3393, 0.3443] | 0.3794 [0.3766, 0.3823] | 0.4607 [0.4585, 0.4630] |
| emb | 0.5506 [0.5480, 0.5531] | 0.3594 [0.3569, 0.3618] | 0.4017 [0.3989, 0.4045] | 0.4778 [0.4756, 0.4799] |
| fused | 0.5528 [0.5503, 0.5552] | 0.3628 [0.3604, 0.3651] | 0.4043 [0.4014, 0.4069] | 0.4807 [0.4786, 0.4828] |
| fused+popularity | 0.5784 [0.5758, 0.5807] | 0.3707 [0.3683, 0.3730] | 0.4184 [0.4157, 0.4210] | 0.4910 [0.4888, 0.4931] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8039 | 16.3525 | 0.1142 |
| emb | 0.7906 | 16.3992 | 0.1130 |
| fused | 0.7916 | 16.3909 | 0.1131 |
| fused+popularity | 0.7963 | 16.3572 | 0.1099 |

## AUC by slice

cold = history length <= 42; head = clicked article with >= 379 train clicks

| slice | n | bm25 | emb | fused | fused+popularity |
|---|---|---|---|---|---|
| cold | 6,463 | 0.5281 [0.5206, 0.5366] | 0.5567 [0.5492, 0.5643] | 0.5612 [0.5534, 0.5688] | 0.5843 [0.5768, 0.5918] |
| warm | 57,902 | 0.5196 [0.5169, 0.5222] | 0.5499 [0.5473, 0.5526] | 0.5518 [0.5491, 0.5545] | 0.5778 [0.5752, 0.5803] |
| head | 1,094 | 0.5091 [0.4903, 0.5266] | 0.6855 [0.6682, 0.7018] | 0.6638 [0.6470, 0.6799] | 0.7192 [0.7030, 0.7337] |
| tail | 63,271 | 0.5207 [0.5180, 0.5233] | 0.5483 [0.5457, 0.5507] | 0.5509 [0.5483, 0.5534] | 0.5760 [0.5735, 0.5784] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0052 [0.0047, 0.0058] | 0.0110 [0.0101, 0.0118] | 0.0214 [0.0202, 0.0225] |
| emb | 0.0045 [0.0040, 0.0050] | 0.0097 [0.0089, 0.0105] | 0.0198 [0.0187, 0.0208] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 6,463 | 0.0284 [0.0245, 0.0323] | 0.0256 [0.0222, 0.0295] | -0.0028 [-0.0080, +0.0022] | no |
| warm | 57,902 | 0.0206 [0.0195, 0.0218] | 0.0191 [0.0180, 0.0202] | -0.0015 [-0.0030, -0.0000] | yes |
| head | 1,094 | 0.0229 [0.0137, 0.0320] | 0.0311 [0.0210, 0.0412] | +0.0082 [-0.0037, +0.0201] | no |
| tail | 63,271 | 0.0214 [0.0203, 0.0226] | 0.0196 [0.0185, 0.0206] | -0.0018 [-0.0034, -0.0004] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | +0.0301 [+0.0269, +0.0336] | yes |
| emb - bm25 (ndcg@10) | +0.0171 [+0.0145, +0.0198] | yes |
| fused - emb (auc) | +0.0022 [+0.0010, +0.0033] | yes |
| fused - emb (ndcg@10) | +0.0029 [+0.0017, +0.0041] | yes |
| fused - bm25 (auc) | +0.0323 [+0.0296, +0.0353] | yes |
| fused - bm25 (ndcg@10) | +0.0200 [+0.0180, +0.0221] | yes |
| fused+popularity - fused (auc) | +0.0257 [+0.0239, +0.0272] | yes |
| fused+popularity - fused (ndcg@10) | +0.0103 [+0.0089, +0.0116] | yes |
| emb - bm25 (recall@50) | -0.0008 [-0.0015, +0.0000] | no |
| emb - bm25 (recall@100) | -0.0013 [-0.0024, -0.0002] | yes |
| emb - bm25 (recall@200) | -0.0016 [-0.0030, -0.0002] | yes |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.
