# Use PyMySQL as a drop-in replacement for the MySQLdb driver Django expects.
# Pure-Python, so no system build tools are required.
import pymysql

pymysql.install_as_MySQLdb()
