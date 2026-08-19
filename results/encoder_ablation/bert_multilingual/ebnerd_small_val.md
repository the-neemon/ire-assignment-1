# ebnerd_small — val

64,365 impressions, 64,365 scored (the rest are all-clicked or none-clicked and carry no ranking signal).

## Accuracy (mean [95% bootstrap CI])

| system | AUC | MRR | nDCG@5 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.5205 [0.5177, 0.5230] | 0.3418 [0.3393, 0.3443] | 0.3794 [0.3766, 0.3823] | 0.4607 [0.4585, 0.4630] |
| emb | 0.4857 [0.4832, 0.4880] | 0.3208 [0.3186, 0.3229] | 0.3518 [0.3492, 0.3544] | 0.4387 [0.4365, 0.4408] |
| fused | 0.5210 [0.5181, 0.5236] | 0.3413 [0.3390, 0.3438] | 0.3793 [0.3765, 0.3820] | 0.4604 [0.4582, 0.4625] |
| fused+popularity | 0.5582 [0.5557, 0.5605] | 0.3563 [0.3539, 0.3585] | 0.4002 [0.3975, 0.4028] | 0.4773 [0.4752, 0.4793] |

## Beyond accuracy (top-10)

| system | diversity | novelty | coverage |
|---|---|---|---|
| bm25 | 0.8039 | 16.3525 | 0.1142 |
| emb | 0.8046 | 16.3235 | 0.1135 |
| fused | 0.8037 | 16.3505 | 0.1136 |
| fused+popularity | 0.8036 | 16.3409 | 0.1100 |

## AUC by slice

cold = history length <= 42; head = clicked article with >= 379 train clicks

| slice | n | bm25 | emb | fused | fused+popularity |
|---|---|---|---|---|---|
| cold | 6,463 | 0.5281 [0.5206, 0.5366] | 0.4880 [0.4802, 0.4967] | 0.5300 [0.5226, 0.5379] | 0.5607 [0.5535, 0.5683] |
| warm | 57,902 | 0.5196 [0.5169, 0.5222] | 0.4854 [0.4826, 0.4881] | 0.5200 [0.5174, 0.5225] | 0.5579 [0.5553, 0.5605] |
| head | 1,094 | 0.5091 [0.4903, 0.5266] | 0.4929 [0.4729, 0.5136] | 0.5060 [0.4872, 0.5248] | 0.6022 [0.5857, 0.6177] |
| tail | 63,271 | 0.5207 [0.5180, 0.5233] | 0.4855 [0.4829, 0.4883] | 0.5213 [0.5186, 0.5237] | 0.5574 [0.5549, 0.5598] |

## Candidate generation — recall@K (full-corpus retrieval)

Share of an impression's clicked articles found in the top K drawn from the whole catalogue, not the pool the log showed. Cold-start impressions retrieve nothing and score 0 rather than being excluded.

| system | recall@50 | recall@100 | recall@200 |
|---|---|---|---|
| bm25 | 0.0052 [0.0047, 0.0058] | 0.0110 [0.0101, 0.0118] | 0.0214 [0.0202, 0.0225] |
| emb | 0.0059 [0.0053, 0.0065] | 0.0096 [0.0088, 0.0103] | 0.0162 [0.0153, 0.0171] |

### recall@200 by slice

Which retriever wins is not the same on every slice — see `emb - bm25`, paired within the slice.

| slice | n | bm25 | emb | emb - bm25 | significant |
|---|---|---|---|---|---|
| cold | 6,463 | 0.0284 [0.0245, 0.0323] | 0.0181 [0.0149, 0.0212] | -0.0103 [-0.0154, -0.0051] | yes |
| warm | 57,902 | 0.0206 [0.0195, 0.0218] | 0.0160 [0.0149, 0.0170] | -0.0046 [-0.0061, -0.0032] | yes |
| head | 1,094 | 0.0229 [0.0137, 0.0320] | 0.0069 [0.0023, 0.0123] | -0.0160 [-0.0261, -0.0059] | yes |
| tail | 63,271 | 0.0214 [0.0203, 0.0226] | 0.0164 [0.0154, 0.0174] | -0.0050 [-0.0066, -0.0035] | yes |

## Paired bootstrap comparisons

A difference counts only if its 95% CI excludes zero.

| comparison | difference | significant |
|---|---|---|
| emb - bm25 (auc) | -0.0348 [-0.0383, -0.0310] | yes |
| emb - bm25 (ndcg@10) | -0.0220 [-0.0245, -0.0192] | yes |
| fused - emb (auc) | +0.0353 [+0.0318, +0.0386] | yes |
| fused - emb (ndcg@10) | +0.0216 [+0.0189, +0.0240] | yes |
| fused - bm25 (auc) | +0.0005 [-0.0003, +0.0015] | no |
| fused - bm25 (ndcg@10) | -0.0004 [-0.0008, +0.0001] | no |
| fused+popularity - fused (auc) | +0.0372 [+0.0353, +0.0390] | yes |
| fused+popularity - fused (ndcg@10) | +0.0169 [+0.0156, +0.0182] | yes |
| emb - bm25 (recall@50) | +0.0006 [-0.0002, +0.0014] | no |
| emb - bm25 (recall@100) | -0.0014 [-0.0025, -0.0003] | yes |
| emb - bm25 (recall@200) | -0.0052 [-0.0066, -0.0037] | yes |

## Serving-availability

`fused+popularity` adds article lifetime popularity (`total_inviews`), a corpus-wide aggregate that embeds the future and is unavailable at serving time. Every other row uses only features computable strictly before the impression. The paired comparison `fused+popularity - fused` above is the cost of honesty.
