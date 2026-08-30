# Formatter Reference Sources

`yngfmt`의 기계적 Python formatting baseline은 아래 공개 자료를 참고합니다.

- PEP 8 — Style Guide for Python Code: https://peps.python.org/pep-0008/
- pycodestyle: https://pycodestyle.pycqa.org/
- autopep8: https://github.com/hhatto/autopep8
- LibCST: https://libcst.readthedocs.io/

이 자료들은 참고 출처이며 `docs/python-style-guide.ko.md`보다 우선하지 않습니다.

특히 PEP 8 또는 외부 formatter의 maximum line length, width-based wrapping, trailing-comma-driven layout처럼 `yngmin’s Python Style Guide`와 충돌하는 규칙은 채택하지 않습니다.

외부 기준의 세부 규칙을 style guide에 반복해서 복제하지 않고, 프로젝트 고유 규칙과 외부 기준이 충돌하는 지점만 canonical style guide에서 명시합니다.
