from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey
from sqlalchemy.orm import relationship
from db import db

class Adjustment(db.Model):
    __tablename__ = 'adjustment'

    id = db.Column(db.Integer, primary_key=True)
    cuenta_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    monto_ajuste = Column(Float, nullable=False)
    descripcion = Column(String(255), nullable=True)  # <-- Nueva columna

    cuenta = relationship('Account', back_populates='ajustes')  # ejemplo

    def to_dict(self):
        return {
            'id': self.id,
            'cuenta_id': self.cuenta_id,
            'fecha': self.fecha.strftime('%Y-%m-%d'),
            'monto_ajuste': float(self.monto_ajuste)
        }
