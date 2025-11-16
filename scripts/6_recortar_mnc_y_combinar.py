"""
Script para recortar los rasters MNC de invierno y verano ajustándolos a los parámetros
del raster 5_NDVI_combinado.tif, y generar un nuevo raster que incluya todas las bandas
del NDVI combinado más dos bandas adicionales: una para píxeles de invierno y otra para
píxeles de verano.

OPTIMIZADO: Procesa por ventanas para evitar saturar la memoria.
"""

import os
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.windows import Window, from_bounds
from rasterio.transform import from_bounds as transform_from_bounds
from tqdm import tqdm
import gc

# Paths relativos desde el script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROC_DIR = os.path.join(DATA_DIR, "proc")
INTA_DIR = os.path.join(RAW_DIR, "INTA_23_24")

# Archivos de entrada
NDVI_COMBINADO_PATH = os.path.join(PROC_DIR, "5_NDVI_combinado.tif")
MNC_INVIERNO_PATH = os.path.join(INTA_DIR, "MNC_invierno2023.tif")
MNC_VERANO_PATH = os.path.join(INTA_DIR, "MNC_verano-2024.tif")

# Archivo de salida
OUTPUT_PATH = os.path.join(PROC_DIR, "6_NDVI_con_mnc.tif")

# Valores a excluir (nodata y máscara)
EXCLUDE_VALUES = [0, 255]

# Tamaño de ventana para procesamiento por chunks (ajustar según RAM disponible)
CHUNK_SIZE = 2000  # píxeles

print("=" * 80)
print("RECORTE DE MNC Y COMBINACION CON NDVI")
print("=" * 80)

# ============================================================================
# PASO 1: Leer parámetros de referencia del NDVI combinado
# ============================================================================
print("\n" + "=" * 80)
print("PASO 1: LEYENDO PARAMETROS DE REFERENCIA")
print("=" * 80)

with rasterio.open(NDVI_COMBINADO_PATH) as src_ref:
    ref_meta = src_ref.meta.copy()
    ref_crs = src_ref.crs
    ref_transform = src_ref.transform
    ref_width = src_ref.width
    ref_height = src_ref.height
    ref_bounds = src_ref.bounds
    ref_count = src_ref.count
    
    print(f"\nParametros de referencia (5_NDVI_combinado.tif):")
    print(f"  Dimensiones: {ref_width} x {ref_height}")
    print(f"  CRS: {ref_crs}")
    print(f"  Numero de bandas: {ref_count}")
    print(f"  Bounds: {ref_bounds}")
    print(f"  Transform: {ref_transform}")

# ============================================================================
# PASO 2: Obtener información de los rasters MNC
# ============================================================================
print("\n" + "=" * 80)
print("PASO 2: OBTENIENDO INFORMACION DE RASTERS MNC")
print("=" * 80)

with rasterio.open(MNC_INVIERNO_PATH) as src_inv:
    print(f"\nParametros originales MNC invierno:")
    print(f"  Dimensiones: {src_inv.width} x {src_inv.height}")
    print(f"  CRS: {src_inv.crs}")
    print(f"  Bounds: {src_inv.bounds}")
    nodata_inv = src_inv.nodata
    dtype_inv = src_inv.dtypes[0]

with rasterio.open(MNC_VERANO_PATH) as src_ver:
    print(f"\nParametros originales MNC verano:")
    print(f"  Dimensiones: {src_ver.width} x {src_ver.height}")
    print(f"  CRS: {src_ver.crs}")
    print(f"  Bounds: {src_ver.bounds}")
    nodata_ver = src_ver.nodata
    dtype_ver = src_ver.dtypes[0]

# Obtener nombres de bandas del NDVI combinado
with rasterio.open(NDVI_COMBINADO_PATH) as src_ndvi:
    nombres_bandas = []
    for i in range(1, ref_count + 1):
        nombre = src_ndvi.descriptions[i-1] if src_ndvi.descriptions[i-1] else f"Banda_{i}"
        nombres_bandas.append(nombre)

# ============================================================================
# PASO 3: Crear raster final y procesar por ventanas
# ============================================================================
print("\n" + "=" * 80)
print("PASO 3: PROCESANDO POR VENTANAS Y CREANDO RASTER FINAL")
print("=" * 80)

# Preparar metadata final
meta_final = ref_meta.copy()
meta_final.update({
    'count': ref_count + 2,  # Bandas originales + 2 nuevas (invierno y verano)
    'dtype': 'float32',
    'compress': 'lzw'
})

