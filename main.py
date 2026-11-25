"""
PDF Page Extractor (PDF 페이지 추출 및 분할기)

주요 기능:
    - 슬림 통합 컨트롤 바 (단일 하단 바 레이아웃):
        · 기존의 자리 차지하던 하단 탭시트를 제거하여 PDF 뷰어 세로 화면을 극대화
        · 좌측: 추출 모드 콤보박스 (연속 범위 / 자유 지정 / 낱장 분할)
        · 중앙: 페이지 내비게이션 (이전/다음, 현재/전체, 직접 점프)
        · 우측: 모드별 동적 설정 컨트롤 및 일원화된 [저장] 버튼
    - 다크 / 라이트 모드 (Dark / Light Theme Toggle):
        · 다크 모드: 모든 버튼 글씨를 선명한 흰색(White), 가독성 극대화
        · 라이트 모드: 모든 버튼 글씨를 또렷한 검정색(Black)으로 표시
        · 우측 상단 토글 버튼 (F6 단축키 지원) 및 설정 자동 저장
    - 3가지 추출 모드:
        1. 연속 범위 추출 (시작 ~ 끝 페이지 지정, '현재 페이지로 지정' 원클릭 버튼)
        2. 자유 페이지 지정 (예: 1, 3, 5-8, 12 등 콤마 및 하이픈 혼합 입력)
        3. 낱장 전체 분할 (문서의 모든 페이지 또는 지정 범위를 각각 1페이지짜리 PDF로 분리 저장)
    - 드래그 앤 드롭 지원: 탐색기에서 PDF 파일을 창으로 바로 끌어다 놓아 열기
    - 편리한 키보드 단축키 지원 (Ctrl+O, Ctrl+S, F6, 화살표, PgUp/PgDown, Zoom 등)
    - pypdf 기반 100% 로컬 오프라인 무손실(Lossless) 고속 추출 (개인정보 및 기밀문서 안전)
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

from PySide6.QtCore import QMargins, QPointF, QSettings, Qt
from PySide6.QtGui import QColor, QIcon, QKeySequence, QPalette, QShortcut
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QRadioButton, QSpinBox,
    QStackedLayout, QStackedWidget, QVBoxLayout, QWidget
)
from pypdf import PdfReader, PdfWriter


def get_app_path() -> str:
    """PyInstaller EXE 또는 일반 스크립트 실행 시 실제 파일이 위치한 폴더 반환"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# 리소스(아이콘 등) 경로 (PyInstaller _MEIPASS 지원)
BASE_DIR = getattr(sys, "_MEIPASS", get_app_path())
ICON_PATH = os.path.join(BASE_DIR, "icon.ico")
if not os.path.exists(ICON_PATH):
    ICON_PATH = os.path.join(get_app_path(), "icon.ico")

import tempfile

SVG_ICONS = {
    "arrow_up_white.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6"><polygon points="5,0 10,6 0,6" fill="#ffffff"/></svg>',
    "arrow_up_gray.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6"><polygon points="5,0 10,6 0,6" fill="#b5b5b5"/></svg>',
    "arrow_up_black.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6"><polygon points="5,0 10,6 0,6" fill="#222222"/></svg>',
    "arrow_up_darkgray.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6"><polygon points="5,0 10,6 0,6" fill="#666666"/></svg>',
    "arrow_down_white.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6"><polygon points="0,0 10,0 5,6" fill="#ffffff"/></svg>',
    "arrow_down_gray.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6"><polygon points="0,0 10,0 5,6" fill="#b5b5b5"/></svg>',
    "arrow_down_black.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6"><polygon points="0,0 10,0 5,6" fill="#222222"/></svg>',
    "arrow_down_darkgray.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6"><polygon points="0,0 10,0 5,6" fill="#666666"/></svg>',
}


def get_icon_paths() -> dict:
    """업/다운 화살표 SVG 아이콘 파일들을 준비하고 경로 딕셔너리 반환"""
    icons_dir = os.path.join(tempfile.gettempdir(), "pdf_page_extractor_icons")
    os.makedirs(icons_dir, exist_ok=True)
    paths = {}
    for filename, svg in SVG_ICONS.items():
        fp = os.path.join(icons_dir, filename).replace("\\", "/")
        if not os.path.exists(fp):
            with open(fp, "w", encoding="utf-8") as f:
                f.write(svg)
        paths[filename] = fp
    return paths


ICON_PATHS = get_icon_paths()


# ---------------------------------------------------------------- 테마 팔레트
def light_palette() -> QPalette:
    """라이트 모드용 고대비 팔레트"""
    pal = QPalette()
    colors = {
        QPalette.Window: "#f3f3f3",
        QPalette.WindowText: "#000000",
        QPalette.Base: "#ffffff",
        QPalette.AlternateBase: "#f7f7f7",
        QPalette.ToolTipBase: "#ffffdc",
        QPalette.ToolTipText: "#000000",
        QPalette.PlaceholderText: "#767676",
        QPalette.Text: "#000000",
        QPalette.Button: "#f0f0f0",
        QPalette.ButtonText: "#000000",
        QPalette.BrightText: "#d90000",
        QPalette.Link: "#0066cc",
        QPalette.Highlight: "#cce8ff",
        QPalette.HighlightedText: "#000000",
        QPalette.Light: "#ffffff",
        QPalette.Midlight: "#e3e3e3",
        QPalette.Mid: "#a0a0a0",
        QPalette.Dark: "#a0a0a0",
        QPalette.Shadow: "#696969",
    }
    for role, c in colors.items():
        pal.setColor(role, QColor(c))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, QColor("#888888"))
    return pal


def dark_palette() -> QPalette:
    """다크 모드용 고대비 팔레트"""
    pal = QPalette()
    colors = {
        QPalette.Window: "#222222",
        QPalette.WindowText: "#ffffff",
        QPalette.Base: "#1a1a1a",
        QPalette.AlternateBase: "#262626",
        QPalette.ToolTipBase: "#3c3c3c",
        QPalette.ToolTipText: "#ffffff",
        QPalette.PlaceholderText: "#8a8a8a",
        QPalette.Text: "#ffffff",
        QPalette.Button: "#333333",
        QPalette.ButtonText: "#ffffff",
        QPalette.BrightText: "#ff5555",
        QPalette.Link: "#4ea1f3",
        QPalette.Highlight: "#264f78",
        QPalette.HighlightedText: "#ffffff",
        QPalette.Light: "#4a4a4a",
        QPalette.Midlight: "#3f3f3f",
        QPalette.Mid: "#303030",
        QPalette.Dark: "#1a1a1a",
        QPalette.Shadow: "#000000",
    }
    for role, c in colors.items():
        pal.setColor(role, QColor(c))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, QColor("#888888"))
    return pal


