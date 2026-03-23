# thompson.py - Thompson's Construction for NFA building
# Supports YALex regex syntax: character classes, string literals, etc.

class State:
    _counter = 0

    def __init__(self):
        self.id = State._counter
        State._counter += 1
        self.transitions = {}  # symbol -> [State]
        self.epsilon = []      # [State]

    @classmethod
    def reset(cls):
        cls._counter = 0

    def add_transition(self, symbol, state):
        if symbol not in self.transitions:
            self.transitions[symbol] = []
        self.transitions[symbol].append(state)

    def add_epsilon(self, state):
        self.epsilon.append(state)


class NFA:
    def __init__(self, start, end):
        self.start = start
        self.end = end
        self.char_set = None  # set of chars if simple char-set NFA


def symbol_nfa(symbol):
    start = State()
    end = State()
    start.add_transition(symbol, end)
    return NFA(start, end)


def concat(nfa1, nfa2):
    nfa1.end.add_epsilon(nfa2.start)
    return NFA(nfa1.start, nfa2.end)


def union(nfa1, nfa2):
    start = State()
    end = State()
    start.add_epsilon(nfa1.start)
    start.add_epsilon(nfa2.start)
    nfa1.end.add_epsilon(end)
    nfa2.end.add_epsilon(end)
    return NFA(start, end)


def kleene(nfa):
    start = State()
    end = State()
    start.add_epsilon(nfa.start)
    start.add_epsilon(end)
    nfa.end.add_epsilon(nfa.start)
    nfa.end.add_epsilon(end)
    return NFA(start, end)


def plus(nfa):
    start = State()
    end = State()
    start.add_epsilon(nfa.start)
    nfa.end.add_epsilon(nfa.start)
    nfa.end.add_epsilon(end)
    return NFA(start, end)


def optional(nfa):
    start = State()
    end = State()
    start.add_epsilon(nfa.start)
    start.add_epsilon(end)
    nfa.end.add_epsilon(end)
    return NFA(start, end)


def parse_escape_char(ch):
    return {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\',
            "'": "'", '"': '"', '0': '\0', ' ': ' '}.get(ch, ch)


def parse_single_quoted_char(s, i):
    """Parse 'c' or '\X' at position i (opening quote). Returns (char, new_i)."""
    assert s[i] == "'"
    i += 1
    if i < len(s) and s[i] == '\\':
        i += 1
        char = parse_escape_char(s[i]) if i < len(s) else '\\'
        i += 1
    else:
        char = s[i] if i < len(s) else ''
        i += 1
    if i < len(s) and s[i] == "'":
        i += 1
    return char, i


def parse_char_class_content(inner):
    """Parse inside [...] and return set of characters."""
    chars = set()
    i = 0
    while i < len(inner):
        c = inner[i]
        if c == ' ':
            i += 1
            continue
        elif c == "'":
            char1, i = parse_single_quoted_char(inner, i)
            # Check for range 'c1' - 'c2'
            j = i
            while j < len(inner) and inner[j] == ' ':
                j += 1
            if j < len(inner) and inner[j] == '-':
                j += 1
                while j < len(inner) and inner[j] == ' ':
                    j += 1
                if j < len(inner) and inner[j] == "'":
                    char2, j = parse_single_quoted_char(inner, j)
                    for code in range(ord(char1), ord(char2) + 1):
                        chars.add(chr(code))
                    i = j
                else:
                    chars.add(char1)
                    i = j
            else:
                chars.add(char1)
                i = j
        elif c == '"':
            j = i + 1
            while j < len(inner) and inner[j] != '"':
                if inner[j] == '\\':
                    j += 1
                j += 1
            s_val = inner[i + 1:j]
            k = 0
            while k < len(s_val):
                if s_val[k] == '\\' and k + 1 < len(s_val):
                    chars.add(parse_escape_char(s_val[k + 1]))
                    k += 2
                else:
                    chars.add(s_val[k])
                    k += 1
            i = j + 1
        else:
            chars.add(c)
            i += 1
    return chars


ALL_CHARS = set(chr(i) for i in range(1, 128))


def char_set_nfa(chars):
    """Build NFA accepting any char in chars."""
    chars = list(chars)
    if not chars:
        start = State()
        end = State()
        return NFA(start, end)
    result = symbol_nfa(chars[0])
    for c in chars[1:]:
        result = union(result, symbol_nfa(c))
    result.char_set = set(chars)
    return result


def string_literal_nfa(s):
    """Build NFA for a literal string (concatenation of chars)."""
    if not s:
        start = State()
        end = State()
        start.add_epsilon(end)
        return NFA(start, end)
    result = symbol_nfa(s[0])
    for c in s[1:]:
        result = concat(result, symbol_nfa(c))
    return result


