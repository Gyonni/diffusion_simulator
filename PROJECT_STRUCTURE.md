# 프로젝트 구조

이 문서는 Diffusion-Reaction GUI Simulator의 파일 구조와 각 파일의 역할을 설명합니다.

## 디렉토리 구조

```
diffusion_simulator/
├── diffreact_gui/              # 메인 패키지
│   ├── __init__.py             # 패키지 초기화
│   ├── __main__.py             # 모듈 실행 진입점
│   ├── config.py               # 기본 설정 및 상수
│   ├── models.py               # 데이터 모델 (LayerParam, SimParams)
│   ├── solver.py               # Crank-Nicolson 수치 해석기
│   ├── physics.py              # 물리 함수 및 분석 해
│   ├── plots.py                # Matplotlib 플롯 헬퍼
│   ├── gui_elements.py         # Tkinter GUI 컴포넌트
│   ├── utils.py                # 유틸리티 함수
│   └── main.py                 # 메인 실행 로직
│
├── tests/                      # 테스트 코드
│   └── test_solver.py          # 수치 해석기 테스트
│
├── docs/                       # 문서
│   ├── USER_MANUAL.md          # 사용자 매뉴얼 (영문)
│   └── USER_MANUAL_KO.md       # 사용자 매뉴얼 (한글)
│
├── results/                    # 시뮬레이션 결과 (gitignore)
│   ├── results.npz             # NumPy 바이너리 결과
│   ├── flux_vs_time.csv        # 플럭스 시계열 데이터
│   ├── concentration_profiles.csv  # 농도 프로필
│   └── metadata.json           # 시뮬레이션 메타데이터
│
├── dist/                       # 빌드 결과물 (gitignore)
│   └── DiffReactGUI.exe        # PyInstaller 실행 파일
│
├── build/                      # 빌드 임시 파일 (gitignore)
├── venv/                       # 가상환경 (gitignore)
│
├── run_diffreact_gui.py        # PyInstaller 진입점
├── run_tests.py                # 테스트 실행 스크립트
│
├── requirements.txt            # 기본 의존성
├── requirements-dev.txt        # 개발 의존성
│
├── .gitignore                  # Git 제외 파일 목록
│
├── materials_library.json      # Material library (사용자가 저장한 물성 데이터)
│
├── README.md                   # 프로젝트 개요
├── DEVELOPMENT_GUIDELINES.md   # 개발 가이드라인 (필수 참고 문서)
├── IMPLEMENTATION_STATUS.md    # 구현 상태 및 기능 목록
└── PROJECT_STRUCTURE.md        # 이 문서
```

## 파일 설명

### 핵심 모듈

#### diffreact_gui/solver.py
- **역할**: 수치 해석 엔진
- **주요 기능**:
  - Crank-Nicolson 시간 적분
  - Thomas 알고리즘 (삼중대각 행렬 해석)
  - 다층 격자 구성
  - 경계 조건 적용
  - 질량 보존 진단
  - 온도 스윕 시뮬레이션 (Arrhenius 방정식 적용)
- **주요 함수**:
  - `run_simulation()`: 메인 시뮬레이션 루프 (반환: "t", "J_end" 등)
  - `run_temperature_sweep()`: 온도별 시뮬레이션 (3D 배열 반환)
  - `_thomas_solve()`: 삼중대각 선형 시스템 해석
  - `_build_grid()`: 격자 생성
  - `mass_balance_diagnostics()`: 질량 보존 검증

#### diffreact_gui/physics.py
- **역할**: 물리 모델 및 분석 해
- **주요 기능**:
  - 특성 길이 계산
  - Damköhler 수 계산
  - 정상 상태 플럭스 분석 해
  - Arrhenius 확산도 계산
- **주요 함수**:
  - `char_length_ell()`: 침투 깊이 계산
  - `damkohler_number()`: 무차원 수
  - `steady_flux()`: 정상 상태 플럭스
  - `calculate_diffusivity_arrhenius()`: D = D0 * exp(-Ea / (kb*T))

#### diffreact_gui/gui_elements.py
- **역할**: Tkinter GUI 인터페이스
- **주요 클래스**:
  - `App`: 메인 애플리케이션 윈도우
  - `LayerTable`: 다층 파라미터 테이블 위젯 (Ea 컬럼 포함)
  - `MaterialLibraryDialog`: Material library 관리 대화상자
- **주요 기능**:
  - 사용자 입력 처리
  - 리사이즈 가능한 패널 (PanedWindow 사용)
  - 상단 고정 제어 버튼 (▶ Run, ■ Stop)
  - 복사 가능한 에러 다이얼로그 (ScrolledText)
  - 온도별 시뮬레이션 지원
  - 플롯 업데이트
  - 파일 내보내기
  - 매뉴얼 표시

#### diffreact_gui/plots.py
- **역할**: 시각화
- **주요 기능**:
  - Matplotlib 그래프 생성
  - 플럭스/흡수량 플롯
  - 농도 프로필 플롯
  - 온도별 농도 플롯 (3번째 그래프)
- **주요 함수**:
  - `create_figures()`: 3개 subplot 그래프 초기화
  - `update_flux_axes()`: 플럭스 데이터 업데이트
  - `update_profile_axes()`: 프로필 업데이트
  - `update_temperature_axes()`: 온도 vs 농도 플롯

#### diffreact_gui/models.py
- **역할**: 데이터 모델 정의
- **주요 클래스**:
  - `LayerParam`: 단일 층 파라미터 (D0, Ea 포함)
  - `SimParams`: 전체 시뮬레이션 파라미터 (temperatures 리스트 포함)

