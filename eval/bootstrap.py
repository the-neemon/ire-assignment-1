"""Bootstrap confidence intervals over per-impression metric values.

Resampling is over impressions, which is the unit that is (approximately) independent
here — resampling candidates within an impression would understate the variance badly.

`paired` reuses the *same* resampled indices for both systems. That is the whole point: two
systems evaluated on the same impressions have correlated errors, so an unpaired comparison
of two independent intervals is far too conservative and will hide real differences.
"""

import numpy as np

RESAMPLES = 1000
SEED = 0


# Resampling 1000 x 73k impressions at once would allocate ~585 MB; draw in chunks instead.
CHUNK = 50


def _resample_means(arrays: tuple[np.ndarray, ...], resamples: int, seed: int) -> tuple[np.ndarray, ...]:
    """Chunked resampling. All arrays share each draw, which is what makes it paired."""
    n = len(arrays[0])
    # Fixed seed, so the CIs I report are the same every run. Without it the last decimal
    # of every interval moves and the results file stops being reproducible.
    rng = np.random.default_rng(seed)
    out = [np.empty(resamples) for _ in arrays]
    for start in range(0, resamples, CHUNK):
        size = min(CHUNK, resamples - start)
        # Draw n indices WITH replacement, n times over: that is the bootstrap. Each row of
        # `idx` is one synthetic dataset the same size as the real one.
        idx = rng.integers(0, n, size=(size, n))
        for values, dest in zip(arrays, out):
            # Every array is indexed by the SAME `idx`. For `paired` this is the crux: both
            # systems get scored on the identical resampled impressions, so the difference
            # I measure is not contaminated by which impressions happened to be drawn.
            dest[start:start + size] = values[idx].mean(axis=1)
    return tuple(out)


def ci(values: np.ndarray, resamples: int = RESAMPLES, seed: int = SEED, level: float = 95.0):
    """(mean, low, high) for one system."""
    (means,) = _resample_means((values,), resamples, seed)
    # Percentile method: I take the middle 95% of the resampled means directly, so 95% level
    # means cutting 2.5% off each tail. The reported point estimate is the TRUE mean, not the
    # mean of the resamples, since the resamples exist only to describe its spread.
    tail = (100.0 - level) / 2.0
    return float(values.mean()), float(np.percentile(means, tail)), float(np.percentile(means, 100 - tail))


def paired(a: np.ndarray, b: np.ndarray, resamples: int = RESAMPLES, seed: int = SEED,
           level: float = 95.0):
    """(mean difference a-b, low, high, excludes_zero) on shared resamples."""
    assert len(a) == len(b), "paired bootstrap needs the same impressions on both sides"
    means_a, means_b = _resample_means((a, b), resamples, seed)
    # I build the CI on the DIFFERENCE, not on each system separately. Two overlapping
    # individual CIs do not imply the difference is insignificant, so comparing intervals
    # by eye would be the wrong test.
    diffs = means_a - means_b
    tail = (100.0 - level) / 2.0
    low, high = float(np.percentile(diffs, tail)), float(np.percentile(diffs, 100 - tail))
    # "Significant" here means the whole interval sits on one side of zero. This is the
    # assignment's bar for claiming an improvement is real.
    return float((a - b).mean()), low, high, bool(low > 0 or high < 0)


def fmt(mean: float, lo: float, hi: float) -> str:
    return f"{mean:.4f} [{lo:.4f}, {hi:.4f}]"