def tokenize(regex):
    """Tokenize a YALex regex string into a list of tokens."""
    tokens = []
    i = 0
    while i < len(regex):
        c = regex[i]
        if c == "'":
            j = i + 1
            if j < len(regex) and regex[j] == '\\':
                j += 2
            elif j < len(regex):
                j += 1
            if j < len(regex) and regex[j] == "'":
                j += 1
            tokens.append(regex[i:j])
            i = j
        elif c == '"':
            j = i + 1
            while j < len(regex) and regex[j] != '"':
                if regex[j] == '\\':
                    j += 1
                j += 1
            tokens.append(regex[i:j + 1])
            i = j + 1
        elif c == '[':
            j = i + 1
            depth = 1
            while j < len(regex) and depth > 0:
                if regex[j] == '[':
                    depth += 1
                elif regex[j] == ']':
                    depth -= 1
                j += 1
            tokens.append(regex[i:j])
            i = j
        elif c in {'|', '*', '+', '?', '(', ')', '#'}:
            tokens.append(c)
            i += 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < len(regex) and not regex[j].isspace() and regex[j] not in {
                '|', '*', '+', '?', '(', ')', '[', ']', '{', '}', "'", '"', '#'
            }:
                j += 1
            tokens.append(regex[i:j] if j > i else c)
            i = j if j > i else i + 1
    return tokens


def add_concat(tokens):
    """Insert explicit concatenation operator '.' where needed."""
    result = []
    operators = {'|', '*', '+', '?', '(', ')', '#'}
    for i in range(len(tokens)):
        t1 = tokens[i]
        result.append(t1)
        if i + 1 < len(tokens):
            t2 = tokens[i + 1]
            t1_is_val = t1 not in operators or t1 in {')', '*', '+', '?'}
            t2_is_val = t2 not in operators or t2 == '('
            if t1_is_val and t2_is_val:
                result.append('.')
    return result


def to_postfix(tokens):
    """Convert infix token list to postfix (Shunting Yard algorithm)."""
    precedence = {'#': 4, '*': 3, '+': 3, '?': 3, '.': 2, '|': 1}
    output = []
    stack = []
    for token in tokens:
        if token == '(':
            stack.append(token)
        elif token == ')':
            while stack and stack[-1] != '(':
                output.append(stack.pop())
            if stack:
                stack.pop()
        elif token in precedence:
            while (stack and stack[-1] != '(' and
                   precedence.get(stack[-1], 0) >= precedence[token]):
                output.append(stack.pop())
            stack.append(token)
        else:
            output.append(token)
    while stack:
        output.append(stack.pop())
    return output


def build_nfa_from_token(token):
    """Build NFA for a single terminal token."""
    if token.startswith("'") and len(token) >= 3:
        inner = token[1:-1]
        if inner.startswith('\\') and len(inner) > 1:
            char = parse_escape_char(inner[1])
        else:
            char = inner[0] if inner else ''
        return symbol_nfa(char)
    elif token.startswith('"') and token.endswith('"'):
        inner = token[1:-1]
        chars = []
        k = 0
        while k < len(inner):
            if inner[k] == '\\' and k + 1 < len(inner):
                chars.append(parse_escape_char(inner[k + 1]))
                k += 2
            else:
                chars.append(inner[k])
                k += 1
        return string_literal_nfa(''.join(chars))
    elif token.startswith('['):
        negated = len(token) > 1 and token[1] == '^'
        inner = token[2:-1] if negated else token[1:-1]
        chars = parse_char_class_content(inner)
        if negated:
            chars = ALL_CHARS - chars
        nfa = char_set_nfa(chars)
        return nfa
    elif token == 'eof':
        return symbol_nfa(None)
    elif token == '_':
        nfa = char_set_nfa(ALL_CHARS)
        return nfa
    elif len(token) == 1:
        return symbol_nfa(token)
    else:
        return string_literal_nfa(token)


def build_nfa(postfix):
    """Build NFA from postfix token list."""
    stack = []
    for token in postfix:
        if token == '*':
            stack.append(kleene(stack.pop()))
        elif token == '+':
            stack.append(plus(stack.pop()))
        elif token == '?':
            stack.append(optional(stack.pop()))
        elif token == '.':
            nfa2 = stack.pop()
            nfa1 = stack.pop()
            stack.append(concat(nfa1, nfa2))
        elif token == '|':
            nfa2 = stack.pop()
            nfa1 = stack.pop()
            stack.append(union(nfa1, nfa2))
        elif token == '#':
            nfa2 = stack.pop()
            nfa1 = stack.pop()
            c1 = getattr(nfa1, 'char_set', None)
            c2 = getattr(nfa2, 'char_set', None)
            if c1 is not None and c2 is not None:
                stack.append(char_set_nfa(c1 - c2))
            else:
                stack.append(nfa1)
        else:
            stack.append(build_nfa_from_token(token))
    return stack[0] if stack else NFA(State(), State())


def regex_to_nfa(regex):
    """Convert a YALex regex string to an NFA."""
    tokens = tokenize(regex)
    tokens = add_concat(tokens)
    postfix = to_postfix(tokens)
    return build_nfa(postfix)


def collect_nfa_states(nfa):
    """Collect all states reachable from nfa.start."""
    visited = {}
    stack = [nfa.start]
    while stack:
        s = stack.pop()
        if id(s) not in visited:
            visited[id(s)] = s
            for targets in s.transitions.values():
                for t in targets:
                    stack.append(t)
            for t in s.epsilon:
                stack.append(t)
    return list(visited.values())
