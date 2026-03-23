class YalexParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.content  = ""
        self.header   = ""
        self.trailer  = ""
        self.lets     = {}
        self.rules    = []

    # ── file ─────────────────────────────────────────────────────────────────
    def read_file(self):
        with open(self.filepath, "r", encoding="utf-8") as f:
            self.content = f.read()

    # ── comment removal ───────────────────────────────────────────────────────
    def remove_comments(self):
        """Remove (* ... *) comments without touching string/char literals."""
        result = []
        i = 0
        s = self.content
        while i < len(s):
            if s[i] == '"':                          # double-quoted string
                result.append(s[i]); i += 1
                while i < len(s) and s[i] != '"':
                    if s[i] == '\\': result.append(s[i]); i += 1
                    if i < len(s):   result.append(s[i]); i += 1
                if i < len(s): result.append(s[i]); i += 1
            elif s[i] == "'":                        # single-quoted char
                result.append(s[i]); i += 1
                if i < len(s) and s[i] == '\\': result.append(s[i]); i += 1
                if i < len(s): result.append(s[i]); i += 1
                if i < len(s) and s[i] == "'": result.append(s[i]); i += 1
            elif s[i] == '(' and i+1 < len(s) and s[i+1] == '*':  # comment
                i += 2
                while i < len(s):
                    if s[i] == '*' and i+1 < len(s) and s[i+1] == ')':
                        i += 2; break
                    i += 1
            else:
                result.append(s[i]); i += 1
        self.content = ''.join(result)

    # ── word / keyword helpers ────────────────────────────────────────────────
    def _find_word(self, text, word):
        """Return index of first occurrence of `word` as a standalone identifier."""
        wlen = len(word)
        i = 0
        while i <= len(text) - wlen:
            if text[i:i+wlen] == word:
                before_ok = i == 0 or not (text[i-1].isalnum() or text[i-1] == '_')
                after_pos = i + wlen
                after_ok  = after_pos >= len(text) or not (text[after_pos].isalnum() or text[after_pos] == '_')
                if before_ok and after_ok:
                    return i
            i += 1
        return len(text)   # not found

    def _is_identifier_char(self, c):
        return c.isalnum() or c == '_'

    # ── brace blocks ──────────────────────────────────────────────────────────
    def extract_brace_blocks(self):
        blocks = []
        stack  = []
        start  = None
        for i, c in enumerate(self.content):
            if c == '{':
                if not stack: start = i
                stack.append(c)
            elif c == '}' and stack:
                stack.pop()
                if not stack and start is not None:
                    blocks.append((start, i))
        return blocks

    def _is_standalone_block(self, pos):
        line_start = self.content.rfind('\n', 0, pos)
        before = self.content[line_start+1:pos].strip()
        return before == ''

    # ── header / trailer ──────────────────────────────────────────────────────
    def extract_header_trailer(self):
        blocks = self.extract_brace_blocks()
        if not blocks:
            return

        standalone = [(s, e) for s, e in blocks if self._is_standalone_block(s)]
        if not standalone:
            return

        rule_pos   = self._find_word(self.content, 'rule')
        before_rule = [(s, e) for s, e in standalone if s < rule_pos]
        after_rule  = [(s, e) for s, e in standalone if s > rule_pos]

        if before_rule:
            h_start, h_end = before_rule[0]
            self.header = self.content[h_start+1:h_end].strip()
            if after_rule:
                t_start, t_end = after_rule[-1]
                self.trailer = self.content[t_start+1:t_end].strip()
                self.content = self.content[:t_start]
            self.content = self.content[h_end+1:]

    # ── let definitions ───────────────────────────────────────────────────────
    def _parse_let_line(self, line):
        """Parse 'let name = value'. Returns (name, value) or None."""
        i = 0
        while i < len(line) and line[i].isspace(): i += 1
        if line[i:i+3] != 'let': return None
        i += 3
        if i >= len(line) or not line[i].isspace(): return None
        while i < len(line) and line[i].isspace(): i += 1
        # identifier
        j = i
        while j < len(line) and self._is_identifier_char(line[j]): j += 1
        if j == i: return None
        name = line[i:j]; i = j
        while i < len(line) and line[i].isspace(): i += 1
        if i >= len(line) or line[i] != '=': return None
        i += 1
        while i < len(line) and line[i].isspace(): i += 1
        value = line[i:].strip()
        return (name, value) if value else None

    def extract_lets(self):
        new_lines = []
        for line in self.content.splitlines():
            parsed = self._parse_let_line(line)
            if parsed:
                name, value = parsed
                self.lets[name] = value
            elif line.strip():
                new_lines.append(line)
        self.content = "\n".join(new_lines)

    # ── rule section ──────────────────────────────────────────────────────────
    def _find_rule_body(self, content):
        """Find 'rule <name> [args] = ...' and return the text after '='."""
        rule_pos = self._find_word(content, 'rule')
        if rule_pos >= len(content):
            return None
        i = rule_pos + 4
        while i < len(content) and content[i].isspace(): i += 1
        # skip entrypoint name
        while i < len(content) and self._is_identifier_char(content[i]): i += 1
        # skip until '='
        while i < len(content) and content[i] != '=': i += 1
        if i >= len(content): return None
        i += 1
        return content[i:].strip()

    def extract_rules(self):
        rules_text = self._find_rule_body(self.content)
        if rules_text is None:
            raise ValueError("No se encontró la sección rule")

        current = ""
        depth   = 0
        rules   = []
        i       = 0

        while i < len(rules_text):
            c = rules_text[i]

            if c == "'" and depth == 0:            # single-quoted char
                current += c; i += 1
                if i < len(rules_text) and rules_text[i] == '\\':
                    current += rules_text[i]; i += 1
                if i < len(rules_text):
                    current += rules_text[i]; i += 1
                if i < len(rules_text) and rules_text[i] == "'":
                    current += rules_text[i]; i += 1
                continue

            if c == '"' and depth == 0:            # double-quoted string
                current += c; i += 1
                while i < len(rules_text) and rules_text[i] != '"':
                    if rules_text[i] == '\\': current += rules_text[i]; i += 1
                    current += rules_text[i]; i += 1
                if i < len(rules_text): current += rules_text[i]; i += 1
                continue

            if c == '[' and depth == 0:            # character class
                j = i + 1; bd = 1
                while j < len(rules_text) and bd > 0:
                    if rules_text[j] == '[': bd += 1
                    elif rules_text[j] == ']': bd -= 1
                    j += 1
                current += rules_text[i:j]; i = j
                continue

            if c == '{': depth += 1
            elif c == '}': depth -= 1

            if c == '|' and depth == 0:
                rules.append(current.strip()); current = ""
            else:
                current += c
            i += 1

        if current.strip():
            rules.append(current.strip())

        for rule in rules:
            self._parse_rule(rule)

    # ── action brace finder ───────────────────────────────────────────────────
    def _find_action_brace(self, text):
        """Find index of '{' that opens the action block (skips quoted content)."""
        i = 0
        while i < len(text):
            c = text[i]
            if c == "'":
                i += 1
                if i < len(text) and text[i] == '\\': i += 2
                elif i < len(text): i += 1
                if i < len(text) and text[i] == "'": i += 1
            elif c == '"':
                i += 1
                while i < len(text) and text[i] != '"':
                    if text[i] == '\\': i += 1
                    i += 1
                i += 1
            elif c == '[':
                depth = 1; i += 1
                while i < len(text) and depth > 0:
                    if text[i] == '[': depth += 1
                    elif text[i] == ']': depth -= 1
                    i += 1
            elif c == '(':
                depth = 1; i += 1
                while i < len(text) and depth > 0:
                    if text[i] == '(': depth += 1
                    elif text[i] == ')': depth -= 1
                    i += 1
            elif c == '{':
                return i
            else:
                i += 1
        return -1

    def _parse_rule(self, text):
        idx = self._find_action_brace(text)
        if idx == -1:
            return
        regex  = text[:idx].strip()
        action = text[idx+1:].rstrip('}').strip()
        if regex:
            self.rules.append({"regex": regex, "action": action})

    # ── let substitution ──────────────────────────────────────────────────────
    def _substitute_let(self, regex, name, value):
        """Replace standalone `name` with `(value)` in regex, skipping literals."""
        result = []
        i = 0
        while i < len(regex):
            c = regex[i]
            if c == '"':                            # skip string literal
                j = i + 1
                while j < len(regex) and regex[j] != '"':
                    if regex[j] == '\\': j += 1
                    j += 1
                result.append(regex[i:j+1]); i = j + 1; continue
            if c == "'":                            # skip single-quoted char
                j = i + 1
                if j < len(regex) and regex[j] == '\\': j += 1
                j += 1
                if j < len(regex) and regex[j] == "'": j += 1
                result.append(regex[i:j]); i = j; continue
            if c == '[':                            # skip char class
                depth = 1; j = i + 1
                while j < len(regex) and depth > 0:
                    if regex[j] == '[': depth += 1
                    elif regex[j] == ']': depth -= 1
                    j += 1
                result.append(regex[i:j]); i = j; continue
            if regex[i:i+len(name)] == name:        # candidate substitution
                before_ok = i == 0 or not self._is_identifier_char(regex[i-1])
                after_pos = i + len(name)
                after_ok  = after_pos >= len(regex) or not self._is_identifier_char(regex[after_pos])
                if before_ok and after_ok:
                    result.append(f"({value})"); i += len(name); continue
            result.append(c); i += 1
        return ''.join(result)

    def resolve_lets(self):
        # Resolve lets within let definitions (transitive)
        changed = True
        while changed:
            changed = False
            for lname, lval in list(self.lets.items()):
                for oname, oval in self.lets.items():
                    if oname == lname: continue
                    new_val = self._substitute_let(lval, oname, oval)
                    if new_val != lval:
                        self.lets[lname] = new_val; lval = new_val; changed = True

        # Resolve lets in rules
        changed = True
        while changed:
            changed = False
            for rule in self.rules:
                for name, value in self.lets.items():
                    new_regex = self._substitute_let(rule["regex"], name, value)
                    if new_regex != rule["regex"]:
                        rule["regex"] = new_regex; changed = True

    # ── validation ───────────────────────────────────────────────────────────
    def validate(self):
        if not self.rules:
            raise ValueError("No se encontraron reglas")
        for r in self.rules:
            if not r["regex"]:
                raise ValueError("Regla con regex vacío")

    # ── public entry point ────────────────────────────────────────────────────
    def parse(self):
        self.read_file()
        self.remove_comments()
        self.extract_header_trailer()
        self.extract_lets()
        self.extract_rules()
        self.resolve_lets()
        self.validate()
        return {
            "header":  self.header,
            "trailer": self.trailer,
            "lets":    self.lets,
            "rules":   self.rules,
        }


if __name__ == "__main__":
    parser = YalexParser("lexer.yal")
    result = parser.parse()
    print("========== HEADER ==========")
    print(result["header"])
    print("\n========== LETS ==========")
    for k, v in result["lets"].items():
        print(f"{k} = {v}")
    print("\n========== RULES ==========")
    for r in result["rules"]:
        print(r)
