from db import db

class Account(db.Model):
    __tablename__ = 'account'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    saldo_inicial = db.Column(db.Numeric(12,2), nullable=False)
    transactions = db.relationship('Transaction', backref='account')
    fixed_expenses = db.relationship('FixedExpense', backref='account')
    # adjustments = db.relationship('Adjustment', backref='account')
    
    ajustes = db.relationship('Adjustment', back_populates='cuenta', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'saldo_inicial': float(self.saldo_inicial)
        }
    
