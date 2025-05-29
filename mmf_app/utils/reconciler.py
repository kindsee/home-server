from datetime import date, timedelta
from db import db 
from dateutil.relativedelta import relativedelta
from models.account import Account
from models.transaction import Transaction
from models.adjustment import Adjustment
from models.fixed_expense import FixedExpense


def calcular_balance_cuenta(cuenta_id: int, fecha_objetivo: date) -> float:
    """
    Calcula el balance de la cuenta hasta la fecha indicada:
    saldo_inicial + sum(transacciones) + sum(ajustes) + sum(gastos/ingresos fijos)
    Aplica todos los movimientos desde la fecha más temprana (saldo_inicial o inicio gastos fijos)
    hasta fecha_objetivo, respetando fecha_fin de gastos fijos.
    """

    cuenta = Account.query.get(cuenta_id)
    if not cuenta:
        raise ValueError(f"Cuenta {cuenta_id} no encontrada")

    saldo = float(cuenta.saldo_inicial)

    # Obtener fecha mínima para comenzar los cálculos
    fecha_minima = cuenta.saldo_inicial_fecha if hasattr(cuenta, 'saldo_inicial_fecha') else None

    # Si no hay fecha mínima, usar la mínima entre ajustes, transacciones y gastos fijos
    # Para simplificar, fijamos fecha_minima a fecha_objetivo (puedes ajustar si tienes fecha inicial de saldo)
    if not fecha_minima:
        fecha_minima = date(1900, 1, 1)  # fecha muy antigua para captar todo

    # 1) Ajustes hasta fecha_objetivo
    ajustes = Adjustment.query.filter(
        Adjustment.cuenta_id == cuenta_id,
        Adjustment.fecha <= fecha_objetivo
    ).all()
    for adj in ajustes:
        saldo += float(adj.monto_ajuste)

    # 2) Transacciones hasta fecha_objetivo
    transacciones = Transaction.query.filter(
        Transaction.cuenta_id == cuenta_id,
        Transaction.fecha <= fecha_objetivo
    ).all()
    for t in transacciones:
        saldo += float(t.monto)

    # 3) Gastos o ingresos fijos, para todas las fechas desde fecha_minima hasta fecha_objetivo
    fijos = FixedExpense.query.filter(
        FixedExpense.cuenta_id == cuenta_id,
        # Se incluyen todos que hayan empezado antes o en fecha_objetivo
        FixedExpense.fecha_inicio <= fecha_objetivo,
        # Y cuyo fin sea nulo o posterior a fecha_minima
        (FixedExpense.fecha_fin == None) | (FixedExpense.fecha_fin >= fecha_minima)
    ).all()

    for f in fijos:
        # Contar ocurrencias desde el máximo entre fecha_minima y f.fecha_inicio hasta fecha_objetivo o fecha_fin
        inicio = max(fecha_minima, f.fecha_inicio)
        fin = f.fecha_fin if f.fecha_fin and f.fecha_fin < fecha_objetivo else fecha_objetivo

        ocurrencia = inicio
        while ocurrencia <= fin:
            saldo += float(f.monto)

            if f.frecuencia == 'semanal':
                ocurrencia += timedelta(weeks=1)
            elif f.frecuencia == 'mensual':
                ocurrencia += relativedelta(months=1)
            elif f.frecuencia == 'trimestral':
                ocurrencia += relativedelta(months=3)
            elif f.frecuencia == 'semestral':
                ocurrencia += relativedelta(months=6)
            elif f.frecuencia == 'anual':
                ocurrencia += relativedelta(years=1)
            else:
                break

    return saldo
