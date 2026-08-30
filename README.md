# yngfmt

`yngfmt`는 `docs/python-style-guide.ko.md`를 기준으로 동작하는 Python formatter와 linter입니다.

이 repository가 다음 두 항목의 source of truth입니다.

- Python style guide: `docs/python-style-guide.ko.md`
- formatter/linter 구현: `src/yngfmt/`

현재 패키지 버전은 `0.6.0`이며 style guide v4 (260726)를 기준으로 합니다.

외부 Python tooling/industry convention의 참고 출처는 `docs/formatter-reference-sources.md`에서 한 번만 관리합니다. 세부 외부 규칙을 각 style 문서에 복제하지 않습니다.

## 설치

개발 중에는 editable install을 사용합니다.

```bash
python -m pip install -e ".[dev]"
```

릴리스 tag 기준으로 직접 설치할 수도 있습니다.

```bash
python -m pip install "git+https://github.com/yng-min/yngfmt.git@v0.6.0"
```

GitHub Release에는 wheel과 sdist를 첨부하도록 구성합니다.

## 사용

Formatter:

```bash
yngfmt src tests
yngfmt --check src tests
```

Linter:

```bash
ynglint src tests
```

프로젝트별 import/result-object 설정은 가장 가까운 `pyproject.toml`의 `[tool.yngfmt.*]` 설정을 읽습니다.

```toml
[tool.yngfmt.imports]
first-party = ["project"]
language-segment = "language"
config-segment = "config"

[tool.yngfmt.result-object]
class-names = ["Result"]
typed-dict-names = ["ResultDict"]
required-fields = ["error", "code", "message", "data"]
marker-fields = ["error", "code"]
aliases = ["success", "msg", "payload"]
```

## Line length policy

`yngfmt`에는 최대 line length 개념이 없습니다.

- column 수를 기준으로 single-line 코드를 자동으로 줄바꿈하지 않습니다.
- 긴 line을 줄이기 위한 formatter rule을 사용하지 않습니다.
- `--line-length` 옵션을 제공하지 않습니다.
- function call의 single-line/multi-line 판단은 line length가 아니라 style guide에 정의된 argument 수와 expression 구조를 기준으로 합니다.
- 구조적인 call-format rule은 `ynglint`의 `YNG701`~`YNG704`가 검증합니다.

따라서 line이 길다는 이유만으로 formatter가 코드 구조를 변경하는 동작은 허용하지 않습니다.

## 책임 경계

`yngfmt`는 안전하게 자동 수정 가능한 기계적 규칙만 수정합니다.

기본 mechanical whitespace normalization은 pycodestyle/autopep8의 명시적인 rule allowlist만 사용하고, line-length 계열 rule이나 외부 formatter 설정은 사용하지 않습니다.

기계적 whitespace pass와 LibCST custom transform pass는 각각 formatting 전후 AST equivalence를 확인하고, syntax tree가 달라지는 rewrite는 거부합니다. Import ordering은 의도적으로 statement order를 바꾸는 별도 단계이므로 이 equivalence gate와 분리합니다.

`ynglint`는 자동 수정이 위험하지만 정적으로 확실하게 판정 가능한 규칙을 검사합니다.

다음처럼 실행 의미나 프로젝트 문맥이 필요한 판단은 formatter/linter가 억지로 결정하지 않습니다.

- logical stage에 따른 blank line
- local variable type hint 필요 여부
- positional argument를 named argument로 바꿀지 여부
- naming intent
- Result와 exception의 선택
- architecture boundary

## 주요 lint rule

- `YNG101`: 일반 문자열 quote
- `YNG102`: docstring quote
- `YNG103`: dictionary key access quote
- `YNG104`~`YNG108`: docstring layout
- `YNG109`: single-line dictionary spacing
- `YNG201`~`YNG203`: naming
- `YNG301`~`YNG302`: function type annotation
- `YNG400`: import ordering
- `YNG401`~`YNG403`: definition spacing
- `YNG501`~`YNG502`: wrapper/return spacing
- `YNG601`~`YNG603`: result object consistency
- `YNG701`~`YNG704`: function call formatting

상세 규칙과 설계 의도는 `docs/python-style-guide.ko.md`가 최종 기준입니다.

## 버전 관리

`yngfmt`는 패키지 버전을 `pyproject.toml`에서 관리합니다.

- patch: 버그 수정, false positive/negative 수정
- minor: 새로운 formatter/linter rule 추가처럼 기존 프로젝트의 검증 결과가 달라질 수 있는 변경
- major: CLI, 설정, rule contract가 안정된 이후의 호환성 변경

릴리스 tag는 `vX.Y.Z` 형식을 사용하고 tag의 버전과 `pyproject.toml` 버전이 일치해야 합니다.

## 검증

```bash
python -m pip install -e ".[dev]"
pytest
pyright
python -m build
```

GitHub Actions에서 main push와 pull request마다 테스트, Pyright, package build, CLI smoke test를 실행합니다.
