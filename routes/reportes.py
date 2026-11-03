
from flask import Blueprint, render_template, session, redirect, url_for, flash
from database.conexion import obtener_conexion
from datetime import date
import mysql.connector

reportes = Blueprint("reportes", __name__)


@reportes.route("/proyectos/<int:id_proyecto>/reportes")
def ver_reportes(id_proyecto):

    if "id_usuario" not in session:
        return redirect(url_for("auth.login"))

    conexion = obtener_conexion()

    if conexion is None:
        flash("No fue posible conectar con la base de datos.")
        return redirect(url_for("proyectos.listar_proyectos"))

    cursor = conexion.cursor(dictionary=True)

    try:
        rol = session.get("rol")
        id_usuario = session["id_usuario"]

        # Verificar los permisos de acceso al proyecto
        if rol == "ADMINISTRADOR":

            cursor.execute("""
                SELECT p.*
                FROM proyectos p
                WHERE p.id_proyecto = %s
            """, (id_proyecto,))

        elif rol == "GESTOR":

            cursor.execute("""
                SELECT p.*
                FROM proyectos p
                WHERE p.id_proyecto = %s
                  AND p.id_gestor = %s
            """, (id_proyecto, id_usuario))

        else:

            cursor.execute("""
                SELECT p.*
                FROM proyectos p
                INNER JOIN integrantes_proyecto ip
                    ON p.id_proyecto = ip.id_proyecto
                WHERE p.id_proyecto = %s
                  AND ip.id_usuario = %s
            """, (id_proyecto, id_usuario))

        proyecto = cursor.fetchone()

        if not proyecto:
            flash("No tienes acceso a este proyecto.")
            return redirect(url_for("proyectos.listar_proyectos"))

        # Consultar las tareas autorizadas para cada usuario
        if rol in ("GESTOR", "ADMINISTRADOR"):

            cursor.execute("""
                SELECT
                    t.id_tarea,
                    t.titulo,
                    t.fecha_entrega,
                    t.estado,
                    u.nombre AS responsable
                FROM tareas t
                INNER JOIN usuarios u
                    ON t.id_responsable = u.id_usuario
                WHERE t.id_proyecto = %s
                ORDER BY t.fecha_entrega ASC
            """, (id_proyecto,))

        else:

            cursor.execute("""
                SELECT
                    t.id_tarea,
                    t.titulo,
                    t.fecha_entrega,
                    t.estado,
                    u.nombre AS responsable
                FROM tareas t
                INNER JOIN usuarios u
                    ON t.id_responsable = u.id_usuario
                WHERE t.id_proyecto = %s
                  AND t.id_responsable = %s
                ORDER BY t.fecha_entrega ASC
            """, (id_proyecto, id_usuario))

        tareas_lista = cursor.fetchall()

        # Calcular estadísticas
        total = len(tareas_lista)

        pendientes = sum(
            1 for t in tareas_lista
            if t["estado"] == "PENDIENTE"
        )

        en_progreso = sum(
            1 for t in tareas_lista
            if t["estado"] == "EN_PROGRESO"
        )

        finalizadas = sum(
            1 for t in tareas_lista
            if t["estado"] == "FINALIZADO"
        )

        retrasadas = sum(
            1 for t in tareas_lista
            if t["estado"] != "FINALIZADO"
            and t["fecha_entrega"] < date.today()
        )

        avance = (
            round((finalizadas / total) * 100, 2)
            if total > 0 else 0
        )

        return render_template(
            "reportes.html",
            proyecto=proyecto,
            tareas=tareas_lista,
            total=total,
            pendientes=pendientes,
            en_progreso=en_progreso,
            finalizadas=finalizadas,
            retrasadas=retrasadas,
            avance=avance
        )

    except mysql.connector.Error as error:
        print("Error al generar reportes:", error)
        flash("No se pudieron generar los reportes.")
        return redirect(url_for("proyectos.listar_proyectos"))

    finally:
        cursor.close()
        conexion.close()
