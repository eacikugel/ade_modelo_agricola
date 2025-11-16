"""
Script para comparar los parametros de los rasters recorte (invierno y verano).
Estos rasters deberian tener los mismos parametros espaciales.
"""

import os
import rasterio
import pandas as pd

# Paths relativos desde el script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PROC_DIR = os.path.join(PROJECT_ROOT, "data", "proc")

# Archivos a comparar
RECORTE_INVIERNO_PATH = os.path.join(PROC_DIR, "recorte_invierno_GTiff.tif")
RECORTE_VERANO_PATH = os.path.join(PROC_DIR, "recorte_verano_GTiff.tif")

print("=" * 80)
print("COMPARACION DE PARAMETROS DE RASTERS RECORTE")
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
if not os.path.exists(RECORTE_INVIERNO_PATH):
    print(f"\n[ERROR] No se encuentra el archivo: {RECORTE_INVIERNO_PATH}")
    exit(1)

if not os.path.exists(RECORTE_VERANO_PATH):
    print(f"\n[ERROR] No se encuentra el archivo: {RECORTE_VERANO_PATH}")
    exit(1)

# Obtener propiedades de ambos rasters
print("\n" + "=" * 80)
print("OBTENIENDO PROPIEDADES DE LOS RASTERS")
print("=" * 80)

props_inv, error_inv = obtener_propiedades(RECORTE_INVIERNO_PATH, "recorte_invierno_GTiff.tif")
if error_inv:
    print(f"\n[ERROR] No se pudo leer recorte_invierno_GTiff.tif: {error_inv}")
    exit(1)

props_ver, error_ver = obtener_propiedades(RECORTE_VERANO_PATH, "recorte_verano_GTiff.tif")
if error_ver:
    print(f"\n[ERROR] No se pudo leer recorte_verano_GTiff.tif: {error_ver}")
    exit(1)

# Mostrar propiedades de cada raster
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

# Comparar propiedades
print("\n" + "=" * 80)
print("COMPARACION DE PROPIEDADES")
print("=" * 80)

comparaciones = {
    'CRS': (props_inv['crs'], props_ver['crs'], props_inv['crs'] == props_ver['crs']),
    'Width': (props_inv['width'], props_ver['width'], props_inv['width'] == props_ver['width']),
    'Height': (props_inv['height'], props_ver['height'], props_inv['height'] == props_ver['height']),
    'Resolucion Width': (props_inv['res_width'], props_ver['res_width'], 
                        abs(props_inv['res_width'] - props_ver['res_width']) < 1e-10),
    'Resolucion Height': (props_inv['res_height'], props_ver['res_height'], 
                         abs(props_inv['res_height'] - props_ver['res_height']) < 1e-10),
    'Nodata': (props_inv['nodata'], props_ver['nodata'], props_inv['nodata'] == props_ver['nodata']),
    'Dtype': (props_inv['dtype'], props_ver['dtype'], props_inv['dtype'] == props_ver['dtype']),
    'Count': (props_inv['count'], props_ver['count'], props_inv['count'] == props_ver['count']),
}

print("\nComparacion detallada:")
print("-" * 80)
print(f"{'Parametro':<25} {'Invierno':<30} {'Verano':<30} {'Coinciden':<10}")
print("-" * 80)

todas_coinciden = True
for param, (val_inv, val_ver, coincide) in comparaciones.items():
    estado = "SI" if coincide else "NO"
    if not coincide:
        todas_coinciden = False
    print(f"{param:<25} {str(val_inv):<30} {str(val_ver):<30} {estado:<10}")

# Comparar transform (mas complejo)
print("\nComparacion de Transform:")
print("-" * 80)
transform_inv = props_inv['transform']
transform_ver = props_ver['transform']
transform_coinciden = transform_inv == transform_ver
print(f"  Transform invierno: {transform_inv}")
print(f"  Transform verano:   {transform_ver}")
print(f"  Coinciden: {'SI' if transform_coinciden else 'NO'}")
if not transform_coinciden:
    todas_coinciden = False
    print("\n  Diferencias en transform:")
    for i in range(6):
        val_inv = transform_inv[i]
        val_ver = transform_ver[i]
        diff = abs(val_inv - val_ver) if isinstance(val_inv, (int, float)) else 0
        print(f"    Parametro {i}: {val_inv} vs {val_ver} (diff: {diff:.10f})")

