# 의존성 관리 가이드

이 문서는 Diffusion-Reaction GUI Simulator의 의존성 관리 전략과 모범 사례를 설명합니다.

## 목차
- [개요](#개요)
- [의존성 파일 구조](#의존성-파일-구조)
- [가상환경 사용](#가상환경-사용)
- [일반적인 문제와 해결책](#일반적인-문제와-해결책)
- [모범 사례](#모범-사례)

---

## 개요

### 왜 가상환경을 사용하는가?

1. **격리**: 프로젝트별 의존성 분리
2. **재현성**: 동일한 환경 재구성 가능
3. **충돌 방지**: 버전 충돌 회피
4. **정리**: 깨끗한 시스템 환경 유지

### 왜 requirements.txt를 사용하는가?

1. **버전 고정**: 특정 버전 범위 지정
2. **자동화**: 한 번에 모든 의존성 설치
3. **문서화**: 프로젝트가 필요로 하는 것 명시
4. **협업**: 팀원 간 동일한 환경 보장

---

## 의존성 파일 구조

### requirements.txt (기본 의존성)

**목적**: 애플리케이션 실행에 필요한 최소 패키지

```txt
numpy>=1.24.0,<2.0.0
matplotlib>=3.7.0,<4.0.0
```

**특징**:
- 사용자용
- 최소한의 패키지만 포함
- 버전 범위 지정으로 유연성 확보

**설치**:
```bash
pip install -r requirements.txt
```

### requirements-dev.txt (개발 의존성)

**목적**: 개발, 테스트, 빌드에 필요한 모든 도구

```txt
-r requirements.txt  # 기본 의존성 포함

# Testing
pytest>=7.0.0,<8.0.0
pytest-cov>=4.0.0,<5.0.0

# Code quality
black>=23.0.0,<24.0.0
flake8>=6.0.0,<7.0.0
mypy>=1.0.0,<2.0.0

# Packaging
pyinstaller>=6.0.0,<7.0.0
```

**특징**:
- 개발자용
- 테스트/린트/빌드 도구 포함
- `requirements.txt` 상속

**설치**:
```bash
pip install -r requirements-dev.txt
```

### requirements-lock.txt (선택사항)

**목적**: 정확한 버전 고정 (재현성)

```bash
# 현재 설치된 정확한 버전 기록
pip freeze > requirements-lock.txt
```

**사용 시기**:
- 프로덕션 배포
- CI/CD 파이프라인
- 버그 재현

---

## 가상환경 사용

### Windows 환경

#### 1. 가상환경 생성

```powershell
# 프로젝트 디렉토리에서
python -m venv venv
```

생성되는 구조:
```
venv/
├── Scripts/          # 실행 파일
│   ├── activate      # 활성화 스크립트
│   ├── python.exe    # 격리된 Python
│   └── pip.exe       # 격리된 pip
├── Lib/              # 패키지 설치 위치
└── pyvenv.cfg        # 설정 파일
```

#### 2. 활성화

```powershell
# PowerShell
.\venv\Scripts\Activate.ps1

# CMD
venv\Scripts\activate.bat
```

활성화 확인:
```powershell
(venv) PS D:\Fun\diffusion_simulator>
```

#### 3. 의존성 설치

```bash
# 사용자
pip install -r requirements.txt

# 개발자
pip install -r requirements-dev.txt
```

#### 4. 비활성화

```bash
deactivate
```

### Linux/macOS 환경

#### 1. 가상환경 생성

```bash
python3 -m venv venv
```

#### 2. 활성화

```bash
source venv/bin/activate
```

#### 3. 의존성 설치 및 비활성화

Windows와 동일

---

## 일반적인 문제와 해결책

### 문제 1: PyInstaller 경로 오류

**증상**:
```
No Python at '"C:\Users\...\Python310\python.exe"'
```

**원인**:
- 가상환경이 활성화되지 않음
- 이전 Python 버전 경로 참조

**해결책**:

```bash
# 1. 가상환경 활성화 확인
(venv) PS D:\Fun\diffusion_simulator>

# 2. Python 경로 확인
python -c "import sys; print(sys.executable)"
# 출력: D:\Fun\diffusion_simulator\venv\Scripts\python.exe

# 3. PyInstaller 재설치
pip uninstall -y pyinstaller
pip install pyinstaller

# 4. 빌드 시 python -m 사용
python -m PyInstaller --onefile --noconsole --name DiffReactGUI run_diffreact_gui.py
```

### 문제 2: 버전 충돌

**증상**:
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed.
```

**원인**:
- 호환되지 않는 패키지 버전
- 오래된 pip

**해결책**:

```bash
# 1. pip 업그레이드
python -m pip install --upgrade pip

# 2. 가상환경 재생성
deactivate
rm -rf venv  # Linux/macOS
rmdir /s /q venv  # Windows

python -m venv venv
venv\Scripts\activate

# 3. 의존성 재설치
pip install -r requirements-dev.txt
```

### 문제 3: 가상환경 활성화 실패 (Windows PowerShell)

**증상**:
```
... cannot be loaded because running scripts is disabled on this system
```

**원인**:
- PowerShell 실행 정책 제한

**해결책**:

```powershell
# 방법 1: 실행 정책 변경 (권장)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 방법 2: CMD 사용
cmd
venv\Scripts\activate.bat

# 방법 3: 한 번만 우회
PowerShell -ExecutionPolicy Bypass -File venv\Scripts\Activate.ps1
```

### 문제 4: tkinter 누락

**증상**:
```
ModuleNotFoundError: No module named 'tkinter'
```

**원인**:
- Tkinter가 포함되지 않은 Python 설치

**해결책**:

**Windows/macOS**:
- Python 공식 배포판 재설치

**Linux**:
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# CentOS/RHEL
sudo yum install python3-tkinter

# Arch Linux
sudo pacman -S tk
```

---

## 모범 사례

### 1. 항상 가상환경 사용

```bash
# 프로젝트 시작 시
cd /path/to/diffusion_simulator
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 작업 완료 후
deactivate
```

### 2. 의존성 업데이트

```bash
# 정기적으로 업데이트 (주의해서)
pip install --upgrade -r requirements-dev.txt

# 특정 패키지만 업데이트
pip install --upgrade numpy

# 현재 버전 확인
pip list --outdated
```

### 3. 의존성 버전 기록

```bash
# 정확한 버전 저장 (배포용)
pip freeze > requirements-lock.txt

# 최소 버전만 지정 (개발용)
pip install pipreqs
pipreqs . --force
```

### 4. 정기적인 환경 정리

```bash
# 사용하지 않는 패키지 제거
pip uninstall <package>

# 가상환경 재생성 (분기별)
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

### 5. 다중 Python 버전 테스트

```bash
# Python 3.10
python3.10 -m venv venv310
source venv310/bin/activate
pip install -r requirements-dev.txt
python run_tests.py

# Python 3.11
python3.11 -m venv venv311
source venv311/bin/activate
pip install -r requirements-dev.txt
python run_tests.py
```

---

## 워크플로우 예시

### 신규 개발자 온보딩

```bash
# 1. 저장소 클론
git clone <repository-url>
cd diffusion_simulator

# 2. 가상환경 생성
python -m venv venv

# 3. 가상환경 활성화
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS

# 4. 개발 의존성 설치
pip install -r requirements-dev.txt

# 5. 테스트 실행
python run_tests.py

# 6. GUI 실행
python -m diffreact_gui
```

### 일일 개발 루틴

```bash
# 아침: 환경 활성화 및 업데이트
cd diffusion_simulator
venv\Scripts\activate
git pull
pip install --upgrade -r requirements-dev.txt

# 개발 중: 테스트 실행
python run_tests.py

# 코드 품질 확인
black diffreact_gui/
flake8 diffreact_gui/
mypy diffreact_gui/

# 저녁: 변경사항 커밋
git add .
git commit -m "feat: new feature"
git push

# 종료
deactivate
```

### 배포 준비

```bash
# 1. 새 가상환경으로 테스트
python -m venv venv-release
venv-release\Scripts\activate

# 2. 최소 의존성만 설치
pip install -r requirements.txt

# 3. 애플리케이션 테스트
python -m diffreact_gui

# 4. 개발 도구 설치
pip install -r requirements-dev.txt

# 5. 빌드
python -m PyInstaller --onefile --noconsole --name DiffReactGUI run_diffreact_gui.py

# 6. 실행 파일 테스트
dist\DiffReactGUI.exe

# 7. 정리
deactivate
```

---

## 체크리스트

### 새 프로젝트 시작

- [ ] 가상환경 생성
- [ ] 가상환경 활성화
- [ ] requirements-dev.txt 설치
- [ ] 테스트 실행 확인
- [ ] Git에 venv/ 제외 확인

### 코드 변경 후

- [ ] 테스트 실행
- [ ] 코드 포맷 (black)
- [ ] 린트 검사 (flake8)
- [ ] 타입 체크 (mypy)
- [ ] 변경사항 커밋

### 의존성 추가 시

- [ ] 가상환경에서 설치
- [ ] 테스트 확인
- [ ] requirements.txt 업데이트
- [ ] 문서 업데이트
- [ ] 변경사항 커밋

### 배포 전

- [ ] 새 가상환경으로 테스트
- [ ] 모든 테스트 통과
- [ ] PyInstaller 빌드 성공
- [ ] 실행 파일 동작 확인
- [ ] 문서 최신화

---

## 참고 자료

- [Python 가상환경 문서](https://docs.python.org/3/library/venv.html)
- [pip 사용자 가이드](https://pip.pypa.io/en/stable/user_guide/)
- [Python 패키징 가이드](https://packaging.python.org/)
- [Semantic Versioning](https://semver.org/)

---

## 요약

### 핵심 명령어

```bash
# 가상환경 생성
python -m venv venv

# 활성화
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS

# 의존성 설치
pip install -r requirements-dev.txt

# PyInstaller (반드시 python -m 사용)
python -m PyInstaller --onefile --noconsole --name DiffReactGUI run_diffreact_gui.py

# 비활성화
deactivate
```

### 황금률

1. **항상 가상환경 사용**
2. **python -m으로 모듈 실행**
3. **정기적인 테스트**
4. **의존성 버전 관리**
5. **문서 최신화 유지**