# ---------------------------------------------------------------- 테마 스타일시트
DARK_STYLE = """
QMainWindow, QWidget#centralWidget {
    background-color: #1e1e1e;
    color: #ffffff;
}
QLabel {
    color: #e6e6e6;
}
QLabel#pageLabel {
    font-weight: bold;
    font-size: 13px;
    color: #ffffff;
}
QLabel#fileLabel {
    font-size: 13px;
    font-weight: 500;
    color: #e6e6e6;
}
QLabel#placeholderText {
    font-size: 15px;
    line-height: 160%;
    color: #cccccc;
}

/* 하단 통합 컨트롤 바 */
QWidget#bottomBar {
    background-color: #252526;
    border-top: 1px solid #383838;
    border-radius: 4px;
}

/* 콤보박스 */
QComboBox {
    background-color: #333333;
    color: #ffffff;
    border: 1px solid #4d4d4d;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
QComboBox:hover {
    border-color: #666666;
}
QComboBox QAbstractItemView {
    background-color: #252526;
    color: #ffffff;
    selection-background-color: #264f78;
    selection-color: #ffffff;
    border: 1px solid #4d4d4d;
}

/* 일반 버튼: 다크 모드에서는 글씨 흰색 */
QPushButton {
    background-color: #333333;
    color: #ffffff;
    border: 1px solid #4d4d4d;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #444444;
    border-color: #666666;
}
QPushButton:pressed {
    background-color: #222222;
}
QPushButton:disabled {
    background-color: #2a2a2a;
    color: #b5b5b5;
    border-color: #3e3e42;
}

/* 상단 PDF 열기 버튼 (파란색 유지 + 흰색 글씨) */
QPushButton#openButton {
    background-color: #0e639c;
    color: #ffffff;
    font-weight: bold;
    padding: 6px 14px;
    border: 1px solid #1177bb;
    border-radius: 4px;
}
QPushButton#openButton:hover {
    background-color: #1177bb;
}
QPushButton#openButton:pressed {
    background-color: #094771;
}

/* 통합 저장 버튼 (초록색 기본) */
QPushButton#saveButton {
    background-color: #28a745;
    color: #ffffff;
    font-weight: bold;
    padding: 6px 14px;
    border: 1px solid #218838;
    border-radius: 4px;
}
QPushButton#saveButton:hover {
    background-color: #218838;
}
QPushButton#saveButton:pressed {
    background-color: #1e7e34;
}
QPushButton#saveButton:disabled {
    background-color: #2e4d35;
    color: #7da583;
    border-color: #263d2b;
}

/* 낱장 분할 모드일 때 저장 버튼 스타일 */
QPushButton#saveButton[mode="split"] {
    background-color: #17a2b8;
    border-color: #138496;
}
QPushButton#saveButton[mode="split"]:hover {
    background-color: #138496;
}
QPushButton#saveButton[mode="split"]:pressed {
    background-color: #117a8b;
}
QPushButton#saveButton[mode="split"]:disabled {
    background-color: #23474d;
    color: #6d969c;
    border-color: #1a3438;
}

/* 테마 토글 버튼 */
QPushButton#themeButton {
    background-color: #383a3d;
    color: #ffffff;
    font-weight: bold;
    border: 1px solid #55585c;
    border-radius: 4px;
}
QPushButton#themeButton:hover {
    background-color: #4a4d52;
}

/* 스핀박스 및 텍스트 입력창 (다크 모드 글씨 흰색, 선명한 업다운 버튼) */
QSpinBox, QLineEdit {
    background-color: #252526;
    color: #ffffff;
    border: 1px solid #4d4d4d;
    border-radius: 4px;
    padding: 3px 6px;
    selection-background-color: #264f78;
    selection-color: #ffffff;
}
QSpinBox {
    padding-left: 6px;
    padding-right: 20px;
}
QSpinBox:disabled, QLineEdit:disabled {
    background-color: #252526;
    color: #cccccc;
    border-color: #3e3e42;
}
QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    background-color: #333333;
    border-left: 1px solid #4d4d4d;
    border-bottom: 1px solid #3d3d3d;
    border-top-right-radius: 3px;
}
QSpinBox::up-button:hover {
    background-color: #444444;
}
QSpinBox::up-button:disabled {
    background-color: #2a2a2a;
    border-color: #3e3e42;
}
QSpinBox::up-arrow {
    image: url("__ARROW_UP_WHITE__");
    width: 10px;
    height: 6px;
}
QSpinBox::up-arrow:disabled {
    image: url("__ARROW_UP_GRAY__");
}
QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    background-color: #333333;
    border-left: 1px solid #4d4d4d;
    border-bottom-right-radius: 3px;
}
QSpinBox::down-button:hover {
    background-color: #444444;
}
QSpinBox::down-button:disabled {
    background-color: #2a2a2a;
    border-color: #3e3e42;
}
QSpinBox::down-arrow {
    image: url("__ARROW_DOWN_WHITE__");
    width: 10px;
    height: 6px;
}
QSpinBox::down-arrow:disabled {
    image: url("__ARROW_DOWN_GRAY__");
}

QRadioButton {
    color: #e6e6e6;
}
QStatusBar {
    background-color: #1e1e1e;
    color: #cccccc;
}
"""
DARK_STYLE = (
    DARK_STYLE.replace("__ARROW_UP_WHITE__", ICON_PATHS["arrow_up_white.svg"])
    .replace("__ARROW_UP_GRAY__", ICON_PATHS["arrow_up_gray.svg"])
    .replace("__ARROW_DOWN_WHITE__", ICON_PATHS["arrow_down_white.svg"])
    .replace("__ARROW_DOWN_GRAY__", ICON_PATHS["arrow_down_gray.svg"])
)

LIGHT_STYLE = """
QMainWindow, QWidget#centralWidget {
    background-color: #f3f3f3;
    color: #000000;
}
QLabel {
    color: #1a1a1a;
}
QLabel#pageLabel {
    font-weight: bold;
    font-size: 13px;
    color: #000000;
}
QLabel#fileLabel {
    font-size: 13px;
    font-weight: 500;
    color: #222222;
}
QLabel#placeholderText {
    font-size: 15px;
    line-height: 160%;
    color: #555555;
}

/* 하단 통합 컨트롤 바 */
QWidget#bottomBar {
    background-color: #f7f7f7;
    border-top: 1px solid #d5d5d5;
    border-radius: 4px;
}

/* 콤보박스 */
QComboBox {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #c5c5c5;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
QComboBox:hover {
    border-color: #a0a0a0;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #000000;
    selection-background-color: #cce8ff;
    selection-color: #000000;
    border: 1px solid #c5c5c5;
}

/* 일반 버튼: 라이트 모드에서는 글씨 검정색 */
QPushButton {
    background-color: #f0f0f0;
    color: #000000;
    border: 1px solid #c5c5c5;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #e2e2e2;
    border-color: #a0a0a0;
}
QPushButton:pressed {
    background-color: #d0d0d0;
}
QPushButton:disabled {
    background-color: #ebebeb;
    color: #444444;
    border-color: #d0d0d0;
}

/* 상단 PDF 열기 버튼 (파란색 유지 + 흰색 글씨) */
QPushButton#openButton {
    background-color: #0e639c;
    color: #ffffff;
    font-weight: bold;
    padding: 6px 14px;
    border: 1px solid #1177bb;
    border-radius: 4px;
}
QPushButton#openButton:hover {
    background-color: #1177bb;
}
QPushButton#openButton:pressed {
    background-color: #094771;
}

/* 통합 저장 버튼 (초록색 기본) */
QPushButton#saveButton {
    background-color: #28a745;
    color: #ffffff;
    font-weight: bold;
    padding: 6px 14px;
    border: 1px solid #218838;
    border-radius: 4px;
}
QPushButton#saveButton:hover {
    background-color: #218838;
}
QPushButton#saveButton:pressed {
    background-color: #1e7e34;
}
QPushButton#saveButton:disabled {
    background-color: #a3d9b0;
    color: #ffffff;
    border-color: #90c79e;
}

/* 낱장 분할 모드일 때 저장 버튼 스타일 */
QPushButton#saveButton[mode="split"] {
    background-color: #17a2b8;
    border-color: #138496;
}
QPushButton#saveButton[mode="split"]:hover {
    background-color: #138496;
}
QPushButton#saveButton[mode="split"]:pressed {
    background-color: #117a8b;
}
QPushButton#saveButton[mode="split"]:disabled {
    background-color: #a0dce4;
    color: #ffffff;
    border-color: #8dcad3;
}

/* 테마 토글 버튼 */
QPushButton#themeButton {
    background-color: #f0f0f0;
    color: #000000;
    font-weight: bold;
    border: 1px solid #b5b5b5;
    border-radius: 4px;
}
QPushButton#themeButton:hover {
    background-color: #e0e0e0;
}

/* 스핀박스 및 텍스트 입력창 (라이트 모드 글씨 검정색, 선명한 업다운 버튼) */
QSpinBox, QLineEdit {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #c5c5c5;
    border-radius: 4px;
    padding: 3px 6px;
    selection-background-color: #cce8ff;
    selection-color: #000000;
}
QSpinBox {
    padding-left: 6px;
    padding-right: 20px;
}
QSpinBox:disabled, QLineEdit:disabled {
    background-color: #f7f7f7;
    color: #333333;
    border-color: #d0d0d0;
}
QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    background-color: #f0f0f0;
    border-left: 1px solid #c5c5c5;
    border-bottom: 1px solid #d5d5d5;
    border-top-right-radius: 3px;
}
QSpinBox::up-button:hover {
    background-color: #e0e0e0;
}
QSpinBox::up-button:disabled {
    background-color: #f7f7f7;
    border-color: #d0d0d0;
}
QSpinBox::up-arrow {
    image: url("__ARROW_UP_BLACK__");
    width: 10px;
    height: 6px;
}
QSpinBox::up-arrow:disabled {
    image: url("__ARROW_UP_DARKGRAY__");
}
QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    background-color: #f0f0f0;
    border-left: 1px solid #c5c5c5;
    border-bottom-right-radius: 3px;
}
QSpinBox::down-button:hover {
    background-color: #e0e0e0;
}
QSpinBox::down-button:disabled {
    background-color: #f7f7f7;
    border-color: #d0d0d0;
}
QSpinBox::down-arrow {
    image: url("__ARROW_DOWN_BLACK__");
    width: 10px;
    height: 6px;
}
QSpinBox::down-arrow:disabled {
    image: url("__ARROW_DOWN_DARKGRAY__");
}

QRadioButton {
    color: #1a1a1a;
}
QStatusBar {
    background-color: #e8e8e8;
    color: #333333;
}
"""
LIGHT_STYLE = (
    LIGHT_STYLE.replace("__ARROW_UP_BLACK__", ICON_PATHS["arrow_up_black.svg"])
    .replace("__ARROW_UP_DARKGRAY__", ICON_PATHS["arrow_up_darkgray.svg"])
    .replace("__ARROW_DOWN_BLACK__", ICON_PATHS["arrow_down_black.svg"])
    .replace("__ARROW_DOWN_DARKGRAY__", ICON_PATHS["arrow_down_darkgray.svg"])
)