# Comparar bounds
print("\nComparacion de Bounds:")
print("-" * 80)
bounds_inv = props_inv['bounds']
bounds_ver = props_ver['bounds']
bounds_coinciden = bounds_inv == bounds_ver
print(f"  Bounds invierno: {bounds_inv}")
print(f"  Bounds verano:   {bounds_ver}")
print(f"  Coinciden: {'SI' if bounds_coinciden else 'NO'}")
if not bounds_coinciden:
    todas_coinciden = False
    print("\n  Diferencias en bounds:")
    nombres = ['left', 'bottom', 'right', 'top']
    for i, nombre in enumerate(nombres):
        val_inv = bounds_inv[i]
        val_ver = bounds_ver[i]
        diff = abs(val_inv - val_ver)
        print(f"    {nombre}: {val_inv:.6f} vs {val_ver:.6f} (diff: {diff:.10f})")

# Resumen final
print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)

if todas_coinciden and transform_coinciden and bounds_coinciden:
    print("\n[OK] Todos los parametros coinciden entre los rasters recorte.")
    print("     Los rasters tienen parametros identicos.")
else:
    print("\n[ADVERTENCIA] Los rasters recorte NO tienen todos los parametros identicos.")
    if not todas_coinciden:
        print("     Algunas propiedades basicas difieren.")
    if not transform_coinciden:
        print("     Las transformaciones difieren.")
    if not bounds_coinciden:
        print("     Los bounds difieren.")

# Guardar reporte
print("\n" + "=" * 80)
print("GUARDANDO REPORTE")
print("=" * 80)

df = pd.DataFrame([props_inv, props_ver])
reporte_path = os.path.join(PROC_DIR, "7_reporte_comparacion_recortes.csv")
df_export = df[['archivo', 'crs', 'width', 'height', 'res_width', 'res_height', 
                'nodata', 'dtype', 'count']].copy()
df_export.to_csv(reporte_path, index=False)

print(f"\n[OK] Reporte guardado en: {reporte_path}")

# Guardar reporte detallado de comparacion
reporte_detallado_path = os.path.join(PROC_DIR, "7_reporte_comparacion_recortes_detallado.txt")
with open(reporte_detallado_path, 'w') as f:
    f.write("COMPARACION DE PARAMETROS DE RASTERS RECORTE\n")
    f.write("=" * 80 + "\n\n")
    
    f.write("PROPIEDADES DE RECORTE_INVIERNO_GTIFF.TIF\n")
    f.write("-" * 80 + "\n")
    for key, value in props_inv.items():
        if key != 'transform' and key != 'bounds':
            f.write(f"  {key}: {value}\n")
    f.write(f"  transform: {props_inv['transform']}\n")
    f.write(f"  bounds: {props_inv['bounds']}\n")
    
    f.write("\nPROPIEDADES DE RECORTE_VERANO_GTIFF.TIF\n")
    f.write("-" * 80 + "\n")
    for key, value in props_ver.items():
        if key != 'transform' and key != 'bounds':
            f.write(f"  {key}: {value}\n")
    f.write(f"  transform: {props_ver['transform']}\n")
    f.write(f"  bounds: {props_ver['bounds']}\n")
    
    f.write("\nCOMPARACION\n")
    f.write("-" * 80 + "\n")
    for param, (val_inv, val_ver, coincide) in comparaciones.items():
        estado = "SI" if coincide else "NO"
        f.write(f"{param}: {val_inv} vs {val_ver} -> {estado}\n")
    
    f.write(f"\nTransform coincide: {'SI' if transform_coinciden else 'NO'}\n")
    f.write(f"Bounds coincide: {'SI' if bounds_coinciden else 'NO'}\n")
    
    f.write("\nCONCLUSION\n")
    f.write("-" * 80 + "\n")
    if todas_coinciden and transform_coinciden and bounds_coinciden:
        f.write("Todos los parametros coinciden.\n")
    else:
        f.write("Los parametros NO coinciden completamente.\n")

print(f"[OK] Reporte detallado guardado en: {reporte_detallado_path}")
print("\n" + "=" * 80)

