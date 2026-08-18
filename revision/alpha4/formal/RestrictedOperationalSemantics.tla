--------------- MODULE RestrictedOperationalSemantics ---------------
EXTENDS RevisionRelations

OperationalProposeRevision(s, t, p) ==
  /\ s \in StateType
  /\ t \in StateType
  /\ p \in ProposalUniverse
  /\ p \notin s
  /\ t = s \cup {p}

=============================================================================
