"""
Script para procesar NDVI por categoría INTA con procesamiento optimizado por ventanas.
Este script calcula el NDVI promedio por categoría para cada mes, procesando por ventanas
para no saturar la memoria.
"""

import numpy as np
import rasterio
from rasterio import warp
from rasterio.windows import Window
from rasterio.warp import transform_bounds, reproject, Resampling
from rasterio.transform import from_bounds
from tqdm import tqdm
import time
import gc
import os
import glob
from collections import defaultdict
import xml.etree.ElementTree as ET

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
CHUNK_SIZE = 2000  # Tamaño de ventana en píxeles (ajustar según RAM disponible)
EXCLUDE_VALUES = [255, 0]  # Valores especiales a excluir (nodata y máscara)

# Paths relativos desde el script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
INTA_DIR = os.path.join(DATA_DIR, "INTA_23_24")
NDVI_DIR = os.path.join(DATA_DIR, "sentinel_23_24")

# Paths a archivos
INTA_INV_PATH = os.path.join(INTA_DIR, "MNC_invierno2023.tif")
INTA_VER_PATH = os.path.join(INTA_DIR, "MNC_verano-2024.tif")
QML_INV_PATH = os.path.join(INTA_DIR, "MNC_inv23.qml")
QML_VER_PATH = os.path.join(INTA_DIR, "MNC_ver24.qml")

# Archivos NDVI
NDVI_FILES = sorted(glob.glob(os.path.join(NDVI_DIR, "NDVI_*.tif")))
MESES = [os.path.basename(f).replace("NDVI_", "").replace(".tif", "") for f in NDVI_FILES]

print("=" * 80)
print("PROCESAMIENTO NDVI POR CATEGORÍA INTA")
print("=" * 80)
print(f"\nConfiguracion:")
print(f"   Chunk size: {CHUNK_SIZE}x{CHUNK_SIZE} píxeles")
print(f"   Archivos NDVI: {len(NDVI_FILES)}")
print(f"   Directorio INTA: {INTA_DIR}")
print(f"   Directorio NDVI: {NDVI_DIR}")


# ============================================================================
# FUNCIÓN: Parsear categorías del QML
# ============================================================================
def parsear_categorias_qml(qml_path):
    """Parsea un archivo QML y retorna valores, labels y colores."""
    tree = ET.parse(qml_path)
    root = tree.getroot()
    
    vals = []
    labels = []
    hex_colors = []
    
    for it in root.iter('item'):
        label = it.get('label')
        value = it.get('value')
        color = it.get('color')
        
        if label and value:
            vals.append(int(float(value)))
            labels.append(label)
            
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
    z = sorted(zip(vals, hex_colors, labels), key=lambda t: t[0])
    vals, hex_colors, labels = [list(x) for x in zip(*z)]
    
    return vals, labels, hex_colors


