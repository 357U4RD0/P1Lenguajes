from yal_parser import YalexParser
from thompson import regex_to_nfa


def test_from_yalex():
    parser = YalexParser("lexer.yal")
    result = parser.parse()

    print("\n===== PROBANDO THOMPSON =====\n")

    for i, rule in enumerate(result["rules"]):
        regex = rule["regex"]

        print(f"\n🔹 Regla {i+1}")
        print("Regex:", regex)

        try:
            nfa = regex_to_nfa(regex)
            print("AFN construido correctamente")

        except Exception as e:
            print("Error:", e)


if __name__ == "__main__":
    test_from_yalex()