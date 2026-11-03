
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash
)
from database.conexion import obtener_conexion
from werkzeug.security import (
    generate_password_hash, check_password_hash
)
from mysql.connector import Error, IntegrityError

auth = Blueprint("auth", __name__)


@auth.route("/registro", methods=["GET", "POST"])
def registro():

    if request.method == "POST":

        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        contrasena = request.form.get("contrasena", "")

        if not nombre or not correo or not contrasena:
            flash("Todos los campos son obligatorios.")
            return redirect(url_for("auth.registro"))

        if len(contrasena) < 8:
            flash("La contraseña debe tener al menos 8 caracteres.")
            return redirect(url_for("auth.registro"))

        conexion = obtener_conexion()

        if conexion is None:
            flash("No se pudo conectar con la base de datos.")
            return redirect(url_for("auth.registro"))

        cursor = None

        try:
            cursor = conexion.cursor()

            hash_contrasena = generate_password_hash(contrasena)

            cursor.execute("""
                INSERT INTO usuarios
                (nombre, correo, contrasena_hash, rol)
                VALUES (%s, %s, %s, 'COLABORADOR')
            """, (nombre, correo, hash_contrasena))

            conexion.commit()

            flash("Registro exitoso. Ahora puedes iniciar sesión.")
            return redirect(url_for("auth.login"))

        except IntegrityError:
            conexion.rollback()
            flash("Este correo electrónico ya está registrado.")

        except Error as error:
            conexion.rollback()
            print("Error de registro:", error)
            flash("Ocurrió un error al registrar el usuario.")

        finally:
            if cursor:
                cursor.close()
            conexion.close()

    return render_template("registro.html")


@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        correo = request.form.get("correo", "").strip().lower()
        contrasena = request.form.get("contrasena", "")

        if not correo or not contrasena:
            flash("Debes ingresar el correo y la contraseña.")
            return redirect(url_for("auth.login"))

        conexion = obtener_conexion()

        if conexion is None:
            flash("No se pudo conectar con la base de datos.")
            return redirect(url_for("auth.login"))

        cursor = None

        try:
            cursor = conexion.cursor(dictionary=True)

            cursor.execute("""
                SELECT id_usuario, nombre, correo,
                       contrasena_hash, rol
                FROM usuarios
                WHERE correo = %s AND activo = TRUE
            """, (correo,))

            usuario = cursor.fetchone()

            if usuario and check_password_hash(
                usuario["contrasena_hash"], contrasena
            ):
                session.clear()
                session.permanent = True

                session["id_usuario"] = usuario["id_usuario"]
                session["nombre"] = usuario["nombre"]
                session["rol"] = usuario["rol"]

                return redirect(url_for("auth.dashboard"))

            flash("Correo o contraseña incorrectos.")

        except Error as error:
            print("Error de inicio de sesión:", error)
            flash("Ocurrió un error al iniciar sesión.")

        finally:
            if cursor:
                cursor.close()
            conexion.close()

    return render_template("login.html")


@auth.route("/dashboard")
def dashboard():

    if "id_usuario" not in session:
        return redirect(url_for("auth.login"))

    return render_template("dashboard.html")


@auth.route("/logout", methods=["POST"])
def logout():

    session.clear()
    flash("Has cerrado sesión correctamente.")

    return redirect(url_for("auth.login"))