# Calcular número de ventanas
n_chunks_h = (ref_height + CHUNK_SIZE - 1) // CHUNK_SIZE
n_chunks_w = (ref_width + CHUNK_SIZE - 1) // CHUNK_SIZE
total_chunks = n_chunks_h * n_chunks_w

print(f"\nProcesando por ventanas:")
print(f"  Tamaño de ventana: {CHUNK_SIZE}x{CHUNK_SIZE} píxeles")
print(f"  Numero de ventanas: {n_chunks_h}x{n_chunks_w} = {total_chunks}")

# Contadores para estadísticas
total_pixeles_inv = 0
total_pixeles_ver = 0

# Abrir todos los rasters
with rasterio.open(NDVI_COMBINADO_PATH) as src_ndvi, \
     rasterio.open(MNC_INVIERNO_PATH) as src_inv, \
     rasterio.open(MNC_VERANO_PATH) as src_ver, \
     rasterio.open(OUTPUT_PATH, 'w', **meta_final) as dst:
    
    # Procesar cada ventana
    with tqdm(total=total_chunks, desc="Procesando ventanas") as pbar:
        for i in range(n_chunks_h):
            for j in range(n_chunks_w):
                try:
                    # Calcular límites de la ventana
                    row_start = i * CHUNK_SIZE
                    row_end = min((i + 1) * CHUNK_SIZE, ref_height)
                    col_start = j * CHUNK_SIZE
                    col_end = min((j + 1) * CHUNK_SIZE, ref_width)
                    
                    if row_end <= row_start or col_end <= col_start:
                        pbar.update(1)
                        continue
                    
                    # Crear ventana
                    window = Window(col_start, row_start, col_end - col_start, row_end - row_start)
                    
                    # Leer todas las bandas del NDVI para esta ventana
                    bandas_ndvi_chunk = []
                    for band_idx in range(1, ref_count + 1):
                        banda = src_ndvi.read(band_idx, window=window)
                        bandas_ndvi_chunk.append(banda)
                    
                    # Calcular bounds de la ventana en coordenadas
                    window_bounds = rasterio.windows.bounds(window, ref_transform)
                    left, bottom, right, top = window_bounds
                    
                    # Reprojectar MNC invierno para esta ventana
                    inv_bounds = transform_bounds(ref_crs, src_inv.crs, left, bottom, right, top)
                    inv_window = from_bounds(*inv_bounds, src_inv.transform)
                    inv_window = inv_window.round_lengths().round_offsets()
                    
                    # Asegurar que la ventana esté dentro de los bounds
                    inv_window = rasterio.windows.intersect(
                        inv_window,
                        Window(0, 0, src_inv.width, src_inv.height)
                    )
                    
                    if inv_window.width > 0 and inv_window.height > 0:
                        inv_chunk_raw = src_inv.read(1, window=inv_window).astype(np.float32)
                        
                        # Reprojectar al tamaño de la ventana de referencia
                        inv_window_bounds = rasterio.windows.bounds(inv_window, src_inv.transform)
                        src_transform_inv = transform_from_bounds(
                            inv_window_bounds[0], inv_window_bounds[1],
                            inv_window_bounds[2], inv_window_bounds[3],
                            inv_window.width, inv_window.height
                        )
                        dst_transform_inv = transform_from_bounds(
                            left, bottom, right, top,
                            col_end - col_start, row_end - row_start
                        )
                        
                        inv_chunk = np.empty((row_end - row_start, col_end - col_start), dtype=np.float32)
                        reproject(
                            source=inv_chunk_raw,
                            destination=inv_chunk,
                            src_transform=src_transform_inv,
                            src_crs=src_inv.crs,
                            dst_transform=dst_transform_inv,
                            dst_crs=ref_crs,
                            resampling=Resampling.nearest
                        )
                    else:
                        inv_chunk = np.zeros((row_end - row_start, col_end - col_start), dtype=np.float32)
                    
                    # Reprojectar MNC verano para esta ventana
                    ver_bounds = transform_bounds(ref_crs, src_ver.crs, left, bottom, right, top)
                    ver_window = from_bounds(*ver_bounds, src_ver.transform)
                    ver_window = ver_window.round_lengths().round_offsets()
                    
                    # Asegurar que la ventana esté dentro de los bounds
                    ver_window = rasterio.windows.intersect(
                        ver_window,
                        Window(0, 0, src_ver.width, src_ver.height)
                    )
                    
                    if ver_window.width > 0 and ver_window.height > 0:
                        ver_chunk_raw = src_ver.read(1, window=ver_window).astype(np.float32)
                        
                        # Reprojectar al tamaño de la ventana de referencia
                        ver_window_bounds = rasterio.windows.bounds(ver_window, src_ver.transform)
                        src_transform_ver = transform_from_bounds(
                            ver_window_bounds[0], ver_window_bounds[1],
                            ver_window_bounds[2], ver_window_bounds[3],
                            ver_window.width, ver_window.height
                        )
                        dst_transform_ver = transform_from_bounds(
                            left, bottom, right, top,
                            col_end - col_start, row_end - row_start
                        )
                        
                        ver_chunk = np.empty((row_end - row_start, col_end - col_start), dtype=np.float32)
                        reproject(
                            source=ver_chunk_raw,
                            destination=ver_chunk,
                            src_transform=src_transform_ver,
                            src_crs=src_ver.crs,
                            dst_transform=dst_transform_ver,
                            dst_crs=ref_crs,
                            resampling=Resampling.nearest
                        )
                    else:
                        ver_chunk = np.zeros((row_end - row_start, col_end - col_start), dtype=np.float32)
                    
                    # Crear bandas binarias para esta ventana
                    banda_inv_chunk = np.zeros((row_end - row_start, col_end - col_start), dtype=np.float32)
                    mask_inv = ~np.isin(inv_chunk, EXCLUDE_VALUES)
                    if nodata_inv is not None:
                        mask_inv = mask_inv & (inv_chunk != nodata_inv)
                    banda_inv_chunk[mask_inv] = 1.0
                    total_pixeles_inv += np.sum(banda_inv_chunk)
                    
                    banda_ver_chunk = np.zeros((row_end - row_start, col_end - col_start), dtype=np.float32)
                    mask_ver = ~np.isin(ver_chunk, EXCLUDE_VALUES)
                    if nodata_ver is not None:
                        mask_ver = mask_ver & (ver_chunk != nodata_ver)
                    banda_ver_chunk[mask_ver] = 1.0
                    total_pixeles_ver += np.sum(banda_ver_chunk)
                    
                    # Escribir todas las bandas para esta ventana
                    for band_idx, banda_chunk in enumerate(bandas_ndvi_chunk, 1):
                        dst.write(banda_chunk, band_idx, window=window)
                    
                    dst.write(banda_inv_chunk, ref_count + 1, window=window)
                    dst.write(banda_ver_chunk, ref_count + 2, window=window)
                    
                    # Limpiar memoria de la ventana
                    del bandas_ndvi_chunk, inv_chunk, ver_chunk, banda_inv_chunk, banda_ver_chunk
                    if 'inv_chunk_raw' in locals():
                        del inv_chunk_raw
                    if 'ver_chunk_raw' in locals():
                        del ver_chunk_raw
                    
                except Exception as e:
                    print(f"\n[ERROR] Error procesando ventana ({i},{j}): {e}")
                
                pbar.update(1)
            
            # Limpiar memoria cada fila de chunks
            if (i + 1) % 5 == 0:
                gc.collect()
        
        # Establecer descripciones de bandas
        nombres_finales = nombres_bandas + ['invierno', 'verano']
        for band_idx, nombre in enumerate(nombres_finales, 1):
            dst.set_band_description(band_idx, nombre)

