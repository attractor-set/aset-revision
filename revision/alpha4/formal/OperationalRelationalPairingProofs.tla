------------- MODULE OperationalRelationalPairingProofs -------------
EXTENDS RestrictedOperationalSemantics, TLAPS

THEOREM ProposeRevisionPairing ==
  \A s, t, p :
    OperationalProposeRevision(s, t, p) <=> ProposeRevision(s, t, p)
PROOF
  BY DEF OperationalProposeRevision, ProposeRevision

THEOREM OperationalRelationalPairing ==
  ProposeRevisionPairing
PROOF
  BY ProposeRevisionPairing

=============================================================================
