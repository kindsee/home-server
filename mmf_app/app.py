from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from db  import db
from datetime import datetime
from datetime import date
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import config



app = Flask(__name__)
app.config.from_object(config)
db.init_app(app)

# Importar modelos
from models.account import Account
from models.transaction import Transaction
from models.fixed_expense import FixedExpense
from models.adjustment import Adjustment

# Utilidades
with app.app_context():
    from utils.reconciler import calcular_balance_cuenta
from datetime import timedelta

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    from utils.reconciler import calcular_balance_cuenta

    fecha_str = request.args.get('fecha')
    if fecha_str:
        fecha_obj = date.fromisoformat(fecha_str)
    else:
        fecha_obj = date.today()

    # Creamos lista de fechas semanales: 8 semanas antes + fecha + 4 semanas después
    fechas_rango = []
    # 8 semanas antes (semana -8 a -1)
    for i in range(8, 0, -1):
        fechas_rango.append(fecha_obj - timedelta(weeks=i))
    # fecha dada (semana 0)
    fechas_rango.append(fecha_obj)
    # 4 semanas después (semana 1 a 4)
    for i in range(1, 5):
        fechas_rango.append(fecha_obj + timedelta(weeks=i))

    cuentas = Account.query.all()

    datos_grafico = {}
    for c in cuentas:
        saldos = []
        for f in fechas_rango:
            saldo = calcular_balance_cuenta(c.id, f)
            saldos.append(round(saldo, 2))
        datos_grafico[c.nombre] = {
            'fechas': [f.isoformat() for f in fechas_rango],
            'saldos': saldos
        }

    # Para mostrar el saldo de la fecha actual en la lista simple
    datos_saldos = []
    for c in cuentas:
        saldo_actual = calcular_balance_cuenta(c.id, fecha_obj)
        datos_saldos.append({
            'nombre': c.nombre,
            'saldo': round(saldo_actual, 2)
    })

    colores_disponibles = [
        '#bcbd22',  # amarillo-verdoso
        '#2ca02c',  # verde
        '#e377c2',  # rosa
        '#17becf',  # turquesa
        '#1f77b4',  # azul
        '#d62728',  # rojo
        '#ff7f0e',  # naranja
        '#9467bd',  # morado
        '#8c564b',  # marrón        
        '#7f7f7f',  # gris
    ]

    colores = {}
    for i, c in enumerate(cuentas):
        colores[c.nombre] = colores_disponibles[i % len(colores_disponibles)]

    return render_template('dashboard.html',
                           fecha=fecha_obj.isoformat(),
                           datos=datos_saldos,
                           datos_grafico=datos_grafico,
                           colores=colores)

@app.route('/api/transactions')
def api_transactions():
    mes = request.args.get('mes')  # formato 'YYYY-MM'
    year, month = map(int, mes.split('-'))
    # Obtener gastos (transacciones negativas)
    inicio = date(year, month, 1)
    fin = inicio + relativedelta(months=1) - relativedelta(days=1)
    gastos = Transaction.query.filter(
        Transaction.fecha >= inicio,
        Transaction.fecha <= fin
    ).all()
    return jsonify([t.to_dict() for t in gastos])


@app.route('/admin')
def admin():
    cuentas = Account.query.all()
    gastos_fijos = FixedExpense.query.all()
    return render_template('admin.html', cuentas=cuentas, gastos_fijos=gastos_fijos,date=date)

@app.route('/admin/create_account', methods=['POST'])
def create_account():
    nombre = request.form['nombre']
    saldo_ini = Decimal(request.form['saldo_inicial'])
    nueva = Account(nombre=nombre, saldo_inicial=saldo_ini)
    db.session.add(nueva)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/create_fixed_expense', methods=['POST'])
def create_fixed_expense():
    try:
        print("Formulario recibido:", request.form)

        cuenta_id = int(request.form['cuenta_id'])
        descripcion = request.form['nombre']
        monto = Decimal(request.form['importe'])
        frecuencia = request.form['periodicidad']
        fecha_inicio = datetime.strptime(request.form['fecha_inicio'], "%Y-%m-%d").date()
        fecha_fin_raw = request.form.get('fecha_fin')
        fecha_fin = datetime.strptime(fecha_fin_raw, "%Y-%m-%d").date() if fecha_fin_raw else None

        fe = FixedExpense(
            cuenta_id=cuenta_id,
            descripcion=descripcion,
            monto=monto,
            frecuencia=frecuencia,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )

        db.session.add(fe)
        db.session.commit()
        flash('Gasto fijo añadido correctamente', 'success')

    except Exception as e:
        flash(f'Error al añadir gasto fijo: {e}', 'danger')
        print(f'Error: {e}')

    return redirect(url_for('admin'))

@app.route('/consolidar', methods=['GET', 'POST'])
def consolidar():
    # --- (aquí va tu código POST, idéntico al que ya tienes) ---
    if request.method == 'POST':
        # ... insertar ajuste ...
        return redirect(url_for('consolidar', cuenta_id=cuenta_id, fecha=fecha_str))

    # --- Empieza GET ---
    cuenta_id = request.args.get('cuenta_id', type=int)
    fecha_str = request.args.get('fecha')
    fecha_obj = date.fromisoformat(fecha_str) if fecha_str else date.today()

    cuentas = Account.query.all()
    cuenta = Account.query.get(cuenta_id) if cuenta_id else None

    movimientos = []
    saldo_final = None

    if cuenta:
        # Rango de visualización
        fecha_inicio = fecha_obj - timedelta(weeks=8)
        fecha_fin    = fecha_obj + timedelta(weeks=4)

        eventos = []

        # 1) Gastos fijos
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

        # 2) Transacciones puntuales
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

        # 3) Ajustes (incluye el que acabas de crear)
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

        # 4) Ordenar todos los eventos y calcular saldo acumulado
        eventos.sort(key=lambda e: e['fecha'])
        saldo = float(cuenta.saldo_inicial)
        for e in eventos:
            saldo += e['importe']
            e['saldo'] = round(saldo, 2)

        saldo_final = round(saldo, 2)

        # 5) Filtrar para mostrar solo ventana de ±2 meses
        movimientos = [e for e in eventos if fecha_inicio <= e['fecha'] <= fecha_fin]

    return render_template('consolidar.html',
                           cuentas=cuentas,
                           cuenta_id=cuenta_id,
                           fecha=fecha_str,
                           saldo_final=saldo_final,
                           movimientos=movimientos)

@app.route('/admin/create_transaction', methods=['POST'])
def create_transaction():
    cuenta_id   = int(request.form['cuenta_id'])
    descripcion = request.form['descripcion']
    monto       = float(request.form['monto'])
    fecha_str   = request.form.get('fecha') or date.today().isoformat()
    fecha       = date.fromisoformat(fecha_str)

    nueva = Transaction(
        cuenta_id=cuenta_id,
        descripcion=descripcion,
        monto=monto,
        fecha=fecha
    )
    db.session.add(nueva)
    db.session.commit()
    flash('Gasto puntual añadido correctamente', 'success')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
