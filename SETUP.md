# 개발 환경 설정 가이드

이 문서는 Diffusion-Reaction GUI Simulator 개발 환경을 설정하는 방법을 설명합니다.

## 목차
- [Python 버전 요구사항](#python-버전-요구사항)
- [가상환경 설정](#가상환경-설정)
- [의존성 설치](#의존성-설치)
- [개발 도구 설정](#개발-도구-설정)
- [문제 해결](#문제-해결)

---

## Python 버전 요구사항

- **Python 3.10 이상** 권장
- Python 3.11.x 테스트 완료
- Tkinter 포함된 표준 Python 배포판 필요

### Python 버전 확인

```bash
python --version
```

예상 출력:
```
Python 3.11.3
```

---

## 가상환경 설정

가상환경을 사용하면 프로젝트별 의존성을 격리하여 버전 충돌을 방지할 수 있습니다.

### Windows

#### 1. 가상환경 생성

```bash
# 프로젝트 디렉토리로 이동
cd d:\Fun\diffusion_simulator

# 가상환경 생성 (venv 이름은 원하는 대로 변경 가능)
python -m venv venv
```

#### 2. 가상환경 활성화

```powershell
# PowerShell
.\venv\Scripts\Activate.ps1

# CMD
venv\Scripts\activate.bat
```

활성화되면 프롬프트 앞에 `(venv)`가 표시됩니다:
```
(venv) PS D:\Fun\diffusion_simulator>
```

#### 3. 가상환경 비활성화

```bash
deactivate
```

### Linux/macOS

#### 1. 가상환경 생성

```bash
cd /path/to/diffusion_simulator
python3 -m venv venv
```

#### 2. 가상환경 활성화

```bash
source venv/bin/activate
```

#### 3. 가상환경 비활성화

```bash
deactivate
```

---

## 의존성 설치

가상환경을 활성화한 상태에서 실행하세요.

### 사용자용 (최소 설치)

```bash
pip install -r requirements.txt
```

설치되는 패키지:
- `numpy` - 수치 계산
- `matplotlib` - 그래프 시각화

### 개발자용 (전체 설치)

```bash
pip install -r requirements-dev.txt
```

추가로 설치되는 패키지:
- `pytest` - 단위 테스트
- `pytest-cov` - 코드 커버리지
- `black` - 코드 포맷터
- `flake8` - 코드 린터
- `mypy` - 타입 체커
- `pyinstaller` - 실행 파일 빌드

### 설치 확인

```bash
pip list
```

또는 특정 패키지 확인:
```bash
python -c "import numpy; import matplotlib; print('모든 패키지 설치됨')"
```

---

## 개발 도구 설정

### 1. 코드 포맷팅 (Black)

```bash
# 전체 프로젝트 포맷
black diffreact_gui/

# 특정 파일 포맷
black diffreact_gui/solver.py

# 확인만 (변경 안 함)
black --check diffreact_gui/
```

### 2. 코드 린팅 (Flake8)

```bash
# 전체 프로젝트 검사
flake8 diffreact_gui/

# 특정 파일 검사
flake8 diffreact_gui/solver.py
```

### 3. 타입 체크 (MyPy)

```bash
# 전체 프로젝트 타입 체크
mypy diffreact_gui/

# 엄격 모드
mypy --strict diffreact_gui/
```

### 4. 테스트 실행

```bash
# 모든 테스트 실행
python run_tests.py

# pytest 사용 (설치된 경우)
pytest -v

# 커버리지 포함
pytest --cov=diffreact_gui --cov-report=html
```

---

## PyInstaller 빌드

가상환경 내에서 빌드하면 경로 문제를 방지할 수 있습니다.

### 1. 이전 빌드 정리

```bash
# Python으로 정리
python -c "import shutil; shutil.rmtree('build', ignore_errors=True); shutil.rmtree('dist', ignore_errors=True)"
```

### 2. 빌드 실행

```bash
python -m PyInstaller --onefile --noconsole --name DiffReactGUI run_diffreact_gui.py
```

### 3. 결과 확인

```bash
# Windows
dir dist\DiffReactGUI.exe

# Linux/macOS
ls -lh dist/DiffReactGUI
```

---

## 문제 해결

### 문제 1: "No module named 'tkinter'"

**원인**: Tkinter가 설치되지 않음

**해결**:
- **Windows/macOS**: Python을 재설치 (공식 배포판 사용)
- **Linux**:
  ```bash
  sudo apt-get install python3-tk  # Ubuntu/Debian
  sudo yum install python3-tkinter  # CentOS/RHEL
  ```

### 문제 2: PyInstaller 경로 오류

**증상**:
```
No Python at '"C:\...\python.exe"'
```

**해결**:
1. 가상환경을 활성화했는지 확인
2. `python -m PyInstaller` 사용 (직접 `pyinstaller` 호출 대신)
3. 이전 빌드 파일 삭제 후 재시도

### 문제 3: 의존성 버전 충돌

**해결**:
```bash
# 가상환경 재생성
deactivate
rm -rf venv  # Linux/macOS
rmdir /s venv  # Windows

python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS

pip install -r requirements-dev.txt
```

### 문제 4: 가상환경 활성화 스크립트 실행 오류 (Windows PowerShell)

**증상**:
```
... cannot be loaded because running scripts is disabled on this system
```

**해결**:
```powershell
# PowerShell을 관리자 권한으로 실행
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 또는 CMD 사용
venv\Scripts\activate.bat
```

---

## 모범 사례

### 1. 항상 가상환경 사용

```bash
# 프로젝트 시작 시
cd d:\Fun\diffusion_simulator
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS
```

### 2. 의존성 업데이트

```bash
# 최신 버전으로 업데이트
pip install --upgrade -r requirements-dev.txt

# 현재 설치된 버전 기록
pip freeze > requirements-lock.txt
```

### 3. 정기적인 테스트

```bash
# 코드 변경 후 항상 테스트
python run_tests.py

# 또는
pytest -v
```

### 4. 코드 커밋 전 검사

```bash
# 포맷 확인
black --check diffreact_gui/

# 린트 확인
flake8 diffreact_gui/

# 타입 체크
mypy diffreact_gui/

# 테스트 실행
pytest
```

---

## 참고 자료

- [Python 가상환경 공식 문서](https://docs.python.org/3/library/venv.html)
- [pip 사용자 가이드](https://pip.pypa.io/en/stable/user_guide/)
- [PyInstaller 문서](https://pyinstaller.org/)
- [Black 코드 스타일](https://black.readthedocs.io/)

---

## 빠른 참조

### 일반 작업 흐름

```bash
# 1. 가상환경 활성화
venv\Scripts\activate

# 2. 의존성 설치 (최초 1회)
pip install -r requirements-dev.txt

# 3. 개발/테스트
python -m diffreact_gui
python run_tests.py

# 4. 빌드 (배포용)
python -m PyInstaller --onefile --noconsole --name DiffReactGUI run_diffreact_gui.py

# 5. 완료 후 비활성화
deactivate
```

### 트러블슈팅 체크리스트

- [ ] Python 버전이 3.10 이상인가?
- [ ] 가상환경이 활성화되어 있는가?
- [ ] 모든 의존성이 설치되었는가?
- [ ] 이전 빌드 파일을 삭제했는가?
- [ ] `python -m` 접두사를 사용하고 있는가?
