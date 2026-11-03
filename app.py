
from flask import Flask, redirect, url_for, session, flash
from flask_wtf.csrf import CSRFProtect
from config import Config
from database.conexion import obtener_conexion
from routes.auth import auth
from routes.proyectos import proyectos
from routes.integrantes import integrantes
from routes.tareas import tareas
from routes.reportes import reportes
import mysql.connector

app = Flask(__name__)
app.config.from_object(Config)

csrf = CSRFProtect(app)

app.register_blueprint(auth)
app.register_blueprint(proyectos)
app.register_blueprint(integrantes)
app.register_blueprint(tareas)
app.register_blueprint(reportes)


@app.before_request
def verificar_usuario_activo():

    id_usuario = session.get("id_usuario")

    # Si no hay sesión, no se necesita comprobar el usuario.
    if not id_usuario:
        return None

    # Permitir el acceso a estas rutas para iniciar sesión,
    # registrarse o cerrar una sesión existente.
    if (
        app.endpoint == "auth.login"
        or app.endpoint == "auth.registro"
        or app.endpoint == "auth.logout"
        or app.endpoint == "static"
    ):
        return None

    conexion = obtener_conexion()

    if conexion is None:
        flash("No fue posible verificar tu cuenta. Intenta nuevamente.")
        return redirect(url_for("auth.login"))

    cursor = conexion.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT activo
            FROM usuarios
            WHERE id_usuario = %s
        """, (id_usuario,))

        usuario = cursor.fetchone()

        if not usuario or usuario["activo"] != 1:
            session.clear()
            flash("Tu cuenta está inactiva o ya no está disponible.")
            return redirect(url_for("auth.login"))

    except mysql.connector.Error as error:
        print("Error al verificar el estado del usuario:", error)
        flash("No fue posible verificar tu cuenta. Intenta nuevamente.")
        return redirect(url_for("auth.login"))

    finally:
        cursor.close()
        conexion.close()

    return None


@app.route("/")
def inicio():
    return redirect(url_for("auth.login"))


if __name__ == "__main__":
    app.run(debug=True)
