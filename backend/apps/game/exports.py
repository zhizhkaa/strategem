"""Export helpers for game result files."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from datetime import timezone, timedelta
from typing import Any

from django.conf import settings

from .models import PARAMETERS_CONFIG, Game, GamePeriod


SUMMARY_PARAMS = [
    ("P1", "Население"),
    ("P4", "Продовольствие на человека"),
    ("P6", "Товары на человека"),
    ("F7", "Экология"),
    ("TF1", "Внешний долг"),
    ("P5", "Смертность"),
    ("P8", "Рождаемость"),
]
MSK = timezone(timedelta(hours=3))


def _periods(game: Game) -> list[GamePeriod]:
    return list(game.periods.order_by("period_number"))


def _number(value: Any) -> float | int | str:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _score(period: GamePeriod) -> float:
    return float(period.P6 or 0) + 4 * float(period.P4 or 0)


def _format_datetime(value: Any) -> str:
    if not value:
        return ""
    return value.astimezone(MSK).strftime("%d.%m.%Y %H:%M")


def _finished_at(game: Game) -> Any:
    if game.finished_at:
        return game.finished_at
    if game.status == "finished":
        return game.updated_at
    return None


def build_export_context(game: Game) -> dict[str, Any]:
    periods = _periods(game)
    final_period = periods[-1] if periods else game.get_current_period_obj()
    score_values = [_score(period) for period in periods]
    average_score = sum(score_values) / len(score_values) if score_values else 0

    return {
        "game": game,
        "periods": periods,
        "final_period": final_period,
        "average_score": average_score,
        "summary": [
            (code, label, _number(getattr(final_period, code, "")))
            for code, label in SUMMARY_PARAMS
        ],
    }


def build_results_xlsx(game: Game) -> bytes:
    """Build a detailed XLSX workbook with all saved period parameters."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    context = build_export_context(game)
    periods: list[GamePeriod] = context["periods"]

    workbook = Workbook()
    header_fill = PatternFill("solid", fgColor="DDEAF7")
    subheader_fill = PatternFill("solid", fgColor="E5E7EB")
    title_fill = PatternFill("solid", fgColor="0F8FCF")
    header_font = Font(bold=True)
    title_font = Font(bold=True, color="FFFFFF", size=12)
    thin = Side(style="thin", color="D1D5DB")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    metadata_rows = [
        ("Команда", game.team.name),
        ("Группа", game.team.group.name if game.team.group_id else ""),
        (
            "Факультет",
            game.team.group.faculty.name if game.team.group_id else "",
        ),
        ("Сложность", game.get_difficulty_display()),
        ("Период", f"{game.current_period} / {game.total_periods}"),
        ("Создана", _format_datetime(game.created_at)),
        ("Обновлена", _format_datetime(game.updated_at)),
        ("Закончена", _format_datetime(_finished_at(game))),
    ]

    def write_metadata(sheet, title: str) -> int:
        sheet.append((title,))
        sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=4)
        sheet["A1"].fill = title_fill
        sheet["A1"].font = title_font
        sheet["A1"].alignment = Alignment(horizontal="center")
        for label, value in metadata_rows:
            sheet.append((label, value))
            sheet.cell(row=sheet.max_row, column=1).font = header_font
        sheet.append(())
        return sheet.max_row + 1

    summary_sheet = workbook.active
    summary_sheet.title = "Сводные итоги"
    summary_start = write_metadata(summary_sheet, "Сводные итоги по периодам")
    summary_headers = [
        "Показатель",
        *[f"Период {period.period_number}" for period in periods],
    ]
    summary_sheet.append(summary_headers)
    for cell in summary_sheet[summary_start]:
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal="center")

    summary_metrics = [
        ("Сводный счёт", lambda period: _score(period)),
        ("Население", lambda period: _number(period.P1)),
        ("Продовольствие/чел", lambda period: _number(period.P4)),
        ("Товары/чел", lambda period: _number(period.P6)),
        ("Экология", lambda period: _number(period.F7)),
        ("Внешний долг", lambda period: _number(period.TF1)),
        ("Смертность", lambda period: _number(period.P5)),
        ("Рождаемость", lambda period: _number(period.P8)),
    ]
    for label, getter in summary_metrics:
        summary_sheet.append([label, *[getter(period) for period in periods]])
        for cell in summary_sheet[summary_sheet.max_row]:
            cell.border = border
            if cell.column >= 2:
                cell.alignment = Alignment(horizontal="right")

    summary_sheet.column_dimensions["A"].width = 24
    for column in range(2, len(summary_headers) + 1):
        summary_sheet.column_dimensions[get_column_letter(column)].width = 14

    periods_sheet = workbook.create_sheet("Периоды")
    period_start = write_metadata(periods_sheet, "Подробные данные по периодам")
    period_headers = ["Код", "Показатель", *[
        f"Период {period.period_number}" for period in periods
    ]]
    periods_sheet.append(period_headers)
    for cell in periods_sheet[period_start]:
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal="center")
    for code, config in PARAMETERS_CONFIG.items():
        periods_sheet.append(
            [
                code,
                config.get("verbose_name", code),
                *[_number(getattr(period, code, "")) for period in periods],
            ]
        )
        for cell in periods_sheet[periods_sheet.max_row]:
            cell.border = border
            if cell.column >= 3:
                cell.alignment = Alignment(horizontal="right")
    periods_sheet.freeze_panes = f"C{period_start + 1}"
    periods_sheet.column_dimensions["A"].width = 10
    periods_sheet.column_dimensions["B"].width = 48
    for index in range(3, len(period_headers) + 1):
        periods_sheet.column_dimensions[get_column_letter(index)].width = 14

    for sheet in (summary_sheet, periods_sheet):
        for row in sheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(
                    horizontal=cell.alignment.horizontal,
                    vertical="center",
                )
        for row in sheet.iter_rows(min_row=1, max_row=sheet.max_row):
            for cell in row:
                if cell.row < 10 and cell.value and not cell.fill.fill_type:
                    cell.fill = subheader_fill

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _pdf_font_path() -> Path | None:
    candidates = [
        settings.BASE_DIR.parent
        / "frontend"
        / "static"
        / "vendor"
        / "pdfjs"
        / "standard_fonts"
        / "LiberationSans-Regular.ttf",
        settings.BASE_DIR.parent
        / "frontend"
        / "static"
        / "vendor"
        / "pdfjs"
        / "standard_fonts"
        / "LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def build_results_pdf(game: Game) -> bytes:
    """Build a compact PDF version of the final results screen."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    context = build_export_context(game)
    periods: list[GamePeriod] = context["periods"]

    font_name = "Helvetica"
    font_path = _pdf_font_path()
    if font_path:
        pdfmetrics.registerFont(TTFont("StrategemRegular", str(font_path)))
        font_name = "StrategemRegular"

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "StrategemTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=18,
        leading=22,
        spaceAfter=6,
    )
    normal_style = ParagraphStyle(
        "StrategemNormal",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        leading=12,
    )

    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Итоги игры {game.team.name}",
    )

    story = [
        Paragraph("Итоги игры", title_style),
        Paragraph(
            (
                f"Команда: {game.team.name}<br/>"
                f"Группа: {game.team.group.name}<br/>"
                f"Статус: {game.get_status_display()}<br/>"
                f"Периоды: {game.current_period} / {game.total_periods}<br/>"
                f"Сводный счёт: {context['average_score']:.2f}"
            ),
            normal_style,
        ),
        Spacer(1, 6 * mm),
    ]

    summary_table = Table(
        [["Код", "Показатель", "Итоговое значение"], *context["summary"]],
        colWidths=[22 * mm, 70 * mm, 35 * mm],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (2, 1), (2, -1), "RIGHT"),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 6 * mm))

    dynamic_rows = [
        [
            "Период",
            "Население",
            "Прод./чел",
            "Товары/чел",
            "Экология",
            "Долг",
            "Смертность",
            "Рождаемость",
        ]
    ]
    for period in periods:
        dynamic_rows.append(
            [
                period.period_number,
                round(period.P1),
                round(period.P4, 2),
                round(period.P6, 2),
                f"{period.F7 * 100:.0f}%",
                round(period.TF1),
                round(period.P5, 1),
                round(period.P8, 1),
            ]
        )

    dynamic_table = Table(dynamic_rows, repeatRows=1)
    dynamic_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(Paragraph("Динамика по периодам", normal_style))
    story.append(Spacer(1, 2 * mm))
    story.append(dynamic_table)

    doc.build(story)
    return output.getvalue()
