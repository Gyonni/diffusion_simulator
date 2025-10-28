# 확산–반응 GUI 시뮬레이터 사용자 매뉴얼

## 1. 개요

본 시뮬레이터는 다층 구조에서의 1차원 확산–반응(transient diffusion–reaction)을 해석합니다. 각 층은 고유한 두께, 확산계수, 반응속도를 가질 수 있으며, 맨 마지막 층은 흡수(또는 반응) 물질로 간주됩니다. 방정식은 다음과 같습니다.

\[
\frac{\partial C}{\partial t} = \frac{\partial}{\partial x}\Bigl(D(x)\,\frac{\partial C}{\partial x}\Bigr) - k(x) C
\]

Crank–Nicolson 기법으로 수치해석하고 Tkinter 기반 GUI로 결과를 시각화합니다. 마지막 층으로 유입되는 플럭스와 누적 흡수량까지 계산하므로 반도체 확산 장벽이나 다층 코팅 평가에 활용할 수 있습니다.

---

## 2. 빠른 시작

### 2.1 실행 환경
- Python 3.10 이상
- 필수 패키지: `numpy`, `matplotlib`, `tkinter`(내장)

```bash
python -m pip install numpy matplotlib
```

### 2.2 GUI 실행

```bash
python -m diffreact_gui
```

기본 파라미터로 GUI가 열립니다. 좌측 패널에서 값을 수정하고 **Run Simulation** 버튼을 클릭하세요.

### 2.3 커맨드라인 모드

```bash
python -m diffreact_gui.main --cli [--debug]
```

CLI 모드는 GUI 없이 기본 스택을 계산하여 `results/`에 저장하고 질량 보존 진단 결과를 로그로 남깁니다. `--debug` 옵션은 배열 크기를 추가로 출력합니다.

---

## 3. 인터페이스 안내

### 3.1 레이아웃
- **좌측 패널**: 전역 변수(`C_s`, `Δt`, `t_max`), 우측 경계 조건 선택, 다층 테이블(추가/수정/삭제/순서 이동). 마지막 행은 보고용(목표) 층으로 간주하여 질량/흡수량을 집계합니다.
- **우측 패널**: Matplotlib 그래프(플럭스/누적량, 농도 분포), 네비게이션 툴바(확대/축소/이동), `Time [s]: …` 형식으로 표시되는 시간 슬라이더.

### 3.2 사용 순서
1. 전역 변수와 층 정보를 입력합니다. 순수 확산층은 `k=0`으로, 반응이 있는 층만 `k>0`을 지정합니다. 확산계수를 직접 입력하지 않으려면 Arrhenius 보조 입력(온도, D₀, Ea)으로 값을 계산할 수 있습니다.
2. 우측 경계 조건(완전 흡수 Dirichlet 또는 불투과 Neumann)을 선택한 뒤 **Run Simulation**을 클릭합니다. 계산 동안 버튼은 비활성화됩니다.
3. 계산이 완료되면:
   - 플럭스 그래프에 표면 플럭스, 목표 층 경계 플럭스, 출구 플럭스, 누적 유입량, 목표 층 내부 질량이 표시되며, 탐침을 지정하면 해당 위치의 플럭스/누적량도 함께 나타납니다.
   - 농도 그래프는 전체 두께를 그리며, 층 경계는 점선으로 표시됩니다.
4. Matplotlib 툴바로 그래프를 확대/이동하고, 하단 슬라이더·◀/▶ 버튼·숫자 입력 스핀박스로 시간을 조절하면 라벨에 정확한 시간이 표시됩니다.
5. **Export Flux CSV**를 누르면 `results.npz`, `flux_vs_time.csv`, `concentration_profiles.csv`가 함께 저장되며, **Export Current Profile CSV**로 현재 시점의 농도 분포를 별도로 저장할 수 있습니다.
6. (선택) 플럭스 탐침 위치[ m ]를 입력하거나 레이어를 선택한 뒤 **Plot**을 누르면 해당 위치의 플럭스/누적량이 그래프에 추가됩니다.
7. **Flux view** 드롭다운을 이용하면 표면·경계·출구·탐침 플럭스 중 원하는 곡선만 표시할 수 있습니다.

