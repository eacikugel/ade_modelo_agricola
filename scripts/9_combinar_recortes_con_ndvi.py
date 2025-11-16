"""
Script para combinar los rasters recorte (invierno y verano) con el NDVI combinado.
Ajusta los valores nodata para que sean consistentes y crea un nuevo raster con:
- Banda 1: recorte_invierno_GTiff.tif
- Banda 2: recorte_verano_GTiff.tif
- Bandas 3+: todas las bandas del 5_NDVI_combinado.tif
"""

import os
import numpy as np
import rasterio
from tqdm import tqdm
import gc

# Paths relativos desde el script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PROC_DIR = os.path.join(PROJECT_ROOT, "data", "proc")

# Archivos de entrada
NDVI_COMBINADO_PATH = os.path.join(PROC_DIR, "5_NDVI_combinado.tif")
RECORTE_INVIERNO_PATH = os.path.join(PROC_DIR, "recorte_invierno_GTiff.tif")
RECORTE_VERANO_PATH = os.path.join(PROC_DIR, "recorte_verano_GTiff.tif")

# Archivo de salida
OUTPUT_PATH = os.path.join(PROC_DIR, "9_NDVI_con_recortes.tif")

print("=" * 80)
print("COMBINACION DE RECORTES CON NDVI COMBINADO")
print("=" * 80)

# Verificar que los archivos existan
archivos_requeridos = {
    'NDVI': NDVI_COMBINADO_PATH,
    'Invierno': RECORTE_INVIERNO_PATH,
    'Verano': RECORTE_VERANO_PATH
}

for nombre, path in archivos_requeridos.items():
    if not os.path.exists(path):
        print(f"\n[ERROR] No se encuentra el archivo {nombre}: {path}")
        exit(1)

# ============================================================================
# PASO 1: Leer parametros de referencia del NDVI combinado
# ============================================================================
print("\n" + "=" * 80)
print("PASO 1: LEYENDO PARAMETROS DE REFERENCIA")
print("=" * 80)

with rasterio.open(NDVI_COMBINADO_PATH) as src_ndvi:
    ref_meta = src_ndvi.meta.copy()
    ref_crs = src_ndvi.crs
    ref_transform = src_ndvi.transform
    ref_width = src_ndvi.width
    ref_height = src_ndvi.height
    ref_bounds = src_ndvi.bounds
    ref_count = src_ndvi.count
    
    print(f"\nParametros de referencia (5_NDVI_combinado.tif):")
    print(f"  Dimensiones: {ref_width} x {ref_height}")
    print(f"  CRS: {ref_crs}")
    print(f"  Numero de bandas: {ref_count}")
    print(f"  Bounds: {ref_bounds}")
    print(f"  Transform: {ref_transform}")
    
    # Obtener nombres de bandas del NDVI combinado
    nombres_bandas_ndvi = []
    for i in range(1, ref_count + 1):
        nombre = src_ndvi.descriptions[i-1] if src_ndvi.descriptions[i-1] else f"Banda_{i}"
        nombres_bandas_ndvi.append(nombre)

# ============================================================================
# PASO 2: Verificar parametros de los rasters recorte
# ============================================================================
print("\n" + "=" * 80)
print("PASO 2: VERIFICANDO PARAMETROS DE RASTERS RECORTE")
print("=" * 80)

with rasterio.open(RECORTE_INVIERNO_PATH) as src_inv:
    inv_width = src_inv.width
    inv_height = src_inv.height
    inv_crs = src_inv.crs
    inv_transform = src_inv.transform
    inv_nodata = src_inv.nodata
    inv_dtype = src_inv.dtypes[0]
    
    print(f"\nParametros recorte_invierno_GTiff.tif:")
    print(f"  Dimensiones: {inv_width} x {inv_height}")
    print(f"  CRS: {inv_crs}")
    print(f"  Nodata: {inv_nodata}")
    print(f"  Dtype: {inv_dtype}")

with rasterio.open(RECORTE_VERANO_PATH) as src_ver:
    ver_width = src_ver.width
    ver_height = src_ver.height
    ver_crs = src_ver.crs
    ver_transform = src_ver.transform
    ver_nodata = src_ver.nodata
    ver_dtype = src_ver.dtypes[0]
    
    print(f"\nParametros recorte_verano_GTiff.tif:")
    print(f"  Dimensiones: {ver_width} x {ver_height}")
    print(f"  CRS: {ver_crs}")
    print(f"  Nodata: {ver_nodata}")
    print(f"  Dtype: {ver_dtype}")

# Verificar que las dimensiones coincidan
if (inv_width != ref_width or inv_height != ref_height or 
    ver_width != ref_width or ver_height != ref_height):
    print("\n[ERROR] Las dimensiones de los rasters recorte no coinciden con el NDVI combinado.")
    exit(1)

