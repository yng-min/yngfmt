# yngmin’s Python Style Guide (Korean) - v5 (260830)

> 코드 스타일, 설계 원칙 및 코딩 컨벤션
> 

## 0. 설계 철학

본 스타일 가이드는 특정 표준을 엄격히 따르는 것보다 가독성, 유지보수성, 일관성을 우선합니다.

주된 목표는 실행 흐름, 설계 의도, 프로젝트 구조가 즉시 드러나도록 만드는 것입니다. 이를 통해 개발, 디버깅, 코드 리뷰, 장기 유지보수 과정에서 필요한 인지 비용을 줄입니다.

또한 코드는 구현 위치보다 역할과 책임을 우선하여 구성하며, 각 구성 요소는 명확한 책임과 변경 이유를 가져야 합니다.

본 컨벤션은 실전 프로젝트 경험, 코드 리딩, 프로젝트 분석, 반복적인 유지보수 과정을 통해 정립되었습니다. 새로운 패턴이나 더 나은 방식이 발견되면 계속 수정될 수 있습니다.

본 문서의 규칙은 기계적으로 지키기 위한 것이 아니라, 각 규칙은 컨텍스트를 보존하고, 모호성을 줄이며, 이후 변경을 더 안전하게 만들기 위해 존재합니다.

---

## 1. 기본 스타일

| 항목 | 규칙 |
| --- | --- |
| String | 큰따옴표(`"`) 사용 |
| Docstring quotes | 큰따옴표 3개(`"""`) 사용 |
| Dictionary key access | 작은따옴표(`'`) 사용 |
| Dictionary literal spacing | 비어 있지 않은 single-line dictionary literal은 여는 중괄호 뒤와 닫는 중괄호 앞에 각각 **1 space**를 두며, 빈 dictionary literal은 `{}`로 작성 |
| Indentation | 4 spaces 사용 |
| Tabs | 사용하지 않음 |

일반 문자열과 `Literal["value"]` 같은 type subscript의 문자열은 큰따옴표를 사용한다. 작은따옴표는 `data['key']`처럼 실제 dictionary key access에만 사용한다.

---

## 1.1 Formatter 정책

기계적으로 처리 가능한 규칙은 가능한 한 formatter를 통해 적용한다.

개발자는 코드 작성 중 따옴표, 들여쓰기, 단순 spacing과 같은 기계적 규칙을 직접 맞추기보다 formatter와 linter를 신뢰한다.

기계적 포맷팅은 자동화 도구가 담당하고, 본 문서는 컨벤션, 설계 의도, 프로젝트 수준의 일관성을 설명하는 것을 목표로 한다.

단, formatter가 세밀하게 표현하지 못하는 개인 컨벤션은 linter 또는 전용 검사기에서 보조적으로 검증한다.

---

## 2. Docstring 배치

| 항목 | 규칙 |
| --- | --- |
| Module docstring | 파일 최상단에 배치하고, 닫는 큰따옴표 3개 아래에 **1 blank line** 유지 |
| Class docstring | class 선언 직후에 배치하며, docstring과 첫 method 사이에는 **blank line을 넣지 않음** |
| Function / method docstring | 선언문 직후에 배치하며, docstring과 body 사이에는 **blank line을 넣지 않음** |

### 2.1 Module Docstring

```python
"""
Project description.
"""

from pathlib import Path
from typing import Any
```

### 2.2 Class Docstring

```python
class ArticleService:
    """
    Manage article processing and rendering.
    """
    def __init__(self, repository: ArticleRepository) -> None:
        self.repository: ArticleRepository = repository
```

### 2.3 Function / Method Docstring

```python
def get_article(article_id: int) -> Article:
    """
    Return an article by ID.
    """
    article: Article | None = repository.find_by_id(article_id=article_id)

    return article
```

---

## 3. Blank Line 규칙

| 항목 | 규칙 |
| --- | --- |
| Top-level definition spacing | 최상위 class와 function 선언 전에는 **2 blank lines** 유지 |
| Class method spacing | class 내부의 인접한 method 선언 사이에는 **1 blank line** 유지<br><br>단, class docstring 바로 다음 첫 method에는 **blank line을 넣지 않음** |
| Function body spacing | function 또는 method 선언 직후에는 **blank line을 넣지 않음**<br><br>docstring 아래에도 **blank line을 넣지 않음**<br><br>body 내부의 blank line은 logical stage를 구분할 때만 사용 |
| Control flow block spacing | `if`, `for`, `while`, `try` 블록 이후 다음 statement가 별도의 logical block으로 넘어가는 경우에만 **1 blank line** 유지 |

### 3.1 Top-level Definition Spacing

최상위 class와 function 선언 전에는 2 blank lines를 유지한다.

파일의 첫 번째 최상위 선언에는 선행 blank line을 요구하지 않는다.

decorator가 있는 경우 decorator를 선언의 시작으로 취급한다.

예시:

```python
def load_config() -> Config:
    ...


def run() -> None:
    ...


class Application:
    ...
```

### 3.2 Function Body Spacing

function 또는 method body는 선언문 또는 docstring 바로 다음에서 시작한다.

function 선언과 첫 번째 statement 사이에는 blank line을 넣지 않는다.

docstring과 body의 첫 번째 statement 사이에도 blank line을 넣지 않는다.

예시:

```python
def process(data: Data) -> Result:
    validated_data = validate(data=data)
    return build_result(validated_data=validated_data)
```

```python
def process(data: Data) -> Result:
    """
    Process data and return a result.
    """
    validated_data = validate(data=data)
    return build_result(validated_data=validated_data)
```

### 3.3 Logical Block Spacing

Blank line은 단순히 코드를 보기 좋게 꾸미기 위한 용도가 아니라, 처리 단계의 경계를 표현하기 위해 사용한다.

코드가 새로운 논리 단계로 넘어갈 때 1 blank line을 둔다.

`if`, `for`, `while`, `try` 블록 이후 다음 statement가 별도의 logical block으로 넘어가는 경우에만 1 blank line을 둔다. 단순히 같은 처리 흐름의 연속이거나, 직전 블록의 결과를 바로 반환하는 경우에는 blank line을 강제하지 않는다.

모든 작은 작업을 기계적으로 분리하지 않는다. 함수 또는 method가 짧고 직선적인 흐름이며 검증, 분기, 예외 처리 단계가 없다면 body를 컴팩트하게 유지한다.

대표적인 논리 단계는 다음과 같다.

- 초기화
- 검증
- 데이터 가공
- 외부 API 호출
- 데이터베이스 또는 저장소 작업
- 예외 처리
- 최종 결과 생성

> **설계 의도**
> 

> Logical block spacing은 실행 흐름을 한눈에 보이게 만든다.
> 

