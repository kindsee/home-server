import os

# URI de conexión a MariaDB
# Ajusta usuario, contraseña, host y nombre de BD según tus datos
SQLALCHEMY_DATABASE_URI = (
    'mysql+pymysql://MMFDbUser:Dako-0kad@192.168.1.200/MMFDatabase'
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Clave secreta para formularios
SECRET_KEY = os.environ.get('SECRET_KEY', 'Dako-0kad')