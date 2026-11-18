# 변경 기록

버전은 [Semantic Versioning](https://semver.org/lang/ko/)을 따릅니다. 새 버전을 낼 때는 `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `SKILL.md`의 버전을 같이 올리고 이 파일에 기록합니다. 테스트가 네 곳의 버전이 같은지 확인합니다.

## 1.0.0 (2026-11-18)

첫 공개 판입니다.

- `writing-plain-korean` 스킬: 쓰는 순서, 번역투 개념어 표, "A가 아니라 B" 꼴과 꾸미는 말을 고치는 법
- `lint_korean.py` 린터: 규칙 11개, 자체 테스트 예시 35개
- Claude Code 훅: `.md` 파일에 새로 쓴 부분 검사, 답변 검사 결과를 다음 답변에 전달
- Codex 훅: 세션 시작 때 짧은 규칙 블록 넣기