def parse_page_ranges(input_str: str, max_pages: int) -> Tuple[List[int], str]:
    """'1, 3, 5-8, 10' 형태의 문자열을 0-based 정렬된 페이지 인덱스 리스트로 파싱.

    반환값: (페이지_인덱스_리스트, 오류_메시지)
    오류가 없으면 오류 메시지는 빈 문자열("")입니다.
    """
    input_str = input_str.strip()
    if not input_str:
        return [], "페이지 번호를 입력해주세요."

    pages = set()
    parts = [p.strip() for p in input_str.replace(";", ",").split(",") if p.strip()]

    if not parts:
        return [], "유효한 페이지 번호가 없습니다."

    for part in parts:
        sep = "-" if "-" in part else ("~" if "~" in part else None)
        if sep:
            range_parts = part.split(sep)
            if len(range_parts) != 2:
                return [], f"잘못된 범위 형식입니다: '{part}'"
            start_str, end_str = range_parts[0].strip(), range_parts[1].strip()
            if not start_str.isdigit() or not end_str.isdigit():
                return [], f"범위에 숫자가 아닌 문자가 포함되어 있습니다: '{part}'"
            start, end = int(start_str), int(end_str)
            if start < 1 or end < 1:
                return [], f"페이지 번호는 1 이상이어야 합니다: '{part}'"
            if start > end:
                return [], f"시작 페이지가 끝 페이지보다 큽니다: '{part}'"
            if end > max_pages:
                return [], f"끝 페이지({end})가 전체 페이지 수({max_pages})를 초과합니다."
            for p in range(start, end + 1):
                pages.add(p - 1)
        else:
            if not part.isdigit():
                return [], f"숫자가 아닌 문자가 포함되어 있습니다: '{part}'"
            p = int(part)
            if p < 1:
                return [], f"페이지 번호는 1 이상이어야 합니다: '{p}'"
            if p > max_pages:
                return [], f"페이지 번호({p})가 전체 페이지 수({max_pages})를 초과합니다."
            pages.add(p - 1)

    sorted_pages = sorted(list(pages))
    return sorted_pages, ""


def format_file_size(size_bytes: int) -> str:
    """파일 크기를 사람이 읽기 쉬운 단위로 변환"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


class DynamicStackedWidget(QStackedWidget):
    """현재 활성화된 페이지만큼의 크기 힌트를 동적으로 반환하는 스택 위젯"""

    def sizeHint(self):
        current = self.currentWidget()
        if current:
            return current.sizeHint()
        return super().sizeHint()

    def minimumSizeHint(self):
        current = self.currentWidget()
        if current:
            return current.minimumSizeHint()
        return super().minimumSizeHint()


class BottomControlBar(QWidget):
    """하단 컨트롤 바: [좌측: 모드선택] <--> [중앙: 내비게이션(정중앙)] <--> [우측: 옵션 & 저장] 3분할 밸런스 레이아웃"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bottomBar")
        self.setFixedHeight(50)
        self.left_widget = None
        self.center_widget = None
        self.right_widget = None
        self.mode_stack = None
        self.btn_save = None

    def set_sections(
        self,
        left: QWidget,
        center: QWidget,
        right: QWidget,
        mode_stack: QWidget,
        btn_save: QWidget,
    ):
        self.left_widget = left
        self.center_widget = center
        self.right_widget = right
        self.mode_stack = mode_stack
        self.btn_save = btn_save
        left.setParent(self)
        center.setParent(self)
        right.setParent(self)
        self.update_layout()

    def update_layout(self):
        if not (self.left_widget and self.center_widget and self.right_widget and self.mode_stack and self.btn_save):
            return
        w = self.width()
        h = self.height()
        margin = 12

        l_w = self.left_widget.sizeHint().width()
        l_h = 34
        l_y = (h - l_h) // 2

        c_w = self.center_widget.sizeHint().width()
        c_h = 34
        c_y = (h - c_h) // 2

        s_w = self.mode_stack.sizeHint().width()
        save_w = self.btn_save.sizeHint().width()
        r_w = s_w + save_w + 10
        r_h = 34
        r_y = (h - r_h) // 2

        # 윈도우 정중앙 위치 계산
        ideal_c_x = (w - c_w) // 2
        min_c_x = margin + l_w + 10
        max_c_x = w - margin - r_w - 10 - c_w

        if min_c_x <= max_c_x:
            # 여유 공간이 있을 때는 정중앙에 고정
            actual_c_x = max(min_c_x, min(ideal_c_x, max_c_x))
        else:
            # 창이 좁을 때는 좌측부터 순차 배치
            actual_c_x = min_c_x

        self.left_widget.setGeometry(margin, l_y, l_w, l_h)
        self.center_widget.setGeometry(actual_c_x, c_y, c_w, c_h)
        self.right_widget.setGeometry(max(actual_c_x + c_w + 10, w - margin - r_w), r_y, r_w, r_h)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_layout()


