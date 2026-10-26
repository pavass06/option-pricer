"""Build excel/option_pricer.xlsx: a Black-Scholes pricer in native Excel formulas.

No macros are needed. Run from the project root:  python excel/build_workbook.py
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

OUT = Path(__file__).resolve().parent / "option_pricer.xlsx"

INPUT_FILL = PatternFill("solid", fgColor="FFF4CC")
HEADER_FILL = PatternFill("solid", fgColor="1F3A5F")
HEADER_FONT = Font(bold=True, color="FFFFFF")
BOLD = Font(bold=True)
THIN = Side(style="thin", color="BBBBBB")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def header(ws, cell, text):
    ws[cell] = text
    ws[cell].fill = HEADER_FILL
    ws[cell].font = HEADER_FONT


def build():
    wb = Workbook()
    ws = wb.active
    ws.title = "Pricer"
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 46

    ws["A1"] = "Black-Scholes option pricer"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = "Edit the yellow cells. Everything else is computed with Excel formulas."
    ws["A2"].font = Font(italic=True, color="666666")

    # --- Inputs (named ranges make the formulas readable) -------------------
    header(ws, "A4", "Inputs")
    inputs = [
        ("Spot (S)", 100, "Spot", "Underlying price"),
        ("Strike (K)", 100, "Strike", ""),
        ("Maturity in years (T)", 1, "Maturity", "e.g. 0.5 = 6 months"),
        ("Risk-free rate (r)", 0.05, "Rate", "Continuously compounded"),
        ("Volatility (sigma)", 0.20, "Vol", "Annualised"),
        ("Dividend yield (q)", 0.0, "DivYield", "Continuous"),
        ("Type (Call / Put)", "Call", "OptType", "Drop-down list"),
    ]
    from openpyxl.workbook.defined_name import DefinedName
    for i, (label, value, name, note) in enumerate(inputs):
        row = 5 + i
        ws.cell(row=row, column=1, value=label)
        c = ws.cell(row=row, column=2, value=value)
        c.fill, c.border = INPUT_FILL, BOX
        ws.cell(row=row, column=3, value=note).font = Font(color="888888")
        ref = f"Pricer!$B${row}"
        dn = DefinedName(name, attr_text=ref)
        try:
            wb.defined_names[name] = dn          # openpyxl >= 3.1
        except TypeError:
            wb.defined_names.append(dn)          # older openpyxl
    for r in (8, 9, 10):
        ws.cell(row=r, column=2).number_format = "0.00%"
    dv = DataValidation(type="list", formula1='"Call,Put"', allow_blank=False)
    ws.add_data_validation(dv)
    dv.add("B11")

    # --- Intermediate terms -------------------------------------------------
    header(ws, "A13", "Intermediate")
    ws["A14"], ws["B14"] = "d1", "=(LN(Spot/Strike)+(Rate-DivYield+Vol^2/2)*Maturity)/(Vol*SQRT(Maturity))"
    ws["A15"], ws["B15"] = "d2", "=B14-Vol*SQRT(Maturity)"
    ws["A16"], ws["B16"] = "Sign (+1 call, -1 put)", '=IF(OptType="Call",1,-1)'
    for r in (14, 15):
        ws.cell(row=r, column=2).number_format = "0.0000"

    # --- Outputs -------------------------------------------------------------
    header(ws, "A18", "Results")
    w = "B16"  # +1 / -1
    outputs = [
        ("Price", f"={w}*(Spot*EXP(-DivYield*Maturity)*NORMSDIST({w}*B14)"
                  f"-Strike*EXP(-Rate*Maturity)*NORMSDIST({w}*B15))", ""),
        ("Delta", f"={w}*EXP(-DivYield*Maturity)*NORMSDIST({w}*B14)", "per 1 unit of spot"),
        ("Gamma", "=EXP(-DivYield*Maturity)*EXP(-B14^2/2)/SQRT(2*PI())/(Spot*Vol*SQRT(Maturity))", ""),
        ("Vega (per 1 vol point)", "=Spot*EXP(-DivYield*Maturity)*EXP(-B14^2/2)/SQRT(2*PI())*SQRT(Maturity)/100",
         "change for +1% volatility"),
        ("Theta (per calendar day)",
         f"=(-Spot*EXP(-DivYield*Maturity)*EXP(-B14^2/2)/SQRT(2*PI())*Vol/(2*SQRT(Maturity))"
         f"-{w}*Rate*Strike*EXP(-Rate*Maturity)*NORMSDIST({w}*B15)"
         f"+{w}*DivYield*Spot*EXP(-DivYield*Maturity)*NORMSDIST({w}*B14))/365",
         "annual theta / 365"),
        ("Rho (per 1% rate)", f"={w}*Strike*Maturity*EXP(-Rate*Maturity)*NORMSDIST({w}*B15)/100",
         "change for +1% rate"),
        ("Forward value S.e^(-qT) - K.e^(-rT)",
         "=Spot*EXP(-DivYield*Maturity)-Strike*EXP(-Rate*Maturity)", "C - P should equal this"),
    ]
    for i, (label, formula, note) in enumerate(outputs):
        row = 19 + i
        ws.cell(row=row, column=1, value=label).font = BOLD if i == 0 else Font()
        c = ws.cell(row=row, column=2, value=formula)
        c.number_format, c.border = "0.0000", BOX
        ws.cell(row=row, column=3, value=note).font = Font(color="888888")
    ws["B19"].font = BOLD

    # --- Price vs spot table and chart --------------------------------------
    ch = wb.create_sheet("Chart data")
    ch.column_dimensions["A"].width = 12
    ch.column_dimensions["B"].width = 14
    ch.column_dimensions["C"].width = 14
    for col, text in zip("ABC", ("Spot", "Option price", "Payoff")):
        header(ch, f"{col}1", text)
    n = 41
    for i in range(n):
        row = 2 + i
        # Spot from 50% to 150% of strike
        ch[f"A{row}"] = f"=Strike*(0.5+{i}/{n - 1})"
        s = f"A{row}"
        d1 = f"((LN({s}/Strike)+(Rate-DivYield+Vol^2/2)*Maturity)/(Vol*SQRT(Maturity)))"
        d2 = f"({d1}-Vol*SQRT(Maturity))"
        ch[f"B{row}"] = (f"=Pricer!$B$16*({s}*EXP(-DivYield*Maturity)*NORMSDIST(Pricer!$B$16*{d1})"
                         f"-Strike*EXP(-Rate*Maturity)*NORMSDIST(Pricer!$B$16*{d2}))")
        ch[f"C{row}"] = f"=MAX(Pricer!$B$16*({s}-Strike),0)"
        for col in "ABC":
            ch[f"{col}{row}"].number_format = "0.00"

    chart = LineChart()
    chart.title = "Option price vs spot (today) and payoff at maturity"
    chart.x_axis.title = "Spot"
    chart.y_axis.title = "Value"
    chart.height, chart.width = 9, 17
    chart.add_data(Reference(ch, min_col=2, min_row=1, max_col=3, max_row=n + 1), titles_from_data=True)
    chart.set_categories(Reference(ch, min_col=1, min_row=2, max_row=n + 1))
    chart.x_axis.number_format = "0"
    chart.x_axis.tickLblSkip = 5
    chart.x_axis.delete = False
    chart.y_axis.delete = False
    ws.add_chart(chart, "E4")

    # --- Notes ----------------------------------------------------------------
    notes = wb.create_sheet("Notes")
    notes.column_dimensions["A"].width = 100
    for i, line in enumerate([
        "Model: Black-Scholes-Merton for European options, continuous dividend yield.",
        "Uses only long-standing functions (NORMSDIST, LN, EXP), so it works in any Excel version and LibreOffice.",
        "Greeks: vega and rho per 1 percentage point, theta per calendar day (annual / 365).",
        "American options and Monte Carlo are only in the Python package (option_pricer).",
        "Optional: vba/BlackScholes.bas adds a =BS_PRICE(...) user function (see README).",
    ], start=1):
        notes[f"A{i}"] = line
        notes[f"A{i}"].alignment = Alignment(wrap_text=True)

    wb.save(OUT)
    print(f"Workbook written to {OUT}")


if __name__ == "__main__":
    build()