> 디버깅, 리뷰, 장기 유지보수 과정에서 컨텍스트를 따라가는 비용을 줄인다. 목표는 의미 있는 처리 단계를 드러내되, 단순한 직선 흐름의 함수를 불필요하게 장황하게 만들지 않는 것이다.
> 

### 3.4 Return Spacing

`return`은 새로운 logical block의 시작이 아니라 현재 logical block의 종료로 취급한다.

직전 계산, 갱신 또는 함수 호출 결과를 바로 반환하는 경우 `return` 위에 blank line을 넣지 않는다.

검증, 예외 처리 등 이전 논리 단계와 반환을 구분해야 하는 경우에만 `return` 위에 blank line을 둘 수 있다.

> **설계 의도**
> 

> `return`은 현재 처리 단계의 결론인 경우가 많다.
> 

> 반환값을 만든 문장과 `return`을 붙여두면 흐름이 끊기지 않는다. blank line은 검증, 예외 처리, 다른 logical block 이후 별도의 최종 반환 단계가 필요할 때만 사용한다.
> 

예시:

```python
result = process(data=data)
return result
```

```python
await self.prepare()
return await self.execute(...)
```

```python
if article is None:
    raise ApplicationError("Article not found")

return article
```

### 3.5 반복되는 독립 작업

반복되는 작업이 각각 독립적인 의미를 가진다면 작업 단위마다 1 blank line으로 구분한다.

대표적인 예시는 다음과 같다.

- 반복되는 설정 등록
- 반복되는 리소스 등록
- 반복되는 객체 생성
- 독립적인 초기화 작업

> **설계 의도**
> 

> 반복 작업은 각각 의미가 분리되어 있더라도 시각적으로 빽빽해 보일 수 있다.
> 

> 작업 단위마다 구분하면 반복 패턴은 유지하면서도 훑어보기 쉬워진다. 각 호출이 독립적인 항목을 나타내는 설정 코드, 등록 코드, 초기화 코드에서 특히 유용하다.
> 

예시:

```python
config.add_argument(...)

config.add_argument(...)

config.add_argument(...)
```

### 3.6 짧은 Wrapper Method

단순한 wrapper method는 최대한 압축된 형태를 유지한다.

준비 작업 한 단계와 위임 호출 한 단계로 이루어진 경우 불필요한 blank line을 사용하지 않는다.

> **설계 의도**
> 

> 짧은 wrapper method는 복잡한 처리가 아니라 위임을 표현하기 위한 경우가 많다.
> 

> 압축된 형태를 유지하면 의도가 즉시 드러난다. 불필요한 blank line은 단순한 wrapper를 실제보다 복잡하게 보이게 만들 수 있다.
> 

예시:

```python
def build(self) -> Response:
    self.initialize()
    return self.builder.build()
```

```python
async def execute(self, request: Request) -> Response:
    await self.validate(request=request)
    return await self.handler.execute(request=request)
```

### 3.7 Dictionary Literal Spacing

비어 있지 않은 single-line dictionary literal은 여는 중괄호(`{`)와 첫 번째 항목 사이, 마지막 항목과 닫는 중괄호(`}`) 사이에 각각 **1 space**를 둔다.

빈 dictionary literal은 내부 공백 없이 `{}`로 작성한다.

> **설계 의도**
> 

> Single-line dictionary literal의 경계를 시각적으로 분리하여 dictionary 내부의 key-value 항목을 쉽게 구분할 수 있도록 한다.
> 

> 빈 dictionary literal은 내부 항목이 없으므로 불필요한 공백을 추가하지 않는다.
> 

예시:

```python
user = { "name": "test" }
options = { "enabled": True, "timeout": 10 }
empty_data = {}
```

여러 줄로 작성하는 dictionary literal에는 이 규칙을 적용하지 않는다.

```python
user = {
    "name": "test",
    "enabled": True,
}
```

### 3.8 줄바꿈

Dictionary literal, list literal, function argument, chained expression은 여러 줄로 펼쳤을 때 의미 구조와 처리 단계를 더 명확하게 드러낼 수 있다면 multi-line 형태로 작성할 수 있다.

줄바꿈 여부는 고정된 line length가 아니라 다음 기준을 바탕으로 판단한다.

- 표현식이 자체적인 내부 구조를 가지는가
- 여러 값이나 처리 단계의 경계를 구분할 필요가 있는가
- 중첩 호출, collection literal, comprehension, 조건식, 연산식 등이 포함되어 있는가
- 주석이나 설명을 보존하기 위해 별도의 줄이 필요한가

느슨한 기준으로, **dictionary literal의 key가 5개 이상이면 multi-line 형태를 우선 고려한다.** 단, 이는 **강제 규칙이 아니다.**

인자가 하나인 function call은 해당 인자가 단순한 값이나 참조인 경우 single-line 형태를 기본으로 한다.

```python
result = service.process(article=article)
repository.save(data)
```

유일한 인자가 중첩 호출, collection literal, comprehension, 조건식, 연산식처럼 자체적인 구조를 가진다면 multi-line 형태를 사용할 수 있다.

```python
result = service.process(
    article=create_article(
        metadata=metadata,
        content=content,
    ),
)
```

```python
service.process(
    options={
        "enabled": True,
        "timeout": 10,
    },
)
```

줄바꿈 여부를 판단할 때 line length는 독립적인 기준으로 사용하지 않는다.

한 줄의 길이가 짧거나 길다는 사실만으로 표현식을 접거나 펼치지 않는다.

> **설계 의도**
> 

> 가독성은 문자 수보다 문맥과 표현식의 구조에 따라 달라진다. 줄바꿈은 고정된 최대 길이를 맞추기 위한 것이 아니라, 논리 구조와 처리 단계의 경계를 드러내고 복잡한 표현식을 더 쉽게 읽을 수 있도록 하기 위해 사용한다.
> 

---

## 4. 네이밍 규칙

이름은 구현 타입만 설명하는 것이 아니라 책임, 역할, 의도를 전달해야 한다.

> **설계 의도**
> 

> 명확한 이름은 코드를 읽을 때 컨텍스트를 반복해서 다시 추론해야 하는 비용을 줄인다. 특히 하나의 값이 여러 처리 단계를 거칠 때 중요하다.
> 

### 4.1 설명적인 변수명

변수명은 역할이 명확해진다면 길어져도 괜찮다.

값이 여러 logical stage에서 사용된다면 짧은 축약어보다 의미가 드러나는 이름을 우선한다.

예시:

```python
user_profile = UserRepository().get_user_profile(...)
locale_settings = LocaleLoader().load(...)
```

### 4.2 짧은 임시 변수

한 글자 또는 매우 짧은 변수명은 생명주기가 짧은 scope에서만 사용한다.

