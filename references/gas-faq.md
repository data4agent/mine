# Gas and Rewards FAQ

## Does mining cost gas?

**No.** Submitting data to the platform does not require on-chain transactions or gas fees. All submissions are signed off-chain using EIP-712 typed data and sent via HTTP to the platform API.

## What is $aMine?

`$aMine` is the reward token earned through successful data submissions. It is awarded based on submission quality, epoch participation, and credit score.

## How do I earn rewards?

1. **Submit data** through the mining workflow. Each accepted submission contributes to your epoch progress.
2. **Meet the epoch target** (typically 80+ submissions per epoch). Meeting or exceeding the target maximizes reward eligibility.
3. **Maintain credit score.** Higher credit tiers earn proportionally better rewards.

## When are rewards distributed?

Rewards are calculated at the end of each epoch. Settlement results are available after the epoch closes. Use `check-status` to see your current reward summary and settlement state.

## Does claiming rewards cost gas?

**Yes.** Claiming `$aMine` rewards to your wallet requires a Base chain transaction, which incurs gas fees. The gas cost is typically minimal (fractions of a cent on Base L2), but you need a small amount of ETH on Base to cover it.

## What is the credit score?

The credit score reflects your mining reliability and submission quality. Tiers include:

| Tier | Meaning |
|---|---|
| `beginner` | New miner, limited submission rate |
| `limited` | Some history, still building trust |
| `normal` | Standard miner |
| `good` | Reliable miner, higher submission limits |
| `excellent` | Top-tier miner, maximum submission limits |

Higher credit tiers allow faster submission rates (less rate limiting) and may receive priority in reward distribution.

## What affects credit score?

- **Submission quality**: well-structured, complete data improves score.
- **Consistency**: regular participation across epochs.
- **Error rate**: frequent failures or rejected submissions lower score.
- **Dedup compliance**: submitting already-occupied URLs penalizes score.

## What is an epoch?

An epoch is a time period (typically one day, identified by date like `2026-04-01`) during which submissions are collected. Each epoch has a target number of submissions. Meeting the target is important for reward eligibility.

## Can I mine without gas?

**Yes.** The entire mining workflow (heartbeat, preflight, PoW, submission) is gas-free. Gas is only needed if you choose to claim earned rewards on-chain.