### 3.3 상태 메시지
- 질량 보존 오차가 1 %를 넘으면 경고 창이 나타납니다.
- 자동 `Δt` 감소에도 해석이 실패하면 에러 창으로 알립니다.

---

## 4. 시뮬레이션 파라미터

| 전역 변수 | 단위 | 기본값 | 설명 |
|-----------|------|--------|------|
| `C_s` | mol·m⁻³ | 1.0 | x=0에서의 Dirichlet 농도 |
| `Δt` | s | 1×10⁻³ | 시간 간격 (해석 실패 시 최대 6회 절반 감소) |
| `t_max` | s | 0.5 | 총 시뮬레이션 시간 |
| 우측 경계 | – | Dirichlet | 스택 끝 경계 조건(Dirichlet / Neumann) |

### 4.1 층 테이블 항목

| 항목 | 단위 | 설명 |
|------|------|------|
| 이름 | – | 메타데이터/내보내기에 기록되는 이름. 마지막 행은 보고용(목표) 층 |
| 두께 | m | 해당 층의 물리적 두께 |
| 확산계수 | m²·s⁻¹ | 층 내부 확산계수 |
| 반응속도 `k` | s⁻¹ | 1차 반응(흡수) 속도. 순수 확산층은 0 |
| 노드 수 | – | 층에 배정할 격자 노드(≥2). 경계 노드는 이전 층과 공유 |

### 4.2 우측 경계 모델
1. **Neumann (불투과)** — `∂C/∂x = 0`으로 스택 끝에서 플럭스가 0.
2. **Dirichlet (완전 흡수)** — `C(L_total,t) = 0`으로 이상적 흡수원을 가정.

### 4.3 진단 지표
- **목표 층 침투 깊이**: `ℓ = √(D_target/k_target)` (`k_target = 0`이면 무한대).
- **격자 해상도 지표**: `ell_over_dx_min` 값이 10 이상이면 충분한 해상도로 간주.
- **총 두께**: `diagnostics['total_thickness']`로 확인 가능.

---

## 5. 수치 모델

### 5.1 이산화
- 각 층의 균일 격자를 이어 붙여 전역 비균일 격자를 구성하며, 층 경계는 노드를 공유합니다.
- `D(x)`와 `k(x)`는 층별 상수로 가정하고, 경계에서는 조화 평균으로 플럭스를 연속시킵니다.
- Crank–Nicolson 기법으로 `∂C/∂t = ∂/∂x(D ∂C/∂x) - kC`를 근사하여 삼중대각 행렬을 풉니다.
- 마지막 층 이전의 `k=0` 층은 농도 구배가 거의 선형이므로 2~4개 노드로 거칠게 잡아도 되고, 세밀한 격자는 목표 층에 집중하는 것이 효율적입니다.

### 5.2 안정성 가이드
- Crank–Nicolson은 안정하지만 정확도를 위해 충분한 공간 해상도가 필요합니다. 특히 반응층에서 `ell_over_dx_min > 10`이 되도록 노드 수를 조정하세요.
- 스택 전체의 최소 `(Δx)^2/D`를 기준으로 `Δt`를 자동으로 제한해 경계 근처 오실레이션을 억제하며, 필요 시 최대 6회까지 절반씩 추가 감소합니다. 진단 정보에서 `dt_requested`, `dt_used` 값을 확인할 수 있습니다.

### 5.3 플럭스 및 흡수량
- **표면 플럭스 (x = 0)** — `J_source`
- **목표 층 경계 플럭스** — 목표 층과 그 위층 사이 인터페이스의 `J_target`
- **출구 플럭스 (x = L)** — `J_end`
- **탐침 플럭스** — 사용자가 지정한 위치(또는 선택한 레이어 중심)에서의 플럭스
- **∫ Flux …** 곡선 — 해당 플럭스의 시간 적분(면적당 누적 유입량)
- **목표 층 질량** — `∫_{target} C(x,t) dx`, 목표 층 내부에 저장된 질량

### 5.4 질량 보존 검사

\[
R = \int J_{\text{source}} dt - \int J_{\text{end}} dt - \iint k(x) C \, dx \, dt - \Bigl[\int C(x,t_{\max}) dx - \int C(x,0) dx\Bigr]
\]

상대 오차 `|R|/max(|ΔM|, 10^{-12})`가 1 %를 넘으면 경고합니다.

