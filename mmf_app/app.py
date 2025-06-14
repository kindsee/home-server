from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from db  import db
from datetime import datetime, date, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import config

app = Flask(__name__)
app.config.from_object(config)
db.init_app(app)

from models.account import Account
from models.transaction import Transaction
from models.fixed_expense import FixedExpense
from models.adjustment import Adjustment

with app.app_context():
    from utils.reconciler import calcular_balance_cuenta

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    from utils.reconciler import calcular_balance_cuenta

    fecha_str = request.args.get('fecha')
    fecha_obj = date.fromisoformat(fecha_str) if fecha_str else date.today()

    fecha_inicio = fecha_obj - timedelta(days=30)
    fecha_fin = fecha_obj + timedelta(days=30)
    fechas_rango = [fecha_inicio + timedelta(days=i) for i in range((fecha_fin - fecha_inicio).days + 1)]

    cuentas = Account.query.all()

    datos_grafico = {}
    for c in cuentas:
        saldos = [round(calcular_balance_cuenta(c.id, f), 2) for f in fechas_rango]
        datos_grafico[c.nombre] = {
            'fechas': [f.isoformat() for f in fechas_rango],
            'saldos': saldos
        }

    datos_saldos = [{'nombre': c.nombre, 'saldo': round(calcular_balance_cuenta(c.id, fecha_obj), 2)} for c in cuentas]

    colores_disponibles = ['#bcbd22', '#2ca02c', '#e377c2', '#17becf', '#1f77b4', '#d62728', '#ff7f0e', '#9467bd', '#8c564b', '#7f7f7f']
    colores = {c.nombre: colores_disponibles[i % len(colores_disponibles)] for i, c in enumerate(cuentas)}

    return render_template('dashboard.html', fecha=fecha_obj.isoformat(), datos=datos_saldos, datos_grafico=datos_grafico, colores=colores)

@app.route('/api/transactions')
def api_transactions():
    mes = request.args.get('mes')
    year, month = map(int, mes.split('-'))
    inicio = date(year, month, 1)
    fin = inicio + relativedelta(months=1) - relativedelta(days=1)
    gastos = Transaction.query.filter(Transaction.fecha >= inicio, Transaction.fecha <= fin).all()
    return jsonify([t.to_dict() for t in gastos])

@app.route('/admin')
def admin():
    cuentas = Account.query.all()
    gastos_fijos = FixedExpense.query.all()
    return render_template('admin.html', cuentas=cuentas, gastos_fijos=gastos_fijos, date=date)

@app.route('/admin/create_account', methods=['POST'])
def create_account():
    nueva = Account(nombre=request.form['nombre'], saldo_inicial=Decimal(request.form['saldo_inicial']))
    db.session.add(nueva)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/create_fixed_expense', methods=['POST'])
