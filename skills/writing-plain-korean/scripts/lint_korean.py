#!/usr/bin/env python3
"""Mechanical checks for Korean prose written for people.

Counts only what a regex can see reliably: em-dash and middle dot, translated
concept words from SKILL.md, noun-form sentence endings in running prose,
chained "~의", double passives, "~에 있어서", and very long sentences.
Code, inline code, quotes, URLs and tables are skipped. Lists and headers are
checked only for words and punctuation, not for endings or length.

CLI:  lint_korean.py FILE...   (or "-" for stdin)  -> exit 1 when it finds hits
      lint_korean.py --self-test
"""
import json
import re
import sys

MAX_EOJEOL = 40  # a prose sentence longer than this many words is flagged

H = "가-힣"  # Hangul syllables

# Words SKILL.md says to unpack. (pattern, word shown in the report)
# Single-syllable words need a particle after them, so 축소, 계층, 층간 do not match.
PARTICLE = r"(?=(?:은|는|이|가|을|를|의|에|과|와|으로|로|도|만|별|마다|\s|$|[,.)]))"
CONCEPT_WORDS = [
    (rf"(?<![{H}])축{PARTICLE}", "축"),
    (rf"(?<![{H}])층{PARTICLE}", "층"),
    (r"두 층|층 [0-9]", "층"),
    (r"표면(?!적으로|장력)", "표면"),
    (r"판정", "판정"),
    (r"집행", "집행"),
    (r"거처", "거처"),
    (r"주체(?!적)", "주체"),
    (r"표식", "표식"),
    (r"분담", "분담"),
    (r"이양", "이양"),
    (r"수렴", "수렴"),
    (r"접근점", "접근점"),
    (r"부여 단위", "부여 단위"),
    (r"게이트(?!웨이)", "게이트"),
    (r"어휘", "어휘"),
]

# Nouns that end in 의 and are not the particle.
UI_NOUNS = set("회의 주의 동의 정의 논의 합의 의의 편의 문의 모의 협의 강의 건의 결의 질의 유의 임의 대의 호의 제의 고의 민의 신의 예의 본의".split())

DOUBLE_PASSIVE = re.compile(rf"[{H}]*(?:되어[지진져졌집질]|지게 되)[{H}]*")
EOE_ISSEOSEO = re.compile(rf"(?:[{H}]+(?:함|기)에|하는 데|것에) 있어서|에 있어서의")
NOUN_ENDING = re.compile(rf"([{H}]+(?:함|임|됨|음|짐|봄|냄|줌))\s*$")
# "A가 아니라 B": say B. Keep A only when the reader would otherwise assume A.
CONTRAST = re.compile(rf"아니라(?!면)|아니고|[{H}]라기보다|뿐(?:만)? 아니라|(?<=[{H}])[이가] 아닌 ")
# Words that add emphasis or certainty but no fact. Plain adverbs (다시, 이미, 따로) stay legal.
FILLER = re.compile(rf"(?<![{H}])(?:실제로|정말|진짜|매우|굉장히|상당히|아주|꽤|확실히|분명히|사실상|그야말로|"
                    rf"완벽하게|완벽히|깔끔하게|제대로|근본적으로|본질적으로|실질적으로|명확하게|명확히|"
                    rf"정확히|정확하게|정상적으로|단순히|그저|핵심은|자체가|자체는|자체를)(?![{H}])")
CHAIN = re.compile(rf"([{H}]+의) ([{H}]+의) [{H}]+")

RULES = {
    "em_dash": "em-dash(—)를 쓰지 않는다. 콜론, 접속사, 두 문장으로 나눈다.",
    "middle_dot": "가운뎃점(·)을 쓰지 않는다. 쉼표, '와/과', 괄호로 바꾼다.",
    "concept_word": "번역투 개념어. 누가 무엇을 하는지로 풀어 쓴다(SKILL.md 표 참고).",
    "noun_ending": "본문 문장을 '~함/~임/~됨'으로 끝내지 않는다. 서술어로 끝맺는다.",
    "contrast": "'A가 아니라 B' 꼴. B만 쓴다. 읽는 사람이 A로 오해할 만할 때만 남긴다.",
    "filler": "사실을 더하지 않는 꾸미는 말. 지워도 뜻이 같으면 지운다.",
    "chain_ui": "'~의'가 이어진다. 조사와 어미로 관계를 드러낸다.",
    "double_passive": "이중 피동. '되어지다' 대신 '되다', '지게 되다' 대신 '지다'나 능동으로 쓴다.",
    "e_isseoseo": "'~에 있어서'는 번역투다. '~에서', '~할 때'로 바꾼다.",
    "long_sentence": f"문장이 {MAX_EOJEOL}어절을 넘는다. 두 문장으로 나눈다.",
}