print(f"\n[OK] Raster final guardado exitosamente en: {OUTPUT_PATH}")
print(f"\nEstadisticas:")
print(f"  Píxeles de invierno válidos: {int(total_pixeles_inv)} ({100*total_pixeles_inv/(ref_width*ref_height):.2f}%)")
print(f"  Píxeles de verano válidos: {int(total_pixeles_ver)} ({100*total_pixeles_ver/(ref_width*ref_height):.2f}%)")

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)
print(f"\nArchivo de salida: {OUTPUT_PATH}")
print(f"  Dimensiones: {ref_width} x {ref_height}")
print(f"  CRS: {ref_crs}")
print(f"  Total de bandas: {ref_count + 2}")
print(f"  Bandas 1-{ref_count}: Bandas del NDVI combinado")
print(f"  Banda {ref_count + 1}: invierno (binaria: 1=válido, 0=no válido)")
print(f"  Banda {ref_count + 2}: verano (binaria: 1=válido, 0=no válido)")

# Guardar lista de nombres de bandas
nombres_finales = nombres_bandas + ['invierno', 'verano']
nombres_path = os.path.join(PROC_DIR, "6_nombres_bandas_ndvi_mnc.txt")
with open(nombres_path, 'w') as f:
    for i, nombre in enumerate(nombres_finales, 1):
        f.write(f"Banda {i}: {nombre}\n")

print(f"\n[OK] Lista de nombres de bandas guardada en: {nombres_path}")
print("\n" + "=" * 80)

