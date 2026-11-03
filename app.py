
from flask import Flask, redirect, url_for
from flask_wtf.csrf import CSRFProtect
from config import Config
from routes.auth import auth
from routes.proyectos import proyectos
from routes.integrantes import integrantes
from routes.tareas import tareas
from routes.reportes import reportes

app = Flask(__name__)
app.config.from_object(Config)
csrf = CSRFProtect(app)

app.register_blueprint(auth)
app.register_blueprint(proyectos)
app.register_blueprint(integrantes)
app.register_blueprint(tareas)
app.register_blueprint(reportes)

@app.route("/")
def inicio():
    return redirect(url_for("auth.login"))


if __name__ == "__main__":
    app.run(debug=True)
