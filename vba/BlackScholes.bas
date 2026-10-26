Attribute VB_Name = "BlackScholes"
' Black-Scholes user-defined functions for Excel (optional companion to
' excel/option_pricer.xlsx, which works without any macro).
'
' Import: Excel > Alt+F11 > File > Import File... > BlackScholes.bas,
' then save the workbook as .xlsm.
'
' Usage in a cell:
'   =BS_PRICE(100; 100; 1; 0,05; 0,2; "call")          (French locale separators)
'   =BS_PRICE(100, 100, 1, 0.05, 0.2, "put", 0.01)     (English locale)
'   =BS_GREEK("delta", 100, 100, 1, 0.05, 0.2, "call")
'
' Units: vega and rho per 1 percentage point, theta per calendar day.
Option Explicit

Private Function NormPdf(ByVal x As Double) As Double
    NormPdf = Exp(-0.5 * x * x) / Sqr(2# * 3.14159265358979)
End Function

Private Function NormCdf(ByVal x As Double) As Double
    NormCdf = Application.WorksheetFunction.NormSDist(x)
End Function

Private Function Sign(ByVal optType As String) As Double
    Select Case LCase$(Trim$(optType))
        Case "call", "c": Sign = 1#
        Case "put", "p": Sign = -1#
        Case Else: Err.Raise 5, , "optType must be ""call"" or ""put"""
    End Select
End Function

Public Function BS_PRICE(ByVal S As Double, ByVal K As Double, ByVal T As Double, _
                         ByVal r As Double, ByVal sigma As Double, _
                         Optional ByVal optType As String = "call", _
                         Optional ByVal q As Double = 0#) As Variant
    On Error GoTo Fail
    If S <= 0 Or K <= 0 Or T <= 0 Or sigma <= 0 Then GoTo Fail
    Dim w As Double, d1 As Double, d2 As Double
    w = Sign(optType)
    d1 = (Log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * Sqr(T))
    d2 = d1 - sigma * Sqr(T)
    BS_PRICE = w * (S * Exp(-q * T) * NormCdf(w * d1) - K * Exp(-r * T) * NormCdf(w * d2))
    Exit Function
Fail:
    BS_PRICE = CVErr(xlErrValue)
End Function

Public Function BS_GREEK(ByVal greek As String, ByVal S As Double, ByVal K As Double, _
                         ByVal T As Double, ByVal r As Double, ByVal sigma As Double, _
                         Optional ByVal optType As String = "call", _
                         Optional ByVal q As Double = 0#) As Variant
    On Error GoTo Fail
    If S <= 0 Or K <= 0 Or T <= 0 Or sigma <= 0 Then GoTo Fail
    Dim w As Double, d1 As Double, d2 As Double, dq As Double, dr As Double
    w = Sign(optType)
    d1 = (Log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * Sqr(T))
    d2 = d1 - sigma * Sqr(T)
    dq = Exp(-q * T)
    dr = Exp(-r * T)
    Select Case LCase$(Trim$(greek))
        Case "delta"
            BS_GREEK = w * dq * NormCdf(w * d1)
        Case "gamma"
            BS_GREEK = dq * NormPdf(d1) / (S * sigma * Sqr(T))
        Case "vega"
            BS_GREEK = S * dq * NormPdf(d1) * Sqr(T) / 100#
        Case "theta"
            BS_GREEK = (-S * dq * NormPdf(d1) * sigma / (2# * Sqr(T)) _
                        - w * r * K * dr * NormCdf(w * d2) _
                        + w * q * S * dq * NormCdf(w * d1)) / 365#
        Case "rho"
            BS_GREEK = w * K * T * dr * NormCdf(w * d2) / 100#
        Case Else
            GoTo Fail
    End Select
    Exit Function
Fail:
    BS_GREEK = CVErr(xlErrValue)
End Function
