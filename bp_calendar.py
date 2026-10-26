"""
Календарь артериального давления
Flet + SQLite для Android
"""
import flet as ft
from flet import (
    Page, Column, Row, TextField, Text, Container,
    MainAxisAlignment, CrossAxisAlignment, Padding, Icon,
    BorderSide, Border, BoxShadow,
    PopupMenuButton, PopupMenuItem, AlertDialog, SnackBar, ScrollMode,
    ThemeMode, Theme, RoundedRectangleBorder, OutlinedButton, Colors,
    TextAlign, FontWeight
)
from flet import icons
import sqlite3
from datetime import datetime, date, timedelta
import os

Icons = icons.Icons

DB_FILE = os.path.join(os.getcwd(), "bp_data.db")

expanded_months = set()
expanded_days = set()


# ==================== БАЗА ДАННЫХ ====================
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bp_sys INTEGER NOT NULL,
            bp_dia INTEGER NOT NULL,
            pulse INTEGER,
            record_time TEXT NOT NULL,
            notes TEXT
        )
    """)
    conn.commit()
    return conn


def date_key(d):
    return d.strftime("%Y-%m-%d")


def weekday_name(d):
    return d.strftime("%A")[:3]


def get_measurements_for_day(conn, d):
    cur = conn.execute(
        "SELECT * FROM measurements WHERE date(record_time) = date(?) ORDER BY record_time ASC",
        date_key(d),
    )
    return cur.fetchall()


def get_last_measurement_before(conn, d):
    cur = conn.execute(
        """
        SELECT bp_sys, bp_dia, pulse, record_time, notes 
        FROM measurements 
        WHERE date(record_time) <= date(?)
        ORDER BY record_time DESC
        LIMIT 1
        """,
        date_key(d),
    )
    row = cur.fetchone()
    if row:
        return {"sys": row[0], "dia": row[1], "pulse": row[2] or "", "time": row[3], "notes": row[4] or ""}
    return None


def save_measurement(conn, bp_sys, bp_dia, pulse, notes):
    record_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO measurements (bp_sys, bp_dia, pulse, record_time, notes) VALUES (?, ?, ?, ?, ?)",
        (bp_sys, bp_dia, pulse, record_time, notes),
    )


# ==================== UI: ДЕНЬ ====================
def toggle_day(d):
    key = date_key(d)
    if key in expanded_days:
        expanded_days.discard(key)
    else:
        expanded_days.add(key)


def build_day_card(conn, d, is_today):
    measurements = get_measurements_for_day(conn, d)
    has_data = len(measurements) > 0

    sys_val, dia_val, pulse_val, time_val = "", "", "", ""
    if measurements:
        last = measurements[-1]
        sys_val = str(last[1])
        dia_val = str(last[2])
        pulse_val = str(last[3]) if last[3] else ""
        time_val = last[4].split(" ")[1] if " " in last[4] else ""

    preview = f"{sys_val}/{dia_val}"
    is_expanded = date_key(d) in expanded_days

    day_num = Text(
        str(d.day),
        size=20,
        weight=FontWeight.BOLD,
        color=Colors.BLUE_900 if is_today else Colors.BLACK87,
    )

    badge = None
    if has_data:
        badge = Container(
            Text(preview, size=12, color=Colors.WHITE, weight=FontWeight.W_700),
            bgcolor=Colors.BLUE_600,
            padding=6,
            border_radius=8,
            margin=6,
            shadow=BoxShadow(2, Colors.BLUE_200, 1),
        )

    detail_content = None
    if is_expanded and has_data:
        items = []
        for m in measurements:
            time_str = m[4].split(" ")[1] if " " in m[4] else m[4]
            row = Row([
                Text(f"{m[1]}/{m[2]}", size=12, weight=FontWeight.W_600),
                Text(time_str, size=10, color=Colors.BLACK54),
                Text(f"пульс: {m[3]}" if m[3] else "", size=10, color=Colors.GREY_600),
            ], alignment=MainAxisAlignment.SPACE_BETWEEN)
            items.append(row)
            if m[5]:
                items.append(Text(f"💬 {m[5]}", size=10, color=Colors.GREY_700, padding=4))

        detail_content = Column(
            items,
            spacing=2,
            padding=8,
            margin=8,
            bgcolor=Colors.BLUE_50,
            border_radius=8,
        )

    add_icon = Icon(
        Icons.add_circle_outline,
        size=20,
        color=Colors.GREEN_600 if has_data else Colors.BLUE_600,
    )

    return Container(
        Column([
            Row([day_num, badge], alignment=MainAxisAlignment.CENTER, spacing=2),
            detail_content,
        ], spacing=0, alignment=MainAxisAlignment.CENTER),
        width=60,
        height=70 if not detail_content else 100,
        border_radius=10,
        bgcolor=Colors.BLUE_50 if is_today else (Colors.WHITE if not has_data else Colors.GREEN_50),
        border=Border.all(
            2 if is_today else 1,
            Colors.BLUE_600 if is_today else Colors.OUTLINE,
        ),
        shadow=BoxShadow(2, Colors.BLACK12, 3),
        on_click=lambda e, dd=d: toggle_day(dd),
        tooltip=f"{d.day}.{d.month:02d}.{d.year} — {weekday_name(d)}" + (f" ({len(measurements)} замеров)" if has_data else ""),
    )


# ==================== UI: МЕСЯЦ ====================
def toggle_month(year, month):
    key = (year, month)
    if key in expanded_months:
        expanded_months.discard(key)
    else:
        expanded_months.add(key)
        today = date.today()
        if today.year == year and today.month == month:
            expanded_days.add(date_key(today))


def build_month_card(conn, year, month):
    first_day = date(year, month, 1)
    last_day = date(year, month + 1, 1) - timedelta(days=1)
    today = date.today()

    month_names = [
        "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
    ]

    expanded = (year, month) in expanded_months
    chevron = Icon(
        Icons.chevron_right,
        size=18,
        color=Colors.BLUE_600,
        rotation=0 if expanded else 0.25,
    )

    header = Container(
        Row([
            Icon(Icons.calendar_month_outlined, size=22, color=Colors.BLUE_700),
            Text(
                f"{month_names[month]} {year}",
                size=16,
                weight=FontWeight.W_600,
                color=Colors.BLUE_900,
            ),
            Spacer(),
            chevron,
        ], alignment=MainAxisAlignment.START, spacing=8),
        padding=14,
        border_radius=12,
        bgcolor=Colors.BLUE_50 if (year == today.year and month == today.month) else Colors.GREY_50,
        border=Border(
            bottom=BorderSide(1, Colors.BLUE_200 if (year == today.year and month == today.month) else Colors.GREY_300),
        ),
        on_click=lambda y=year, m=month: toggle_month(y, m),
        hover_color=Colors.BLUE_100,
    )

    days = []
    for day_num in range(1, last_day.day + 1):
        the_date = date(year, month, day_num)
        is_today = (the_date == today)
        card = build_day_card(conn, the_date, is_today)
        days.append(card)

    days_row = Row(days, wrap=False, scroll=ScrollMode.AUTO, spacing=2)

    return Column(
        [header, days_row],
        border_radius=12,
        border=Border.all(1, Colors.BLUE_100),
        bgcolor=Colors.WHITE,
        margin=4,
        spacing=0,
    )


# ==================== ГЛАВНЫЙ КАЛЕНДАРЬ ====================
def build_calendar_view(conn):
    today = date.today()
    start_year = today.year + (today.month - 1 - 2) // 12
    start_month = ((today.month - 1 - 2) % 12) + 1

    months = []
    for i in range(5):
        m = start_month + i
        y = start_year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        card = build_month_card(conn, y, m)
        months.append(card)

    return Column(months, spacing=0, scroll=ScrollMode.ADAPTIVE)


# ==================== ДИАЛОГ ВВОДА ====================
def open_add_dialog(page, selected_date):
    conn = get_db()
    last = get_last_measurement_before(conn, selected_date)

    sys_val = str(last["sys"]) if last and last["sys"] else ""
    dia_val = str(last["dia"]) if last and last["dia"] else ""
    pulse_val = str(last["pulse"]) if last and last["pulse"] else ""
    notes_val = last["notes"] if last else ""

    sys_tf = TextField(
        label="Систолическое (верхнее)",
        hint_text="120",
        keyboard=ft.TextFieldKeyboardType.NUMBER,
        text_size=22,
        width=220,
        value=sys_val,
        autofocus=True,
    )
    dia_tf = TextField(
        label="Диастолическое (нижнее)",
        hint_text="80",
        keyboard=ft.TextFieldKeyboardType.NUMBER,
        text_size=22,
        width=220,
        value=dia_val,
    )
    pulse_tf = TextField(
        label="Пульс",
        hint_text="72",
        keyboard=ft.TextFieldKeyboardType.NUMBER,
        text_size=22,
        width=220,
        value=pulse_val,
    )
    notes_tf = TextField(
        label="Примечания",
        hint_text="После тренировки, после кофе...",
        width=220,
        max_lines=2,
        value=notes_val,
    )

    now = datetime.now()
    auto_info = Text(
        f"📅 {selected_date.strftime('%d.%m.%Y')} ({weekday_name(selected_date)}) | ⏰ {now.strftime('%H:%M')}",
        size=11,
        color=Colors.BLACK54,
    )

    def cancel(e):
        page.dialog.open = False
        page.update()

    def save(e):
        try:
            sys_raw = sys_tf.value.strip() if sys_tf.value else ""
            dia_raw = dia_tf.value.strip() if dia_tf.value else ""
            pulse_raw = pulse_tf.value.strip() if pulse_tf.value else ""
            notes_raw = (notes_tf.value or "").strip()

            if not sys_raw and not dia_raw:
                page.overlay.append(SnackBar(Text("Введите хотя бы одно значение давления!"), bgcolor=Colors.RED))
                page.update()
                return

            bp_sys = int(sys_raw) if sys_raw else None
            bp_dia = int(dia_raw) if dia_raw else None
            pulse = int(pulse_raw) if pulse_raw else None

            save_measurement(conn, bp_sys, bp_dia, pulse, notes_raw)

            page.dialog.open = False
            page.overlay.append(SnackBar(
                Text(f"✓ Записано: {bp_sys}/{bp_dia}" + (f" пульс {pulse}" if pulse else ""), bgcolor=Colors.GREEN)
            ))
            page.update()

            rebuild_calendar(page)

        except ValueError:
            page.overlay.append(SnackBar(Text("Введите корректные числа!"), bgcolor=Colors.RED))
            page.update()

    cancel_btn = OutlinedButton("Отмена", icon=Icons.cancel_outlined, on_click=cancel)
    save_btn = OutlinedButton("Сохранить", icon=Icons.check_outlined, bgcolor=Colors.GREEN_600, color=Colors.WHITE, on_click=save)

    page.dialog = AlertDialog(
        title=Column([
            Text("Новое измерение", size=20, weight=FontWeight.W_700, color=Colors.BLUE_900),
            auto_info,
        ], alignment=MainAxisAlignment.CENTER, horizontal_alignment=CrossAxisAlignment.CENTER, spacing=2),
        content=Column([
            sys_tf, dia_tf, pulse_tf, notes_tf,
            Row([cancel_btn, save_btn], alignment=MainAxisAlignment.SPACE_BETWEEN)
        ],
            alignment=MainAxisAlignment.CENTER,
            horizontal_alignment=CrossAxisAlignment.CENTER,
            spacing=4,
        ),
        modal=True,
        shape=RoundedRectangleBorder(16),
    )
    page.dialog.open = True
    page.update()
    sys_tf.focus()


# ==================== HEADER & FOOTER ====================
def make_header(page):
    def on_about(e):
        about_dialog = AlertDialog(
            title=Text("О приложении", size=22, weight=FontWeight.W_700, color=Colors.BLUE_900),
            content=Column([
                Text("Календарь артериального давления", size=16, weight=FontWeight.W_600),
                Text("• Записывайте измерения ежедневно"),
                Text("• Нажмите на + для добавления"),
                Text("• Нажмите на дату для разворота"),
                Text("• Данные хранятся локально в SQLite"),
                Text("V1.0", size=10, color=Colors.GREY_600),
            ], spacing=6),
            modal=True,
        )
        page.dialog = about_dialog
        page.dialog.open = True
        page.update()

    menu = PopupMenuButton(items=[
        PopupMenuItem(text="🔄 Обновить", on_click=lambda e: rebuild_calendar(page)),
        PopupMenuItem(text="ℹ️ О приложении", on_click=on_about),
    ])

    return Row([
        Icon(Icons.favorite, size=32, color=Colors.RED),
        Column([
            Text("Календарь давления", size=22, weight=FontWeight.W_700, color=Colors.BLACK87),
            Text("Записывайте измерения ежедневно", size=12, color=Colors.GREY_600),
        ], alignment=MainAxisAlignment.CENTER),
        Spacer(),
        menu,
    ], alignment=MainAxisAlignment.SPACE_BETWEEN)


def make_footer():
    return Padding(
        Text(
            "Нажмите на день для разворота  •  Нажмите на + для добавления",
            size=10,
            color=Colors.GREY_600,
            text_align=TextAlign.CENTER,
        ),
        12,
    )


# ==================== REBUILD ====================
def rebuild_calendar(page):
    conn = get_db()
    page.clean()
    header = make_header(page)
    calendar = build_calendar_view(conn)
    footer = make_footer()
    page.add(Padding(header, 16), calendar, footer)


# ==================== MAIN ====================
def main(page: Page):
    page.title = "Календарь давления"
    page.theme_mode = ThemeMode.LIGHT
    page.theme = Theme(color_scheme_seed=Colors.BLUE)
    page.scroll = ScrollMode.ADAPTIVE

    conn = get_db()
    header = make_header(page)
    calendar = build_calendar_view(conn)
    footer = make_footer()

    page.add(Padding(header, 16), calendar, footer)


if __name__ == "__main__":
    ft.app(target=main)
