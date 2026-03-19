import io
from dataclasses import dataclass
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Render charts server-side (no display required)
import pendulum
from matplotlib import pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import extract, func, select

from app import models


@dataclass(frozen=True)
class MonthlyPoint:
    year: int
    month: int
    total: float


def _fill_monthly_series(
    *,
    monthly_points: list[MonthlyPoint],
    start_date,
    end_date,
) -> list[MonthlyPoint]:
    totals_by_key = {(p.year, p.month): p.total for p in monthly_points}

    # Iterate month-by-month so charts and tables have consistent X axes.
    cursor = start_date.start_of("month")
    end_cursor = end_date.start_of("month")

    filled: list[MonthlyPoint] = []
    while cursor <= end_cursor:
        key = (cursor.year, cursor.month)
        filled.append(MonthlyPoint(year=cursor.year, month=cursor.month, total=totals_by_key.get(key, 0.0)))
        cursor = cursor.add(months=1)

    return filled


def _query_monthly_expenses(*, db, user_id: int, start_date, end_date) -> list[MonthlyPoint]:
    stmt = (
        select(
            extract("year", models.Transactions.transaction_date).label("year"),
            extract("month", models.Transactions.transaction_date).label("month"),
            func.sum(models.Transactions.amount).label("total_amount"),
        )
        .join(models.Category, models.Transactions.category_id == models.Category.id)
        .where(
            models.Transactions.user_id == user_id,
            models.Category.type == "expense",
            models.Transactions.transaction_date >= start_date,
            models.Transactions.transaction_date <= end_date,
        )
        .group_by(
            extract("year", models.Transactions.transaction_date),
            extract("month", models.Transactions.transaction_date),
        )
        .order_by(
            extract("year", models.Transactions.transaction_date),
            extract("month", models.Transactions.transaction_date),
        )
    )

    rows = db.execute(stmt).all()
    return [
        MonthlyPoint(year=int(year), month=int(month), total=float(total) if total else 0.0)
        for year, month, total in rows
    ]


def _query_category_distribution(*, db, user_id: int, start_date, end_date, top_n: int = 8) -> list[dict[str, Any]]:
    stmt = (
        select(
            models.Category.name.label("category_name"),
            func.sum(models.Transactions.amount).label("total_amount"),
        )
        .join(models.Category, models.Transactions.category_id == models.Category.id)
        .where(
            models.Transactions.user_id == user_id,
            models.Category.type == "expense",
            models.Transactions.transaction_date >= start_date,
            models.Transactions.transaction_date <= end_date,
        )
        .group_by(models.Category.name)
        .order_by(func.sum(models.Transactions.amount).desc())
    )

    rows = db.execute(stmt).all()

    points: list[dict[str, Any]] = [
        {"category": str(category_name), "total": float(total) if total else 0.0} for category_name, total in rows
    ]
    return points[:top_n]


def _plot_line_monthly(monthly_points: list[MonthlyPoint]) -> io.BytesIO:
    fig = plt.figure(figsize=(8, 3.5))
    ax = fig.add_subplot(111)

    if not monthly_points:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
    else:
        labels = [f"{p.year}-{p.month:02d}" for p in monthly_points]
        values = [p.total for p in monthly_points]
        ax.plot(labels, values, marker="o", linewidth=2)
        ax.set_title("Expenses by Month")
        ax.set_ylabel("Total amount")
        ax.grid(True, linestyle="--", alpha=0.4)
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200)
    plt.close(fig)
    buf.seek(0)
    return buf


def _plot_bar_monthly(monthly_points: list[MonthlyPoint]) -> io.BytesIO:
    fig = plt.figure(figsize=(8, 3.5))
    ax = fig.add_subplot(111)

    if not monthly_points:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
    else:
        labels = [f"{p.month:02d}" for p in monthly_points]
        values = [p.total for p in monthly_points]
        ax.bar(labels, values, color="#e74c3c")
        ax.set_title("Expenses by Month")
        ax.set_xlabel("Month")
        ax.set_ylabel("Total amount")
        ax.grid(True, axis="y", linestyle="--", alpha=0.4)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200)
    plt.close(fig)
    buf.seek(0)
    return buf


