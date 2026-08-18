---------------------- MODULE SeedProjection ----------------------
EXTENDS RevisionRelations

Seed == INSTANCE ComponentRelations
  WITH Subjects <- RevisionTransitionUniverse,
       Authorities <- Contexts,
       EvidenceItems <- ProposalUniverse,
       AuthorityRecognition <- {}

RecognitionTheory == INSTANCE RecognitionCardinality

SeedSource(p) ==
  [subject |-> p.transition,
   authority |-> p.target,
   evidence |-> {},
   recognition |-> "UNKNOWN"]

SeedTarget(p) ==
  [SeedSource(p) EXCEPT !.evidence = @ \cup {p}]

ProposalSeedObservation(p) ==
  Seed!ObserveUnknown(SeedSource(p), SeedTarget(p), p)

ProjectedSeedRecognition(p) == SeedTarget(p).recognition
ProjectedSeedEffectPermitted(p) ==
  RecognitionTheory!EffectPermitted(
    Seed!ToTheoryRecognition(SeedTarget(p).recognition))

=============================================================================
