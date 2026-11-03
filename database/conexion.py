
import mysql.connector
from config import Config

def obtener_conexion():
    try:
        conexion = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            connection_timeout=10,
            use_pure=True
        )

        print("Conexión con MySQL establecida correctamente.")
        return conexion

    except mysql.connector.Error as error:
        print("Error al conectar con MySQL:", error)
        return None
