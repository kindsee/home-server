from db import db

class Transaction(db.Model):
    __tablename__ = 'transaction'

    id = db.Column(db.Integer, primary_key=True)
    cuenta_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    descripcion = db.Column(db.String(100), nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    fecha = db.Column(db.Date, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'cuenta_id': self.cuenta_id,
            'descripcion': self.descripcion,
            'monto': float(self.monto),
            'fecha': self.fecha.strftime('%Y-%m-%d')
        }
