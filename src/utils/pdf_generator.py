"""
Markdown / Plain Text → PDF 生成器（基于 reportlab）。
支持中文、多级标题、代码块、表格。
"""

from __future__ import annotations

import platform
import re
from pathlib import Path
from typing import List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---------------------------------------------------------------------------
# 中文字体发现 & 注册（跨平台：Windows / Linux）
# ---------------------------------------------------------------------------

def _get_font_search_dirs() -> list[Path]:
    """返回当前平台的中文字体搜索目录列表（按优先级排序）。"""
    dirs: list[Path] = []
    if platform.system() == "Windows":
        win_dir = Path(platform.win32_ver()[0] if hasattr(platform, 'win32_ver') else "C:/Windows")
        dirs.append(win_dir / "Fonts")
    else:
        # Linux 常见字体目录
        dirs = [
            Path("/usr/share/fonts/truetype/wqy"),      # WenQuanYi
            Path("/usr/share/fonts/opentype/noto"),     # Noto CJK
            Path("/usr/share/fonts/truetype"),           # 通用
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
        ]
    return dirs


# 中文字体候选列表（文件名, 标签）
# reportlab 的 TTFont 支持 .ttc 文件，通过 subfontIndex 选择子字体（0=第一个字体）
WINDOWS_FONT_CANDIDATES: list[tuple[str, str, int]] = [
    ("msyh.ttc",       "Microsoft YaHei",       0),
    ("msyhbd.ttc",     "Microsoft YaHei Bold",  0),
    ("simhei.ttf",     "SimHei",                0),
    ("simsun.ttc",     "SimSun",                0),
    ("NotoSansSC-VF.ttf", "NotoSansSC",          0),
]

LINUX_FONT_CANDIDATES: list[tuple[str, str, int]] = [
    ("wqy-microhei.ttc",  "WenQuanYi Micro Hei", 0),
    ("wqy-zenhei.ttc",    "WenQuanYi Zen Hei",   0),
]

# 全局注册字体别名（模块级别只注册一次）
_font_normal: str = "Helvetica"
_font_bold: str = "Helvetica-Bold"
_font_registered: bool = False


def _register_chinese_font() -> None:
    """注册中文字体到 reportlab，全局只执行一次。

    先尝试注册粗体（用于标题 / **粗体**），再注册常规体。
    优先使用 Noto Sans CJK（Linux）或 Microsoft YaHei（Windows）。
    全部失败则回退到内置 Helvetica（不支持中文，显示为方框）。
    """
    global _font_normal, _font_bold, _font_registered
    if _font_registered:
        return
    _font_registered = True

    is_linux = platform.system() != "Windows"
    search_dirs = _get_font_search_dirs()
    candidates = LINUX_FONT_CANDIDATES if is_linux else WINDOWS_FONT_CANDIDATES

    # 1) 尝试注册粗体（Bold）
    bold_alias = "ChineseFont-Bold"
    bold_ok = False
    for font_file, _label, subfont in candidates:
        if "Bold" not in font_file and "bd" not in font_file:
            continue  # 跳过非粗体候选
        for d in search_dirs:
            p = d / font_file
            if not p.exists():
                continue
            try:
                pdfmetrics.registerFont(TTFont(bold_alias, str(p), subfontIndex=subfont))
                bold_ok = True
                break
            except Exception:
                continue
        if bold_ok:
            break

    # 2) 尝试注册常规体（Regular）
    normal_alias = "ChineseFont"
    normal_ok = False
    for font_file, _label, subfont in candidates:
        if "Bold" in font_file or "bd" in font_file:
            continue  # 跳过粗体候选
        for d in search_dirs:
            p = d / font_file
            if not p.exists():
                continue
            try:
                pdfmetrics.registerFont(TTFont(normal_alias, str(p), subfontIndex=subfont))
                normal_ok = True
                break
            except Exception:
                continue
        if normal_ok:
            break

    # 3) 如果只找到了一个，两个都用同一个
    if normal_ok:
        _font_normal = normal_alias
        _font_bold = bold_alias if bold_ok else normal_alias
        return
    if bold_ok:
        _font_normal = bold_alias
        _font_bold = bold_alias
        return

    # 4) 全部失败：回退到 Helvetica
    _font_normal = "Helvetica"
    _font_bold = "Helvetica-Bold"


def _get_fonts() -> tuple:
    _register_chinese_font()
    return _font_normal, _font_bold


