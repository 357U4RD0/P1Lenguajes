import re

class YalexParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.content = ""

        self.header = ""
        self.trailer = ""
        self.lets = {}
        self.rules = []

    # =============================
    # 🔹 Lectura del archivo
    # =============================
    def read_file(self):
        with open(self.filepath, "r", encoding="utf-8") as f:
            self.content = f.read()

    # =============================
    # 🔹 Eliminar comentarios (* *)
    # =============================
    def remove_comments(self):
        pattern = r'\(\*.*?\*\)'
        self.content = re.sub(pattern, '', self.content, flags=re.DOTALL)

    # =============================
    # 🔹 Extraer bloques { }
    # =============================
    def extract_brace_blocks(self):
        blocks = []
        stack = []
        start = None

        for i, c in enumerate(self.content):
            if c == '{':
                if not stack:
                    start = i
                stack.append(c)
            elif c == '}':
                stack.pop()
                if not stack and start is not None:
                    blocks.append((start, i))

        return blocks

    def extract_header_trailer(self):
        blocks = self.extract_brace_blocks()

        if not blocks:
            return

        # header = primer bloque
        h_start, h_end = blocks[0]
        self.header = self.content[h_start+1:h_end].strip()

        # trailer = último bloque (si hay más de uno)
        if len(blocks) > 1:
            t_start, t_end = blocks[-1]
            self.trailer = self.content[t_start+1:t_end].strip()

            # eliminar trailer del contenido
            self.content = self.content[:t_start]

        # eliminar header del contenido
        self.content = self.content[h_end+1:]

    # =============================
    # 🔹 Extraer LETS
    # =============================
    def extract_lets(self):
        let_pattern = re.compile(r'let\s+(\w+)\s*=\s*(.+)')

        new_lines = []
        for line in self.content.splitlines():
            line = line.strip()
            if not line:
                continue

            match = let_pattern.match(line)
            if match:
                name = match.group(1)
                regex = match.group(2).strip()
                self.lets[name] = regex
            else:
                new_lines.append(line)

        self.content = "\n".join(new_lines)

    # =============================
    # 🔹 Extraer RULES correctamente
    # =============================
    def extract_rules(self):
        match = re.search(r'rule\s+\w+.*?=\s*(.*)', self.content, re.DOTALL)
        if not match:
            raise ValueError("No se encontró la sección rule")

        rules_text = match.group(1).strip()

        current = ""
        depth = 0
        rules = []

        for c in rules_text:
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1

            if c == '|' and depth == 0:
                rules.append(current.strip())
                current = ""
            else:
                current += c

        if current.strip():
            rules.append(current.strip())

        # procesar cada regla
        for rule in rules:
            self._parse_rule(rule)

    def _parse_rule(self, text):
        # busca el primer { que no esté dentro de nada raro
        idx = text.find('{')
        if idx == -1:
            return

        regex = text[:idx].strip()
        action = text[idx+1:].rstrip('}').strip()

        if regex:
            self.rules.append({
                "regex": regex,
                "action": action
            })

    # =============================
    # 🔹 Resolver LETS correctamente
    # =============================
    def resolve_lets(self):
        changed = True

        # repetir hasta que ya no haya cambios (por si hay lets dentro de lets)
        while changed:
            changed = False

            for rule in self.rules:
                for name, value in self.lets.items():
                    pattern = r'(?<!\w)' + re.escape(name) + r'(?!\w)'
                    new_regex = re.sub(pattern, f"({value})", rule["regex"])

                    if new_regex != rule["regex"]:
                        rule["regex"] = new_regex
                        changed = True

    # =============================
    # 🔹 Validaciones útiles
    # =============================
    def validate(self):
        if not self.rules:
            raise ValueError("No se encontraron reglas")

        for r in self.rules:
            if not r["regex"]:
                raise ValueError("Regla con regex vacío")

    # =============================
    # 🔹 Pipeline completo
    # =============================
    def parse(self):
        self.read_file()
        self.remove_comments()
        self.extract_header_trailer()
        self.extract_lets()
        self.extract_rules()
        self.resolve_lets()
        self.validate()

        return {
            "header": self.header,
            "trailer": self.trailer,
            "lets": self.lets,
            "rules": self.rules
        }


# =============================
# 🔥 TEST
# =============================
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