대표적인 예시는 다음과 같다.

- 반복문 변수
- 예외 변수
- 임시 파일명 변수
- 매우 짧은 지역 변환용 변수

예시:

```python
for field in fields:
    validate(field=field)
```

### 4.3 Class 네이밍

Class는 **PascalCase 명사**로 작성한다.

Private class의 선행 underscore(`_`)는 visibility marker로 취급하며 이름 형식 검사에서는 제외한다. 따라서 `_InternalCache`는 `InternalCache`에 기존 PascalCase 규칙을 그대로 적용한다. 별도의 private-class naming convention을 만들지 않는다.

Class 이름은 해당 class가 나타내는 객체, 서비스, builder, manager, domain concept를 설명해야 한다.

예시:

```python
class DatabaseArticle:
    ...

class ConfigurationLoader:
    ...
```

### 4.4 Function / Method 네이밍

Function과 method는 **snake_case 동사 또는 동사구**로 작성한다.

이름은 해당 함수가 수행하는 동작을 설명해야 한다.

예시:

```python
def parse_args(...):
    ...

def get_article_title(...):
    ...
```

### 4.5 Boolean 네이밍

Boolean 값은 조건이나 상태가 명확히 드러나는 이름을 사용한다.

필요하다면 `is_`, `has_`, `can_`, `should_` 같은 prefix나 상태를 나타내는 이름을 사용한다.

예시:

```python
is_private: bool = False
has_attachment: bool = True
```

### 4.6 Type annotation이 있는 변수명

Type annotation을 사용하더라도 변수명에는 값의 의미적 역할이 드러나야 한다.

타입 힌트만으로 변수의 의미를 대신 설명하지 않는다.

예시:

```python
article_metadata: dict[str, Any] = article.metadata
```

### 4.7 Config 네이밍

설정값을 구조화하여 보관하는 설정 객체는 `_config` suffix를 사용한다.

prefix에는 해당 설정이 무엇에 대한 설정인지 드러나야 한다.

예시:

```python
path_config: PathConfig
runtime_config = RuntimeConfig()
color_map_config: ColorMapConfig = load_color_map_config()
```

설정을 읽거나 해석하거나 생성하거나 제공하는 역할의 객체에는 이 규칙을 적용하지 않는다.

```python
config_loader = ConfigLoader()
config_parser = ConfigParser()
config_builder = ConfigBuilder()
config_provider = ConfigProvider()
```

설정 데이터 객체와 설정을 처리하는 객체는 이름만으로 구분할 수 있어야 한다.

> **설계 의도**
> 

> `_config` suffix는 설정값을 보관하는 데이터 객체를 명확하게 식별하기 위해 사용한다.
> 

> 설정을 처리하는 loader, parser, builder, provider 등의 역할까지 `_config`로 통일하면 객체의 실제 책임이 흐려질 수 있으므로 구분한다.
> 

### 4.8 Named Argument Preference

Function 또는 method 호출 시에는 positional argument보다 named argument 사용을 기본으로 한다.

특히 동일한 타입의 인자가 여러 개 존재하거나, boolean 값, 설정값, 옵션값이 포함된 경우에는 named argument 사용을 권장한다.

`True`와 `False` 같은 boolean literal은 값 자체만으로 의미를 설명하지 못하므로 원칙적으로 named argument로 전달한다.

```python
create_user(
    user_id=user_id,
    is_admin=True,
)

request.execute(should_retry=False)
```

다음과 같이 boolean literal을 positional argument로 전달하는 것은 권장하지 않는다.

```python
create_user(user_id, True)
request.execute(False)
```

변수나 expression을 통해 전달되는 boolean 값은 호출부의 문맥과 API 관례를 함께 고려한다.

```python
create_user(
    user_id=user_id,
    is_admin=is_admin,
)
```

다만 Python 표준 라이브러리, 내장 함수, 외부 라이브러리 등에서 positional argument 사용이 일반적인 경우에는 해당 라이브러리의 관례를 따른다.

> **설계 의도**
> 

> 호출부만 읽어도 어떤 값이 어떤 의미로 전달되는지 즉시 파악할 수 있어야 한다.
> 

> Named argument는 코드 탐색 비용을 줄이고, parameter 순서 변경에 대한 안정성을 높이며, boolean argument와 설정값의 의미를 명확하게 드러낸다.
> 

예시:

```python
user = service.create_user(
    user_id=user_id,
    nickname=nickname,
    is_admin=is_admin,
)
```

### 4.8.1 Function Call Formatting

Function call의 single-line 또는 multi-line 형태는 전역 line length가 아니라 expression 구조와 인접한 호출의 일관성을 기준으로 결정한다.

인자 수 자체는 multi-line의 이유가 아니다. 인자가 여러 개여도 모든 argument가 flat simple expression이면 single-line을 기본으로 한다.

Flat simple expression에는 단순 값/참조뿐 아니라 내부에 nested call, collection, conditional 등 별도 구조가 없는 평평한 arithmetic, comparison, boolean expression을 포함한다.

```python
self.assertEqual(comparison_process.returncode, 0, comparison_process.stdout + comparison_process.stderr)
process(first + second + third, lower <= value < upper)
```

반대로 nested call, collection/comprehension, conditional, lambda, multi-line string, 설명 주석, `*args`/`**kwargs`처럼 실제 내부 구조가 있으면 multi-line을 유지할 수 있다.

```python
process(
    first,
    build_value(
        enabled=True,
        timeout=10,
    ),
)
```

이미 nested expression 안에서 여러 인자로 펼쳐진 call은 일반적인 formatter pass에서 억지로 접지 않는다. 구조가 드러나는 현재 표현을 유지한다.

Zero-argument call은 call 자체를 `method()` 형태로 유지한다. Receiver expression이 여러 줄이라는 이유만으로 zero-argument call 자체가 multi-line call이 되는 것은 아니다.

```python
return (
    project_directory
    / "Assets"
    / "Audio"
).as_posix()
```

### 4.8.2 Homogeneous Call Run

같은 receiver에서 같은 method family가 다른 statement 없이 연속되면 하나의 homogeneous call run으로 취급한다.

CamelCase method는 첫 대문자 전 prefix, snake_case method는 첫 underscore 전 prefix를 method family로 본다. 예를 들어 `self.assertEqual`, `self.assertIn`은 같은 `self.assert*` family이며 `client.get_value`, `client.get_other`는 같은 `client.get_*` family다.

동일 run에서는 가능한 호출의 shape을 일관되게 맞춘다. 일반 규칙상 nested structure 때문에 multi-line인 call도, 주석과 multi-line string을 훼손하지 않고 한 줄로 안전하게 표현할 수 있으며 결과가 지나치게 길지 않다면 compact할 수 있다.

