# nfa_to_dfa.py - Subset construction: NFA -> DFA


class DFAState:
    _counter = 0

    def __init__(self):
        self.id = DFAState._counter
        DFAState._counter += 1
        self.transitions = {}      # symbol -> DFAState
        self.accept = None         # token name if accept state
        self.accept_priority = float('inf')

    @classmethod
    def reset(cls):
        cls._counter = 0


def epsilon_closure(states):
    """Return list of all states reachable via epsilon transitions."""
    visited = {}
    stack = list(states)
    while stack:
        s = stack.pop()
        if id(s) not in visited:
            visited[id(s)] = s
            for t in s.epsilon:
                stack.append(t)
    return list(visited.values())


def move(states, symbol):
    """Return states reachable via symbol."""
    result = {}
    for s in states:
        if symbol in s.transitions:
            for t in s.transitions[symbol]:
                result[id(t)] = t
    return list(result.values())


def get_all_symbols(states):
    """Get all non-epsilon, non-None symbols from NFA states."""
    symbols = set()
    for s in states:
        symbols.update(s.transitions.keys())
    symbols.discard(None)
    return symbols


def nfa_to_dfa(nfa_list, token_names):
    """
    Convert a list of NFAs (one per token) to a single DFA via subset construction.
    Returns (dfa_start, all_dfa_states).
    """
    from thompson import State
    DFAState.reset()

    # Build combined start state
    combined_start = State()
    accept_map = {}  # id(nfa_end) -> (token_name, priority)
    for i, (nfa, name) in enumerate(zip(nfa_list, token_names)):
        combined_start.add_epsilon(nfa.start)
        accept_map[id(nfa.end)] = (name, i)

    initial = epsilon_closure([combined_start])

    # frozenset of NFA state ids -> (DFAState, [nfa_states])
    nfa_set_to_dfa = {}

    def get_or_create(nfa_states):
        key = frozenset(id(s) for s in nfa_states)
        if key not in nfa_set_to_dfa:
            dfa = DFAState()
            nfa_set_to_dfa[key] = (dfa, nfa_states)
            for s in nfa_states:
                if id(s) in accept_map:
                    name, priority = accept_map[id(s)]
                    if priority < dfa.accept_priority:
                        dfa.accept = name
                        dfa.accept_priority = priority
        return nfa_set_to_dfa[key][0]

    dfa_start = get_or_create(initial)
    worklist = [initial]
    processed = set()

    while worklist:
        nfa_states = worklist.pop()
        key = frozenset(id(s) for s in nfa_states)
        if key in processed:
            continue
        processed.add(key)

        dfa_state = nfa_set_to_dfa[key][0]
        for symbol in get_all_symbols(nfa_states):
            moved = move(nfa_states, symbol)
            if not moved:
                continue
            closure = epsilon_closure(moved)
            if not closure:
                continue
            next_dfa = get_or_create(closure)
            dfa_state.transitions[symbol] = next_dfa
            next_key = frozenset(id(s) for s in closure)
            if next_key not in processed:
                worklist.append(closure)

    all_states = [v[0] for v in nfa_set_to_dfa.values()]
    return dfa_start, all_states
