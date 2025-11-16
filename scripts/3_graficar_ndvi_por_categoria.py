"""
Script para generar gráfico de evolución temporal del NDVI por categoría INTA.
Lee los resultados guardados por 2_procesar_ndvi_por_categoria.py
"""

import os
import pickle
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PROC_DIR = os.path.join(SCRIPT_DIR, "..", "data", "proc")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "img")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Cargar resultados
results_path = os.path.join(DATA_PROC_DIR, "2_ndvi_por_categoria.pkl")

if not os.path.exists(results_path):
    print(f"[ERROR] Error: No se encontro el archivo de resultados: {results_path}")
    print("   Ejecuta primero: python scripts/2_procesar_ndvi_por_categoria.py")
    exit(1)

print("=" * 80)
print("GENERANDO GRAFICO DE EVOLUCION TEMPORAL")
print("=" * 80)

with open(results_path, 'rb') as f:
    resultados = pickle.load(f)

# Extraer datos
inv_data = resultados['invierno']
ver_data = resultados['verano']

categorias_inv = inv_data['categorias']
labels_inv = inv_data['labels']
vals_inv = inv_data['vals']
ndvi_por_categoria_inv = inv_data['ndvi_por_categoria']
meses = inv_data['meses']

categorias_ver = ver_data['categorias']
labels_ver = ver_data['labels']
vals_ver = ver_data['vals']
ndvi_por_categoria_ver = ver_data['ndvi_por_categoria']

# Parsear colores (necesitamos los QML para los colores)
import xml.etree.ElementTree as ET

def parsear_colores_qml(qml_path):
    """Parsea colores del QML."""
    tree = ET.parse(qml_path)
    root = tree.getroot()
    
    vals = []
    hex_colors = []
    
    for it in root.iter('item'):
        value = it.get('value')
        color = it.get('color')
        
        if value:
            vals.append(int(float(value)))
            if color is None:
                hex_colors.append("#888888")
            elif color.startswith("#"):
                hex_colors.append(color)
            elif "," in color:
                rgb_split = color.split(",")
                try:
                    rgb = tuple(map(int, rgb_split[:3]))
                    hex_colors.append('#{:02x}{:02x}{:02x}'.format(*rgb))
                except:
                    hex_colors.append("#888888")
            else:
                hex_colors.append("#888888")
    
    # Ordenar por valor
    z = sorted(zip(vals, hex_colors), key=lambda t: t[0])
    vals, hex_colors = [list(x) for x in zip(*z)]
    
    return dict(zip(vals, hex_colors))

# Obtener colores
INTA_DIR = os.path.join(SCRIPT_DIR, "..", "data", "raw", "INTA_23_24")
QML_INV_PATH = os.path.join(INTA_DIR, "MNC_inv23.qml")
QML_VER_PATH = os.path.join(INTA_DIR, "MNC_ver24.qml")

colores_inv = parsear_colores_qml(QML_INV_PATH)
colores_ver = parsear_colores_qml(QML_VER_PATH)

# Crear figura con 2 subplots (1 fila, 2 columnas)
fig, axes = plt.subplots(1, 2, figsize=(20, 8))

# ============================================================================
# SUBPLOT IZQUIERDO: INVIERNO
# ============================================================================
ax_inv = axes[0]

# Graficar cada categoría de invierno
for cat_val in categorias_inv:
    # Buscar el índice de la categoría en vals_inv para obtener label y color
    try:
        idx = vals_inv.index(cat_val)
        label = labels_inv[idx]
        color = colores_inv.get(cat_val, None)
    except ValueError:
        label = f"Categoría {cat_val}"
        color = None
    
    # Obtener valores NDVI para esta categoría
    valores_ndvi = ndvi_por_categoria_inv[cat_val]
    
    # Solo graficar si hay valores válidos
    if any(not np.isnan(v) for v in valores_ndvi):
        ax_inv.plot(meses, valores_ndvi, marker='o', label=label, 
                   color=color if color else None, linewidth=2, markersize=6)

ax_inv.set_xlabel("Mes", fontsize=12)
ax_inv.set_ylabel("NDVI promedio", fontsize=12)
ax_inv.set_title("Evolución temporal NDVI por categoría - INVIERNO 2023", fontsize=14, fontweight='bold')
ax_inv.set_xticks(range(len(meses)))
ax_inv.set_xticklabels(meses, rotation=45, ha='right')
ax_inv.grid(True, linestyle='--', alpha=0.5)
ax_inv.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
ax_inv.set_ylim(bottom=0)  # NDVI típicamente va de 0 a 1

# ============================================================================
# SUBPLOT DERECHO: VERANO
# ============================================================================
ax_ver = axes[1]

# Graficar cada categoría de verano
for cat_val in categorias_ver:
    # Buscar el índice de la categoría en vals_ver para obtener label y color
    try:
        idx = vals_ver.index(cat_val)
        label = labels_ver[idx]
        color = colores_ver.get(cat_val, None)
    except ValueError:
        label = f"Categoría {cat_val}"
        color = None
    
    # Obtener valores NDVI para esta categoría
    valores_ndvi = ndvi_por_categoria_ver[cat_val]
    
    # Solo graficar si hay valores válidos
    if any(not np.isnan(v) for v in valores_ndvi):
        ax_ver.plot(meses, valores_ndvi, marker='o', label=label,
                   color=color if color else None, linewidth=2, markersize=6)

ax_ver.set_xlabel("Mes", fontsize=12)
ax_ver.set_ylabel("NDVI promedio", fontsize=12)
ax_ver.set_title("Evolución temporal NDVI por categoría - VERANO 2024", fontsize=14, fontweight='bold')
ax_ver.set_xticks(range(len(meses)))
ax_ver.set_xticklabels(meses, rotation=45, ha='right')
ax_ver.grid(True, linestyle='--', alpha=0.5)
ax_ver.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
ax_ver.set_ylim(bottom=0)  # NDVI típicamente va de 0 a 1

# Ajustar layout
plt.tight_layout()

# Guardar gráfico
output_path = os.path.join(OUTPUT_DIR, "3_evolucion_ndvi_por_categoria.png")
plt.savefig(output_path, dpi=200, bbox_inches='tight')
print(f"\n[OK] Grafico guardado en: {output_path}")

plt.show()

# Mostrar resumen de datos
print("\n" + "=" * 80)
print("RESUMEN DE DATOS PROCESADOS")
print("=" * 80)

print("\nINVIERNO:")
for cat_val in categorias_inv:
    try:
        idx = vals_inv.index(cat_val)
        label = labels_inv[idx]
    except ValueError:
        label = f"Categoría {cat_val}"
    valores = ndvi_por_categoria_inv[cat_val]
    valores_validos = [v for v in valores if not np.isnan(v)]
    if valores_validos:
        print(f"  {label}: NDVI promedio anual = {np.mean(valores_validos):.3f} "
              f"(rango: {np.min(valores_validos):.3f} - {np.max(valores_validos):.3f})")

print("\nVERANO:")
for cat_val in categorias_ver:
    try:
        idx = vals_ver.index(cat_val)
        label = labels_ver[idx]
    except ValueError:
        label = f"Categoría {cat_val}"
    valores = ndvi_por_categoria_ver[cat_val]
    valores_validos = [v for v in valores if not np.isnan(v)]
    if valores_validos:
        print(f"  {label}: NDVI promedio anual = {np.mean(valores_validos):.3f} "
              f"(rango: {np.min(valores_validos):.3f} - {np.max(valores_validos):.3f})")

print("\n[OK] Grafico generado exitosamente")

