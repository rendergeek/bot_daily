import json
from collections import Counter
from datetime import datetime

# Ruta al archivo de registros
LOG_PATH = "logs/trades.json"
operaciones = []

# Leer cada operación registrada
with open(LOG_PATH, "r") as f:
    for linea in f:
        operaciones.append(json.loads(linea))

# Estadísticas
total = len(operaciones)
por_accion = Counter(op['accion'] for op in operaciones)
precios_venta = [op['precio'] for op in operaciones if op['accion'] == "VENDER"]
precios_compra = [op['precio'] for op in operaciones if op['accion'] == "COMPRAR"]

# Métricas básicas
promedio_venta = sum(precios_venta) / len(precios_venta) if precios_venta else 0
promedio_compra = sum(precios_compra) / len(precios_compra) if precios_compra else 0
fecha_inicio = operaciones[0]['fecha'] if operaciones else "N/A"
fecha_fin = operaciones[-1]['fecha'] if operaciones else "N/A"

# Mostrar resultados
print("📊 Estadísticas del bot:")
print(f"🔁 Total de operaciones: {total}")
print(f"🟢 Compras: {por_accion.get('COMPRAR', 0)}")
print(f"🔴 Ventas: {por_accion.get('VENDER', 0)}")
print(f"📈 Precio promedio de compra: {promedio_compra:.2f}")
print(f"📉 Precio promedio de venta: {promedio_venta:.2f}")
print(f"🗓️ Período: {fecha_inicio} → {fecha_fin}")