```python
self.assertIn("first", output)
self.assertEqual(actual, build_expected(enabled=True, timeout=10))
self.assertIn("second", output)
```

이 일관성 보정에서만 compact 결과가 **200자 이하인지** 확인하는 제한적인 guard를 사용한다. 이는 전역 maximum line length가 아니며 일반 코드의 줄바꿈 기준으로 사용하지 않는다.

200자를 넘거나 comment/multi-line string 보존이 필요한 경우에는 해당 call의 multi-line 구조를 유지한다. 일관성을 이유로 의미 구조를 손상시키거나 비정상적으로 긴 한 줄을 만들지 않는다.

> **운영 기준**
>
> Single-line call에는 trailing comma를 사용하지 않는다.
>
> Multi-line call에는 마지막 argument 뒤에도 trailing comma를 사용한다.

---

## 5. Type Hint 정책

Type hint는 모든 값을 기계적으로 표시하기 위한 것이 아니라, 값의 역할과 구조를 명확히 드러내기 위해 사용한다.

함수 또는 method의 parameter와 return type은 가능한 한 명시한다.

지역 변수 또한 정적 타입 분석 도구가 안정적으로 추론할 수 있도록 type hint를 명시하는 것을 기본으로 한다.

설정값, 저장소 응답, 요청 결과, 파싱 결과처럼 구조가 복잡하거나 여러 logical stage에서 사용되는 값은 type hint를 우선 사용한다.

다만 반복 변수, 예외 변수, 매우 짧은 생명주기를 가지는 임시 변수처럼 타입과 역할이 즉시 드러나는 경우에는 type hint를 생략할 수 있다.

> **운영 기준**
> 

> 본 프로젝트는 `Pyright Standard` 기준에서 경고 없이 동작하는 코드를 기본 목표로 한다.
> 

> 또한 가능한 경우 정적 타입 정보를 적극적으로 명시하며, 반복 변수, 예외 변수, 매우 짧은 생명주기를 가지는 임시 변수를 제외한 동적 타이핑 스타일은 권장하지 않는다.
> 

> 동적 타이핑은 작은 스크립트, 빠른 프로토타이핑, 외부 라이브러리 제약, 점진적 마이그레이션 등 정당한 이유가 존재하는 경우에 한해 제한적으로 허용할 수 있다.
> 

### 5.1 Dictionary Type Hint

JSON-like dictionary는 기본적으로 `dict[str, Any]`를 사용한다.

`dict[Any, Any]`는 key type이 실제로 여러 타입이거나, key type을 특정할 수 없는 경우에만 사용한다.

### 5.2 Annotated Alias

`Annotated` alias는 동일한 primitive type이라도 의미, 포맷, 사용 목적을 구분해야 할 때 사용한다.

Alias 이름은 번호보다 용도 중심으로 작성한다.

> **설계 의도**
> 

> Type hint는 코드의 모든 값을 장식하기 위한 것이 아니라, 읽는 사람이 값의 구조와 책임을 다시 추론하지 않도록 하기 위한 장치다.
> 

> 특히 입력값, 저장소 응답, 요청 결과, 파싱 결과처럼 값의 형태가 코드만으로 즉시 드러나지 않는 경우 type hint를 통해 컨텍스트를 보존한다.
> 

---

## 6. Result Object Convention

Result object field consistency의 자동 검사(`YNG601`~`YNG603`)는 전역 Python 규칙이 아니다. 프로젝트가 `[tool.yngfmt.result-object]`를 명시적으로 설정한 경우에만 해당 프로젝트 convention으로 활성화한다.

Result object는 dictionary 기반으로도 사용할 수 있지만, `dataclass`, `TypedDict`, `StrEnum` 등을 사용한 구조화된 result object를 우선 고려한다.

Dictionary 기반 result object는 작은 프로젝트, 빠른 구현, 기존 코드와의 호환, 점진적 마이그레이션 상황에서 사용할 수 있다.

### 6.1 구조화된 Result Object

Result object가 프로젝트 전반에서 반복적으로 사용된다면 dictionary보다 구조화된 object를 우선 고려한다.

구조화된 result object는 필드 일관성, 타입 안정성, IDE 지원, 리팩터링 안정성 면에서 유리하다.

API, 데이터베이스, 저장소, 외부 서비스와 상호작용하는 작업은 호출부에서 데이터와 실행 상태를 함께 판단해야 하는 경우 구조화된 result object로 반환한다.

Result object는 상태 정보와 필요한 경우 실제 반환 데이터를 함께 포함해야 한다.

예시:

```python
from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar


T = TypeVar("T")


class ResultCode(StrEnum):
    SUCCESS = "SUCCESS"
    IGNORED = "IGNORED"
    FAILED = "FAILED"


@dataclass(slots=True)
class Result(Generic[T]):
    error: bool
    code: ResultCode
    message: str
    data: T | None = None
```

사용 예시:

```python
return Result(
    error=False,
    code=ResultCode.SUCCESS,
    message="Successfully processed the request.",
    data=data,
)
```

대표적인 필드는 다음과 같다.

- `error`: 작업 실패 여부
- `code`: 기계적으로 처리할 수 있는 상태 코드
- `message`: 사람이 읽을 수 있는 설명
- `data`: 실제 반환 데이터

> **설계 의도**
> 

> 호출부는 반환값 자체뿐만 아니라 작업이 어떤 상태로 끝났는지도 알아야 하는 경우가 많다.
> 

> 결과를 상태 컨텍스트와 함께 감싸면 성공, 실패, 무시, 정상적인 비처리 케이스를 일관되게 다루기 쉬워진다. 또한 예외적인 실패와 조건상 정상적으로 스킵된 상황을 분리할 수 있다.
> 

### 6.2 Dictionary 기반 Result Object

가볍게 구조를 유지하는 것이 엄격한 타입 안정성보다 중요한 경우 dictionary 기반 result object를 사용할 수 있다.

예시:

```python
return {
    "error": False,
    "code": "SUCCESS",
    "message": "Successfully processed the request.",
    "data": data,
}
```

조건이 충족되지 않아 정상적으로 무시되는 경우는 에러가 아니라 명시적인 상태로 표현한다.

```python
return {
    "error": False,
    "code": "IGNORED",
    "message": "The condition was not met.",
    "data": None,
}
```

작업을 안전하게 계속할 수 없는 예외적인 실패는 여전히 exception으로 처리할 수 있다.

설계 원칙은 동일하다. 호출부가 데이터와 실행 상태를 모두 필요로 한다면, 둘을 함께 반환한다.

---

## 7. Exception Policy

Result object와 exception은 서로 대체 관계가 아니라, 실패를 다루는 목적이 다르다.

