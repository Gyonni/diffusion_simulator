# PyInstaller 빌드 가이드

## 문제 해결

### "Unable to create process" 오류

#### 증상
```
Fatal error in launcher: Unable to create process using '"D:\Data\Fun\diffusion_simulator\.venv\Scripts\python.exe"
"D:\Fun\diffusion_simulator\.venv\Scripts\pyinstaller.exe"
```

#### 원인
- 가상환경(venv)에서 `pyinstaller` 명령을 직접 실행할 때 발생
- Windows에서 경로 또는 실행 권한 문제

#### 해결 방법

❌ **잘못된 방법**:
```bash
pyinstaller --onefile --noconsole --name DiffReactGUI run_diffreact_gui.py
```

✅ **올바른 방법**:
```bash
python -m PyInstaller --onefile --noconsole --name DiffReactGUI run_diffreact_gui.py
```

## 단계별 빌드 가이드

### 1. PyInstaller 설치

```bash
python -m pip install pyinstaller
```

**확인**:
```bash
python -m pip list | findstr pyinstaller
```

예상 출력:
```
pyinstaller                6.16.0
pyinstaller-hooks-contrib  2025.9
```

### 2. 빌드 실행

```bash
python -m PyInstaller --onefile --noconsole --name DiffReactGUI run_diffreact_gui.py
```

**옵션 설명**:
- `--onefile`: 단일 실행 파일 생성
- `--noconsole`: 콘솔 창 숨김 (GUI 앱용)
- `--name DiffReactGUI`: 실행 파일 이름 지정

### 3. 빌드 결과 확인

빌드가 완료되면:
```
dist/
  └── DiffReactGUI.exe  (약 40 MB)
```

**파일 확인**:
```bash
dir dist\DiffReactGUI.exe
```

### 4. 실행 테스트

```bash
.\dist\DiffReactGUI.exe
```

GUI가 정상적으로 열리면 성공!

## 빌드 최적화

### 크기 줄이기 (선택사항)

#### UPX 압축 사용
```bash
python -m PyInstaller --onefile --noconsole --name DiffReactGUI --upx-dir=path/to/upx run_diffreact_gui.py
```

#### 불필요한 모듈 제외
`DiffReactGUI.spec` 파일 수정:
```python
excludes=['tkinter.test', 'test', 'unittest']
```

재빌드:
```bash
python -m PyInstaller DiffReactGUI.spec
```

## 배포 체크리스트

- [ ] PyInstaller 설치됨
- [ ] 빌드 명령 실행 (`python -m PyInstaller ...`)
- [ ] `dist/DiffReactGUI.exe` 생성 확인
- [ ] 실행 파일 테스트 완료
- [ ] 필요한 경우 README.txt 포함
- [ ] 라이선스 파일 포함
- [ ] 예제 설정 파일 포함 (선택)

## 일반적인 문제

### 1. 임포트 오류

**증상**: 실행 파일이 특정 모듈을 찾지 못함

**해결**: `DiffReactGUI.spec`에 hidden imports 추가
```python
hiddenimports=['matplotlib.backends.backend_tkagg']
```

### 2. 데이터 파일 누락

**증상**: 설정 파일이나 리소스 파일이 없음

**해결**: spec 파일에 데이터 추가
```python
datas=[('docs/*.md', 'docs')]
```

### 3. 바이러스 백신 경고

**증상**: 일부 백신이 오탐지

**해결**:
- 코드 서명 인증서 구매 및 적용
- 사용자에게 예외 처리 안내

## 디버깅 팁

### 빌드 로그 확인
```bash
python -m PyInstaller --onefile --noconsole --name DiffReactGUI run_diffreact_gui.py --log-level=DEBUG
```

### 콘솔 출력 확인
개발 중에는 `--noconsole` 옵션을 제거:
```bash
python -m PyInstaller --onefile --name DiffReactGUI run_diffreact_gui.py
```

### Spec 파일 수정
자동 생성된 `DiffReactGUI.spec` 파일을 직접 수정 후:
```bash
python -m PyInstaller DiffReactGUI.spec
```

## 참고 자료

- [PyInstaller 공식 문서](https://pyinstaller.org/)
- [Windows 빌드 가이드](https://pyinstaller.readthedocs.io/en/stable/usage.html)
- [일반적인 문제 해결](https://pyinstaller.readthedocs.io/en/stable/when-things-go-wrong.html)

## 요약

핵심 명령어:
```bash
# 설치
python -m pip install pyinstaller

# 빌드
python -m PyInstaller --onefile --noconsole --name DiffReactGUI run_diffreact_gui.py

# 결과
dist/DiffReactGUI.exe
```

**중요**: 항상 `python -m PyInstaller`를 사용하세요!