if inv_crs != ref_crs or ver_crs != ref_crs:
    print("\n[ERROR] Los CRS de los rasters recorte no coinciden con el NDVI combinado.")
    exit(1)

print("\n[OK] Todos los parametros espaciales coinciden.")

# ============================================================================
# PASO 3: Leer y procesar los rasters
# ============================================================================
print("\n" + "=" * 80)
print("PASO 3: LEYENDO Y PROCESANDO RASTERS")
print("=" * 80)

print("\nLeyendo recorte_invierno_GTiff.tif...")
with rasterio.open(RECORTE_INVIERNO_PATH) as src_inv:
    banda_invierno = src_inv.read(1).astype(np.float32)
    
    # Convertir nodata a nan
    if inv_nodata is not None:
        banda_invierno[banda_invierno == inv_nodata] = np.nan
    print(f"  Shape: {banda_invierno.shape}")
    print(f"  Valores validos: {np.sum(~np.isnan(banda_invierno)):,} de {banda_invierno.size:,}")

print("\nLeyendo recorte_verano_GTiff.tif...")
with rasterio.open(RECORTE_VERANO_PATH) as src_ver:
    banda_verano = src_ver.read(1).astype(np.float32)
    
    # Convertir nodata a nan
    if ver_nodata is not None:
        banda_verano[banda_verano == ver_nodata] = np.nan
    print(f"  Shape: {banda_verano.shape}")
    print(f"  Valores validos: {np.sum(~np.isnan(banda_verano)):,} de {banda_verano.size:,}")

print("\nLeyendo bandas del 5_NDVI_combinado.tif...")
bandas_ndvi = []
with rasterio.open(NDVI_COMBINADO_PATH) as src_ndvi:
    for i in tqdm(range(1, ref_count + 1), desc="Leyendo bandas NDVI"):
        banda = src_ndvi.read(i).astype(np.float32)
        
        # Asegurar que nodata sea nan
        if src_ndvi.nodata is not None:
            banda[banda == src_ndvi.nodata] = np.nan
        elif np.isnan(src_ndvi.nodata):
            # Ya es nan, no hacer nada
            pass
        
        bandas_ndvi.append(banda)

print(f"  Total de bandas NDVI leidas: {len(bandas_ndvi)}")

# ============================================================================
# PASO 4: Crear raster final
# ============================================================================
print("\n" + "=" * 80)
print("PASO 4: CREANDO RASTER FINAL")
print("=" * 80)

# Preparar metadata final
meta_final = ref_meta.copy()
meta_final.update({
    'count': 2 + ref_count,  # 2 bandas de recortes + bandas NDVI
    'dtype': 'float32',
    'nodata': np.nan,
    'compress': 'lzw'
})

# Orden de bandas: recortes primero, luego NDVI
bandas_finales = [banda_invierno, banda_verano] + bandas_ndvi
nombres_finales = ['invierno', 'verano'] + nombres_bandas_ndvi

print(f"\nTotal de bandas en el raster final: {len(bandas_finales)}")
print(f"  Banda 1: invierno")
print(f"  Banda 2: verano")
print(f"  Bandas 3-{len(bandas_finales)}: {ref_count} bandas del NDVI combinado")

# Guardar raster
print(f"\nGuardando raster en: {OUTPUT_PATH}")

with rasterio.open(OUTPUT_PATH, 'w', **meta_final) as dst:
    for i, (banda, nombre) in enumerate(tqdm(zip(bandas_finales, nombres_finales), 
                                               total=len(bandas_finales),
                                               desc="Escribiendo bandas"), 1):
        dst.write(banda, i)
        dst.set_band_description(i, nombre)

print(f"\n[OK] Raster combinado guardado exitosamente.")

# Limpiar memoria
del bandas_finales, banda_invierno, banda_verano, bandas_ndvi
gc.collect()

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)

print(f"\nArchivo de salida: {OUTPUT_PATH}")
print(f"  Dimensiones: {ref_width} x {ref_height}")
print(f"  CRS: {ref_crs}")
print(f"  Total de bandas: {2 + ref_count}")
print(f"  Banda 1: invierno (recorte_invierno_GTiff.tif)")
print(f"  Banda 2: verano (recorte_verano_GTiff.tif)")
print(f"  Bandas 3-{2 + ref_count}: Bandas del 5_NDVI_combinado.tif")
print(f"  Dtype: float32")
print(f"  Nodata: nan")

# Guardar lista de nombres de bandas
nombres_path = os.path.join(PROC_DIR, "9_nombres_bandas_ndvi_recortes.txt")
with open(nombres_path, 'w') as f:
    for i, nombre in enumerate(nombres_finales, 1):
        f.write(f"Banda {i}: {nombre}\n")

print(f"\n[OK] Lista de nombres de bandas guardada en: {nombres_path}")
print("\n" + "=" * 80)

