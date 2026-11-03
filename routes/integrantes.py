
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.conexion import obtener_conexion
import mysql.connector

integrantes = Blueprint("integrantes", __name__)


@integrantes.route("/proyectos/<int:id_proyecto>/integrantes", methods=["GET", "POST"])
def gestionar_integrantes(id_proyecto):

    if "id_usuario" not in session:
        return redirect(url_for("auth.login"))

    if session.get("rol") not in ("GESTOR", "ADMINISTRADOR"):
        flash("No tienes permisos para gestionar integrantes.")
        return redirect(url_for("proyectos.listar_proyectos"))

    conexion = obtener_conexion()

    if conexion is None:
        flash("No se pudo conectar con la base de datos.")
        return redirect(url_for("proyectos.listar_proyectos"))

    cursor = conexion.cursor(dictionary=True)

    try:
        # Comprobar que el proyecto existe y pertenece al gestor
        if session.get("rol") == "ADMINISTRADOR":
            cursor.execute("""
                SELECT id_proyecto, nombre
                FROM proyectos
                WHERE id_proyecto = %s
            """, (id_proyecto,))
        else:
            cursor.execute("""
                SELECT id_proyecto, nombre
                FROM proyectos
                WHERE id_proyecto = %s AND id_gestor = %s
            """, (id_proyecto, session["id_usuario"]))

        proyecto = cursor.fetchone()

        if not proyecto:
            flash("El proyecto no existe o no tienes permiso para gestionarlo.")
            return redirect(url_for("proyectos.listar_proyectos"))

        # Agregar un colaborador
        if request.method == "POST":
            id_usuario = request.form.get("id_usuario", type=int)

            if not id_usuario:
                flash("Selecciona un colaborador.")
                return redirect(url_for(
                    "integrantes.gestionar_integrantes",
                    id_proyecto=id_proyecto
                ))

            cursor.execute("""
                SELECT id_usuario
                FROM usuarios
                WHERE id_usuario = %s
                  AND rol = 'COLABORADOR'
                  AND activo = TRUE
            """, (id_usuario,))

            colaborador = cursor.fetchone()

            if not colaborador:
                flash("El usuario seleccionado no es un colaborador activo.")
            else:
                try:
                    cursor.execute("""
                        INSERT INTO integrantes_proyecto
                        (id_proyecto, id_usuario)
                        VALUES (%s, %s)
                    """, (id_proyecto, id_usuario))

                    conexion.commit()
                    flash("Colaborador agregado correctamente.")

                except mysql.connector.IntegrityError:
                    conexion.rollback()
                    flash("Este colaborador ya pertenece al proyecto.")

                return redirect(url_for(
                    "integrantes.gestionar_integrantes",
                    id_proyecto=id_proyecto
                ))

        # Consultar integrantes actuales
        cursor.execute("""
            SELECT u.id_usuario, u.nombre, u.correo
            FROM integrantes_proyecto ip
            INNER JOIN usuarios u
                ON ip.id_usuario = u.id_usuario
            WHERE ip.id_proyecto = %s
            ORDER BY u.nombre
        """, (id_proyecto,))

        lista_integrantes = cursor.fetchall()

        # Consultar colaboradores que todavía no pertenecen al proyecto
        cursor.execute("""
            SELECT id_usuario, nombre, correo
            FROM usuarios
            WHERE rol = 'COLABORADOR'
              AND activo = TRUE
              AND id_usuario NOT IN (
                  SELECT id_usuario
                  FROM integrantes_proyecto
                  WHERE id_proyecto = %s
              )
            ORDER BY nombre
        """, (id_proyecto,))

        colaboradores = cursor.fetchall()

        return render_template(
            "integrantes.html",
            proyecto=proyecto,
            integrantes=lista_integrantes,
            colaboradores=colaboradores
        )

    except mysql.connector.Error as error:
        conexion.rollback()
        print("Error al gestionar integrantes:", error)
        flash("Ocurrió un error al consultar los integrantes.")
        return redirect(url_for("proyectos.listar_proyectos"))

    finally:
        cursor.close()
        conexion.close()
