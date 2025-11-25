"""
Script para aplicar filtro de Moving Window (ventana móvil) de 3x3 píxeles
a las predicciones del Random Forest. Este filtro suaviza las predicciones
aplicando un filtro de mayoría (moda) en una ventana 3x3, eliminando píxeles
aislados y mejorando la coherencia espacial.

Input: 11_prediccion_rf_verano.tif
Output: 11_prediccion_rf_verano_MW_3x3.tif
"""

import os
import numpy as np
import rasterio
from scipy.ndimage import generic_filter

# ---------------------------
# Paths del proyecto
# ---------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PROC_DIR = os.path.join(DATA_DIR, "proc")

# Raster de entrada: predicción RF verano
raster_path = os.path.join(PROC_DIR, "11_prediccion_rf_verano.tif")

# Raster de salida (moving window)
output_path = os.path.join(PROC_DIR, "11_prediccion_rf_verano_MW_3x3.tif")

# ---------------------------
# Función de moda (mayoría)
# ---------------------------
def moda(vecindario):
    """
    Calcula la moda (valor más frecuente) en un vecindario.
    Ignora valores nodata (< 0).
    """
    vec = vecindario[vecindario >= 0]  # ignorar nodata
    if len(vec) == 0:
        return -1
    valores, conteos = np.unique(vec, return_counts=True)
    return valores[np.argmax(conteos)]


# ---------------------------
# Leer raster
# ---------------------------
print("=" * 80)
print("APLICANDO FILTRO MOVING WINDOW 3x3")
print("=" * 80)
print(f"\nLeyendo raster de predicción RF...")
print(f"  Entrada: {raster_path}")

if not os.path.exists(raster_path):
    raise FileNotFoundError(f"Raster no encontrado: {raster_path}")

with rasterio.open(raster_path) as src:
    pred = src.read(1)
    meta = src.meta.copy()
    print(f"  Dimensiones: {src.height} x {src.width}")
    print(f"  CRS: {src.crs}")


# ---------------------------
# Aplicar Moving Window 3×3
# ---------------------------
print("\nAplicando filtro de mayoría (3x3)...")

pred_filtrado = generic_filter(
    pred,
    function=moda,
    size=3,           # ventana 3×3 (cambiar si se quiere de 5 o 7)
    mode='nearest'     # bordes
)

print("Filtro aplicado correctamente.")


# ---------------------------
# Guardar raster suavizado
# ---------------------------
meta.update({
    'dtype': 'int32',
    'count': 1,
    'nodata': -1
})

print(f"\nGuardando raster suavizado...")
print(f"  Salida: {output_path}")

with rasterio.open(output_path, 'w', **meta) as dst:
    dst.write(pred_filtrado.astype(np.int32), 1)
    dst.set_band_description(1, 'Prediccion_RF_Verano_MW_3x3')

print(f"\n[OK] Raster suavizado guardado exitosamente")
print("=" * 80)