---

## 6. 출력물

| 파일 | 설명 |
|------|------|
| `results.npz` | `t`, `x`, `C_xt`, `J_source`, `J_target`, `J_end`, `cum_source`, `cum_target`, `cum_end`, `mass_target`, `layer_boundaries`, `D_nodes`, `D_edges`(있을 경우) |
| `flux_vs_time.csv` | `t`, `Flux_surface`, `Flux_target_interface`, `Flux_exit`, `Cum_flux_surface`, `Cum_flux_target_interface`, `Cum_flux_exit`, `Mass_target`, (설정 시) `Flux_probe`, `Cum_flux_probe` |
| `concentration_profiles.csv` | `x`와 모든 저장 시점의 `C(x,t)`를 열 방향으로 포함한 행렬 |
| `profile_t_<t>.csv` | 현재 슬라이더 시간의 농도–위치 프로필 |
| `metadata.json` | 전역 변수, 층 테이블, 경계 조건, 탐침 위치(있을 경우), 층 경계 정보 |

매 실행마다 덮어쓰므로 필요 시 다른 위치에 복사해 보관하세요.

---

## 7. 권장 사용 절차

1. **단일 층 검증**: 반응이 있는 단일 층을 실행하여 `physics.steady_flux`의 해석값과 `J_source`를 비교합니다.
2. **장벽 추가**: `k=0` 층을 목표 층 앞에 추가하여 확산 지연 효과를 살펴보고, `ell_over_dx_min`이 충분히 커질 때까지 노드 수를 조정합니다.
3. **경계 감도 분석**: Neumann ↔ Dirichlet를 전환하며 잔류/배출 특성을 비교합니다.
4. **보고용 내보내기**: 플럭스 CSV(시간에 따른 플럭스·누적량)와 프로필 CSV(특정 시점 농도 분포)를 활용해 보고자료를 작성합니다.

---

## 8. 문제 해결

| 증상 | 원인 추정 | 해결 방법 |
|------|-----------|-----------|
| 질량 보존 경고 | 목표 층 해상도 부족 또는 `Δt` 과다 | 문제 구간의 노드 수 증가, `Δt` 축소, 물성 재확인 |
| “Zero pivot” 오류 | `Δt`가 너무 크거나 파라미터 극단 | 자동 감소를 허용하거나 직접 더 작은 `Δt` 사용 |
| 플럭스 신호가 요동 | 격자 해상도 부족 | 기울기가 큰 층의 노드 수 증가 |
| GUI 응답 지연 | 매우 세밀한 격자와 작은 `Δt` | 계산 완료까지 대기, 또는 CLI 모드 활용 |

---

## 9. PyInstaller 패키징 (Windows)

### 9.1 준비
- Python 3.10+, 필수 패키지 설치
- 가상환경 사용 권장

### 9.2 빌드

```bash
python -m pip install pyinstaller
pyinstaller --onefile --noconsole --name DiffReactGUI run_diffreact_gui.py
```

- 생성 파일: `dist/DiffReactGUI.exe`
- 실행 즉시 GUI가 열리며, CLI 모드는 계속 Python 명령(`--cli`)으로 실행하세요.

### 9.3 배포 구조 예시

```
DistReactGUI/
├── DiffReactGUI.exe
├── README.txt
├── LICENSE (MIT)
├── examples/
│   ├── default_config.json
│   └── test_case_steady_state.csv
└── logs/
```

배포 시 README에 사용법과 추가 런타임 요구 사항(예: `vc_redist`)을 안내하세요.

---

## 10. 확장 아이디어

- `solver.py` : 다층 Crank–Nicolson 해석과 진단
- `physics.py` : 해석해(정상상태 플럭스, 특성 길이 등)
- `plots.py`, `gui_elements.py` : 시각화 및 GUI 구성 요소
- `utils.py` : 검증, 로깅, 결과 저장 유틸리티

향후 기능으로 Robin 경계 조건, 온도 의존 확산, 2D 확장, 파라미터 스윕 자동화 등을 고려할 수 있습니다.

---

### 도움이 필요할 때

`results/metadata.json`과 로그를 확인해 `ell_over_dx_min`, 사용된 `Δt` 등을 점검한 후 격자 해상도나 시간 간격을 조정하세요.
