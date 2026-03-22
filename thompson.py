class State:
    def __init__(self):
        self.transitions = {}   
        self.epsilon = []       

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
    return concat(nfa, kleene(nfa))


def optional(nfa):
    start = State()
    end = State()

    start.add_epsilon(nfa.start)
    start.add_epsilon(end)

    nfa.end.add_epsilon(end)

    return NFA(start, end)

def tokenize(regex):
    tokens = []
    i = 0

    while i < len(regex):
        c = regex[i]

        if c == '"':
            j = i + 1
            while j < len(regex) and regex[j] != '"':
                j += 1
            tokens.append(regex[i:j+1])
            i = j + 1
            continue

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
            continue

        elif c in {'|', '*', '+', '?', '(', ')'}:
            tokens.append(c)

        elif c.strip() == '':
            pass

        else:
            tokens.append(c)

        i += 1

    return tokens

def add_concat(tokens):
    result = []
    operators = {'|', '*', '+', '?', '(', ')'}

    for i in range(len(tokens)):
        t1 = tokens[i]
        result.append(t1)

        if i + 1 < len(tokens):
            t2 = tokens[i + 1]

            if (t1 not in operators or t1 in {')', '*', '+', '?'}) and \
               (t2 not in operators or t2 == '('):
                result.append('.')

    return result

def to_postfix(tokens):
    precedence = {'|': 1, '.': 2, '*': 3, '+': 3, '?': 3}
    output = []
    stack = []

    for token in tokens:
        if token == '(':
            stack.append(token)

        elif token == ')':
            while stack and stack[-1] != '(':
                output.append(stack.pop())
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

def build_nfa(postfix):
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

        else:
            stack.append(symbol_nfa(token))

    return stack[0]

def regex_to_nfa(regex):
    tokens = tokenize(regex)
    tokens = add_concat(tokens)
    postfix = to_postfix(tokens)
    return build_nfa(postfix)

if __name__ == "__main__":
    test_regex = "(['0'-'9'])+"
    
    print("Regex:", test_regex)

    tokens = tokenize(test_regex)
    print("Tokens:", tokens)

    tokens = add_concat(tokens)
    print("Con concat:", tokens)

    postfix = to_postfix(tokens)
    print("Postfix:", postfix)

    nfa = build_nfa(postfix)
    print("AFN construido correctamente ✅")