def blank_code(text):
    """Replace code, inline code, quotes, URLs and tables with spaces, keeping line numbers."""
    def keep_lines(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    text = re.sub(r"```.*?```", keep_lines, text, flags=re.S)
    text = re.sub(r"~~~.*?~~~", keep_lines, text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", " CODE ", text)
    text = re.sub(r"https?://\S+", " URL ", text)
    text = re.sub(r"\[\[[^\]\n]*\]\]", " LINK ", text)  # wiki links name existing notes
    text = re.sub(r"(?m)^\s*>.*$", "", text)
    text = re.sub(r"(?m)^\s*\|.*$", "", text)
    text = re.sub(r"(?s)\A---\n.*?\n---\n", keep_lines, text)  # frontmatter
    text = re.sub(r"<!--.*?-->", keep_lines, text, flags=re.S)
    return text


def korean_share(text):
    body = blank_code(text)
    hangul = len(re.findall(f"[{H}]", body))
    latin = len(re.findall(r"[A-Za-z]", body))
    return hangul / (hangul + latin) if hangul + latin else 0.0


def sentences(line):
    """Split a prose line into sentences on . ? ! that follow a Hangul ending."""
    parts = re.split(rf"(?<=[{H}][.?!])\s+", line.strip())
    return [p for p in parts if p]


def is_structure(line):
    s = line.lstrip()
    return bool(re.match(r"(#{1,6}\s|[-*+]\s|\d+[.)]\s|- \[.\])", s))


def lint(text):
    """Return a list of hits: {line, rule, text}."""
    hits = []
    body = blank_code(text)
    for no, line in enumerate(body.split("\n"), 1):
        def hit(rule, snippet):
            hits.append({"line": no, "rule": rule, "text": snippet.strip()[:60]})
        # Quoted text is a citation: UI copy, a word under discussion, a bad example. Skip it.
        unquoted = re.sub(r"\"[^\"\n]*\"|“[^”\n]*”|'[^'\n]*'|「[^」\n]*」", " ", line)
        for m in re.finditer("—", unquoted):
            hit("em_dash", unquoted[max(0, m.start() - 15): m.end() + 15])
        for m in re.finditer("[·ㆍ]", unquoted):
            hit("middle_dot", unquoted[max(0, m.start() - 10): m.end() + 10])
        if not re.search(f"[{H}]", line):
            continue
        seen = set()
        for pattern, word in CONCEPT_WORDS:
            for m in re.finditer(pattern, unquoted):
                pos = unquoted.find(word, m.start())
                if (word, pos) not in seen:
                    seen.add((word, pos))
                    hit("concept_word", f"{word}: {unquoted[max(0, m.start() - 12): m.end() + 12]}")
        for m in DOUBLE_PASSIVE.finditer(unquoted):
            hit("double_passive", m.group(0))
        for m in EOE_ISSEOSEO.finditer(unquoted):
            hit("e_isseoseo", unquoted[max(0, m.start() - 10): m.end() + 5])
        for m in CONTRAST.finditer(unquoted):
            hit("contrast", unquoted[max(0, m.start() - 20): m.end() + 15])
        for m in FILLER.finditer(unquoted):
            hit("filler", unquoted[max(0, m.start() - 10): m.end() + 15])
        for m in CHAIN.finditer(unquoted):
            if m.group(1) not in UI_NOUNS and m.group(2) not in UI_NOUNS:
                hit("chain_ui", m.group(0))
        if is_structure(line):
            continue
        for s in sentences(line):
            core = s.rstrip(".?! ")
            m = NOUN_ENDING.search(core)
            # one bare word, or "Label: value", is a label, not a sentence
            if m and ":" not in core and re.search(rf"[{H}]+\s+[{H}]+", core):
                hit("noun_ending", s[-30:])
            if len(s.split()) > MAX_EOJEOL:
                hit("long_sentence", s[:40] + "...")
    return hits


def summary(hits, limit=12):
    lines = []
    for h in hits[:limit]:
        lines.append(f"  {h['line']}행 {h['rule']}: {h['text']}")
    if len(hits) > limit:
        lines.append(f"  그 밖에 {len(hits) - limit}건")
    rules = sorted({h["rule"] for h in hits})
    lines.append("고치는 법:")
    lines += [f"  {r}: {RULES[r]}" for r in rules]
    return "\n".join(lines)


SELF_TESTS = [
    ("판정은 인증 서버가 하고 집행은 사이드카가 합니다.", {"concept_word"}),
    ("소속 축으로 행을 거릅니다.", {"concept_word"}),
    ("화면을 축소합니다. 계층 구조를 봅니다. API 게이트웨이를 둡니다.", set()),
    ("설정이 변경되어졌습니다.", {"double_passive"}),
    ("배포에 있어서의 주의점입니다.", {"e_isseoseo"}),
    ("이 값을 확인함.", {"noun_ending"}),
    ("- 로그인 화면 수정함", set()),
    ("## 확인함", set()),
    ("사용자의 권한의 범위를 봅니다.", {"chain_ui"}),
    ("회의의 결과를 정리합니다.", set()),
    ("A — B", {"em_dash"}),
    ('em-dash("—")를 쓰지 않습니다.', set()),
    ("스킬·훅 정리", {"middle_dot"}),
    ("`판정` 함수를 고칩니다.", set()),
    ("```\n판정 — 집행\n```\n본문입니다.", set()),
    ("> 판정은 원문 인용입니다.", set()),
    ("결과: 성공함", set()),
    ("마음.", set()),
    ("두 층으로 나눕니다.", {"concept_word"}),
    ("배포하는 데 있어서 주의합니다. 확인은 다음 단계에 있어서 거기서 봅니다.", {"e_isseoseo"}),
    ("문서에 있어야 합니다.", set()),
    ("두 값이 짝지어지는가 봅니다.", set()),
    ('부가줄은 "내 선택 · 도보 N분"입니다.', set()),
    ("Expected: 에러 없음.", set()),
    ("실제 앱키는 발급받음.", {"noun_ending"}),
    ("효과는 린터 점수가 아니라 눈에 보이는 결과로 잽니다.", {"contrast"}),
    ("에러가 아닌 경고로 둡니다.", {"contrast"}),
    ("문제라기보다 질문입니다.", {"contrast"}),
    ("값이 없다면 기본값을 씁니다. 아니라면 그대로 둡니다.", set()),
    ("실제로 가까운 시각에 기록이 없었습니다.", {"filler"}),
    ("정상적으로 반영되었습니다.", {"filler"}),
    ("실제 브라우저에서 다시 확인했습니다.", set()),
    ('"판정", "집행" 같은 말은 풀어 씁니다.', set()),
    ("「문제라기보다 질문」이라는 문장은 고칩니다.", set()),
    ('예시 "실제로 됩니다"를 고쳤고, 실제로 반영했습니다.', {"filler"}),
]


def self_test():
    failed = 0
    for text, want in SELF_TESTS:
        got = {h["rule"] for h in lint(text)}
        if got != want:
            failed += 1
            print(f"FAIL {text!r}: want {sorted(want)}, got {sorted(got)}")
    print(f"{len(SELF_TESTS) - failed}/{len(SELF_TESTS)} passed")
    return 1 if failed else 0


def main(argv):
    if argv[1:2] == ["--self-test"]:
        return self_test()
    as_json = "--json" in argv
    paths = [a for a in argv[1:] if a != "--json"] or ["-"]
    found = 0
    for path in paths:
        text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
        hits = lint(text)
        found += len(hits)
        if as_json:
            print(json.dumps({"path": path, "hits": hits}, ensure_ascii=False))
        elif hits:
            print(f"{path}: {len(hits)}건\n{summary(hits, limit=50)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
