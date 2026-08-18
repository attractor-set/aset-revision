------------------ MODULE SeedBoundaryProofs ------------------
EXTENDS SeedProjection, TLAPS

THEOREM ProposalSeedStatesAreWellTyped ==
  \A p \in ProposalUniverse :
    /\ SeedSource(p) \in Seed!StateType
    /\ SeedTarget(p) \in Seed!StateType
PROOF
  BY SMTT(30)
     DEF SeedSource, SeedTarget, Seed!StateType,
         Seed!RecognitionValues, ProposalUniverse,
         RevisionTransitionUniverse

THEOREM ProposeRevisionProjectsToSeedObserveUnknown ==
  \A s, t, p : ProposeRevision(s, t, p) => ProposalSeedObservation(p)
PROOF
  BY SMTT(30), ProposalSeedStatesAreWellTyped
     DEF ProposeRevision, ProposalSeedObservation,
         Seed!ObserveUnknown, SeedSource, SeedTarget,
         Seed!ToTheoryRecognition, Seed!TheoryObserveUnknown,
         Seed!TheoryUnknown, ProposalUniverse,
         RevisionTransitionUniverse

THEOREM ProposalSeedObservationKeepsUnknown ==
  \A p : ProposalSeedObservation(p) =>
    SeedTarget(p).recognition = "UNKNOWN"
PROOF
  BY DEF ProposalSeedObservation, Seed!ObserveUnknown, Seed!StateType

THEOREM ProposalProjectionRemainsUnknown ==
  \A s, t, p : ProposeRevision(s, t, p) =>
    ProjectedSeedRecognition(p) = "UNKNOWN"
PROOF
  BY ProposeRevisionProjectsToSeedObserveUnknown,
     ProposalSeedObservationKeepsUnknown
     DEF ProjectedSeedRecognition

THEOREM ProposalProjectionDoesNotPermitEffect ==
  \A s, t, p : ProposeRevision(s, t, p) =>
    ~ProjectedSeedEffectPermitted(p)
PROOF
  BY SMTT(30), ProposalProjectionRemainsUnknown
     DEF ProjectedSeedEffectPermitted,
         ProjectedSeedRecognition,
         RecognitionTheory!EffectPermitted,
         Seed!ToTheoryRecognition, Seed!TheoryUnknown

THEOREM RevisionPreservesSeedBoundary ==
  \A s, t, p : ProposeRevision(s, t, p) =>
    /\ ProposalSeedObservation(p)
    /\ ProjectedSeedRecognition(p) = "UNKNOWN"
    /\ ~ProjectedSeedEffectPermitted(p)
PROOF
  BY ProposeRevisionProjectsToSeedObserveUnknown,
     ProposalProjectionRemainsUnknown,
     ProposalProjectionDoesNotPermitEffect

=============================================================================