def _plot_category_pie(category_points: list[dict[str, Any]]) -> io.BytesIO:
    fig = plt.figure(figsize=(6.4, 4.6))
    ax = fig.add_subplot(111)

    if not category_points:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
    else:
        top = category_points[:8]
        other_total = sum(p["total"] for p in category_points[8:]) if len(category_points) > 8 else 0.0
        labels = [p["category"] for p in top]
        values = [p["total"] for p in top]
        if other_total > 0:
            labels.append("Other")
            values.append(other_total)

        total_value = sum(values)

        def _pct_fmt(pct: float) -> str:
            # Hide tiny percentages to reduce overlap noise.
            return f"{pct:.1f}%" if pct >= 3 else ""

        wedges, _texts, _autotexts = ax.pie(
            values,
            labels=None,  # labels are shown in the legend to avoid overlap
            autopct=_pct_fmt if total_value > 0 else None,
            startangle=90,
            pctdistance=0.72,
            textprops={"fontsize": 9},
        )
        ax.legend(
            wedges,
            labels,
            title="Categories",
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            fontsize=9,
            title_fontsize=10,
            frameon=False,
        )
        ax.axis("equal")
        fig.subplots_adjust(right=0.75)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200)
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_spending_report_pdf_bytes(
    *,
    db,
    user_id: int,
    report_type: str,
    start_year: int | None = None,
    start_month: int | None = None,
    end_year: int | None = None,
    end_month: int | None = None,
    year: int | None = None,
) -> bytes:
    if report_type not in {"monthly", "yearly"}:
        raise ValueError("report_type must be 'monthly' or 'yearly'")

    if report_type == "monthly":
        if start_year is None or start_month is None or end_year is None or end_month is None:
            raise ValueError("start_year/start_month/end_year/end_month are required for monthly reports")

        start_date = pendulum.datetime(start_year, start_month, 1)
        end_date = pendulum.datetime(end_year, end_month, 1).end_of("month")
    else:
        if year is None:
            raise ValueError("year is required for yearly reports")

        start_date = pendulum.datetime(year, 1, 1)
        end_date = pendulum.datetime(year, 12, 1).end_of("month")

    monthly_points = _query_monthly_expenses(
        db=db,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
    )
    monthly_points = _fill_monthly_series(monthly_points=monthly_points, start_date=start_date, end_date=end_date)

    total_spent = sum(p.total for p in monthly_points)
    avg_monthly = total_spent / len(monthly_points) if monthly_points else 0.0
    top_month = max(monthly_points, key=lambda p: p.total) if monthly_points else None

    # Query a bit more than the visible pie slices so we can group the rest as "Other".
    category_points_top = _query_category_distribution(
        db=db,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        top_n=20,
    )

    pie_points: list[dict[str, Any]] = category_points_top

    if report_type == "yearly":
        chart_img = _plot_bar_monthly(monthly_points)
        chart_title = "Yearly Spending Summary"
    else:
        chart_img = _plot_line_monthly(monthly_points)
        chart_title = "Monthly Spending Summary"

    pie_img = _plot_category_pie(pie_points)

    # Build PDF
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    if report_type == "yearly":
        report_label = f"Year {year}"
        range_label = f"{start_date.format('YYYY-MM-DD')} to {end_date.format('YYYY-MM-DD')}"
    else:
        report_label = f"{start_year:04d}-{start_month:02d} to {end_year:04d}-{end_month:02d}"
        range_label = f"{start_date.format('YYYY-MM-DD')} to {end_date.format('YYYY-MM-DD')}"

    story: list[Any] = []
    story.append(Paragraph("Spending Report", styles["Title"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(report_label, styles["Heading2"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Range: {range_label}", styles["BodyText"]))
    story.append(Spacer(1, 14))

    summary_table_data = [
        ["Total spent", f"${total_spent:,.2f}"],
        ["Average / month", f"${avg_monthly:,.2f}"],
        ["Top month", f"{top_month.year}-{top_month.month:02d} (${top_month.total:,.2f})" if top_month else "—"],
    ]

    summary_table = Table(summary_table_data, colWidths=[2.1 * inch, 2.4 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.lightgrey]),
            ]
        )
    )

    story.append(Paragraph(chart_title, styles["Heading2"]))
    story.append(Spacer(1, 6))
    story.append(summary_table)
    story.append(Spacer(1, 12))

    # Monthly breakdown table (useful even when the chart is present).
    # Limit to keep PDF readable for wider ranges.
    max_rows = 24
    months_to_show = monthly_points
    if len(monthly_points) > max_rows:
        months_to_show = monthly_points[-max_rows:]

    month_table_data = [["Month", "Total"]]
    for p in months_to_show:
        month_table_data.append([f"{p.year}-{p.month:02d}", f"${p.total:,.2f}"])
    month_table_data = (
        month_table_data
        if len(monthly_points) <= max_rows
        else month_table_data + [["…", "…"]]
    )

    month_table = Table(month_table_data, colWidths=[3.0 * inch, 2.0 * inch])
    month_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.lightgrey]),
            ]
        )
    )
    story.append(month_table)
    story.append(Spacer(1, 18))

    # Chart image (line/bar)
    # reportlab Image can render directly from an in-memory file-like object (BytesIO).
    chart_flow = Image(chart_img, width=7.4 * inch, height=3.3 * inch)
    story.append(chart_flow)
    story.append(Spacer(1, 18))

    # Pie chart for categories starts on a new page to keep layout clean.
    story.append(PageBreak())
    story.append(Paragraph("Spending by Category", styles["Heading2"]))
    story.append(Spacer(1, 6))
    pie_flow = Image(pie_img, width=6.8 * inch, height=4.8 * inch)
    story.append(pie_flow)
    story.append(Spacer(1, 10))

    if category_points_top:
        top_rows = [[p["category"], f"${p['total']:,.2f}"] for p in category_points_top[:5]]
        top_table = Table([["Top categories", "Amount"]] + top_rows, colWidths=[3.4 * inch, 1.8 * inch])
        top_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(top_table)

    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()