#### diffreact_gui/utils.py
- **역할**: 유틸리티 함수
- **주요 기능**:
  - 파라미터 검증
  - 결과 저장 (NPZ, CSV, JSON)
  - Material library 관리 (load/save/add)
  - 누적 적분 계산
  - 로깅 설정

#### diffreact_gui/config.py
- **역할**: 기본 설정
- **내용**:
  - 기본 파라미터 값
  - 결과 디렉토리 경로
  - 로그 레벨

### 진입점

#### run_diffreact_gui.py
- PyInstaller용 간단한 진입점
- `diffreact_gui.main.main()` 호출

#### diffreact_gui/main.py
- CLI 및 GUI 모드 처리
- 명령줄 인자 파싱

#### diffreact_gui/__main__.py
- `python -m diffreact_gui` 실행 시 호출

### 테스트

#### tests/test_solver.py
- 수치 해석기 단위 테스트
- 순수 확산 테스트
- 정상 상태 비교 테스트
- 질량 보존 테스트

#### run_tests.py
- 모든 테스트 실행
- pytest 없이 실행 가능

### 문서

#### README.md
- 프로젝트 개요
- 빠른 시작 가이드
- 기능 요약
- 설치, 실행, 패키징 방법 통합

#### DEVELOPMENT_GUIDELINES.md
- **필수 참고 문서**: 모든 코드 수정 시 준수해야 할 가이드라인
- 핵심 개발 원칙 (사용자 확인, 코드 품질, 문서화, 테스트)
- 세계 수준의 개발 워크플로우
- 프로젝트별 가이드라인 (수치 정확도, GUI 디자인, 입력 검증)
- 개발 체크리스트

#### IMPLEMENTATION_STATUS.md
- 구현 완료된 기능 목록 (Phase 1, Phase 2)
- 최근 업데이트 내역
- 알려진 이슈
- 다음 단계 계획

#### PROJECT_STRUCTURE.md
- 이 문서
- 프로젝트 파일 구조 및 각 파일의 역할
- 모듈 간 의존성 다이어그램
- 데이터 흐름 설명

#### docs/USER_MANUAL.md
- 사용자 매뉴얼 (영문)
- GUI 사용법
- 수치 모델 설명
- 파라미터 설명 및 워크플로우

#### docs/USER_MANUAL_KO.md
- 사용자 매뉴얼 (한글)
- 동일 내용 한글 버전

### 의존성 관리

#### requirements.txt
- **필수 패키지만 포함**:
  - `numpy` - 수치 계산
  - `matplotlib` - 시각화

#### requirements-dev.txt
- **개발 도구 포함**:
  - `requirements.txt` 의존성
  - `pytest` - 테스트
  - `black` - 포맷터
  - `flake8` - 린터
  - `mypy` - 타입 체커
  - `pyinstaller` - 빌드 도구

### 설정 파일

#### .gitignore
- Git에서 제외할 파일 지정
- 주요 제외 항목:
  - 가상환경 (`venv/`, `.venv/`)
  - 빌드 결과 (`dist/`, `build/`)
  - 캐시 (`__pycache__/`, `*.pyc`)
  - 결과 파일 (`results/`, `*.npz`, `*.csv`)
  - IDE 설정 (`.vscode/`, `.idea/`)

## 모듈 간 의존성

```
main.py
  ├── gui_elements.py
  │     ├── plots.py
  │     ├── models.py
  │     ├── solver.py
  │     │     ├── physics.py
  │     │     ├── models.py
  │     │     └── utils.py
  │     ├── utils.py
  │     └── config.py
  └── solver.py (CLI 모드)
```

## 데이터 흐름

1. **사용자 입력** → `gui_elements.App`
2. **파라미터 검증** → `utils.validate_params()`
3. **시뮬레이션 실행** → `solver.run_simulation()`
4. **결과 계산**:
   - 격자 생성 → `solver._build_grid()`
   - 시간 반복 → Crank-Nicolson
   - 플럭스 계산 → `solver._compute_flux()`
5. **시각화** → `plots.update_*_axes()`
6. **내보내기** → `utils.save_*()` 함수들

## 코딩 규칙

### 네이밍 컨벤션

- **모듈**: `snake_case.py`
- **클래스**: `PascalCase`
- **함수**: `snake_case()`
- **상수**: `UPPER_SNAKE_CASE`
- **비공개 함수**: `_leading_underscore()`

### 타입 힌트

모든 함수에 타입 힌트 사용:
```python
def function_name(param: ParamType) -> ReturnType:
    ...
```

### Docstring 스타일

Google 스타일 또는 NumPy 스타일:
```python
def function(arg: int) -> float:
    """Brief description.

    Args:
        arg: Description with units if applicable

    Returns:
        Description of return value

    Raises:
        ValueError: When and why
    """
```

## 버전 관리

### 브랜치 전략
- `main`: 안정 버전
- `dev`: 개발 브랜치
- `feature/*`: 새 기능
- `bugfix/*`: 버그 수정

### 커밋 메시지
```
<type>: <subject>

<body>

<footer>
```

타입:
- `feat`: 새 기능
- `fix`: 버그 수정
- `refactor`: 리팩토링
- `docs`: 문서
- `test`: 테스트
- `chore`: 기타

## 참고

- [Python 코딩 스타일 가이드 (PEP 8)](https://pep8.org/)
- [타입 힌트 (PEP 484)](https://www.python.org/dev/peps/pep-0484/)
- [Docstring 컨벤션 (PEP 257)](https://www.python.org/dev/peps/pep-0257/)
