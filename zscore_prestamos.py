import random
import statistics
from datetime import datetime, timedelta

import mysql.connector  # pip install mysql-connector-python

random.seed(42)  # resultados reproducibles para el reporte

# ---------- 1. Datos simulados (duraciones en minutos) ----------
RANGOS = {
    "uso_rapido": (15, 45),
    "diagnostico": (25, 35),
    "potencia": (60, 180),
}
N_POR_TIPO = 40  # préstamos normales por tipo
N_ANOMALOS = 6   # préstamos anómalos (más de 4 horas)

def generar_simulados():
    datos = []
    for tipo, (a, b) in RANGOS.items():
        for _ in range(N_POR_TIPO):
            datos.append((tipo, random.uniform(a, b), 0))
    for _ in range(N_ANOMALOS):
        tipo = random.choice(list(RANGOS))
        datos.append((tipo, random.uniform(240, 360), 1))  # etiqueta 1 = anómalo
    return datos

# ---------- 2. Regla z-score por tipo de herramienta ----------
def ajustar(datos):
    """Calcula media y desviación estándar de la duración normal por tipo."""
    modelo = {}
    for tipo in RANGOS:
        normales = [d for t, d, y in datos if t == tipo and y == 0]
        modelo[tipo] = (statistics.mean(normales), statistics.stdev(normales))
    return modelo

UMBRAL_Z = 3.0

def es_anomalo(tipo, duracion, modelo, umbral=UMBRAL_Z):
    media, sd = modelo[tipo]
    z = (duracion - media) / sd
    return z > umbral, z

# ---------- 3. Evaluación con los datos simulados ----------
def evaluar(datos, modelo):
    tp = fp = tn = fn = 0
    for tipo, d, y in datos:
        pred, _ = es_anomalo(tipo, d, modelo)
        if pred and y: tp += 1
        elif pred and not y: fp += 1
        elif not pred and y: fn += 1
        else: tn += 1
    print(f"Verdaderos positivos: {tp}  Falsos positivos: {fp}")
    print(f"Falsos negativos:    {fn}  Verdaderos negativos: {tn}")
    print(f"Precisión: {tp/(tp+fp) if tp+fp else 0:.2f}  Recall: {tp/(tp+fn) if tp+fn else 0:.2f}")

if __name__ == "__main__":
    datos = generar_simulados()
    modelo = ajustar(datos)
    for tipo, (m, s) in modelo.items():
        print(f"{tipo}: media={m:.1f} min, sd={s:.1f} min")
    evaluar(datos, modelo)

    # ---------- 4. Préstamos reales de la base (opcional) ----------
    conn = mysql.connector.connect(host="localhost", user="root", password="", database="taller_rfid")
    cur = conn.cursor()
    cur.execute("""
        SELECT a.herramienta_uid, a.fecha_hora AS inicio, b.fecha_hora AS fin
        FROM movimientos a
        JOIN movimientos b ON b.herramienta_uid = a.herramienta_uid
          AND b.tipo = 'devolucion' AND a.tipo = 'prestamo'
          AND b.id = (SELECT MIN(id) FROM movimientos
                      WHERE herramienta_uid = a.herramienta_uid
                        AND tipo = 'devolucion' AND id > a.id)
    """)
    for uid, inicio, fin in cur.fetchall():
        minutos = (fin - inicio).total_seconds() / 60
        print(f"Real {uid}: {minutos:.1f} min")
    conn.close()