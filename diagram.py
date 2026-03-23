# diagram.py - State diagram generation using graphviz

import subprocess


# ── label helpers ────────────────────────────────────────────────────────────

_ESCAPE_MAP = {
    '"': '\\"', '\\': '\\\\', '\n': '\\\\n', '\t': '\\\\t', '\r': '\\\\r',
    '<': '\\<', '>': '\\>', '{': '\\{', '}': '\\}', '|': '\\|',
}

def _escape(sym):
    if sym is None:
        return 'EOF'
    return _ESCAPE_MAP.get(sym, sym if 32 <= ord(sym) <= 126 else f'\\\\x{ord(sym):02x}')


def _chars_to_label(syms, max_len=28):
    """Compress a symbol list to a compact range label."""
    # Only include printable ASCII and a few known escapes
    special = []
    printable = []
    for s in syms:
        if s is None:
            special.append('EOF')
        elif s == '\n':
            special.append('\\\\n')
        elif s == '\t':
            special.append('\\\\t')
        elif s == '\r':
            special.append('\\\\r')
        elif 32 <= ord(s) <= 126:
            printable.append(s)
        # silently drop other control chars from label

    printable.sort(key=ord)
    ranges = []
    i = 0
    while i < len(printable):
        start = printable[i]
        end = start
        j = i + 1
        while j < len(printable) and ord(printable[j]) == ord(end) + 1:
            end = printable[j]
            j += 1
        span = ord(end) - ord(start)
        if span >= 2:
            ranges.append(f'{_escape(start)}-{_escape(end)}')
        elif span == 1:
            ranges.append(_escape(start))
            ranges.append(_escape(end))
        else:
            ranges.append(_escape(start))
        i = j

    all_parts = ranges + special
    label = ', '.join(all_parts)
    if len(label) > max_len:
        label = label[:max_len - 3] + '...'
    return label if label else '?'


# ── engine selection ─────────────────────────────────────────────────────────

def _engine(n_states):
    if n_states <= 40:
        return 'dot'
    return 'fdp'


# ── NFA ──────────────────────────────────────────────────────────────────────

def _collect_nfa(nfa):
    from collections import deque
    visited, order = {}, []
    q = deque([nfa.start])
    while q:
        s = q.popleft()
        if id(s) not in visited:
            visited[id(s)] = s
            order.append(s)
            for targets in s.transitions.values():
                for t in targets:
                    q.append(t)
            for t in s.epsilon:
                q.append(t)
    id_map = {id(s): i for i, s in enumerate(order)}
    return order, id_map


def nfa_to_dot(nfa, token_name=""):
    states, id_map = _collect_nfa(nfa)
    n = len(states)
    start_id, end_id = id(nfa.start), id(nfa.end)

    lines = [
        'digraph NFA {',
        '  rankdir=LR;',
        '  bgcolor="#1a0a00";',
        '  node [fontcolor="#ffe8cc" color="#ff8c00" fontname="Helvetica" fontsize=10];',
        '  edge [color="#ffb347" fontcolor="#c8a070" fontname="Helvetica" fontsize=8];',
        '  __start [shape=none label="" style=invis];',
    ]
    for s in states:
        sid = id_map[id(s)]
        if id(s) == end_id:
            lbl = f'q{sid}\\n{token_name}' if token_name else f'q{sid}'
            lines.append(f'  q{sid} [shape=doublecircle label="{lbl}" color="#ff6b00" fontcolor="#ff6b00"];')
        elif id(s) == start_id:
            lines.append(f'  q{sid} [shape=circle label="q{sid}" color="#ffd060" fontcolor="#ffd060"];')
        else:
            lines.append(f'  q{sid} [shape=circle label="q{sid}"];')

    lines.append(f'  __start -> q{id_map[start_id]} [color="#ffd060"];')

    for s in states:
        sid = id_map[id(s)]
        by_target = {}
        for sym, targets in s.transitions.items():
            for t in targets:
                tid = id_map[id(t)]
                by_target.setdefault(tid, []).append(sym)
        for tid, syms in by_target.items():
            lbl = _chars_to_label(syms)
            lines.append(f'  q{sid} -> q{tid} [label="{lbl}"];')
        for t in s.epsilon:
            tid = id_map[id(t)]
            lines.append(f'  q{sid} -> q{tid} [label="ε" style=dashed color="#4a2000" fontcolor="#4a2000"];')

    lines.append('}')
    return '\n'.join(lines), _engine(n)


