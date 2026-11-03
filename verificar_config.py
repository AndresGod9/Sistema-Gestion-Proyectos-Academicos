from config import Config

print("Host:", repr(Config.DB_HOST))
print("Puerto:", Config.DB_PORT)
print("Usuario:", repr(Config.DB_USER))
print("Base de datos:", repr(Config.DB_NAME))
print("Contraseña configurada:", bool(Config.DB_PASSWORD))