호출부가 다음 행동을 선택할 수 있으면 Result object로 반환한다.

호출부가 안전하게 복구할 수 없거나 프로그램의 불변식이 깨졌다면 exception으로 처리한다.

| 상황 | 권장 처리 |
| --- | --- |
| 정상 성공 | `Result(error=False, code=SUCCESS)` |
| 조건 미충족으로 인한 정상 스킵 | `Result(error=False, code=IGNORED)` |
| 호출자가 복구 가능한 실패 | `Result(error=True, code=FAILED)` |
| 호출자가 복구 불가능한 실패 | exception |
| 프로그래머 실수 | exception |
| 잘못된 인자 / 불변식 위반 | `ValueError` 또는 domain exception |
| 외부 API 일시 실패 | retry 후 Result 또는 retryable exception |
| DB 연결 실패 / schema mismatch | exception |

> **설계 의도**
> 

> Result object는 호출부의 의사결정을 돕기 위한 반환 구조다.
> 

> Exception은 현재 실행 흐름을 안전하게 유지할 수 없을 때 사용한다. 두 방식을 명확히 구분하면 정상적인 비처리 케이스와 실제 실패를 혼동하지 않을 수 있다.
> 

---

## 8. Architecture Boundary

코드는 파일 위치보다 **책임**과 **변경 이유**를 기준으로 배치한다.

어떤 코드가 어느 계층에 속하는지 판단할 때는 "어디에서 호출되는가"보다 "무엇 때문에 변경되는가"를 우선한다.

예를 들어 입력 이벤트에서 호출되는 코드라도, 실제 책임이 저장소 접근이라면 application이 아니라 infrastructure에 가까운 코드다.

반대로 외부 client를 호출하더라도, 호출 순서와 use case 흐름을 조립하는 코드라면 application에 가까운 코드다.

> **설계 의도**
> 

> 프로젝트 구조는 폴더 이름을 맞추기 위한 장식이 아니라 변경 비용을 줄이기 위한 장치다.
> 

> 변경 이유가 같은 코드는 가까운 곳에 두고, 변경 이유가 다른 코드는 분리한다.
> 

### 8.1 Layer Responsibility

- **application**: 실행 흐름과 use case 조립을 담당한다.
- **domain**: 핵심 규칙과 도메인 개념을 담당한다.
- **infrastructure**: 저장소, 파일 시스템, HTTP client, 외부 API, storage 등 외부 시스템과의 연결을 담당한다.
- **exception**: 예외 타입과 예외 처리 정책을 담당한다.
- **logging**: 기록 방식과 로그 출력을 담당한다.
- **config**: 설정값과 실행 옵션을 담당한다.
- **language**: 다국어 문구와 문자열 치환을 담당한다.

### 8.2 Placement Rule

하나의 코드가 여러 책임을 동시에 가진다면, **변경 이유가 가장 강한 계층**을 기준으로 배치한다.

서로 다른 변경 이유가 한 객체에 계속 섞이면 별도 객체로 분리한다.

### 8.3 Boundary Smell

다음 경우는 책임 경계가 섞였을 가능성이 높다.

- application 코드가 저장 방식이나 요청 세부 구현을 직접 다룬다.
- infrastructure 코드가 use case의 의사결정 흐름을 판단한다.
- config 코드가 설정값 제공을 넘어 실제 작업을 수행한다.
- logging 코드가 기록 외에 기능 흐름을 변경한다.
- language 코드가 문자열 치환이나 locale 선택을 넘어, 비즈니스 규칙이나 use case 흐름을 판단한다.
- 하나의 class가 입력 처리, 저장, 예외 처리, 메시지 생성까지 모두 담당한다.

> **운영 기준**
> 

> 책임 경계가 애매할 때는 "이 코드가 바뀌는 이유는 무엇인가?"를 먼저 확인한다.
> 

> 변경 이유가 다르면 분리하고, 변경 이유가 같으면 같은 계층 안에서 관리한다.
> 

### 8.4 General Layer Model

위 segment들은 프로젝트 구조에 맞춘 예시이며, 보다 일반적인 계층 책임은 다음과 같이 해석할 수 있다.

- View / Controller 계층은 입력을 해석하고 작업을 위임한다.
- Application / Service 계층은 Use Case의 흐름을 조율한다.
- Domain 계층은 핵심 비즈니스 규칙과 도메인 개념을 표현한다.
- Infrastructure 계층은 Database, Storage, HTTP Client, 외부 API 등 구체적인 구현을 담당한다.
- 하위 계층의 구현 세부사항이 상위 계층의 의사결정 로직으로 새어 나오지 않도록 한다.

> **설계 의도**
> 

> 책임을 명확히 분리하면 결합도를 낮추고, 코드의 이해와 변경을 쉽게 만들 수 있다. 각 계층은 명확한 인터페이스를 통해 협력하며, 불필요하게 서로의 구현 세부사항에 의존하지 않아야 한다.
> 

---

## 9. Import 규칙

### 9.1 Import 그룹 순서

1. Standard Library
2. Third-party library
3. First-party package

Standard Library 그룹과 Third-party library 그룹 사이에는 **1 blank line**을 둔다.

Third-party library 그룹과 First-party package 그룹 사이에는 **1 blank line**을 둔다.

마지막 import 그룹과 main code 사이에는 **2 blank lines**를 둔다.

> **설계 의도**
> 

> Import section은 해당 파일의 의존성을 압축해서 보여주는 지도 역할을 해야 한다.
> 

> import를 출처와 프로젝트 레이어 기준으로 그룹화하면 구현부를 읽기 전에 파일이 프로젝트 전체와 어떤 관계를 가지는지 이해하기 쉬워진다.
> 

### 9.2 Standard Library와 Third-party Library

Standard Library import와 Third-party library import는 서로 다른 그룹으로 취급한다.

각 그룹 내부에서는 blank line을 사용하지 않는다.

서로 다른 라이브러리는 알파벳 오름차순(A to Z)으로 정렬한다.

#### 9.2.1 Import 타입

- 각 그룹 내부에서 `from ... import ...` 문은 `import ...` 문보다 위에 배치한다.
- `import ...` 문은 항상 해당 그룹의 가장 아래에 배치한다.

> **설계 의도**
> 

> 본 컨벤션은 필요한 의존성을 명시적으로 드러내기 위해 `from ... import ...`를 우선 사용한다.
> 

> `import ...`는 module namespace 자체가 의미를 가지거나, 개별 import가 오히려 가독성을 해치는 경우에만 사용한다.
> 

> 필요한 객체를 직접 import하면 파일이 실제로 무엇에 의존하는지 import section만으로도 빠르게 파악할 수 있다.
> 