def create_fixed_expense():
    try:
        cuenta_id = int(request.form['cuenta_id'])
        descripcion = request.form['nombre']
        monto = Decimal(request.form['importe'])
        frecuencia = request.form['periodicidad']
        fecha_inicio = datetime.strptime(request.form['fecha_inicio'], "%Y-%m-%d").date()
        fecha_fin_raw = request.form.get('fecha_fin')
        fecha_fin = datetime.strptime(fecha_fin_raw, "%Y-%m-%d").date() if fecha_fin_raw else None

        fe = FixedExpense(cuenta_id=cuenta_id, descripcion=descripcion, monto=monto, frecuencia=frecuencia, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
        db.session.add(fe)
        db.session.commit()
        flash('Gasto fijo añadido correctamente', 'success')
    except Exception as e:
        flash(f'Error al añadir gasto fijo: {e}', 'danger')
    return redirect(url_for('admin'))

@app.route('/consolidar', methods=['GET', 'POST'])
def consolidar():
    from decimal import Decimal

    if request.method == 'POST':
        cuenta_id = int(request.form['cuenta_id'])
        fecha_str = request.form['fecha']
        saldo_reportado = Decimal(request.form['saldo_reportado'])

        fecha_obj = date.fromisoformat(fecha_str)
        saldo_calculado = calcular_balance_cuenta(cuenta_id, fecha_obj)

        ajuste = saldo_reportado - Decimal(str(saldo_calculado))

        if ajuste == 0:
            flash('El saldo ya coincide, no se necesita ajuste.', 'success')
        else:
            nuevo_ajuste = Adjustment(
                cuenta_id=cuenta_id,
                fecha=fecha_obj,
                monto_ajuste=ajuste,
                descripcion='Consolidación manual'
            )
            db.session.add(nuevo_ajuste)
            db.session.commit()
            flash(f'Consolidación registrada con un ajuste de {ajuste:.2f} €', 'success')

        return redirect(url_for('consolidar', cuenta_id=cuenta_id, fecha=fecha_str))

    # --- Método GET ---
    cuenta_id = request.args.get('cuenta_id', type=int)
    fecha_str = request.args.get('fecha')
    fecha_obj = date.fromisoformat(fecha_str) if fecha_str else date.today()

    cuentas = Account.query.all()
    cuenta = Account.query.get(cuenta_id) if cuenta_id else None

    movimientos = []
    saldo_final = None
    saldo_calculado = None

    if cuenta:
        fecha_inicio = fecha_obj - timedelta(weeks=8)
        fecha_fin = fecha_obj + timedelta(weeks=4)
        eventos = []

        # Gastos fijos
        gastos_fijos = FixedExpense.query.filter_by(cuenta_id=cuenta.id).all()
        for g in gastos_fijos:
            f = g.fecha_inicio
            while not g.fecha_fin or f <= g.fecha_fin:
                if f > fecha_fin:
                    break
                if f >= fecha_inicio:
                    eventos.append({
                        'fecha': f,
                        'concepto': g.descripcion,
                        'importe': float(g.monto),
                        'tipo': 'fijo'
                    })
                if g.frecuencia == 'mensual':
                    f += relativedelta(months=1)
                elif g.frecuencia == 'semanal':
                    f += timedelta(weeks=1)
                else:
                    break

        # Transacciones
        transacciones = Transaction.query.filter(
            Transaction.cuenta_id == cuenta.id,
            Transaction.fecha >= fecha_inicio,
            Transaction.fecha <= fecha_fin
        ).order_by(Transaction.fecha).all()
        for t in transacciones:
            eventos.append({
                'fecha': t.fecha,
                'concepto': t.descripcion,
                'importe': float(t.monto),
                'tipo': 'puntual'
            })

        # Ajustes
        ajustes = Adjustment.query.filter(
            Adjustment.cuenta_id == cuenta.id,
            Adjustment.fecha >= fecha_inicio,
            Adjustment.fecha <= fecha_fin
        ).order_by(Adjustment.fecha).all()
        for a in ajustes:
            eventos.append({
                'fecha': a.fecha,
                'concepto': a.descripcion or 'Ajuste',
                'importe': float(a.monto_ajuste),
                'tipo': 'ajuste'
            })

        eventos.sort(key=lambda e: e['fecha'])

        saldo = float(cuenta.saldo_inicial)
        for e in eventos:
            saldo += e['importe']
            e['saldo'] = round(saldo, 2)

        saldo_final = round(saldo, 2)
        movimientos = [e for e in eventos if fecha_inicio <= e['fecha'] <= fecha_fin]
        saldo_calculado = calcular_balance_cuenta(cuenta.id, fecha_obj)

    return render_template('consolidar.html',
                           cuentas=cuentas,
                           cuenta_id=cuenta_id,
                           fecha=fecha_str,
                           saldo_final=saldo_final,
                           saldo_calculado=saldo_calculado,
                           movimientos=movimientos)


@app.route('/admin/create_transaction', methods=['POST'])
def create_transaction():
    nueva = Transaction(
        cuenta_id=int(request.form['cuenta_id']),
        descripcion=request.form['descripcion'],
        monto=float(request.form['monto']),
        fecha=date.fromisoformat(request.form.get('fecha') or date.today().isoformat())
    )
    db.session.add(nueva)
    db.session.commit()
    flash('Gasto puntual añadido correctamente', 'success')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