def text_to_pdf(
    text: str,
    output_path: str | Path,
    title: str = "",
    font_size: int = 11,
    line_spacing: float = 1.5,
) -> Path:
    """
    将 markdown 或纯文本内容渲染为 PDF 文件。

    - markdown 标题 (# ## ###) → 加大加粗
    - 代码块 (``` ```) → 等宽灰色背景
    - 表格 (| ... |) → 表格样式
    - 空行 → Spacer
    - 其余 → 正文
    """
    path = Path(output_path)
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=title or path.stem,
    )

    fn_normal, fn_bold = _get_fonts()

    def sty(name: str, **kwargs) -> ParagraphStyle:
        return ParagraphStyle(name, **kwargs)

    def sty_copy(base: ParagraphStyle, **kwargs) -> ParagraphStyle:
        """基于已有样式复制，只取 style 相关的属性。"""
        base_dict = {k: v for k, v in base.__dict__.items()
                     if k not in ('_name', 'parent', 'name')}
        base_dict.update(kwargs)
        return ParagraphStyle("_copied", **base_dict)

    s_title = sty("MyTitle", fontName=fn_bold, fontSize=22, leading=28,
                  alignment=TA_CENTER, spaceAfter=12, textColor=colors.HexColor("#1a1a2e"))
    s_h1 = sty("MyH1", fontName=fn_bold, fontSize=18, leading=24,
               spaceBefore=18, spaceAfter=8, textColor=colors.HexColor("#16213e"))
    s_h2 = sty("MyH2", fontName=fn_bold, fontSize=15, leading=20,
               spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#0f3460"))
    s_h3 = sty("MyH3", fontName=fn_bold, fontSize=13, leading=18,
               spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#1a1a2e"))
    s_body = sty("MyBody", fontName=fn_normal, fontSize=font_size,
                 leading=font_size * line_spacing, spaceAfter=4,
                 textColor=colors.HexColor("#333333"))
    s_code = sty("MyCode", fontName="Courier", fontSize=9, leading=13,
                 spaceBefore=4, spaceAfter=4, leftIndent=16,
                 textColor=colors.HexColor("#2d2d2d"))
    s_th = sty("MyTh", fontName=fn_bold, fontSize=font_size - 1, leading=14,
               alignment=TA_CENTER, textColor=colors.white)
    s_td = sty("MyTd", fontName=fn_normal, fontSize=font_size - 1, leading=14,
               textColor=colors.HexColor("#333333"))
    s_quote = sty("MyQuote", fontName=fn_normal, fontSize=font_size,
                  leading=font_size * line_spacing, leftIndent=20, rightIndent=20,
                  spaceAfter=4, textColor=colors.HexColor("#555555"))

    story: List = []

    if title:
        story.append(Paragraph(title, s_title))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))
        story.append(Spacer(1, 12))

    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 标题
        if stripped.startswith("### "):
            story.append(Paragraph(_esc(stripped[4:]), s_h3))
        elif stripped.startswith("## "):
            story.append(Paragraph(_esc(stripped[3:]), s_h2))
        elif stripped.startswith("# "):
            story.append(Paragraph(_esc(stripped[2:]), s_h1))
        # 代码块
        elif stripped.startswith("```"):
            code_lines: List[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(_esc(lines[i]))
                i += 1
            story.append(Paragraph("<br/>".join(code_lines), s_code))
            story.append(Spacer(1, 6))
        # 表格
        elif stripped.startswith("|") and stripped.endswith("|"):
            rows, i = _parse_table(lines, i)
            if rows:
                ncols = len(rows[0])
                col_w = (A4[0] - 4 * cm) / ncols
                tbl_data = []
                for ri, row in enumerate(rows):
                    p_row = [
                        Paragraph(_render(row[ci], s_th if ri == 0 else s_td),
                                  s_th if ri == 0 else s_td)
                        for ci in range(ncols)
                    ]
                    tbl_data.append(p_row)
                tbl = Table(tbl_data, colWidths=[col_w] * ncols, repeatRows=1)
                tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), fn_bold),
                    ("FONTSIZE", (0, 0), (-1, -1), font_size - 1),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.white, colors.HexColor("#f9f9f9")]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(tbl)
                story.append(Spacer(1, 10))
        # 引用
        elif stripped.startswith("> "):
            story.append(Paragraph(_render(stripped[2:], s_body), s_quote))
        # 列表
        elif re.match(r"^(\s*)[-*+]\s+", stripped) or re.match(r"^(\s*)\d+\.\s+", stripped):
            m = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)", stripped)
            if m:
                indent, bullet, rest = m.groups()
                lvl = len(indent) // 2
                story.append(Paragraph(_render(f"{'  ' * lvl}{bullet} {rest}", s_body),
                                       sty_copy(s_body, leftIndent=16 + lvl * 16)))
        # 空行
        elif not stripped:
            story.append(Spacer(1, 6))
        # 正文
        else:
            story.append(Paragraph(_render(stripped, s_body), s_body))

        i += 1

    doc.build(story)
    return path


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _replace_inline(m: re.Match) -> str:
    """根据匹配的分组返回对应的 reportlab XML 标签。"""
    if m.group(1) is not None:
        return f"<b>{m.group(1)}</b>"
    if m.group(2) is not None:
        return f"<b>{m.group(2)}</b>"
    if m.group(3) is not None:
        return f"<i>{m.group(3)}</i>"
    if m.group(4) is not None:
        return f"<i>{m.group(4)}</i>"
    if m.group(5) is not None:
        return f"<font face='Courier' color='#c7254e'>{m.group(5)}</font>"
    return m.group(0)


def _render(text: str, base_style: ParagraphStyle) -> str:
    """将 markdown 行内样式转为 reportlab XML 标记。

    使用单次正则替换，按优先级匹配 **粗体** > __粗体__ > *斜体* > _斜体_ > `代码`，
    确保 **...*...*** 这类重叠标记生成正确嵌套的 XML 标签。
    """
    result = _esc(text)
    result = re.sub(
        r"\*\*(.+?)\*\*|__(.+?)__|\*(.+?)\*|_(.+?)_|`(.+?)`",
        _replace_inline,
        result,
    )
    return result


def _parse_table(lines: List[str], start: int) -> tuple:
    """解析 markdown 表格，返回 (rows, next_idx)。"""
    rows: List[List[str]] = []
    i = start
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("|") or not line.endswith("|"):
            break
        row = [c.strip() for c in line.strip("|").split("|")]
        # 跳过对齐行
        if all(re.match(r"^[\s:|-]+$", c) for c in row):
            i += 1
            continue
        rows.append(row)
        i += 1
        if len(rows) > 30:
            break
    return rows, i