> 따라서 `import ...` 문은 예외적인 경우로 취급하며, 같은 그룹 내부에서는 항상 `from ... import ...` 문보다 아래에 배치한다.
> 

이 규칙은 일반적인 import sorter 기본값과 다를 수 있으므로, 자동화 시 전용 설정 또는 custom checker를 사용한다.

#### 9.2.2 Root Module 그룹화

같은 Root Module을 공유하는 import는 하나의 그룹으로 취급한다.

예시:

```python
from package import A
from package.subpackage import B
```

#### 9.2.3 같은 Root Module 내부 정렬

같은 Root Module 내부에서는 다음 순서로 정렬한다.

1. module depth가 낮은 import
2. module depth가 높은 import

#### 9.2.4 Root Module 정렬

서로 다른 Root Module은 알파벳 오름차순(A to Z)으로 정렬한다.

### 9.3 내부 패키지

내부 패키지는 Root Package 다음의 첫 번째 segment를 기준으로 그룹화한다.

segment가 바뀌면 **1 blank line**을 추가한다.

#### 9.3.1 프로젝트 계층 Segment

프로젝트 계층 segment는 고정된 정적 자산으로 관리하지 않는다. Root Package 다음의 첫 번째 segment를 기준으로 동적으로 감지한다.

대표적인 프로젝트 계층 segment 예시는 다음과 같다.

- `application`
- `domain`
- `service`
- `interface`
- `infrastructure`
- `database`
- `repository`
- `model`
- `schema`
- `exception`
- `logging`
- `utils`

위 항목들은 예시일 뿐이다. 새로 생성된 계층도 동일한 그룹화 규칙에 따라 자동으로 처리한다.

#### 9.3.2 예약 Segment

- `language`는 항상 내부 패키지 그룹의 가장 위에 배치한다.
- `config`는 항상 내부 패키지 그룹의 가장 아래에 배치한다.
- `config` 그룹 앞에는 **2 blank lines**를 둔다.

#### 9.3.3 일반 Segment

예약 segment가 아닌 모든 segment는 알파벳 오름차순(A to Z)으로 정렬한다.

이 규칙은 별도 설정 없이 새로 생성된 segment에도 자동으로 적용된다.

#### 9.3.4 같은 Segment 내부 정렬

같은 segment 내부에서는 다음 순서로 정렬한다.

1. module depth가 낮은 import
2. module depth가 높은 import

---

## 10. 예시

아래 예시는 import ordering을 설명하기 위한 예시이며, 실제 service class가 모든 계층 의존성을 직접 가져야 한다는 의미는 아니다.

```python
"""
Article processing module.
"""

from argparse import ArgumentParser
from pathlib import Path
from sys import argv
from typing import Any
import datetime
import json

from pydantic import BaseModel
from requests import Session

from project.language.i18n.substitution import Substitution

from project.application.client import ConfigurationLoader
from project.application.renderer import ApplicationRenderer

from project.domain.article import Article
from project.domain.author import Author

from project.exception.error_handler import handle_exceptions
from project.exception.exceptions import ApplicationError

from project.infrastructure.database.manage_article_database import DatabaseArticle
from project.infrastructure.repository.article_repository import ArticleRepository
from project.infrastructure.storage.file_storage import FileStorage
from project.infrastructure.utils.argparser import parse_args
from project.infrastructure.utils.config import ProjectConfig

from project.logging.logging import Logging

from project.config.default_config import default_config
from project.config.runtime_config import runtime_config


class ArticleService:
    """
    Manage article processing and rendering.
    """
    def __init__(self, repository: ArticleRepository) -> None:
        self.repository: ArticleRepository = repository

    def get_article(self, article_id: int) -> Article:
        """
        Return an article by ID.
        """
        article: Article | None = self.repository.find_by_id(article_id=article_id)
        if article is None:
            raise ApplicationError("Article not found")

        return article

    def get_article_title(self, article: Article) -> str:
        metadata: dict[str, Any] = article.metadata
        return metadata['title']
```

---

## 11. Tooling Policy

본 문서는 Black, Ruff, isort, Pyright 같은 기존 Python tooling을 대체하기 위한 문서가 아니다.

기존 도구로 안정적으로 처리할 수 있는 규칙은 해당 도구를 우선 사용한다.

다만 본 문서에서 정의하는 logical block spacing, import segment grouping, Result Object convention처럼 프로젝트 맥락을 보존하기 위한 규칙은 별도 검사기 또는 code review 기준으로 관리한다.

프로젝트 고유 규칙 중 기계적으로 판정 가능한 부분은 `yngfmt` formatter/linter와 CI에서 검증하고, 의미 판단이 필요한 부분만 code review 기준으로 남긴다.

자동 검증 가능한 규칙은 formatter, linter, import sorter, pre-commit hook, CI 단계에서 점진적으로 적용한다.

logical stage 구분, naming intent, 책임 분리처럼 사람의 설계 판단이 필요한 규칙은 code review 기준으로 유지한다.

도구와 문서가 충돌하는 경우, formatter가 처리하는 기계적 규칙은 도구 설정을 따른다.

설계 의도, 책임 분리, 예외 처리 정책처럼 의미 판단이 필요한 규칙은 본 문서를 우선한다.

---

## 12. Automation Mapping

| Category | Rule | Current Enforcement | CI Level | Review Required |
| --- | --- | --- | --- | --- |
| Basic Style | indentation / tabs / string quotes / dictionary spacing | `yngfmt` / `ynglint` | Error | Low |
| Docstring | quote / delimiter / spacing layout | `yngfmt` / `ynglint` | Error | Low |
| Blank Line | mechanical definition/body spacing | `yngfmt` / `ynglint` | Error | Low |
| Blank Line | logical stage spacing | code review | Review | High |
| Line Breaking | simple and homogeneous call formatting | `yngfmt` / `ynglint` | Error | Low |
| Import | origin / segment grouping / ordering | `yngfmt` / `ynglint` | Error | Low |
| Naming | class / function / method naming format | `ynglint` | Error | Low |
| Naming | semantic naming intent | code review | Review | High |
| Result Object | configured result field consistency | opt-in `ynglint` | Error | Medium |
| Exception | result vs exception boundary | code review | Review | High |
| Architecture | responsibility and layer boundary | architecture review | Review | High |

CI Level은 해당 규칙을 자동으로 차단할지, 코드 리뷰 기준으로 유지할지를 나타낸다.

- **Error**: 기계적으로 판단 가능한 규칙으로, 위반 시 CI를 실패시킨다.
- **Review**: 문맥이나 설계 의도에 따라 판단해야 하는 규칙으로, 코드 리뷰를 통해 검토한다.

