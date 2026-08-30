# Repository Agent Instructions

## Scope

이 repository는 `yngfmt` Python formatter/linter와 Python style guide의 source of truth입니다.

## Mandatory bootstrap

Python 코드나 style guide를 분석, 수정, 생성하기 전에 `docs/python-style-guide.ko.md`를 현재 branch 기준으로 전체 읽고 그대로 적용합니다.

기억, 요약본, 다른 repository의 복사본을 source of truth로 사용하지 않습니다.

## Ownership

- Style contract: `docs/python-style-guide.ko.md`
- Formatter/linter implementation: `src/yngfmt/`
- Tests: `tests/`
- Package/version/dependencies: `pyproject.toml`
- CI/release automation: `.github/workflows/`

Style guide의 규칙이 바뀌면 formatter/linter로 안전하게 자동화 가능한 범위가 변하는지 함께 검토합니다.

기계적으로 확실하게 판정할 수 없는 semantic rule을 억지로 formatter/linter에 넣지 않습니다.

## Changes

- behavior를 바꾸는 lint/format rule 추가는 package version 영향까지 검토합니다.
- formatter는 source semantics를 보존할 수 있는 변경만 자동 수행합니다.
- linter는 false positive 가능성이 높은 규칙을 Error로 만들지 않습니다.
- public CLI (`yngfmt`, `ynglint`)와 `pyproject.toml` 설정 호환성을 보존합니다.
- style guide와 구현이 어긋나면 둘 중 하나를 임의로 맞추지 말고 owning rule을 기준으로 일관되게 수정합니다.

## Validation

변경 후 최소한 다음을 실행합니다.

```bash
python -m pip install -e ".[dev]"
pytest
pyright
python -m build
```

formatter/linter rule을 바꿨다면 positive/negative regression test를 함께 추가합니다.

실행하지 못한 검증은 성공했다고 보고하지 않습니다.

## Release

- package version source of truth는 `pyproject.toml`입니다.
- release tag는 `vX.Y.Z` 형식을 사용합니다.
- tag와 package version은 반드시 일치해야 합니다.
- 특별한 지시가 없으면 완료된 변경은 commit/push 대상입니다.
