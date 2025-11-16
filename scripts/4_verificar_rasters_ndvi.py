"""
Script para verificar que todos los rasters de NDVI tengan las mismas propiedades
(CRS, transform, dimensiones, nodata) antes de combinarlos.
"""

import os
import glob
import rasterio
from rasterio.transform import Affine
import pandas as pd

# Paths relativos desde el script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")

# Directorio con archivos NDVI
NDVI_DIR = os.path.join(DATA_DIR, "sentinel_23_24")

print("=" * 80)
print("VERIFICACION DE PROPIEDADES DE RASTERS NDVI")
print("=" * 80)

# Buscar todos los archivos NDVI
ndvi_files = sorted(glob.glob(os.path.join(NDVI_DIR, "NDVI_*.tif")))

print(f"\nArchivos encontrados en sentinel_23_24: {len(ndvi_files)}")

# Función para obtener propiedades de un raster
def obtener_propiedades(raster_path, banda_idx=1):
    """Obtiene las propiedades clave de un raster."""
    try:
        with rasterio.open(raster_path) as src:
            # Si el archivo tiene múltiples bandas, usar la banda especificada
            if src.count > 1:
                # Intentar encontrar la banda NDVI por nombre
                descripciones = src.descriptions
                if descripciones:
                    try:
                        banda_idx = [i+1 for i, desc in enumerate(descripciones) if desc and 'NDVI' in desc.upper()][0]
                    except IndexError:
                        banda_idx = 1  # Usar primera banda si no se encuentra NDVI
                
            props = {
                'archivo': os.path.basename(raster_path),
                'ruta': raster_path,
                'banda_usada': banda_idx,
                'crs': str(src.crs),
                'width': src.width,
                'height': src.height,
                'transform': src.transform,
                'nodata': src.nodata,
                'dtype': str(src.dtypes[banda_idx-1]),
                'count': src.count,
                'bounds': src.bounds,
                'res': (src.transform[0], abs(src.transform[4])),  # pixel width, pixel height
            }
            return props, None
    except Exception as e:
        return None, str(e)

# Verificar todos los archivos
print("\n" + "=" * 80)
print("VERIFICANDO PROPIEDADES DE CADA RASTER")
print("=" * 80)

todas_propiedades = []
errores = []

# Procesar archivos de sentinel_23_24
for archivo in ndvi_files:
    props, error = obtener_propiedades(archivo, banda_idx=1)
    if props:
        todas_propiedades.append(props)
        print(f"\n[OK] {props['archivo']}")
        print(f"     CRS: {props['crs']}, Size: {props['width']}x{props['height']}, "
              f"Res: {props['res'][0]:.2f}x{props['res'][1]:.2f}")
    else:
        errores.append((archivo, error))
        print(f"\n[ERROR] {os.path.basename(archivo)}: {error}")

if not todas_propiedades:
    print("\n[ERROR] No se pudieron leer propiedades de ningún raster.")
    exit(1)

# Crear DataFrame para comparación
print("\n" + "=" * 80)
print("COMPARACION DE PROPIEDADES")
print("=" * 80)

df = pd.DataFrame(todas_propiedades)

# Verificar consistencia
print("\nPropiedades únicas por columna:")
print("-" * 80)
for col in ['crs', 'width', 'height', 'nodata', 'dtype']:
    valores_unicos = df[col].unique()
    print(f"{col:15s}: {len(valores_unicos)} valor(es) único(s)")
    if len(valores_unicos) > 1:
        print(f"  {valores_unicos}")

# Verificar transform (más complejo)
print("\nVerificando transformaciones (primeros valores):")
transforms_unicos = df['transform'].unique()
print(f"  Transformaciones únicas: {len(transforms_unicos)}")
if len(transforms_unicos) > 1:
    print("  [ADVERTENCIA] Los rasters tienen transformaciones diferentes")
    for i, t in enumerate(transforms_unicos[:3]):
        print(f"    Transform {i+1}: {t}")

# Verificar bounds
print("\nVerificando bounds (extensión geográfica):")
bounds_unicos = df['bounds'].unique()
print(f"  Bounds únicos: {len(bounds_unicos)}")
if len(bounds_unicos) > 1:
    print("  [ADVERTENCIA] Los rasters tienen bounds diferentes")
    # Mostrar diferencias
    bounds_df = pd.DataFrame([list(b) for b in df['bounds']], 
                             columns=['left', 'bottom', 'right', 'top'])
    print("\n  Rango de bounds:")
    print(f"    Left:   {bounds_df['left'].min():.2f} a {bounds_df['left'].max():.2f}")
    print(f"    Bottom: {bounds_df['bottom'].min():.2f} a {bounds_df['bottom'].max():.2f}")
    print(f"    Right:  {bounds_df['right'].min():.2f} a {bounds_df['right'].max():.2f}")
    print(f"    Top:    {bounds_df['top'].min():.2f} a {bounds_df['top'].max():.2f}")

# Resumen final
print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)

todos_iguales = (
    len(df['crs'].unique()) == 1 and
    len(df['width'].unique()) == 1 and
    len(df['height'].unique()) == 1 and
    len(transforms_unicos) == 1
)

if todos_iguales:
    print("\n[OK] Todos los rasters tienen las mismas propiedades básicas:")
    print(f"     CRS: {df['crs'].iloc[0]}")
    print(f"     Dimensiones: {df['width'].iloc[0]}x{df['height'].iloc[0]}")
    print(f"     Resolución: {df['res'].iloc[0][0]:.2f} x {df['res'].iloc[0][1]:.2f}")
    print(f"     Nodata: {df['nodata'].iloc[0]}")
    print(f"     Dtype: {df['dtype'].iloc[0]}")
    print("\n[OK] Los rasters pueden ser combinados directamente.")
else:
    print("\n[ADVERTENCIA] Los rasters NO tienen todas las mismas propiedades.")
    print("     Será necesario reproyectar o recortar algunos rasters antes de combinarlos.")
    
    # Detectar qué propiedades difieren
    if len(df['crs'].unique()) > 1:
        print("\n  - CRS diferentes: se requiere reproyección")
    if len(df['width'].unique()) > 1 or len(df['height'].unique()) > 1:
        print("  - Dimensiones diferentes: se requiere recorte o reproyección")
    if len(transforms_unicos) > 1:
        print("  - Transformaciones diferentes: se requiere reproyección")

# Guardar reporte
output_dir = os.path.join(PROJECT_ROOT, "data", "proc")
os.makedirs(output_dir, exist_ok=True)

reporte_path = os.path.join(output_dir, "4_reporte_verificacion_ndvi.csv")
df_export = df[['archivo', 'crs', 'width', 'height', 'nodata', 'dtype', 'res']].copy()
df_export['res_width'] = df_export['res'].apply(lambda x: x[0])
df_export['res_height'] = df_export['res'].apply(lambda x: x[1])
df_export = df_export.drop('res', axis=1)
df_export.to_csv(reporte_path, index=False)

print(f"\n[OK] Reporte guardado en: {reporte_path}")