> **운영 기준**
>
> 자동화 가능한 규칙은 `yngfmt`/`ynglint`로 처리하고, 의미 판단이 필요한 규칙은 리뷰 기준으로 남긴다.
>
> Result Object 검사는 프로젝트가 명시적으로 opt-in한 경우에만 활성화한다.

---

## 13. Practical Examples

이 섹션은 규칙 자체보다 실제 의사결정 기준을 설명하기 위해 존재한다.

동일한 결과를 만드는 코드라도 함수 길이, 책임 범위, 처리 단계 수, 중간 판단 여부에 따라 적절한 표현 방식은 달라질 수 있다.

본 섹션은 어떤 형태가 권장되는지, 어떤 경우 허용되는지, 어떤 경우 피하는 것이 좋은지를 예시와 함께 설명한다.

---

## 13.1 Logical Block Spacing

Blank line은 함수 호출이 바뀌었다는 이유만으로 사용하지 않는다.

중간 값이 다음 호출에 그대로 전달되는 짧은 직선 흐름은 compact하게 유지한다.

### Good

```python
def process(data: Data) -> Result:
    validated_data = validate(data=data)
    response_data = client.request(validated_data=validated_data)
    return build_result(response_data=response_data)
```

- 검증 결과가 바로 요청에 사용된다.
- 요청 결과가 바로 결과 생성에 사용된다.
- 중간 판단, 추가 가공, 예외 처리 단계가 없다.
- 따라서 blank line 없이 compact하게 유지한다.

---

### Good

```python
def process(data: Data) -> Result:
    validated_data = validate(data=data)
    if validated_data is None:
        raise ValidationError("Invalid data")

    response_data = client.request(validated_data=validated_data)
    if response_data['error']:
        raise ClientError(response_data['message'])

    result = build_result(response_data=response_data)
    return result
```

- 검증 후 실패 여부를 판단한다.
- 외부 요청 후 오류 여부를 판단한다.
- 결과 생성 단계가 별도로 존재한다.
- 각 단계의 책임이 분리되어 있으므로 blank line을 사용한다.

---

### Acceptable

```python
def process(data: Data) -> Result:
    validated_data = validate(data=data)
    response_data = client.request(validated_data=validated_data)

    return build_result(response_data=response_data)
```

- 함수가 짧고 단순하다.
- 다만 반환부를 시각적으로 분리하고 싶을 때 허용할 수 있다.
- 하지만 기본적으로는 `return`이 새로운 logical stage가 아니라면 붙여 쓰는 쪽을 우선한다.

---

### Avoid

```python
def process(data: Data) -> Result:
    validated_data = validate(data=data)

    response_data = client.request(validated_data=validated_data)

    return build_result(response_data=response_data)
```

- 각 줄이 독립된 logical stage를 형성하지 않는다.
- 중간 판단이나 추가 가공 없이 값이 그대로 다음 호출에 전달된다.
- blank line이 실제 실행 흐름보다 단계를 과장한다.

---

## 13.2 Return Spacing

`return`은 새로운 logical block의 시작이 아니라 현재 logical block의 종료로 취급한다.

### Good

```python
def get_result(data: Data) -> Result:
    result = process(data=data)
    return result
```

`result`를 만든 직후 바로 반환하므로 blank line을 넣지 않는다.

---

### Good

```python
def get_article(article_id: int) -> Article:
    article = repository.find_by_id(article_id=article_id)
    if article is None:
        raise ArticleNotFoundError("Article not found")

    return article
```

검증/예외 처리 단계와 최종 반환 단계가 분리되어 있으므로 `return` 위에 blank line을 둔다.

---

### Avoid

```python
def get_result(data: Data) -> Result:
    result = process(data=data)

    return result
```

`return`이 별도 logical stage가 아니므로 blank line이 불필요하다.

---

## 13.3 Wrapper Method

단순 wrapper method는 가능한 한 compact하게 유지한다.

### Good

```python
def build(self) -> Response:
    self.initialize()
    return self.builder.build()
```

준비 작업 한 단계와 위임 호출 한 단계로 이루어진 짧은 wrapper다.

---

### Good

```python
async def execute(self, request: Request) -> Response:
    await self.validate(request=request)
    return await self.handler.execute(request=request)
```

검증 후 바로 다른 handler에 위임한다. 별도 판단이나 가공이 없으므로 blank line을 넣지 않는다.

---

### Avoid

```python
def build(self) -> Response:
    self.initialize()

    return self.builder.build()
```

단순 위임 흐름인데 blank line을 넣으면 실제보다 복잡한 처리처럼 보인다.

---

## 13.4 Dictionary Multi-line

Dictionary literal은 항목 수, 의미 단위, 가독성을 기준으로 single-line 또는 multi-line을 선택한다.

### Good

```python
payload = {
    "article_id": article_id,
    "author_id": author_id,
    "created_at": created_at,
    "updated_at": updated_at,
    "is_deleted": False,
    "visibility": visibility,
}
```

key가 많고 의미 단위가 여러 개라 multi-line이 적합하다.

---

### Good

```python
payload = { "article_id": article_id, "author_id": author_id }
```

값의 개수가 적고 의미가 단순하므로 single-line이 적합하다.

---

### Acceptable

```python
payload = {
    "article_id": article_id,
    "author_id": author_id,
    "created_at": created_at,
}
```

key가 5개 미만이어도 의미 단위를 분명하게 보여주는 편이 낫다면 multi-line을 사용할 수 있다.

---

### Avoid

```python
payload = { "article_id": article_id, "author_id": author_id, "created_at": created_at, "updated_at": updated_at, "is_deleted": False, "visibility": visibility }
```

key가 많아 한 줄에서 구조를 파악하기 어렵다.

---

## 13.5 Type Hint

Type hint는 모든 값을 장식하기 위한 것이 아니라, 값의 구조와 역할을 명확히 하기 위해 사용한다.

### Good

```python
article_data: dict[str, Any] = repository.read(article_id=article_id)
article: Article | None = ArticleMapper().to_entity(article_data=article_data)
result: Result[Article] = service.process(article=article)
```

- 프로젝트의 기본 작성 방식이다.
- 정적 타입 정보가 명시되어 있다.
- 호출부에서 named argument를 사용해 값의 의미가 명확하다.
- `service.process()`의 유일한 인자가 단순한 참조이므로 single-line call을 유지한다.
- IDE 지원, 리팩터링 안정성, 코드 탐색성을 높일 수 있다.
- `Pyright Standard` 기준에서 안정적인 타입 분석이 가능하다.

---

### Acceptable

```python
for article in articles:
    ...

for index, article in enumerate(articles):
    ...

except Exception as error:
    ...
```