# ============================================================================
# FUNCIÓN: Procesar NDVI por categoría (OPTIMIZADA)
# ============================================================================
def procesar_ndvi_por_categoria(raster_inta_path, raster_ndvi_path, categorias, 
                                 exclude_values=None, chunk_size=2000, desc="Procesando"):
    """
    Procesa rasters por ventanas y calcula NDVI promedio por categoría.
    OPTIMIZADA: Lee solo ventanas necesarias, no carga rasters completos.
    
    Returns:
        dict: {categoria_valor: ndvi_promedio}
    """
    if exclude_values is None:
        exclude_values = []
    
    resultados = defaultdict(list)  # {categoria: [valores_ndvi]}
    
    # Abrir rasters
    with rasterio.open(raster_inta_path) as src_inta, \
         rasterio.open(raster_ndvi_path) as src_ndvi:
        
        # Obtener dimensiones del raster INTA (referencia)
        height, width = src_inta.height, src_inta.width
        n_chunks_h = (height + chunk_size - 1) // chunk_size
        n_chunks_w = (width + chunk_size - 1) // chunk_size
        total_chunks = n_chunks_h * n_chunks_w
        
        print(f"   Procesando {total_chunks} ventanas ({n_chunks_h}x{n_chunks_w})...")
        necesita_reproyeccion = (src_inta.crs != src_ndvi.crs or 
                                src_inta.height != src_ndvi.height or 
                                src_inta.width != src_ndvi.width)
        if necesita_reproyeccion:
            print(f"   [AVISO] Reproyectando NDVI por ventanas (CRS/dimensiones diferentes)")
        
        # Procesar cada ventana
        with tqdm(total=total_chunks, desc=desc, unit="chunk") as pbar:
            for i in range(n_chunks_h):
                for j in range(n_chunks_w):
                    try:
                        # Calcular límites de la ventana en píxeles INTA
                        row_start = i * chunk_size
                        row_end = min((i + 1) * chunk_size, height)
                        col_start = j * chunk_size
                        col_end = min((j + 1) * chunk_size, width)
                        
                        # Validar que la ventana tenga tamaño válido
                        if row_end <= row_start or col_end <= col_start:
                            pbar.update(1)
                            continue
                        
                        # Crear ventana
                        window = Window(col_start, row_start, col_end - col_start, row_end - row_start)
                        
                        # Leer solo esta ventana del raster INTA
                        inta_chunk = src_inta.read(1, window=window)
                        
                        # Calcular bounds de esta ventana en coordenadas (retorna tupla: left, bottom, right, top)
                        window_bounds = rasterio.windows.bounds(window, src_inta.transform)
                        left, bottom, right, top = window_bounds
                        
                        # Leer NDVI: si mismo CRS y dimensiones, leer ventana directamente
                        if not necesita_reproyeccion:
                            ndvi_chunk = src_ndvi.read(1, window=window).astype(np.float32)
                        else:
                            # Reprojectar solo esta ventana del NDVI
                            # Transformar bounds a CRS del NDVI para encontrar ventana correspondiente
                            try:
                                ndvi_bounds = transform_bounds(
                                    src_inta.crs, src_ndvi.crs,
                                    left, bottom, right, top
                                )
                                ndvi_left, ndvi_bottom, ndvi_right, ndvi_top = ndvi_bounds
                                
                                # Validar que los bounds sean válidos
                                if ndvi_left >= ndvi_right or ndvi_bottom >= ndvi_top:
                                    pbar.update(1)
                                    continue
                                
                                # Leer área del NDVI que corresponde a esta ventana
                                ndvi_window = rasterio.windows.from_bounds(
                                    ndvi_left, ndvi_bottom, ndvi_right, ndvi_top,
                                    src_ndvi.transform
                                )
                                
                                # Validar que la ventana tenga tamaño válido
                                if ndvi_window.width <= 0 or ndvi_window.height <= 0:
                                    pbar.update(1)
                                    continue
                                
                                ndvi_window = ndvi_window.round_lengths().round_offsets()
                                
                                # Asegurar que la ventana esté dentro de los bounds del raster
                                if (ndvi_window.col_off < 0 or ndvi_window.row_off < 0 or
                                    ndvi_window.col_off + ndvi_window.width > src_ndvi.width or
                                    ndvi_window.row_off + ndvi_window.height > src_ndvi.height):
                                    # Ajustar ventana para que esté dentro de los bounds
                                    ndvi_window = rasterio.windows.intersect(
                                        ndvi_window,
                                        Window(0, 0, src_ndvi.width, src_ndvi.height)
                                    )
                                    if ndvi_window.width <= 0 or ndvi_window.height <= 0:
                                        pbar.update(1)
                                        continue
                                
                                # Leer chunk del NDVI
                                ndvi_raw = src_ndvi.read(1, window=ndvi_window).astype(np.float32)
                                
                                # Calcular transforms
                                ndvi_window_bounds = rasterio.windows.bounds(ndvi_window, src_ndvi.transform)
                                src_transform = from_bounds(
                                    ndvi_window_bounds[0], ndvi_window_bounds[1],
                                    ndvi_window_bounds[2], ndvi_window_bounds[3],
                                    ndvi_window.width, ndvi_window.height
                                )
                                dst_transform = from_bounds(
                                    left, bottom, right, top,
                                    col_end - col_start, row_end - row_start
                                )
                                
                                # Reprojectar este chunk al tamaño de la ventana INTA
                                ndvi_chunk = np.empty((row_end - row_start, col_end - col_start), dtype=np.float32)
                                
                                reproject(
                                    source=ndvi_raw,
                                    destination=ndvi_chunk,
                                    src_transform=src_transform,
                                    src_crs=src_ndvi.crs,
                                    dst_transform=dst_transform,
                                    dst_crs=src_inta.crs,
                                    resampling=Resampling.bilinear
                                )
                                
                                del ndvi_raw  # Liberar memoria
                                
                            except Exception as e:
                                # Si falla la reproyección, saltar esta ventana
                                print(f"\n      [ERROR] Error en ventana ({i},{j}): {e}")
                                pbar.update(1)
                                continue
                        
                        # Crear máscara de valores válidos en NDVI
                        ndvi_valid = ~np.isnan(ndvi_chunk)
                        if src_ndvi.nodata is not None:
                            ndvi_valid = ndvi_valid & (ndvi_chunk != src_ndvi.nodata)
                        
                        # Para cada categoría
                        for cat_val in categorias:
                            if cat_val in exclude_values:
                                continue
                            
                            # Máscara: píxeles de esta categoría Y válidos en NDVI
                            mask = (inta_chunk == cat_val) & ndvi_valid
                            
                            if np.any(mask):
                                # Extraer valores NDVI para esta categoría en esta ventana
                                ndvi_values = ndvi_chunk[mask]
                                # Filtrar NaN por si acaso
                                ndvi_values = ndvi_values[~np.isnan(ndvi_values)]
                                if len(ndvi_values) > 0:
                                    resultados[cat_val].extend(ndvi_values.tolist())
                        
                        # Limpiar variables de la ventana
                        del inta_chunk, ndvi_chunk, ndvi_valid
                        
                    except Exception as e:
                        print(f"\n      [ERROR] Error procesando ventana ({i},{j}): {e}")
                    
                    pbar.update(1)
                
                # Limpiar memoria cada fila de chunks
                if (i + 1) % 5 == 0:
                    gc.collect()
        
        # Calcular promedios finales por categoría
        promedios = {}
        for cat_val, valores in resultados.items():
            if len(valores) > 0:
                promedios[cat_val] = np.mean(valores)
            else:
                promedios[cat_val] = np.nan
        
        return promedios