# ── DFA ──────────────────────────────────────────────────────────────────────

def _reachable_bfs(dfa_start, max_states=120):
    """Return up to max_states DFA states reachable from start (BFS order)."""
    from collections import deque
    visited, order = {dfa_start.id}, [dfa_start]
    q = deque([dfa_start])
    while q and len(order) < max_states:
        s = q.popleft()
        for t in s.transitions.values():
            if t.id not in visited and len(order) < max_states:
                visited.add(t.id)
                order.append(t)
                q.append(t)
    return order, visited


def dfa_to_dot(dfa_start, all_states):
    # Limit diagram to at most 120 states (BFS from start)
    MAX = 120
    show_states, shown_ids = _reachable_bfs(dfa_start, MAX)
    truncated = len(all_states) > MAX
    n = len(show_states)

    lines = [
        'digraph DFA {',
        f'  // {len(all_states)} total states, showing {n}{"+" if truncated else ""}',
        '  rankdir=LR;',
        '  bgcolor="#1a0a00";',
        '  node [fontcolor="#ffe8cc" color="#ff8c00" fontname="Helvetica" fontsize=10];',
        '  edge [color="#ffb347" fontcolor="#c8a070" fontname="Helvetica" fontsize=8];',
        '  __start [shape=none label="" style=invis];',
    ]

    if truncated:
        lines.append(
            f'  __note [shape=note style=filled fillcolor="#4a2000" fontcolor="#ffd060" '
            f'label="Mostrando {n} de {len(all_states)} estados" fontsize=9];'
        )

    for s in show_states:
        if s.accept:
            lbl = f'D{s.id}\\n{s.accept}'
            lines.append(f'  D{s.id} [shape=doublecircle label="{lbl}" color="#ff6b00" fontcolor="#ff6b00"];')
        elif s.id == dfa_start.id:
            lines.append(f'  D{s.id} [shape=circle label="D{s.id}" color="#ffd060" fontcolor="#ffd060"];')
        else:
            lines.append(f'  D{s.id} [shape=circle label="D{s.id}"];')

    lines.append(f'  __start -> D{dfa_start.id} [color="#ffd060"];')

    for s in show_states:
        by_target = {}
        for sym, target in s.transitions.items():
            if target.id in shown_ids:  # only draw edges within shown states
                by_target.setdefault(target.id, []).append(sym)
        for tid, syms in by_target.items():
            lbl = _chars_to_label(syms)
            lines.append(f'  D{s.id} -> D{tid} [label="{lbl}"];')

    lines.append('}')
    return '\n'.join(lines), _engine(n)


# ── render ────────────────────────────────────────────────────────────────────

def render_dot_to_png(dot_str, engine, output_path):
    try:
        result = subprocess.run(
            [engine, '-Tpng', '-Gdpi=96', '-o', output_path],
            input=dot_str.encode('utf-8'),
            capture_output=True, timeout=60
        )
        return result.returncode == 0, result.stderr.decode()
    except Exception as e:
        return False, str(e)


def generate_nfa_diagram(nfa, token_name, output_path):
    dot, engine = nfa_to_dot(nfa, token_name)
    return render_dot_to_png(dot, engine, output_path)


def generate_dfa_diagram(dfa_start, all_states, output_path):
    dot, engine = dfa_to_dot(dfa_start, all_states)
    return render_dot_to_png(dot, engine, output_path)
