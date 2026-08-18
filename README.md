# ASET Revision

ASET Revision 0.4alpha is a minimal proposal layer over ASET Seed.

It owns one semantic state:

    proposals

and one transition:

    PROPOSE-REVISION

A successful proposal appends one fresh revision transition.

ASET Revision does not own terminal recognition, grant effect
permission, or establish a recognized revision. Every admitted
proposal projects only to target-local Seed OBSERVE-UNKNOWN.

## Structure

- revision/alpha4/REVISION.aset: machine-readable composition boundary.
- revision/alpha4/operational/: restricted operational expression.
- revision/alpha4/formal/: relational model and TLAPS proofs.
- revision/alpha4/causal/: restricted causal expression.
- upstream/ASET_SEED_ALPHA4_BINDING.aset: exact Seed binding.
- tools/: verification and deterministic release tooling.
- tests/: regression and release-assurance tests.

## Upstream

ASET Seed:

https://github.com/attractor-set/aset-seed

## Repository

https://github.com/attractor-set/aset-revision

## License

Apache-2.0
