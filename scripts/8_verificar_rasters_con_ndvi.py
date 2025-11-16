"""
Script para verificar si los parametros de los rasters recorte (invierno y verano)
coinciden con los parametros del raster 5_NDVI_combinado.tif.
"""

import os
import rasterio
import pandas as pd

# Paths relativos desde el script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PROC_DIR = os.path.join(PROJECT_ROOT, "data", "proc")

# Archivos a comparar
NDVI_COMBINADO_PATH = os.path.join(PROC_DIR, "5_NDVI_combinado.tif")
RECORTE_INVIERNO_PATH = os.path.join(PROC_DIR, "recorte_invierno_GTiff.tif")
RECORTE_VERANO_PATH = os.path.join(PROC_DIR, "recorte_verano_GTiff.tif")

print("=" * 80)
print("VERIFICACION DE PARAMETROS CON NDVI COMBINADO")
print("=" * 80)

# Funcion para obtener propiedades de un raster
def obtener_propiedades(raster_path, nombre):
    """Obtiene las propiedades clave de un raster."""
    try:
        with rasterio.open(raster_path) as src:
            props = {
                'archivo': nombre,
                'ruta': raster_path,
                'crs': str(src.crs),
                'width': src.width,
                'height': src.height,
                'transform': src.transform,
                'nodata': src.nodata,
                'dtype': str(src.dtypes[0]),
                'count': src.count,
                'bounds': src.bounds,
                'res_width': src.transform[0],
                'res_height': abs(src.transform[4]),
            }
            return props, None
    except Exception as e:
        return None, str(e)

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

# Obtener propiedades de todos los rasters
print("\n" + "=" * 80)
print("OBTENIENDO PROPIEDADES DE LOS RASTERS")
print("=" * 80)

props_ndvi, error_ndvi = obtener_propiedades(NDVI_COMBINADO_PATH, "5_NDVI_combinado.tif")
if error_ndvi:
    print(f"\n[ERROR] No se pudo leer 5_NDVI_combinado.tif: {error_ndvi}")
    exit(1)

props_inv, error_inv = obtener_propiedades(RECORTE_INVIERNO_PATH, "recorte_invierno_GTiff.tif")
if error_inv:
    print(f"\n[ERROR] No se pudo leer recorte_invierno_GTiff.tif: {error_inv}")
    exit(1)

props_ver, error_ver = obtener_propiedades(RECORTE_VERANO_PATH, "recorte_verano_GTiff.tif")
if error_ver:
    print(f"\n[ERROR] No se pudo leer recorte_verano_GTiff.tif: {error_ver}")
    exit(1)

# Mostrar propiedades de cada raster
print("\nPropiedades de 5_NDVI_combinado.tif (REFERENCIA):")
print("-" * 80)
print(f"  CRS: {props_ndvi['crs']}")
print(f"  Dimensiones: {props_ndvi['width']} x {props_ndvi['height']}")
print(f"  Resolucion: {props_ndvi['res_width']:.6f} x {props_ndvi['res_height']:.6f}")
print(f"  Nodata: {props_ndvi['nodata']}")
print(f"  Dtype: {props_ndvi['dtype']}")
print(f"  Numero de bandas: {props_ndvi['count']}")
print(f"  Bounds: {props_ndvi['bounds']}")
print(f"  Transform: {props_ndvi['transform']}")

print("\nPropiedades de recorte_invierno_GTiff.tif:")
print("-" * 80)
print(f"  CRS: {props_inv['crs']}")
print(f"  Dimensiones: {props_inv['width']} x {props_inv['height']}")
print(f"  Resolucion: {props_inv['res_width']:.6f} x {props_inv['res_height']:.6f}")
print(f"  Nodata: {props_inv['nodata']}")
print(f"  Dtype: {props_inv['dtype']}")
print(f"  Numero de bandas: {props_inv['count']}")
print(f"  Bounds: {props_inv['bounds']}")
print(f"  Transform: {props_inv['transform']}")