# ============================================================================
# MAIN: Procesar invierno y verano
# ============================================================================
def main():
    # Parsear categorías
    print("\n" + "=" * 80)
    print("PARSEANDO CATEGORIAS")
    print("=" * 80)
    
    vals_inv, labels_inv, hex_colors_inv = parsear_categorias_qml(QML_INV_PATH)
    vals_ver, labels_ver, hex_colors_ver = parsear_categorias_qml(QML_VER_PATH)
    
    print(f"\nCategorías invierno: {len(vals_inv)}")
    print(f"Categorías verano: {len(vals_ver)}")
    
    # Filtrar categorías válidas
    categorias_inv_validas = [v for v in vals_inv if v not in EXCLUDE_VALUES]
    categorias_ver_validas = [v for v in vals_ver if v not in EXCLUDE_VALUES]
    
    print(f"\nCategorías válidas invierno: {len(categorias_inv_validas)}")
    print(f"Categorías válidas verano: {len(categorias_ver_validas)}")
    
    # Inicializar resultados
    ndvi_por_categoria_inv = {cat: [] for cat in categorias_inv_validas}
    ndvi_por_categoria_ver = {cat: [] for cat in categorias_ver_validas}
    
    # ============================================================================
    # PROCESAR INVIERNO
    # ============================================================================
    print("\n" + "=" * 80)
    print("PROCESANDO CATEGORIAS DE INVIERNO")
    print("=" * 80)
    
    tiempo_inicio = time.time()
    for idx, (archivo_ndvi, mes) in enumerate(zip(NDVI_FILES, MESES), 1):
        print(f"\nMes {idx}/{len(NDVI_FILES)}: {mes}")
        tiempo_mes_inicio = time.time()
        
        try:
            promedios = procesar_ndvi_por_categoria(
                INTA_INV_PATH, archivo_ndvi, categorias_inv_validas,
                exclude_values=EXCLUDE_VALUES, chunk_size=CHUNK_SIZE,
                desc=f"  Mes {mes}"
            )
            
            # Guardar resultados
            for cat in categorias_inv_validas:
                ndvi_por_categoria_inv[cat].append(promedios.get(cat, np.nan))
            
            tiempo_mes = time.time() - tiempo_mes_inicio
            tiempo_restante = (tiempo_mes * (len(NDVI_FILES) - idx))
            print(f"  [OK] Completado en {tiempo_mes:.1f}s | ETA restante: {tiempo_restante/60:.1f} min")
            
        except Exception as e:
            print(f"  [ERROR] Error procesando mes {mes}: {e}")
            # Agregar NaN para este mes
            for cat in categorias_inv_validas:
                ndvi_por_categoria_inv[cat].append(np.nan)
        
        # Limpiar memoria después de cada mes
        del promedios
        gc.collect()
    
    tiempo_total_inv = time.time() - tiempo_inicio
    print(f"\n[OK] Invierno completado en {tiempo_total_inv/60:.1f} minutos")
    gc.collect()
    
    # ============================================================================
    # PROCESAR VERANO
    # ============================================================================
    print("\n" + "=" * 80)
    print("PROCESANDO CATEGORIAS DE VERANO")
    print("=" * 80)
    
    tiempo_inicio = time.time()
    for idx, (archivo_ndvi, mes) in enumerate(zip(NDVI_FILES, MESES), 1):
        print(f"\nMes {idx}/{len(NDVI_FILES)}: {mes}")
        tiempo_mes_inicio = time.time()
        
        try:
            promedios = procesar_ndvi_por_categoria(
                INTA_VER_PATH, archivo_ndvi, categorias_ver_validas,
                exclude_values=EXCLUDE_VALUES, chunk_size=CHUNK_SIZE,
                desc=f"  Mes {mes}"
            )
            
            # Guardar resultados
            for cat in categorias_ver_validas:
                ndvi_por_categoria_ver[cat].append(promedios.get(cat, np.nan))
            
            tiempo_mes = time.time() - tiempo_mes_inicio
            tiempo_restante = (tiempo_mes * (len(NDVI_FILES) - idx))
            print(f"  [OK] Completado en {tiempo_mes:.1f}s | ETA restante: {tiempo_restante/60:.1f} min")
            
        except Exception as e:
            print(f"  [ERROR] Error procesando mes {mes}: {e}")
            # Agregar NaN para este mes
            for cat in categorias_ver_validas:
                ndvi_por_categoria_ver[cat].append(np.nan)
        
        # Limpiar memoria después de cada mes
        del promedios
        gc.collect()
    
    tiempo_total_ver = time.time() - tiempo_inicio
    print(f"\n[OK] Verano completado en {tiempo_total_ver/60:.1f} minutos")
    gc.collect()
    
    # ============================================================================
    # GUARDAR RESULTADOS
    # ============================================================================
    print("\n" + "=" * 80)
    print("GUARDANDO RESULTADOS")
    print("=" * 80)
    
    import pickle
    
    output_dir = os.path.join(SCRIPT_DIR, "..", "data", "proc")
    os.makedirs(output_dir, exist_ok=True)
    
    resultados = {
        'invierno': {
            'categorias': categorias_inv_validas,
            'labels': labels_inv,
            'vals': vals_inv,
            'ndvi_por_categoria': ndvi_por_categoria_inv,
            'meses': MESES
        },
        'verano': {
            'categorias': categorias_ver_validas,
            'labels': labels_ver,
            'vals': vals_ver,
            'ndvi_por_categoria': ndvi_por_categoria_ver,
            'meses': MESES
        }
    }
    
    output_path = os.path.join(output_dir, "2_ndvi_por_categoria.pkl")
    with open(output_path, 'wb') as f:
        pickle.dump(resultados, f)
    
    print(f"\n[OK] Resultados guardados en: {output_path}")
    print(f"\n{'='*80}")
    print(f"TIEMPO TOTAL: {(tiempo_total_inv + tiempo_total_ver)/60:.1f} minutos")
    print(f"{'='*80}")
    
    # Limpieza final
    print("\nLimpieza final de memoria...")
    gc.collect()
    print("[OK] Procesamiento completado")
    
    return resultados


if __name__ == "__main__":
    resultados = main()

