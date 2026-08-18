---------------- MODULE ComponentCompositionProofs ----------------
EXTENDS RevisionRelations, TLAPS

THEOREM ProposalTargetIsExactGenesis ==
  \A s, t, p : ProposeRevision(s, t, p) =>
    p.target = p.transition.genesis
PROOF
  BY DEF ProposeRevision, ProposalUniverse

THEOREM ProposalChangesExactStateRoot ==
  \A s, t, p : ProposeRevision(s, t, p) =>
    p.transition.fromState # p.transition.toState
PROOF
  BY DEF ProposeRevision, ProposalUniverse, RevisionTransitionUniverse

THEOREM ExistingProposalsArePreserved ==
  \A s, t, p : ProposeRevision(s, t, p) => s \subseteq t
PROOF
  BY DEF ProposeRevision

THEOREM ProposedItemIsPresentAfterStep ==
  \A s, t, p : ProposeRevision(s, t, p) => p \in t
PROOF
  BY DEF ProposeRevision

THEOREM ProposalWasFreshBeforeStep ==
  \A s, t, p : ProposeRevision(s, t, p) => p \notin s
PROOF
  BY DEF ProposeRevision

THEOREM RevisionProposalSafety ==
  \A s, t, p : ProposeRevision(s, t, p) =>
    /\ s \subseteq t
    /\ p \notin s
    /\ p \in t
    /\ p.target = p.transition.genesis
    /\ p.transition.fromState # p.transition.toState
PROOF
  BY ExistingProposalsArePreserved,
     ProposedItemIsPresentAfterStep,
     ProposalWasFreshBeforeStep,
     ProposalTargetIsExactGenesis,
     ProposalChangesExactStateRoot

=============================================================================
