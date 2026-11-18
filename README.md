# plain-korean

AI가 쓰는 한국어를 회의에서 동료에게 말하듯 쓰게 하는 스킬입니다. 번역투 개념어, "A가 아니라 B" 꼴, 사실을 더하지 않는 꾸미는 말을 찾아서 고치게 합니다. Claude Code와 Codex 플러그인으로 설치할 수 있고, 다른 도구에서는 규칙 블록을 지침 파일에 붙여 넣어 쓸 수 있습니다.

영어판으로는 [SimpleEnglish](https://github.com/AminBlg/SimpleEnglish)가 있습니다. 이 저장소는 그 구조를 빌려 한국어에서 자주 나오는 문제를 다룹니다.

## 고치는 문장

| 스킬이 없을 때 | 스킬을 쓸 때 |
|---|---|
| "판정은 인증 서버가 하고 집행은 사이드카가 합니다" | "인증 서버가 허락할지 정하고, 사이드카가 허락되지 않은 요청을 막습니다" |
| "효과는 린터 점수가 아니라 눈에 보이는 결과로 잽니다" | "효과는 눈에 보이는 결과로 잽니다" |
| "실제로 가까운 시각에 기록이 없었습니다" | "가까운 시각에 기록이 없었습니다" |
| "케이블 교체는 정상적으로 반영되었습니다" | "케이블 교체가 반영되었습니다" |

## 설치

Claude Code에서는 플러그인으로 설치합니다. 스킬과 훅이 같이 들어옵니다.

```bash
claude plugin marketplace add tofutree23/plain-korean
claude plugin install plain-korean@plain-korean
```

Codex에서도 플러그인으로 설치합니다. Codex는 세션을 시작할 때 짧은 규칙 블록을 넣는 훅만 씁니다. 처음 실행할 때 `/hooks`에서 훅을 허용해야 합니다.

```bash
codex plugin marketplace add tofutree23/plain-korean
codex plugin add plain-korean@plain-korean
```

스킬만 필요하면 [skills CLI](https://github.com/vercel-labs/skills)로 받을 수 있습니다. 이 방법으로는 훅이 설치되지 않습니다.

```bash
npx skills add tofutree23/plain-korean
```

스킬도 훅도 쓸 수 없는 도구라면 [`prompts/rules.md`](prompts/rules.md)의 규칙 블록을 `AGENTS.md`나 `.cursorrules`에 붙여 넣습니다.

훅은 Python 3.9 이상이 필요합니다. 외부 패키지는 쓰지 않습니다.

## 들어 있는 것

| 파일 | 하는 일 |
|---|---|
| `skills/writing-plain-korean/SKILL.md` | 쓰는 순서, 번역투 개념어 표, "A가 아니라 B" 꼴과 꾸미는 말을 고치는 법 |
| `skills/writing-plain-korean/scripts/lint_korean.py` | 정규식으로 셀 수 있는 문제를 찾는 린터 |
| `hooks/lint_hook.py` | Claude Code 훅. 린터 결과를 모델에게 알려 줍니다 |
| `hooks/session_start.py` | Codex 훅. 세션 시작 때 규칙 블록을 넣습니다 |
| `prompts/rules.md` | 짧은 규칙 블록 |

## Claude Code 훅이 하는 일

훅은 작업을 막지 않고 알려 주기만 합니다.

- `.md` 파일을 쓰거나 고치면 새로 쓴 부분만 검사합니다. 그래서 다른 사람이 쓴 기존 문장으로 알림이 뜨지 않습니다. `~/.claude` 아래 파일, 경로에 `.claude`가 들어간 파일, 한국어가 적은 파일은 건너뜁니다.
- 답변이 끝나면 답변을 검사해서 화면에 한 줄로 결과를 보여 줍니다. 답을 다시 쓰게 하지는 않습니다.
- 다음 질문을 받을 때 직전 답변에서 걸린 내용을 모델에게 한 번 알려 줍니다. 모델은 다음 답변에서 같은 꼴을 피합니다.

## 린터가 찾는 것

| 규칙 | 예 |
|---|---|
| `concept_word` | "축", "표면", "층", "판정", "집행", "거처", "주체", "분담", "이양", "수렴", "게이트", "어휘" |
| `contrast` | "~가 아니라", "~가 아닌", "~라기보다", "~뿐 아니라" |
| `filler` | "실제로", "정상적으로", "확실히", "제대로", "정확히", "~자체가", "핵심은" |
| `em_dash`, `middle_dot` | "—", "·" |
| `noun_ending` | 본문 문장을 "~함", "~임", "~됨"으로 끝냄 (목록과 제목은 빼고 봅니다) |
| `chain_ui` | "사용자의 권한의 범위" |
| `double_passive` | "되어지다", "~지게 되다" |
| `e_isseoseo` | "~하는 데 있어서", "~에 있어서의" |
| `long_sentence` | 40어절이 넘는 문장 |

코드 블록, 인라인 코드, 인용문, 표, 따옴표 안 문구는 검사하지 않습니다. 따옴표 안은 화면 문구나 예시로 든 말로 봅니다.

```bash
python3 skills/writing-plain-korean/scripts/lint_korean.py 문서.md   # 걸린 것이 있으면 exit 1
python3 skills/writing-plain-korean/scripts/lint_korean.py --json 문서.md
```

## 규칙을 고른 방법

SimpleEnglish 저장소는 50개 넘는 규칙을 넣었다가, 8줄짜리 짧은 프롬프트에 눈에 보이는 결과에서 졌다고 스스로 분석했습니다. 그래서 이 저장소는 규칙을 적게 두고, 각 규칙을 실제 글에 돌려 본 뒤 남겼습니다.

- Claude Code 답변 1540개(약 22만 어절)에서 "아니라"는 1만 어절마다 9번 나왔습니다. 꾸미는 말 중에서는 "실제로"가 8.4번으로 가장 많았고, "정말"이나 "매우" 같은 강조어는 거의 없었습니다.
- 마크다운 문서 134개에 돌려서 잘못 걸리는 경우를 고쳤습니다. 예를 들어 "단계에 있어서"처럼 장소를 말하는 "있다", "짝지어지다" 같은 정상 피동, 따옴표 안 화면 문구가 그랬습니다.
- "다시", "이미", "따로"는 자주 나오지만 대부분 뜻이 있는 말이라 넣지 않았습니다.

린터는 뜻을 모릅니다. 품질 업무의 "판정"처럼 업무 용어가 걸릴 수 있고, 읽는 사람의 오해를 바로잡는 "A가 아니라 B"는 필요한 문장입니다. 훅 안내문도 이런 경우는 그대로 두라고 알려 줍니다.

## 테스트

```bash
python3 -m unittest discover -s tests -v
```

테스트는 이 README, 규칙 블록, SKILL.md가 린터를 통과하는지도 확인합니다.

## 라이선스

MIT