- 반복 변수와 예외 변수는 생명주기가 매우 짧다.
- 타입과 역할이 즉시 드러나는 경우에는 type hint를 생략할 수 있다.
- 작은 스크립트, 빠른 프로토타이핑, 점진적 마이그레이션 상황에서도 제한적으로 허용할 수 있다.

---

### Avoid

```python
article_data = repository.read(article_id=article_id)
article = ArticleMapper().to_entity(article_data=article_data)
result = service.process(article=article)
```

- 여러 logical stage를 거치는 값의 타입이 명시되어 있지 않다.
- 호출부가 값의 구조를 다시 추론해야 한다.
- 정적 분석 품질과 리팩터링 안정성이 낮아질 수 있다.

---

### Avoid

```python
result: Result[Article] = service.process(
    article=article,
)
```

- 유일한 인자가 단순한 변수 참조다.
- multi-line 형태로 분리해도 추가적인 표현식 구조나 처리 단계가 드러나지 않는다.
- multi-line call이 의미적 정보를 추가하지 않고 세로 공간만 늘린다.
- 이 경우에는 `service.process(article=article)` 형태를 우선한다.

---

### Avoid

```python
article_data: dict[Any, Any] = repository.read(article_id=article_id)
```

대부분의 JSON-like dictionary는 key가 문자열이다.

key type이 실제로 다양하지 않다면 `dict[Any, Any]`보다 `dict[str, Any]`를 우선한다.

---

## 13.6 Annotated Alias

`Annotated` alias는 동일한 primitive type이라도 의미나 포맷을 구분해야 할 때 사용한다.

### Good

```python
TimestampFileName = Annotated[str, "Format: yy.mm.dd_HH;MM;SS"]
TimestampDisplay = Annotated[str, "Format: yy.mm.dd HH:MM:SS"]
```

alias 이름이 사용 목적을 설명한다.

---

### Avoid

```python
TimestampFormat_1 = Annotated[str, "Format: yy.mm.dd_HH;MM;SS"]
TimestampFormat_2 = Annotated[str, "Format: yy.mm.dd HH:MM:SS"]
```

번호 기반 이름은 의미를 다시 확인해야 하므로 유지보수성이 떨어진다.

---

## 13.7 Result Object

실행 상태와 반환 데이터를 함께 전달해야 할 때 result object를 사용할 수 있다.

Dictionary 기반 result object는 작은 프로젝트, 빠른 구현, 기존 코드와의 호환, 점진적 마이그레이션 상황에서 허용할 수 있다.

### Preferred

```python
from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar


T = TypeVar("T")


class ResultCode(StrEnum):
    SUCCESS = "SUCCESS"
    IGNORED = "IGNORED"
    FAILED = "FAILED"


@dataclass(slots=True)
class Result(Generic[T]):
    error: bool
    code: ResultCode
    message: str
    data: T | None = None
```

```python
return Result(
    error=False,
    code=ResultCode.SUCCESS,
    message="Successfully processed the request.",
    data=data,
)
```

- 필드 일관성을 유지하기 쉽다.
- 타입 안정성과 IDE 지원을 받을 수 있다.
- result object의 구조가 프로젝트 전반에서 명확해진다.
- 리팩터링 시 field 이름이나 상태 코드 변경을 추적하기 쉽다.

---

### Acceptable

```python
return {
    "error": False,
    "code": "SUCCESS",
    "message": "Successfully processed the request.",
    "data": data,
}
```

Dictionary 기반 result object도 사용할 수 있다.

다만 이 경우에도 field 이름과 의미는 프로젝트 전반에서 일관되게 유지해야 한다.

---

### Acceptable

```python
return {
    "error": False,
    "code": "IGNORED",
    "message": "The condition was not met.",
    "data": None,
}
```

예상 가능한 skip case를 error로 취급하지 않고 명시적 상태로 표현한다.

---

### Avoid

```python
return {
    "success": True,
    "msg": "ok",
    "payload": data,
}
```

field 이름이 기존 result object 구조와 다르면 호출자가 매번 구조를 다시 추론해야 한다.

---

### Avoid

```python
return None
```

호출자가 성공, 실패, skip case를 구분해야 하는 상황이라면 `None`만 반환하는 것은 정보가 부족하다.

---

## 13.8 Architecture Boundary

코드는 호출 위치보다 책임과 변경 이유를 기준으로 배치한다.

### Good

```python
class ArticleCommandHandler:
    def execute(self, request: CreateArticleRequest) -> Result[Article]:
        article_data = self.validator.validate(request=request)
        article = self.article_service.create(article_data=article_data)
        return self.response_builder.build(article=article)
```

application 계층은 입력을 해석하고 use case 흐름을 조립한다.

---

### Good

```python
class ArticleRepository:
    def read(self, article_id: int) -> dict[str, Any]:
        return self.database.fetch_one(article_id=article_id)
```

infrastructure 계층은 저장 방식의 세부 구현을 담당한다.

---

### Avoid

```python
class ArticleCommandHandler:
    def execute(self, request: CreateArticleRequest) -> Result[Article]:
        sql = "SELECT * FROM article WHERE article_id = ?"
        article_data = sqlite.execute(query=sql, parameter=request.article_id)
        return self.response_builder.build(article_data=article_data)
```

application 계층이 저장 방식의 세부 구현까지 직접 알고 있다.

저장 방식이 바뀌면 application 코드까지 함께 변경되어야 하므로 책임 경계가 섞인다.

---

## 13.9 Import Ordering

Import section은 파일의 의존성을 보여주는 지도 역할을 한다.

### Good

```python
from pathlib import Path
from typing import Any
import datetime
import json

from pydantic import BaseModel
from requests import Session

from project.application.service import ArticleService

from project.domain.article import Article

from project.infrastructure.repository import ArticleRepository
```

- Standard Library
- Third-party libraries
- First-party packages

순서가 명확하다.

---

### Avoid

```python
from project.domain.article import Article
import json
from requests import Session
from pathlib import Path
from project.application.service import ArticleService
```

import origin이 섞여 있어 파일의 의존성을 파악하기 어렵다.

---

## 13.10 이 섹션의 목적

이 섹션은 규칙을 강제하기 위한 것이 아니라, 동일한 문제 상황에서 일관된 의사결정을 내릴 수 있도록 돕기 위해 존재한다.

실제 프로젝트에서는 책임 범위, 표현식 구조, 처리 단계, 가독성, 팀 컨벤션, 자동화 가능 여부를 함께 고려하여 판단한다.

특히 blank line은 “코드가 여러 줄이다”라는 이유가 아니라, **책임 있는 처리 단계가 분리되었는가**를 기준으로 사용한다.

Function call과 expression의 줄바꿈은 “한 줄에 들어가는가”가 아니라, **구조와 처리 단계를 별도의 줄로 드러낼 필요가 있는가**를 기준으로 판단한다.