print("\nPropiedades de recorte_verano_GTiff.tif:")
print("-" * 80)
print(f"  CRS: {props_ver['crs']}")
print(f"  Dimensiones: {props_ver['width']} x {props_ver['height']}")
print(f"  Resolucion: {props_ver['res_width']:.6f} x {props_ver['res_height']:.6f}")
print(f"  Nodata: {props_ver['nodata']}")
print(f"  Dtype: {props_ver['dtype']}")
print(f"  Numero de bandas: {props_ver['count']}")
print(f"  Bounds: {props_ver['bounds']}")
print(f"  Transform: {props_ver['transform']}")

# Comparar propiedades con NDVI combinado
print("\n" + "=" * 80)
print("COMPARACION CON NDVI COMBINADO")
print("=" * 80)

def comparar_con_referencia(props_ref, props_comp, nombre_comp):
    """Compara propiedades de un raster con el de referencia."""
    comparaciones = {
        'CRS': (props_ref['crs'], props_comp['crs'], props_ref['crs'] == props_comp['crs']),
        'Width': (props_ref['width'], props_comp['width'], props_ref['width'] == props_comp['width']),
        'Height': (props_ref['height'], props_comp['height'], props_ref['height'] == props_comp['height']),
        'Resolucion Width': (props_ref['res_width'], props_comp['res_width'], 
                            abs(props_ref['res_width'] - props_comp['res_width']) < 1e-10),
        'Resolucion Height': (props_ref['res_height'], props_comp['res_height'], 
                             abs(props_ref['res_height'] - props_comp['res_height']) < 1e-10),
        'Nodata': (props_ref['nodata'], props_comp['nodata'], props_ref['nodata'] == props_comp['nodata']),
        'Dtype': (props_ref['dtype'], props_comp['dtype'], props_ref['dtype'] == props_comp['dtype']),
    }
    
    transform_coinciden = props_ref['transform'] == props_comp['transform']
    bounds_coinciden = props_ref['bounds'] == props_comp['bounds']
    
    todas_coinciden = all(comp[2] for comp in comparaciones.values()) and transform_coinciden and bounds_coinciden
    
    return comparaciones, transform_coinciden, bounds_coinciden, todas_coinciden

# Comparar invierno con NDVI
print("\nComparacion: recorte_invierno_GTiff.tif vs 5_NDVI_combinado.tif")
print("-" * 80)
comp_inv, trans_inv, bounds_inv, todas_inv = comparar_con_referencia(props_ndvi, props_inv, "invierno")

print(f"{'Parametro':<25} {'NDVI (Ref)':<30} {'Invierno':<30} {'Coinciden':<10}")
print("-" * 80)
for param, (val_ref, val_comp, coincide) in comp_inv.items():
    estado = "SI" if coincide else "NO"
    print(f"{param:<25} {str(val_ref):<30} {str(val_comp):<30} {estado:<10}")

print(f"\n  Transform coincide: {'SI' if trans_inv else 'NO'}")
print(f"  Bounds coincide: {'SI' if bounds_inv else 'NO'}")

# Comparar verano con NDVI
print("\nComparacion: recorte_verano_GTiff.tif vs 5_NDVI_combinado.tif")
print("-" * 80)
comp_ver, trans_ver, bounds_ver, todas_ver = comparar_con_referencia(props_ndvi, props_ver, "verano")

print(f"{'Parametro':<25} {'NDVI (Ref)':<30} {'Verano':<30} {'Coinciden':<10}")
print("-" * 80)
for param, (val_ref, val_comp, coincide) in comp_ver.items():
    estado = "SI" if coincide else "NO"
    print(f"{param:<25} {str(val_ref):<30} {str(val_comp):<30} {estado:<10}")

print(f"\n  Transform coincide: {'SI' if trans_ver else 'NO'}")
print(f"  Bounds coincide: {'SI' if bounds_ver else 'NO'}")

# Resumen final
print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)

