
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.conexion import obtener_conexion
from datetime import date
import mysql.connector

proyectos = Blueprint("proyectos", __name__)


def es_gestor():
    return (
        "id_usuario" in session
        and session.get("rol") in ("GESTOR", "ADMINISTRADOR")
    )


@proyectos.route("/proyectos")
def listar_proyectos():

    if "id_usuario" not in session:
        return redirect(url_for("auth.login"))

    conexion = obtener_conexion()

    if conexion is None:
        flash("No se pudo conectar con la base de datos.")
        return redirect(url_for("auth.dashboard"))

    cursor = conexion.cursor(dictionary=True)

    try:
        rol = session.get("rol")
        id_usuario = session["id_usuario"]

        if rol == "ADMINISTRADOR":

            cursor.execute("""
                SELECT p.*, u.nombre AS nombre_gestor
                FROM proyectos p
                INNER JOIN usuarios u
                    ON p.id_gestor = u.id_usuario
                ORDER BY p.fecha_creacion DESC
            """)

        elif rol == "GESTOR":

            cursor.execute("""
                SELECT p.*, u.nombre AS nombre_gestor
                FROM proyectos p
                INNER JOIN usuarios u
                    ON p.id_gestor = u.id_usuario
                WHERE p.id_gestor = %s
                ORDER BY p.fecha_creacion DESC
            """, (id_usuario,))

        else:

            cursor.execute("""
                SELECT DISTINCT p.*, u.nombre AS nombre_gestor
                FROM proyectos p
                INNER JOIN usuarios u
                    ON p.id_gestor = u.id_usuario
                INNER JOIN integrantes_proyecto ip
                    ON p.id_proyecto = ip.id_proyecto
                WHERE ip.id_usuario = %s
                ORDER BY p.fecha_creacion DESC
            """, (id_usuario,))

        lista = cursor.fetchall()

        return render_template(
            "proyectos.html",
            proyectos=lista,
            puede_crear=es_gestor()
        )

    except mysql.connector.Error as error:
        print("Error al consultar proyectos:", error)
        flash("No se pudieron consultar los proyectos.")
        return redirect(url_for("auth.dashboard"))

    finally:
        cursor.close()
        conexion.close()


@proyectos.route("/proyectos/crear", methods=["GET", "POST"])
def crear_proyecto():

    if "id_usuario" not in session:
        return redirect(url_for("auth.login"))

    if not es_gestor():
        flash("No tienes permisos para crear proyectos.")
        return redirect(url_for("proyectos.listar_proyectos"))

    if request.method == "POST":

        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        fecha_inicio = request.form.get("fecha_inicio", "")
        fecha_entrega = request.form.get("fecha_entrega", "")

        if not nombre or not fecha_inicio or not fecha_entrega:
            flash("Completa todos los campos obligatorios.")
            return redirect(url_for("proyectos.crear_proyecto"))

        try:
            inicio = date.fromisoformat(fecha_inicio)
            entrega = date.fromisoformat(fecha_entrega)

            if entrega < inicio:
                flash(
                    "La fecha de entrega no puede ser anterior "
                    "a la fecha de inicio."
                )
                return redirect(url_for("proyectos.crear_proyecto"))

        except ValueError:
            flash("Las fechas ingresadas no son válidas.")
            return redirect(url_for("proyectos.crear_proyecto"))

        conexion = obtener_conexion()

        if conexion is None:
            flash("No se pudo conectar con la base de datos.")
            return redirect(url_for("proyectos.crear_proyecto"))

        cursor = conexion.cursor()

        try:
            cursor.execute("""
                INSERT INTO proyectos
                (nombre, descripcion, fecha_inicio, fecha_entrega, id_gestor)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                nombre,
                descripcion,
                inicio,
                entrega,
                session["id_usuario"]
            ))

            conexion.commit()

            flash("Proyecto creado correctamente.")
            return redirect(url_for("proyectos.listar_proyectos"))

        except mysql.connector.Error as error:
            conexion.rollback()
            print("Error al crear proyecto:", error)
            flash("No se pudo guardar el proyecto.")

        finally:
            cursor.close()
            conexion.close()

    return render_template("crear_proyecto.html")
