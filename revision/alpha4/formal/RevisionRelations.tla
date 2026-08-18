-------------------- MODULE RevisionRelations --------------------

CONSTANTS Contexts, StateRoots

ASSUME /\ Contexts # {}
       /\ StateRoots # {}

RevisionTransition(g, f, t) ==
  [genesis |-> g, fromState |-> f, toState |-> t]

RevisionTransitionUniverse ==
  {tr \in [genesis : Contexts,
            fromState : StateRoots,
            toState : StateRoots] :
    tr.fromState # tr.toState}

Proposal(c, tr) ==
  [target |-> c, transition |-> tr]

ProposalUniverse ==
  {p \in [target : Contexts,
           transition : RevisionTransitionUniverse] :
    p.target = p.transition.genesis}

StateType == SUBSET ProposalUniverse

ProposeRevision(s, t, p) ==
  /\ s \in StateType
  /\ t \in StateType
  /\ p \in ProposalUniverse
  /\ p \notin s
  /\ t = s \cup {p}

=============================================================================
