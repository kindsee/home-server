import enum
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from db import db
class FixedExpense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cuenta_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    descripcion = db.Column(db.String(100), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    frecuencia = db.Column(db.Enum('semanal', 'mensual', 'trimestral', 'semestral', 'anual', name='frecuencia_enum'), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'cuenta_id': self.cuenta_id,
            'descripcion': self.descripcion,
            'monto': float(self.monto),
            'frecuencia': self.frecuencia,
            'fecha_inicio': self.fecha_inicio.isoformat(),
            'fecha_fin': self.fecha_fin.isoformat() if self.fecha_fin else None
        }
        