print("\nComparacion con 5_NDVI_combinado.tif:")
print("-" * 80)
print(f"  recorte_invierno_GTiff.tif: {'COINCIDE' if todas_inv else 'NO COINCIDE'}")
print(f"  recorte_verano_GTiff.tif:   {'COINCIDE' if todas_ver else 'NO COINCIDE'}")

if todas_inv and todas_ver:
    print("\n[OK] Ambos rasters recorte tienen parametros identicos al NDVI combinado.")
else:
    print("\n[ADVERTENCIA] Algunos rasters recorte NO tienen parametros identicos al NDVI combinado.")
    if not todas_inv:
        print("  - recorte_invierno_GTiff.tif tiene diferencias")
    if not todas_ver:
        print("  - recorte_verano_GTiff.tif tiene diferencias")

# Guardar reporte
print("\n" + "=" * 80)
print("GUARDANDO REPORTE")
print("=" * 80)

df = pd.DataFrame([props_ndvi, props_inv, props_ver])
reporte_path = os.path.join(PROC_DIR, "8_reporte_verificacion_con_ndvi.csv")
df_export = df[['archivo', 'crs', 'width', 'height', 'res_width', 'res_height', 
                'nodata', 'dtype', 'count']].copy()
df_export.to_csv(reporte_path, index=False)

print(f"\n[OK] Reporte guardado en: {reporte_path}")

# Guardar reporte detallado de comparacion
reporte_detallado_path = os.path.join(PROC_DIR, "8_reporte_verificacion_con_ndvi_detallado.txt")
with open(reporte_detallado_path, 'w') as f:
    f.write("VERIFICACION DE PARAMETROS CON NDVI COMBINADO\n")
    f.write("=" * 80 + "\n\n")
    
    f.write("PROPIEDADES DE 5_NDVI_COMBINADO.TIF (REFERENCIA)\n")
    f.write("-" * 80 + "\n")
    for key, value in props_ndvi.items():
        if key != 'transform' and key != 'bounds':
            f.write(f"  {key}: {value}\n")
    f.write(f"  transform: {props_ndvi['transform']}\n")
    f.write(f"  bounds: {props_ndvi['bounds']}\n")
    
    f.write("\nCOMPARACION: RECORTE_INVIERNO_GTIFF.TIF\n")
    f.write("-" * 80 + "\n")
    for param, (val_ref, val_comp, coincide) in comp_inv.items():
        estado = "SI" if coincide else "NO"
        f.write(f"{param}: {val_ref} vs {val_comp} -> {estado}\n")
    f.write(f"Transform coincide: {'SI' if trans_inv else 'NO'}\n")
    f.write(f"Bounds coincide: {'SI' if bounds_inv else 'NO'}\n")
    f.write(f"TODAS COINCIDEN: {'SI' if todas_inv else 'NO'}\n")
    
    f.write("\nCOMPARACION: RECORTE_VERANO_GTIFF.TIF\n")
    f.write("-" * 80 + "\n")
    for param, (val_ref, val_comp, coincide) in comp_ver.items():
        estado = "SI" if coincide else "NO"
        f.write(f"{param}: {val_ref} vs {val_comp} -> {estado}\n")
    f.write(f"Transform coincide: {'SI' if trans_ver else 'NO'}\n")
    f.write(f"Bounds coincide: {'SI' if bounds_ver else 'NO'}\n")
    f.write(f"TODAS COINCIDEN: {'SI' if todas_ver else 'NO'}\n")
    
    f.write("\nCONCLUSION\n")
    f.write("-" * 80 + "\n")
    if todas_inv and todas_ver:
        f.write("Todos los rasters recorte tienen parametros identicos al NDVI combinado.\n")
    else:
        f.write("Algunos rasters recorte NO tienen parametros identicos al NDVI combinado.\n")

print(f"[OK] Reporte detallado guardado en: {reporte_detallado_path}")
print("\n" + "=" * 80)

