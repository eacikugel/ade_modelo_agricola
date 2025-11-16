"""
Script para combinar todos los rasters de NDVI en uno solo.
Cada imagen satelital será una banda, y se agregarán 4 bandas al principio
con estadísticos: mediana, min, max, desviación estándar.
"""

import os
import glob
import numpy as np
import rasterio
from rasterio.transform import Affine
from tqdm import tqdm
import gc

# Paths relativos desde el script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "proc")

# Directorio con archivos NDVI
NDVI_DIR = os.path.join(DATA_DIR, "sentinel_23_24")

print("=" * 80)
print("COMBINACION DE RASTERS NDVI")
print("=" * 80)

# Buscar todos los archivos NDVI
ndvi_files = sorted(glob.glob(os.path.join(NDVI_DIR, "NDVI_*.tif")))

print(f"\nArchivos encontrados en sentinel_23_24: {len(ndvi_files)} archivos")

# Función para leer banda NDVI de un raster
def leer_banda_ndvi(raster_path):
    """
    Lee la banda NDVI de un raster (archivos de sentinel_23_24 tienen una sola banda).
    """
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        meta = src.meta.copy()
        return data, meta

# Recopilar todos los archivos con sus nombres
todos_archivos = []
nombres_bandas = []

# Archivos de sentinel_23_24
for archivo in ndvi_files:
    nombre = os.path.basename(archivo).replace("NDVI_", "").replace(".tif", "")
    todos_archivos.append(archivo)
    nombres_bandas.append(f"NDVI_{nombre}")

# Obtener propiedades de referencia del primer raster
# (todos tienen las mismas propiedades según la verificación)
print("\nObteniendo propiedades de referencia...")
primer_data, primer_meta = leer_banda_ndvi(todos_archivos[0])

# Propiedades de referencia
ref_height = primer_meta['height']
ref_width = primer_meta['width']
ref_crs = primer_meta['crs']
ref_transform = primer_meta['transform']
ref_nodata = primer_meta.get('nodata', None)

print(f"\nPropiedades de referencia:")
print(f"  Dimensiones: {ref_width} x {ref_height}")
print(f"  CRS: {ref_crs}")
print(f"  Nodata: {ref_nodata}")

print(f"\nTotal de archivos a combinar: {len(todos_archivos)}")
print(f"Total de bandas en el raster final: {len(todos_archivos) + 4} (4 estadísticas + {len(todos_archivos)} temporales)")

# Leer todos los rasters
print("\n" + "=" * 80)
print("LEYENDO RASTERS")
print("=" * 80)

datos_rasters = []
archivos_validos = []
nombres_validos = []

for archivo, nombre_banda in tqdm(zip(todos_archivos, nombres_bandas), 
                                  total=len(todos_archivos), 
                                  desc="Leyendo rasters"):
    try:
        data, meta = leer_banda_ndvi(archivo)
        
        # Convertir a float32 para cálculos estadísticos
        if data.dtype != np.float32:
            data = data.astype(np.float32)
        
        # Manejar nodata
        if ref_nodata is not None:
            data[data == ref_nodata] = np.nan
        elif meta.get('nodata') is not None:
            data[data == meta['nodata']] = np.nan
        
        datos_rasters.append(data)
        archivos_validos.append(archivo)
        nombres_validos.append(nombre_banda)
        
    except Exception as e:
        print(f"\n[ERROR] No se pudo leer {os.path.basename(archivo)}: {e}")
        continue

if not datos_rasters:
    print("\n[ERROR] No se pudieron leer rasters válidos.")
    exit(1)

print(f"\n[OK] {len(datos_rasters)} rasters leídos correctamente.")

# Apilar todos los datos
print("\n" + "=" * 80)
print("CALCULANDO ESTADISTICOS")
print("=" * 80)

print("Apilando datos...")
stack = np.stack(datos_rasters, axis=0)  # Shape: (n_bandas, height, width)
print(f"  Shape del stack: {stack.shape}")

# Calcular estadísticos
print("\nCalculando estadísticos...")
print("  Mediana...")
mediana = np.nanmedian(stack, axis=0)

print("  Mínimo...")
minimo = np.nanmin(stack, axis=0)

print("  Máximo...")
maximo = np.nanmax(stack, axis=0)

print("  Desviación estándar...")
desviacion = np.nanstd(stack, axis=0)

# Limpiar memoria
del stack
gc.collect()

# Crear raster final
print("\n" + "=" * 80)
print("CREANDO RASTER COMBINADO")
print("=" * 80)

# Orden de bandas: estadísticos primero, luego temporales
bandas_finales = [mediana, minimo, maximo, desviacion] + datos_rasters
nombres_finales = ['mediana', 'min', 'max', 'sd'] + nombres_validos

# Actualizar metadata
meta_final = primer_meta.copy()
meta_final.update({
    'count': len(bandas_finales),
    'dtype': 'float32',
    'nodata': np.nan,
    'compress': 'lzw'  # Compresión para reducir tamaño
})

# Guardar raster
output_path = os.path.join(OUTPUT_DIR, "5_NDVI_combinado.tif")
print(f"\nGuardando raster en: {output_path}")

with rasterio.open(output_path, 'w', **meta_final) as dst:
    for i, (banda, nombre) in enumerate(tqdm(zip(bandas_finales, nombres_finales), 
                                               total=len(bandas_finales),
                                               desc="Escribiendo bandas"), 1):
        dst.write(banda, i)
        dst.set_band_description(i, nombre)

print(f"\n[OK] Raster combinado guardado exitosamente.")
print(f"\nResumen:")
print(f"  Total de bandas: {len(bandas_finales)}")
print(f"  Bandas estadísticas (1-4): mediana, min, max, sd")
print(f"  Bandas temporales (5-{len(bandas_finales)}): {len(nombres_validos)} imágenes NDVI")
print(f"  Dimensiones: {ref_width} x {ref_height}")
print(f"  CRS: {ref_crs}")

# Guardar lista de nombres de bandas
nombres_path = os.path.join(OUTPUT_DIR, "5_nombres_bandas_ndvi.txt")
with open(nombres_path, 'w') as f:
    for i, nombre in enumerate(nombres_finales, 1):
        f.write(f"Banda {i}: {nombre}\n")

print(f"\n[OK] Lista de nombres de bandas guardada en: {nombres_path}")