class PdfExtractorWindow(QMainWindow):
    """PDF Page Extractor 메인 윈도우"""

    def __init__(self):
        super().__init__()

        self.pdf_path: Path | None = None
        self.total_pages = 0
        self.zoom_factor = 1.0
        self.dark_mode = False
        self.two_page_mode = False
        self.current_page_idx = 0

        self.pdf_document = QPdfDocument(self)

        self.init_ui()
        self.connect_signals()
        self.init_shortcuts()

        # 테마 복원 (설정 저장소 확인, 없으면 시스템 다크 모드 감지)
        settings = QSettings("PdfPageExtractor", "Settings")
        saved = settings.value("dark_mode", None)
        if saved is None:
            hints = QApplication.instance().styleHints()
            initial_dark = hints.colorScheme() == Qt.ColorScheme.Dark if hasattr(hints, "colorScheme") else False
        else:
            initial_dark = (saved == "true" or saved is True)

        self.apply_theme(initial_dark)

        # 드래그 앤 드롭 활성화
        self.setAcceptDrops(True)

    def init_ui(self):
        """UI 컴포넌트 초기화 및 배치"""
        self.setWindowTitle("PDF Page Extractor - PDF 페이지 추출기")
        self.resize(1160, 880)
        self.setMinimumSize(920, 620)

        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))

        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 8)
        main_layout.setSpacing(8)

        # -------------------------------------------------------------
        # 1. 상단 툴바: 파일 열기 및 정보, 줌 컨트롤, 다크/라이트 토글
        # -------------------------------------------------------------
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)

        self.open_button = QPushButton("📁 PDF 열기 (Ctrl+O)")
        self.open_button.setObjectName("openButton")
        self.open_button.setFixedHeight(34)

        self.file_label = QLabel("열린 PDF 파일이 없습니다. 파일을 열거나 여기로 드래그하세요.")
        self.file_label.setObjectName("fileLabel")
        self.file_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        top_layout.addWidget(self.open_button)
        top_layout.addWidget(self.file_label, 1)

        # 줌 컨트롤 및 테마 토글 버튼 그룹
        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(5)

        self.btn_zoom_out = QPushButton("🔍 - 축소")
        self.btn_zoom_out.setFixedHeight(30)
        self.btn_zoom_out.setToolTip("화면 축소 (Ctrl + -)")
        self.btn_zoom_out.setEnabled(False)

        self.btn_zoom_in = QPushButton("🔍 + 확대")
        self.btn_zoom_in.setFixedHeight(30)
        self.btn_zoom_in.setToolTip("화면 확대 (Ctrl + +)")
        self.btn_zoom_in.setEnabled(False)

        self.btn_fit_view = QPushButton("화면 맞춤")
        self.btn_fit_view.setFixedHeight(30)
        self.btn_fit_view.setToolTip("전체 페이지가 한눈에 들어오도록 맞춤 (Ctrl + 0)")
        self.btn_fit_view.setEnabled(False)

        self.btn_fit_width = QPushButton("너비 맞춤")
        self.btn_fit_width.setFixedHeight(30)
        self.btn_fit_width.setToolTip("페이지 너비를 창 너비에 맞춤")
        self.btn_fit_width.setEnabled(False)

        self.btn_toggle_page_mode = QPushButton("📖 두쪽 보기")
        self.btn_toggle_page_mode.setFixedHeight(30)
        self.btn_toggle_page_mode.setToolTip("한쪽 보기 / 두쪽 보기 전환 (Ctrl+D)")
        self.btn_toggle_page_mode.setEnabled(False)

        # 다크 / 라이트 모드 전환 토글 버튼 (우측 상단)
        self.btn_theme = QPushButton()
        self.btn_theme.setObjectName("themeButton")
        self.btn_theme.setCheckable(True)
        self.btn_theme.setFixedHeight(30)
        self.btn_theme.setMinimumWidth(88)
        self.btn_theme.setToolTip("라이트 / 다크 모드 전환 (F6)")

        zoom_layout.addWidget(self.btn_zoom_out)
        zoom_layout.addWidget(self.btn_zoom_in)
        zoom_layout.addWidget(self.btn_fit_view)
        zoom_layout.addWidget(self.btn_fit_width)
        zoom_layout.addWidget(self.btn_toggle_page_mode)
        zoom_layout.addSpacing(6)
        zoom_layout.addWidget(self.btn_theme)

        top_layout.addLayout(zoom_layout)
        main_layout.addLayout(top_layout)

        # -------------------------------------------------------------
        # 2. 중앙 뷰어 및 빈 상태 플레이스홀더 (세로 공간 대폭 확장)
        # -------------------------------------------------------------
        view_container = QWidget()
        self.view_stack = QStackedLayout(view_container)

        # 플레이스홀더 (PDF 미열람 상태)
        self.empty_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        placeholder_icon = QLabel("📄")
        placeholder_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_icon.setStyleSheet("font-size: 56px; margin-bottom: 8px;")

        self.placeholder_text = QLabel(
            "PDF 파일을 여기에 마우스로 끌어다 놓거나(Drag & Drop),\n"
            "상단의 [PDF 열기] 버튼(Ctrl+O)을 클릭하세요."
        )
        self.placeholder_text.setObjectName("placeholderText")
        self.placeholder_text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_layout.addWidget(placeholder_icon)
        empty_layout.addWidget(self.placeholder_text)

        # PDF 뷰어 컨테이너 (한쪽 보기 / 두쪽 보기 겸용)
        self.viewer_widget = QWidget()
        self.viewer_layout = QHBoxLayout(self.viewer_widget)
        self.viewer_layout.setContentsMargins(0, 0, 0, 0)
        self.viewer_layout.setSpacing(0)

        # 두쪽 보기 시 두 페이지를 가깝게 나란히 배치하기 위한 스프레드 컨테이너
        self.spread_container = QWidget()
        self.spread_layout = QHBoxLayout(self.spread_container)
        self.spread_layout.setContentsMargins(0, 0, 0, 0)
        self.spread_layout.setSpacing(2)  # 두 페이지 사이의 얇은 제본선 여백 (2px)

        # 좌측 뷰어 (한쪽 보기 시 100% 사용)
        self.pdf_view_left = QPdfView()
        self.pdf_view_left.setDocument(self.pdf_document)
        self.pdf_view_left.setPageMode(QPdfView.PageMode.SinglePage)
        self.pdf_view_left.setZoomMode(QPdfView.ZoomMode.FitInView)
        self.pdf_view_left.setDocumentMargins(QMargins(0, 0, 0, 0))
        self.pdf_view = self.pdf_view_left  # 기존 호환성 유지

        # 우측 뷰어 컨테이너 (두쪽 보기 시 사용, 마지막 홀수 페이지일 때는 빈 슬롯 표시)
        self.right_container = QWidget()
        self.right_stack = QStackedLayout(self.right_container)
        self.right_stack.setContentsMargins(0, 0, 0, 0)

        self.pdf_view_right = QPdfView()
        self.pdf_view_right.setDocument(self.pdf_document)
        self.pdf_view_right.setPageMode(QPdfView.PageMode.SinglePage)
        self.pdf_view_right.setZoomMode(QPdfView.ZoomMode.FitInView)
        self.pdf_view_right.setDocumentMargins(QMargins(0, 0, 0, 0))

        self.right_empty = QLabel()
        self.right_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.right_stack.addWidget(self.pdf_view_right)
        self.right_stack.addWidget(self.right_empty)
        self.right_container.hide()  # 기본: 한쪽 보기이므로 숨김

        self.spread_layout.addWidget(self.pdf_view_left)
        self.spread_layout.addWidget(self.right_container)

        # viewer_layout: 좌우 스트레치로 감싸 두쪽 보기 시 정중앙에 밀착 배치
        self.viewer_layout.addStretch(1)
        self.viewer_layout.addWidget(self.spread_container)
        self.viewer_layout.addStretch(1)

        # 기본(한쪽 보기): spread_container가 가로 100% 채움
        self.viewer_layout.setStretch(0, 0)
        self.viewer_layout.setStretch(1, 1)
        self.viewer_layout.setStretch(2, 0)

        self.view_stack.addWidget(self.empty_widget)
        self.view_stack.addWidget(self.viewer_widget)
        self.view_stack.setCurrentWidget(self.empty_widget)

        main_layout.addWidget(view_container, 1)

        # -------------------------------------------------------------
        # 3. 하단 통합 컨트롤 바 (좌측 모드선택 / 중앙 내비게이션 / 우측 옵션&저장 3분할 밸런스 레이아웃)
        # -------------------------------------------------------------
        self.bottom_bar = BottomControlBar()

        # [3-1. 좌측] 추출 모드 선택
        left_widget = QWidget()
        l_lay = QHBoxLayout(left_widget)
        l_lay.setContentsMargins(0, 0, 0, 0)
        l_lay.setSpacing(8)

        l_lay.addWidget(QLabel("추출 모드:"))
        self.mode_combo = QComboBox()
        self.mode_combo.setFixedHeight(32)
        self.mode_combo.setMinimumWidth(150)
        self.mode_combo.addItems([
            "📑 연속 범위 추출",
            "🎯 자유 페이지 지정",
            "✂️ 낱장 전체 분할"
        ])
        self.mode_combo.setEnabled(False)
        l_lay.addWidget(self.mode_combo)

        # [3-2. 중앙] 페이지 내비게이션 (화면 정중앙에 고정 배치)
        center_widget = QWidget()
        c_lay = QHBoxLayout(center_widget)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(6)

        self.btn_prev = QPushButton("◀ 이전")
        self.btn_prev.setFixedHeight(32)
        self.btn_prev.setEnabled(False)

        self.page_label = QLabel("0 / 0 페이지")
        self.page_label.setObjectName("pageLabel")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setMinimumWidth(110)

        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 1)
        self.page_spin.setEnabled(False)
        self.page_spin.setSuffix(" 페이지")
        self.page_spin.setKeyboardTracking(False)
        self.page_spin.setFixedHeight(32)
        self.page_spin.setFixedWidth(108)

        self.btn_next = QPushButton("다음 ▶")
        self.btn_next.setFixedHeight(32)
        self.btn_next.setEnabled(False)

        c_lay.addWidget(self.btn_prev)
        c_lay.addWidget(self.page_label)
        c_lay.addWidget(self.page_spin)
        c_lay.addWidget(self.btn_next)

        # [3-3. 우측] 모드별 동적 설정 패널 + 일원화된 저장 버튼
        right_widget = QWidget()
        r_lay = QHBoxLayout(right_widget)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.setSpacing(10)

        self.mode_stack = DynamicStackedWidget()
        self.mode_stack.setFixedHeight(34)

        # Mode 0: 연속 범위
        panel_range = QWidget()
        r_lay0 = QHBoxLayout(panel_range)
        r_lay0.setContentsMargins(0, 0, 0, 0)
        r_lay0.setSpacing(4)

        r_lay0.addWidget(QLabel("시작:"))
        self.start_page_spin = QSpinBox()
        self.start_page_spin.setRange(1, 1)
        self.start_page_spin.setEnabled(False)
        self.start_page_spin.setFixedWidth(58)
        self.start_page_spin.setFixedHeight(30)
        r_lay0.addWidget(self.start_page_spin)

        self.btn_set_start = QPushButton("현재")
        self.btn_set_start.setToolTip("현재 화면 페이지를 시작 페이지로 지정")
        self.btn_set_start.setEnabled(False)
        self.btn_set_start.setFixedWidth(42)
        self.btn_set_start.setFixedHeight(30)
        r_lay0.addWidget(self.btn_set_start)

        r_lay0.addWidget(QLabel("~ 끝:"))
        self.end_page_spin = QSpinBox()
        self.end_page_spin.setRange(1, 1)
        self.end_page_spin.setEnabled(False)
        self.end_page_spin.setFixedWidth(58)
        self.end_page_spin.setFixedHeight(30)
        r_lay0.addWidget(self.end_page_spin)

        self.btn_set_end = QPushButton("현재")
        self.btn_set_end.setToolTip("현재 화면 페이지를 끝 페이지로 지정")
        self.btn_set_end.setEnabled(False)
        self.btn_set_end.setFixedWidth(42)
        self.btn_set_end.setFixedHeight(30)
        r_lay0.addWidget(self.btn_set_end)

        self.range_count_label = QLabel("선택: 0페이지")
        self.range_count_label.setStyleSheet("font-weight: bold;")
        self.range_count_label.setMinimumWidth(85)
        r_lay0.addWidget(self.range_count_label)

        # Mode 1: 자유 지정
        panel_custom = QWidget()
        c_lay1 = QHBoxLayout(panel_custom)
        c_lay1.setContentsMargins(0, 0, 0, 0)
        c_lay1.setSpacing(6)

        c_lay1.addWidget(QLabel("페이지:"))
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("예: 1, 3, 5-8, 12")
        self.custom_input.setEnabled(False)
        self.custom_input.setFixedWidth(160)
        self.custom_input.setFixedHeight(30)
        c_lay1.addWidget(self.custom_input)

        self.btn_add_current_custom = QPushButton("+현재")
        self.btn_add_current_custom.setToolTip("현재 화면 페이지 번호 추가")
        self.btn_add_current_custom.setEnabled(False)
        self.btn_add_current_custom.setFixedHeight(30)
        c_lay1.addWidget(self.btn_add_current_custom)

        self.custom_count_label = QLabel("선택: 0페이지")
        self.custom_count_label.setStyleSheet("font-weight: bold;")
        self.custom_count_label.setMinimumWidth(85)
        c_lay1.addWidget(self.custom_count_label)

        # Mode 2: 낱장 분할
        panel_split = QWidget()
        s_lay2 = QHBoxLayout(panel_split)
        s_lay2.setContentsMargins(0, 0, 0, 0)
        s_lay2.setSpacing(10)

        self.radio_split_all = QRadioButton("전체 낱장 분할")
        self.radio_split_all.setChecked(True)
        self.radio_split_all.setEnabled(False)
        s_lay2.addWidget(self.radio_split_all)

        self.radio_split_range = QRadioButton("지정 범위 분할")
        self.radio_split_range.setEnabled(False)
        s_lay2.addWidget(self.radio_split_range)

        self.mode_stack.addWidget(panel_range)
        self.mode_stack.addWidget(panel_custom)
        self.mode_stack.addWidget(panel_split)

        # [3-4. 우측 끝] 일원화된 통합 저장 버튼
        self.btn_save = QPushButton("💾 범위 저장 (Ctrl+S)")
        self.btn_save.setObjectName("saveButton")
        self.btn_save.setFixedHeight(34)
        self.btn_save.setMinimumWidth(140)
        self.btn_save.setEnabled(False)

        r_lay.addWidget(self.mode_stack)
        r_lay.addWidget(self.btn_save)

        # 3분할 섹션 등록
        self.bottom_bar.set_sections(
            left_widget, center_widget, right_widget, self.mode_stack, self.btn_save
        )

        main_layout.addWidget(self.bottom_bar)

        # 하단 상태바
        self.statusBar().showMessage("준비 완료 - PDF 파일을 열거나 여기로 드래그하세요.")

    def apply_theme(self, dark: bool):
        """다크 / 라이트 모드 전환 (버튼 글씨: 다크=흰색, 라이트=검정색 완벽 분리)"""
        self.dark_mode = dark
        app = QApplication.instance()
        hints = app.styleHints()
        if hasattr(hints, "setColorScheme"):
            hints.setColorScheme(Qt.ColorScheme.Dark if dark else Qt.ColorScheme.Light)
        app.setPalette(dark_palette() if dark else light_palette())

        # 전역 스타일시트 일괄 적용
        self.setStyleSheet(DARK_STYLE if dark else LIGHT_STYLE)

        self.btn_theme.blockSignals(True)
        self.btn_theme.setChecked(dark)
        self.btn_theme.setText("🌙 Dark" if dark else "☀ Light")
        self.btn_theme.blockSignals(False)

        # 우측 빈 슬롯 배경색 동기화
        if hasattr(self, "right_empty"):
            bg_color = "#1e1e1e" if dark else "#f3f3f3"
            self.right_empty.setStyleSheet(f"background-color: {bg_color};")

        # 상태 갱신
        self.update_range_count()
        if self.custom_input.text():
            self.on_custom_input_changed(self.custom_input.text())

        # 저장 버튼 스타일 갱신
        self.on_mode_changed(self.mode_combo.currentIndex())

        # 설정 영구 저장
        settings = QSettings("PdfPageExtractor", "Settings")
        settings.setValue("dark_mode", dark)
        self.statusBar().showMessage(f"테마 전환: {'다크 모드' if dark else '라이트 모드'}", 2000)

    def connect_signals(self):
        """위젯 시그널과 슬롯 연결"""
        self.open_button.clicked.connect(self.open_pdf_dialog)

        # 모드 전환
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)

        # 내비게이션
        self.btn_prev.clicked.connect(self.go_previous_page)
        self.btn_next.clicked.connect(self.go_next_page)
        self.page_spin.valueChanged.connect(self.go_to_page)

        # 줌 및 테마 컨트롤
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        self.btn_fit_view.clicked.connect(self.fit_in_view)
        self.btn_fit_width.clicked.connect(self.fit_width)
        self.btn_toggle_page_mode.clicked.connect(self.toggle_page_mode)
        self.btn_theme.toggled.connect(self.apply_theme)

        # 범위 추출 컨트롤
        self.btn_set_start.clicked.connect(self.set_current_as_start)
        self.btn_set_end.clicked.connect(self.set_current_as_end)
        self.start_page_spin.valueChanged.connect(self.update_range_count)
        self.end_page_spin.valueChanged.connect(self.update_range_count)

        # 자유 지정 컨트롤
        self.custom_input.textChanged.connect(self.on_custom_input_changed)
        self.btn_add_current_custom.clicked.connect(self.add_current_page_to_custom)

        # 통합 저장 버튼
        self.btn_save.clicked.connect(self.execute_save)

        # 뷰어 페이지 이동 감지
        navigator = self.pdf_view_left.pageNavigator()
        navigator.currentPageChanged.connect(self.on_current_page_changed)

    def init_shortcuts(self):
        """키보드 단축키 설정"""
        QShortcut(QKeySequence("Ctrl+O"), self, self.open_pdf_dialog)
        QShortcut(QKeySequence("Ctrl+S"), self, self.execute_save)
        QShortcut(QKeySequence("Ctrl+D"), self, self.toggle_page_mode)
        QShortcut(QKeySequence("F6"), self, lambda: self.btn_theme.toggle())

        # 이전 / 다음 페이지 이동 (좌우 화살표, PgUp, PgDown)
        QShortcut(QKeySequence(Qt.Key_Left), self, self.go_previous_page)
        QShortcut(QKeySequence(Qt.Key_Right), self, self.go_next_page)
        QShortcut(QKeySequence("PgUp"), self, self.go_previous_page)
        QShortcut(QKeySequence("PgDown"), self, self.go_next_page)

        # 처음 / 끝 페이지
        QShortcut(QKeySequence("Home"), self, lambda: self.move_to_page(0))
        QShortcut(QKeySequence("End"), self, lambda: self.move_to_page(self.total_pages - 1))

        # 확대 / 축소 / 맞춤
        QShortcut(QKeySequence("Ctrl++"), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl+="), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self.fit_in_view)

        # 도움말
        QShortcut(QKeySequence("F1"), self, self.show_help)

    def on_mode_changed(self, index: int):
        """추출 모드 변경 시 스택 위젯 및 저장 버튼 전환"""
        self.mode_stack.setCurrentIndex(index)

        if index == 0:  # 연속 범위
            self.btn_save.setText("💾 범위 저장 (Ctrl+S)")
            self.btn_save.setProperty("mode", "normal")
            self.btn_save.setEnabled(self.pdf_path is not None and self.start_page_spin.value() <= self.end_page_spin.value())
        elif index == 1:  # 자유 지정
            self.btn_save.setText("💾 지정 저장 (Ctrl+S)")
            self.btn_save.setProperty("mode", "normal")
            pages, err = parse_page_ranges(self.custom_input.text(), self.total_pages) if self.pdf_path else ([], "error")
            self.btn_save.setEnabled(self.pdf_path is not None and len(pages) > 0 and not err)
        elif index == 2:  # 낱장 분할
            self.btn_save.setText("✂️ 낱장 분할 저장")
            self.btn_save.setProperty("mode", "split")
            self.btn_save.setEnabled(self.pdf_path is not None)

        # 스타일 리프레시
        self.btn_save.style().unpolish(self.btn_save)
        self.btn_save.style().polish(self.btn_save)

        # 3분할 밸런스 레이아웃 동적 갱신
        self.bottom_bar.update_layout()

    # -------------------------------------------------------------
    # 드래그 앤 드롭 이벤트 처리
    # -------------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(".pdf"):
                self.load_pdf_file(file_path)
                event.acceptProposedAction()
                return

    # -------------------------------------------------------------
    # PDF 로드 및 컨트롤 상태 관리
    # -------------------------------------------------------------
    def open_pdf_dialog(self):
        """파일 다이얼로그로 PDF 파일 선택"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "PDF 파일 선택", "", "PDF 파일 (*.pdf)"
        )
        if file_path:
            self.load_pdf_file(file_path)

    def load_pdf_file(self, file_path: str):
        """지정한 경로의 PDF 파일을 열어 뷰어에 표시"""
        path_obj = Path(file_path)
        if not path_obj.exists():
            QMessageBox.critical(self, "오류", f"파일을 찾을 수 없습니다:\n{file_path}")
            return

        try:
            self.pdf_document.close()
            error = self.pdf_document.load(file_path)

            if error != QPdfDocument.Error.None_:
                raise RuntimeError(f"PDF 파일을 열 수 없습니다 (오류 코드: {error})")

            self.total_pages = self.pdf_document.pageCount()
            if self.total_pages <= 0:
                raise RuntimeError("PDF 문서에 유효한 페이지가 없습니다.")

            self.pdf_path = path_obj
            file_size_str = format_file_size(path_obj.stat().st_size)

            # 상단 레이블 갱신
            self.file_label.setText(
                f"<b>{path_obj.name}</b> · 전체 {self.total_pages}페이지 ({file_size_str})"
            )

            # 컨트롤 활성화 및 범위 설정
            self.set_controls_enabled(True)

            self.page_spin.blockSignals(True)
            self.page_spin.setRange(1, self.total_pages)
            self.page_spin.setValue(1)
            self.page_spin.blockSignals(False)

            self.start_page_spin.blockSignals(True)
            self.start_page_spin.setRange(1, self.total_pages)
            self.start_page_spin.setValue(1)
            self.start_page_spin.blockSignals(False)

            self.end_page_spin.blockSignals(True)
            self.end_page_spin.setRange(1, self.total_pages)
            self.end_page_spin.setValue(self.total_pages)
            self.end_page_spin.blockSignals(False)

            self.update_range_count()
            self.on_mode_changed(self.mode_combo.currentIndex())

            # 뷰어 표시
            self.view_stack.setCurrentWidget(self.viewer_widget)
            self.current_page_idx = 0
            self.move_to_page(0)
            if self.two_page_mode:
                self.recalc_spread_size()
            else:
                self.fit_in_view()

            self.statusBar().showMessage(f"열기 완료: {path_obj.name} (전체 {self.total_pages}페이지)", 5000)

        except Exception as e:
            self.pdf_path = None
            self.total_pages = 0
            self.set_controls_enabled(False)
            self.view_stack.setCurrentWidget(self.empty_widget)
            self.file_label.setText("열린 PDF 파일이 없습니다.")
            QMessageBox.critical(self, "PDF 열기 실패", str(e))

    def set_controls_enabled(self, enabled: bool):
        """UI 버튼 및 스핀박스 활성/비활성 제어"""
        self.btn_zoom_out.setEnabled(enabled)
        self.btn_zoom_in.setEnabled(enabled)
        self.btn_fit_view.setEnabled(enabled)
        self.btn_fit_width.setEnabled(enabled)
        self.btn_toggle_page_mode.setEnabled(enabled)

        self.mode_combo.setEnabled(enabled)

        self.page_spin.setEnabled(enabled)
        self.btn_prev.setEnabled(enabled)
        self.btn_next.setEnabled(enabled)

        self.start_page_spin.setEnabled(enabled)
        self.end_page_spin.setEnabled(enabled)
        self.btn_set_start.setEnabled(enabled)
        self.btn_set_end.setEnabled(enabled)

        self.custom_input.setEnabled(enabled)
        self.btn_add_current_custom.setEnabled(enabled)

        self.radio_split_all.setEnabled(enabled)
        self.radio_split_range.setEnabled(enabled)

        self.btn_save.setEnabled(enabled)

        if not enabled:
            self.page_label.setText("0 / 0 페이지")
            self.range_count_label.setText("선택: 0페이지")
            self.custom_count_label.setText("선택: 0페이지")
            self.btn_toggle_page_mode.setText("📖 두쪽 보기")
            self.btn_toggle_page_mode.setToolTip("한쪽 보기 / 두쪽 보기 전환 (Ctrl+D)")
            self.two_page_mode = False
            self.viewer_layout.setStretch(0, 0)
            self.viewer_layout.setStretch(1, 1)
            self.viewer_layout.setStretch(2, 0)
            self.spread_container.setMinimumSize(0, 0)
            self.spread_container.setMaximumSize(16777215, 16777215)
            self.pdf_view_left.setMinimumSize(0, 0)
            self.pdf_view_left.setMaximumSize(16777215, 16777215)
            self.right_container.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "two_page_mode", False):
            self.recalc_spread_size()

    def recalc_spread_size(self):
        """두쪽 보기 모드에서 스크롤바가 표시되지 않도록 화면 크기에 맞춰 두 페이지를 최적 크기로 조정"""
        if not getattr(self, "two_page_mode", False) or self.total_pages <= 0:
            return

        avail_w = self.viewer_widget.width()
        avail_h = self.viewer_widget.height()
        if avail_w <= 20 or avail_h <= 20:
            return

        # 상하 12px, 좌우 16px 안전 여백으로 스크롤바/오버플로 원천 방지
        target_h = avail_h - 12
        target_w = avail_w - 16
        spacing = self.spread_layout.spacing()

        # 현재 페이지 포인트 크기 및 종횡비
        p_size = self.pdf_document.pagePointSize(self.current_page_idx)
        pw = p_size.width()
        ph = p_size.height()
        if ph <= 0 or pw <= 0:
            pw, ph = 595.0, 842.0

        ar = pw / ph

        # 가로 폭 기준 최대 높이 vs 세로 가용 높이 중 작은 값 채택 (스크롤바 절대 방지)
        h_from_w = (target_w - spacing) / (2.0 * ar)
        h_from_h = target_h

        chosen_h = max(100, int(min(h_from_w, h_from_h)))
        chosen_w = max(50, int(chosen_h * ar))

        spread_w = chosen_w * 2 + spacing
        self.spread_container.setFixedSize(spread_w, chosen_h)
        self.pdf_view_left.setFixedSize(chosen_w, chosen_h)
        self.right_container.setFixedSize(chosen_w, chosen_h)

        self.pdf_view_left.setZoomMode(QPdfView.ZoomMode.FitInView)
        self.pdf_view_right.setZoomMode(QPdfView.ZoomMode.FitInView)

    # -------------------------------------------------------------
    # 페이지 이동 및 뷰어 제어
    # -------------------------------------------------------------
    def toggle_page_mode(self):
        """한쪽 보기 / 두쪽 보기 전환"""
        if self.total_pages <= 0:
            return

        self.two_page_mode = not self.two_page_mode
        if self.two_page_mode:
            self.btn_toggle_page_mode.setText("📄 한쪽 보기")
            self.btn_toggle_page_mode.setToolTip("한쪽 보기로 전환 (Ctrl+D)")

            # 두쪽 보기: 중앙 밀착 레이아웃 및 스크롤바 숨김
            self.viewer_layout.setStretch(0, 1)
            self.viewer_layout.setStretch(1, 0)
            self.viewer_layout.setStretch(2, 1)

            self.pdf_view_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.pdf_view_left.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.pdf_view_right.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.pdf_view_right.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

            self.right_container.show()
            self.move_to_page(self.current_page_idx)
            self.recalc_spread_size()
            self.statusBar().showMessage("보기 모드: 두쪽 보기 (스크롤바 없이 중앙 밀착)", 2000)
        else:
            self.btn_toggle_page_mode.setText("📖 두쪽 보기")
            self.btn_toggle_page_mode.setToolTip("두쪽 보기로 전환 (Ctrl+D)")

            # 한쪽 보기: 전체 영역 확장 및 스크롤바 필요시 표시
            self.viewer_layout.setStretch(0, 0)
            self.viewer_layout.setStretch(1, 1)
            self.viewer_layout.setStretch(2, 0)

            self.right_container.hide()
            self.spread_container.setMinimumSize(0, 0)
            self.spread_container.setMaximumSize(16777215, 16777215)
            self.pdf_view_left.setMinimumSize(0, 0)
            self.pdf_view_left.setMaximumSize(16777215, 16777215)
            self.pdf_view_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.pdf_view_left.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

            self.move_to_page(self.current_page_idx)
            self.fit_in_view()
            self.statusBar().showMessage("보기 모드: 한쪽 보기", 2000)

    def move_to_page(self, page_index: int):
        """0-based 페이지 인덱스로 이동"""
        if self.total_pages <= 0:
            return
        target_idx = max(0, min(page_index, self.total_pages - 1))

        if self.two_page_mode:
            left_idx = (target_idx // 2) * 2
            right_idx = left_idx + 1
            self.current_page_idx = left_idx
            try:
                self.pdf_view_left.pageNavigator().jump(left_idx, QPointF(0, 0), 0)
                if right_idx < self.total_pages:
                    self.right_stack.setCurrentWidget(self.pdf_view_right)
                    self.pdf_view_right.pageNavigator().jump(right_idx, QPointF(0, 0), 0)
                else:
                    self.right_stack.setCurrentWidget(self.right_empty)
            except Exception as e:
                self.statusBar().showMessage(f"페이지 이동 오류: {e}", 3000)
            self.update_page_display(left_idx)
            self.recalc_spread_size()
        else:
            self.current_page_idx = target_idx
            try:
                self.pdf_view_left.pageNavigator().jump(target_idx, QPointF(0, 0), 0)
            except Exception as e:
                self.statusBar().showMessage(f"페이지 이동 오류: {e}", 3000)
            self.update_page_display(target_idx)

    def go_previous_page(self):
        if self.two_page_mode:
            if self.current_page_idx >= 2:
                self.move_to_page(self.current_page_idx - 2)
            elif self.current_page_idx > 0:
                self.move_to_page(0)
        else:
            if self.current_page_idx > 0:
                self.move_to_page(self.current_page_idx - 1)

    def go_next_page(self):
        if self.two_page_mode:
            if self.current_page_idx + 2 < self.total_pages:
                self.move_to_page(self.current_page_idx + 2)
        else:
            if self.current_page_idx < self.total_pages - 1:
                self.move_to_page(self.current_page_idx + 1)

    def go_to_page(self, page_number: int):
        self.move_to_page(page_number - 1)

    def on_current_page_changed(self, page_index: int):
        if not self.two_page_mode:
            self.current_page_idx = page_index
            self.update_page_display(page_index)

    def update_page_display(self, page_index: int):
        if self.total_pages <= 0:
            return
        if self.two_page_mode:
            left_page = (page_index // 2) * 2 + 1
            right_page = left_page + 1
            if right_page <= self.total_pages:
                self.page_label.setText(f"{left_page}-{right_page} / {self.total_pages} 페이지")
            else:
                self.page_label.setText(f"{left_page} / {self.total_pages} 페이지")

            self.page_spin.blockSignals(True)
            self.page_spin.setValue(left_page)
            self.page_spin.blockSignals(False)

            self.btn_prev.setEnabled(left_page > 1)
            self.btn_next.setEnabled(left_page + 1 < self.total_pages)
        else:
            curr_page = page_index + 1
            self.page_label.setText(f"{curr_page} / {self.total_pages} 페이지")

            self.page_spin.blockSignals(True)
            self.page_spin.setValue(curr_page)
            self.page_spin.blockSignals(False)

            self.btn_prev.setEnabled(page_index > 0)
            self.btn_next.setEnabled(page_index < self.total_pages - 1)

    def get_current_page_number(self) -> int:
        return self.current_page_idx + 1

    # -------------------------------------------------------------
    # 줌 컨트롤 (확대, 축소, 맞춤)
    # -------------------------------------------------------------
    def fit_in_view(self):
        if self.two_page_mode:
            self.recalc_spread_size()
            self.statusBar().showMessage("보기: 두쪽 화면 맞춤", 2000)
        else:
            self.pdf_view_left.setZoomMode(QPdfView.ZoomMode.FitInView)
            self.zoom_factor = self.pdf_view_left.zoomFactor()
            self.statusBar().showMessage("보기: 화면 맞춤 (FitInView)", 2000)

    def fit_width(self):
        if self.two_page_mode:
            self.recalc_spread_size()
            self.statusBar().showMessage("보기: 두쪽 화면 맞춤", 2000)
        else:
            self.pdf_view_left.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            self.zoom_factor = self.pdf_view_left.zoomFactor()
            self.statusBar().showMessage("보기: 너비 맞춤 (FitToWidth)", 2000)

    def zoom_in(self):
        self.pdf_view_left.setZoomMode(QPdfView.ZoomMode.Custom)
        self.pdf_view_right.setZoomMode(QPdfView.ZoomMode.Custom)
        self.zoom_factor = min(4.0, self.pdf_view_left.zoomFactor() * 1.2)
        self.pdf_view_left.setZoomFactor(self.zoom_factor)
        self.pdf_view_right.setZoomFactor(self.zoom_factor)
        self.statusBar().showMessage(f"확대: {int(self.zoom_factor * 100)}%", 2000)

    def zoom_out(self):
        self.pdf_view_left.setZoomMode(QPdfView.ZoomMode.Custom)
        self.pdf_view_right.setZoomMode(QPdfView.ZoomMode.Custom)
        self.zoom_factor = max(0.2, self.pdf_view_left.zoomFactor() / 1.2)
        self.pdf_view_left.setZoomFactor(self.zoom_factor)
        self.pdf_view_right.setZoomFactor(self.zoom_factor)
        self.statusBar().showMessage(f"축소: {int(self.zoom_factor * 100)}%", 2000)

    # -------------------------------------------------------------
    # 모드 0: 연속 범위 설정
    # -------------------------------------------------------------
    def set_current_as_start(self):
        curr = self.get_current_page_number()
        self.start_page_spin.setValue(curr)

    def set_current_as_end(self):
        if self.two_page_mode:
            right_page = min(self.total_pages, self.current_page_idx + 2)
            self.end_page_spin.setValue(right_page)
        else:
            curr = self.get_current_page_number()
            self.end_page_spin.setValue(curr)

    def update_range_count(self):
        start = self.start_page_spin.value()
        end = self.end_page_spin.value()
        highlight_color = "#4ea1f3" if getattr(self, "dark_mode", False) else "#0e639c"
        if start <= end:
            count = end - start + 1
            self.range_count_label.setText(f"선택: {count}페이지")
            self.range_count_label.setStyleSheet(f"font-weight: bold; color: {highlight_color};")
            if self.mode_combo.currentIndex() == 0:
                self.btn_save.setEnabled(self.pdf_path is not None)
        else:
            self.range_count_label.setText("오류(시작>끝)")
            self.range_count_label.setStyleSheet("font-weight: bold; color: #ff5555;")
            if self.mode_combo.currentIndex() == 0:
                self.btn_save.setEnabled(False)

    def save_range_pages(self):
        """연속 범위 추출 저장"""
        if not self.pdf_path:
            return
        start = self.start_page_spin.value()
        end = self.end_page_spin.value()
        if start > end:
            QMessageBox.warning(self, "오류", "시작 페이지가 끝 페이지보다 큽니다.")
            return

        indices = list(range(start - 1, end))
        default_name = f"{self.pdf_path.stem}_{start}-{end}.pdf"
        self._write_extracted_pdf(indices, default_name, f"{start}~{end} 페이지 ({len(indices)}장)")

    # -------------------------------------------------------------
    # 모드 1: 자유 페이지 지정
    # -------------------------------------------------------------
    def add_current_page_to_custom(self):
        if self.two_page_mode and self.current_page_idx + 1 < self.total_pages:
            curr = f"{self.current_page_idx + 1}, {self.current_page_idx + 2}"
        else:
            curr = str(self.get_current_page_number())
        text = self.custom_input.text().strip()
        if text:
            if not text.endswith(","):
                text += ", "
            text += curr
        else:
            text = curr
        self.custom_input.setText(text)

    def on_custom_input_changed(self, text: str):
        if not self.pdf_path or self.total_pages <= 0:
            return
        highlight_color = "#4ea1f3" if getattr(self, "dark_mode", False) else "#0e639c"
        if not text.strip():
            self.custom_count_label.setText("선택: 0페이지")
            self.custom_count_label.setStyleSheet(f"font-weight: bold; color: {highlight_color};")
            if self.mode_combo.currentIndex() == 1:
                self.btn_save.setEnabled(False)
            return

        pages, err = parse_page_ranges(text, self.total_pages)
        if err:
            self.custom_count_label.setText(f"오류: {err}")
            self.custom_count_label.setStyleSheet("font-weight: bold; color: #ff5555;")
            if self.mode_combo.currentIndex() == 1:
                self.btn_save.setEnabled(False)
        else:
            self.custom_count_label.setText(f"선택: {len(pages)}페이지")
            self.custom_count_label.setStyleSheet(f"font-weight: bold; color: {highlight_color};")
            if self.mode_combo.currentIndex() == 1:
                self.btn_save.setEnabled(len(pages) > 0)

    def save_custom_pages(self):
        """자유 지정 페이지 추출 저장"""
        if not self.pdf_path:
            return
        text = self.custom_input.text().strip()
        pages, err = parse_page_ranges(text, self.total_pages)
        if err or not pages:
            QMessageBox.warning(self, "페이지 형식 오류", err or "추출할 페이지를 입력하세요.")
            return

        default_name = f"{self.pdf_path.stem}_custom_{len(pages)}p.pdf"
        self._write_extracted_pdf(pages, default_name, f"지정된 {len(pages)}개 페이지")

    # -------------------------------------------------------------
    # 모드 2: 낱장 분할
    # -------------------------------------------------------------
    def save_split_pages(self):
        """각 페이지를 1페이지짜리 PDF 파일로 낱장 분할 저장"""
        if not self.pdf_path:
            return

        if self.radio_split_all.isChecked():
            indices = list(range(self.total_pages))
        else:
            start = self.start_page_spin.value()
            end = self.end_page_spin.value()
            if start > end:
                QMessageBox.warning(self, "오류", "연속 범위 모드의 시작 페이지가 끝 페이지보다 큽니다.")
                return
            indices = list(range(start - 1, end))

        target_dir = QFileDialog.getExistingDirectory(
            self, "분할된 PDF 파일을 저장할 폴더 선택", str(self.pdf_path.parent)
        )
        if not target_dir:
            return

        try:
            reader = PdfReader(str(self.pdf_path))
            stem = self.pdf_path.stem
            saved_count = 0

            for idx in indices:
                writer = PdfWriter()
                writer.add_page(reader.pages[idx])
                out_name = f"{stem}_page_{idx + 1:03d}.pdf"
                out_path = os.path.join(target_dir, out_name)
                with open(out_path, "wb") as f:
                    writer.write(f)
                saved_count += 1

            QMessageBox.information(
                self, "낱장 분할 완료",
                f"총 {saved_count}개의 1페이지 PDF 파일로 분할 저장을 완료했습니다!\n\n저장 경로:\n{target_dir}"
            )
            self.statusBar().showMessage(f"낱장 분할 완료: {saved_count}개 파일 저장됨", 5000)

        except Exception as e:
            QMessageBox.critical(self, "분할 저장 실패", f"파일 분할 중 오류가 발생했습니다:\n{e}")

    # -------------------------------------------------------------
    # 일원화된 저장 실행 (현재 선택된 모드에 따라 실행)
    # -------------------------------------------------------------
    def execute_save(self):
        idx = self.mode_combo.currentIndex()
        if idx == 0:
            self.save_range_pages()
        elif idx == 1:
            self.save_custom_pages()
        elif idx == 2:
            self.save_split_pages()

    # -------------------------------------------------------------
    # 공통 PDF 파일 쓰기 헬퍼
    # -------------------------------------------------------------
    def _write_extracted_pdf(self, page_indices: List[int], default_filename: str, summary_desc: str):
        save_path, _ = QFileDialog.getSaveFileName(
            self, "추출 PDF 저장",
            str(self.pdf_path.parent / default_filename),
            "PDF 파일 (*.pdf)"
        )
        if not save_path:
            return

        if not save_path.lower().endswith(".pdf"):
            save_path += ".pdf"

        try:
            reader = PdfReader(str(self.pdf_path))
            writer = PdfWriter()

            for idx in page_indices:
                writer.add_page(reader.pages[idx])

            with open(save_path, "wb") as f:
                writer.write(f)

            QMessageBox.information(
                self, "저장 완료",
                f"{summary_desc} 저장을 완료했습니다!\n\n저장 파일:\n{save_path}"
            )
            self.statusBar().showMessage(f"저장 성공: {save_path}", 5000)

        except PermissionError:
            QMessageBox.critical(self, "저장 실패", "파일 쓰기 권한이 없거나 다른 프로그램에서 사용 중입니다.")
        except Exception as e:
            QMessageBox.critical(self, "저장 실패", f"저장 중 오류 발생:\n{e}")

    def show_help(self):
        """도움말 대화상자 표시"""
        help_text = (
            "PDF Page Extractor (PDF 페이지 추출기)\n\n"
            "[주요 기능]\n"
            "  1. 연속 범위 추출: 시작/끝 번호 지정 후 일괄 추출\n"
            "  2. 자유 페이지 지정: '1, 3, 5-8' 처럼 원하는 페이지만 골라 추출\n"
            "  3. 낱장 전체 분할: 각 페이지를 1페이지짜리 PDF로 개별 저장\n"
            "  4. 드래그 앤 드롭: 파일 탐색기에서 창으로 PDF를 끌어다 놓아 열기\n"
            "  5. 다크/라이트 모드: 우측 상단 버튼 또는 F6 키로 언제든 전환\n\n"
            "[단축키 안내]\n"
            "  Ctrl + O         : PDF 파일 열기\n"
            "  Ctrl + S         : 현재 선택된 페이지 저장/추출\n"
            "  F6               : 다크 / 라이트 테마 전환\n"
            "  ← / PgUp         : 이전 페이지 이동\n"
            "  → / PgDown       : 다음 페이지 이동\n"
            "  Home / End       : 첫 페이지 / 마지막 페이지 이동\n"
            "  Ctrl + + / =     : 화면 확대\n"
            "  Ctrl + -         : 화면 축소\n"
            "  Ctrl + 0         : 화면 맞춤 (Fit in view)\n"
            "  F1               : 도움말 창 표시\n\n"
            "[안내]\n"
            "  - 모든 처리는 인터넷 연결 없이 PC 로컬에서 100% 안전하게 수행됩니다.\n"
            "  - 원본 PDF 문서의 화질 손실 없이 벡터 텍스트/이미지를 그대로 보존합니다."
        )
        QMessageBox.information(self, "도움말", help_text)


def main():
    # 고해상도(HiDPI) 디스플레이 지원 설정
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("pdfpageextractor.app.1.0")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    window = PdfExtractorWindow()
    window.show()

    # 인자로 PDF 파일 경로가 전달된 경우 즉시 열기
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".pdf"):
        window.load_pdf_file(sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
