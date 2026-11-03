
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.conexion import obtener_conexion
from datetime import date
import mysql.connector

tareas = Blueprint("tareas", __name__)


# VERIFICAR ACCESO AL PROYECTO
def tiene_acceso_proyecto(cursor, id_proyecto):

    rol = session.get("rol")
    id_usuario = session.get("id_usuario")

    if rol == "ADMINISTRADOR":

        cursor.execute("""
            SELECT id_proyecto, nombre
            FROM proyectos
            WHERE id_proyecto = %s
        """, (id_proyecto,))

    elif rol == "GESTOR":

        cursor.execute("""
            SELECT id_proyecto, nombre
            FROM proyectos
            WHERE id_proyecto = %s
              AND id_gestor = %s
        """, (id_proyecto, id_usuario))

    else:

        cursor.execute("""
            SELECT p.id_proyecto, p.nombre
            FROM proyectos p
            INNER JOIN integrantes_proyecto ip
                ON p.id_proyecto = ip.id_proyecto
            WHERE p.id_proyecto = %s
              AND ip.id_usuario = %s
        """, (id_proyecto, id_usuario))

    return cursor.fetchone()


# LISTAR TAREAS
@tareas.route("/proyectos/<int:id_proyecto>/tareas")
def listar_tareas(id_proyecto):

    if "id_usuario" not in session:
        return redirect(url_for("auth.login"))

    conexion = obtener_conexion()

    if conexion is None:
        flash("No se pudo conectar con la base de datos.")
        return redirect(url_for("proyectos.listar_proyectos"))

    cursor = conexion.cursor(dictionary=True)

    try:

        proyecto = tiene_acceso_proyecto(cursor, id_proyecto)

        if not proyecto:
            flash("No tienes acceso a este proyecto.")
            return redirect(url_for("proyectos.listar_proyectos"))

        if session.get("rol") in ("GESTOR", "ADMINISTRADOR"):

            cursor.execute("""
                SELECT t.*, u.nombre AS responsable
                FROM tareas t
                INNER JOIN usuarios u
                    ON t.id_responsable = u.id_usuario
                WHERE t.id_proyecto = %s
                ORDER BY t.fecha_entrega ASC
            """, (id_proyecto,))

        else:

            cursor.execute("""
                SELECT t.*, u.nombre AS responsable
                FROM tareas t
                INNER JOIN usuarios u
                    ON t.id_responsable = u.id_usuario
                WHERE t.id_proyecto = %s
                  AND t.id_responsable = %s
                ORDER BY t.fecha_entrega ASC
            """, (id_proyecto, session["id_usuario"]))

        lista_tareas = cursor.fetchall()

        return render_template(
            "tareas.html",
            proyecto=proyecto,
            tareas=lista_tareas,
            puede_crear=session.get("rol") in ("GESTOR", "ADMINISTRADOR")
        )

    except mysql.connector.Error as error:
        print("Error al consultar tareas:", error)
        flash("No se pudieron consultar las tareas.")
        return redirect(url_for("proyectos.listar_proyectos"))

    finally:
        cursor.close()
        conexion.close()


# CREAR TAREA
@tareas.route(
    "/proyectos/<int:id_proyecto>/tareas/crear",
    methods=["GET", "POST"]
)
def crear_tarea(id_proyecto):

    if "id_usuario" not in session:
        return redirect(url_for("auth.login"))

    if session.get("rol") not in ("GESTOR", "ADMINISTRADOR"):
        flash("No tienes permisos para crear tareas.")
        return redirect(url_for(
            "tareas.listar_tareas",
            id_proyecto=id_proyecto
        ))

    conexion = obtener_conexion()

    if conexion is None:
        flash("No se pudo conectar con la base de datos.")
        return redirect(url_for("proyectos.listar_proyectos"))

    cursor = conexion.cursor(dictionary=True)

    try:

        proyecto = tiene_acceso_proyecto(cursor, id_proyecto)

        if not proyecto:
            flash("No tienes permiso para gestionar este proyecto.")
            return redirect(url_for("proyectos.listar_proyectos"))

        # Consultar colaboradores activos del proyecto
        cursor.execute("""
            SELECT u.id_usuario, u.nombre, u.correo
            FROM integrantes_proyecto ip
            INNER JOIN usuarios u
                ON ip.id_usuario = u.id_usuario
            WHERE ip.id_proyecto = %s
              AND u.rol = 'COLABORADOR'
              AND u.activo = TRUE
            ORDER BY u.nombre
        """, (id_proyecto,))

        colaboradores = cursor.fetchall()

        if request.method == "POST":

            titulo = request.form.get("titulo", "").strip()
            descripcion = request.form.get("descripcion", "").strip()
            fecha_entrega = request.form.get("fecha_entrega", "")
            id_responsable = request.form.get("id_responsable", type=int)

            if not titulo or not fecha_entrega or not id_responsable:
                flash("Completa todos los campos obligatorios.")
                return redirect(url_for(
                    "tareas.crear_tarea",
                    id_proyecto=id_proyecto
                ))

            try:
                entrega = date.fromisoformat(fecha_entrega)

            except ValueError:
                flash("La fecha de entrega no es válida.")
                return redirect(url_for(
                    "tareas.crear_tarea",
                    id_proyecto=id_proyecto
                ))

            # Comprobar que el responsable sea un colaborador activo
            # y que pertenezca al proyecto
            cursor.execute("""
                SELECT u.id_usuario
                FROM integrantes_proyecto ip
                INNER JOIN usuarios u
                    ON ip.id_usuario = u.id_usuario
                WHERE ip.id_proyecto = %s
                  AND ip.id_usuario = %s
                  AND u.rol = 'COLABORADOR'
                  AND u.activo = TRUE
            """, (id_proyecto, id_responsable))

            colaborador = cursor.fetchone()

            if not colaborador:
                flash(
                    "El responsable debe ser un colaborador activo "
                    "que pertenezca al proyecto."
                )
                return redirect(url_for(
                    "tareas.crear_tarea",
                    id_proyecto=id_proyecto
                ))

            cursor.execute("""
                INSERT INTO tareas
                (
                    titulo,
                    descripcion,
                    fecha_entrega,
                    id_proyecto,
                    id_responsable,
                    id_creador
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                titulo,
                descripcion,
                entrega,
                id_proyecto,
                id_responsable,
                session["id_usuario"]
            ))

            conexion.commit()

            flash("Tarea creada y asignada correctamente.")

            return redirect(url_for(
                "tareas.listar_tareas",
                id_proyecto=id_proyecto
            ))

        return render_template(
            "crear_tarea.html",
            proyecto=proyecto,
            colaboradores=colaboradores
        )

    except mysql.connector.Error as error:
        conexion.rollback()
        print("Error al crear tarea:", error)
        flash("No se pudo guardar la tarea.")
        return redirect(url_for(
            "tareas.listar_tareas",
            id_proyecto=id_proyecto
        ))

    finally:
        cursor.close()
        conexion.close()


# TABLERO KANBAN
@tareas.route("/proyectos/<int:id_proyecto>/kanban")
def tablero_kanban(id_proyecto):

    if "id_usuario" not in session:
        return redirect(url_for("auth.login"))

    conexion = obtener_conexion()

    if conexion is None:
        flash("No se pudo conectar con la base de datos.")
        return redirect(url_for("proyectos.listar_proyectos"))

    cursor = conexion.cursor(dictionary=True)

    try:

        proyecto = tiene_acceso_proyecto(cursor, id_proyecto)

        if not proyecto:
            flash("No tienes acceso a este proyecto.")
            return redirect(url_for("proyectos.listar_proyectos"))

        if session.get("rol") in ("GESTOR", "ADMINISTRADOR"):

            cursor.execute("""
                SELECT t.*, u.nombre AS responsable
                FROM tareas t
                INNER JOIN usuarios u
                    ON t.id_responsable = u.id_usuario
                WHERE t.id_proyecto = %s
                ORDER BY t.fecha_entrega ASC
            """, (id_proyecto,))

        else:

            cursor.execute("""
                SELECT t.*, u.nombre AS responsable
                FROM tareas t
                INNER JOIN usuarios u
                    ON t.id_responsable = u.id_usuario
                WHERE t.id_proyecto = %s
                  AND t.id_responsable = %s
                ORDER BY t.fecha_entrega ASC
            """, (id_proyecto, session["id_usuario"]))

        lista_tareas = cursor.fetchall()

        return render_template(
            "kanban.html",
            proyecto=proyecto,
            tareas=lista_tareas,
            puede_cambiar_estado=True
        )

    except mysql.connector.Error as error:
        print("Error al cargar Kanban:", error)
        flash("No se pudo cargar el tablero.")
        return redirect(url_for("proyectos.listar_proyectos"))

    finally:
        cursor.close()
        conexion.close()


# CAMBIAR ESTADO DE UNA TAREA
@tareas.route(
    "/proyectos/<int:id_proyecto>/tareas/<int:id_tarea>/estado",
    methods=["POST"]
)
def cambiar_estado(id_proyecto, id_tarea):

    if "id_usuario" not in session:
        return redirect(url_for("auth.login"))

    estado = request.form.get("estado")

    estados_validos = (
        "PENDIENTE",
        "EN_PROGRESO",
        "FINALIZADO"
    )

    if estado not in estados_validos:
        flash("El estado seleccionado no es válido.")
        return redirect(url_for(
            "tareas.tablero_kanban",
            id_proyecto=id_proyecto
        ))

    conexion = obtener_conexion()

    if conexion is None:
        flash("No se pudo conectar con la base de datos.")
        return redirect(url_for("proyectos.listar_proyectos"))

    cursor = conexion.cursor(dictionary=True)

    try:

        proyecto = tiene_acceso_proyecto(cursor, id_proyecto)

        if not proyecto:
            flash("No tienes acceso a este proyecto.")
            return redirect(url_for("proyectos.listar_proyectos"))

        # Comprobar que la tarea exista y que el usuario tenga permiso
        if session.get("rol") in ("GESTOR", "ADMINISTRADOR"):

            cursor.execute("""
                SELECT id_tarea
                FROM tareas
                WHERE id_tarea = %s
                  AND id_proyecto = %s
            """, (id_tarea, id_proyecto))

        else:

            cursor.execute("""
                SELECT id_tarea
                FROM tareas
                WHERE id_tarea = %s
                  AND id_proyecto = %s
                  AND id_responsable = %s
            """, (
                id_tarea,
                id_proyecto,
                session["id_usuario"]
            ))

        tarea = cursor.fetchone()

        if not tarea:
            flash(
                "No existe la tarea o no tienes permiso para modificarla."
            )
            return redirect(url_for(
                "tareas.tablero_kanban",
                id_proyecto=id_proyecto
            ))

        # Actualizar el estado
        cursor.execute("""
            UPDATE tareas
            SET estado = %s
            WHERE id_tarea = %s
              AND id_proyecto = %s
        """, (estado, id_tarea, id_proyecto))

        conexion.commit()

        flash("Estado de la tarea actualizado correctamente.")

    except mysql.connector.Error as error:
        conexion.rollback()
        print("Error al cambiar el estado:", error)
        flash("No se pudo actualizar el estado.")

    finally:
        cursor.close()
        conexion.close()

    return redirect(url_for(
        "tareas.tablero_kanban",
        id_proyecto=id_proyecto
    ))
