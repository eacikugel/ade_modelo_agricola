"""
Script para encontrar el tamaño máximo de buffer que se puede descargar
con getDownloadURL() (límite ~50MB)
"""

import ee
import requests
from pathlib import Path
from tqdm import tqdm
import datetime

# Configuración
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw" / "test_buffer"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Coordenadas de Tres Arroyos
TRES_ARROYOS_LON = -60.2793
TRES_ARROYOS_LAT = -38.3731

# Inicializar Google Earth Engine
try:
    ee.Initialize()
    print("Google Earth Engine inicializado correctamente\n")
except Exception as e:
    print(f"Error al inicializar GEE: {e}")
    raise SystemExit(1)

def calcular_ndvi(imagen):
    """Calcula el NDVI"""
    ndvi = imagen.normalizedDifference(['B8', 'B4']).rename('NDVI')
    return ndvi

def probar_descarga(buffer_size, fecha_prueba):
    """Intenta descargar con un tamaño de buffer específico"""
    try:
        AOI = ee.Geometry.Point([TRES_ARROYOS_LON, TRES_ARROYOS_LAT]).buffer(buffer_size)
        
        # Buscar imagen
        fecha_inicio_ee = ee.Date(str(fecha_prueba))
        fecha_fin_ee = fecha_inicio_ee.advance(15, 'day')
        
        coleccion = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                     .filterDate(fecha_inicio_ee, fecha_fin_ee)
                     .filterBounds(AOI)
                     .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
                     .sort('CLOUDY_PIXEL_PERCENTAGE'))
        
        count = coleccion.size().getInfo()
        if count == 0:
            return None, "No hay imagenes disponibles"
        
        imagen = coleccion.first()
        ndvi = calcular_ndvi(imagen)
        
        # Intentar obtener URL
        url = ndvi.getDownloadURL({
            'scale': 10,
            'crs': 'EPSG:4326',
            'region': AOI,
            'format': 'GEO_TIFF'
        })
        
        # Intentar descargar (solo los primeros bytes para ver el tamaño)
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        
        # Obtener tamaño del archivo desde headers
        total_size = int(r.headers.get('content-length', 0))
        
        if total_size == 0:
            # Si no hay content-length, descargar un poco para estimar
            chunk = next(r.iter_content(chunk_size=1024), None)
            if chunk:
                # Estimación aproximada basada en el primer chunk
                r.close()
                return None, "No se pudo determinar el tamano"
        
        # Cerrar la conexión sin descargar todo
        r.close()
        
        return total_size, None
        
    except Exception as e:
        error_msg = str(e)
        if "must be less than or equal to 50331648 bytes" in error_msg:
            return None, "LIMITE_EXCEDIDO"
        else:
            return None, f"Error: {error_msg}"

# Probar con diferentes tamaños de buffer
print("="*60)
print("PRUEBA DE TAMANOS DE BUFFER MAXIMOS")
print("="*60)
print("Buscando el tamano maximo que se puede descargar...\n")

fecha_prueba = datetime.date(2023, 6, 1)

# Tamaños a probar (en metros) - probando más cerca del límite
tamanos_km = [5, 7, 10, 12, 13, 14, 15]
tamanos_metros = [k * 1000 for k in tamanos_km]

resultados = []
ultimo_exitoso = None

for buffer_km, buffer_m in zip(tamanos_km, tamanos_metros):
    print(f"Probando buffer de {buffer_km}km ({buffer_m}m)...", end=" ")
    
    tamano_archivo, error = probar_descarga(buffer_m, fecha_prueba)
    
    if error == "LIMITE_EXCEDIDO":
        print(f"LIMITE EXCEDIDO (~50MB)")
        print(f"\n{'='*60}")
        print(f"RESULTADO: El tamano maximo es {ultimo_exitoso[0]}km")
        print(f"Tamano del archivo: {ultimo_exitoso[1] / (1024*1024):.2f} MB")
        print(f"{'='*60}")
        break
    elif error:
        print(f"ERROR: {error}")
        if ultimo_exitoso:
            print(f"\nUltimo tamano exitoso: {ultimo_exitoso[0]}km ({ultimo_exitoso[1] / (1024*1024):.2f} MB)")
        break
    else:
        tamano_mb = tamano_archivo / (1024*1024)
        print(f"OK - {tamano_mb:.2f} MB")
        ultimo_exitoso = (buffer_km, tamano_archivo)
        resultados.append((buffer_km, tamano_archivo))

if not resultados:
    print("\nNo se pudieron descargar imagenes para ninguna prueba")
elif not any(r[1] is None for r in resultados if len(resultados) > 0):
    print(f"\n{'='*60}")
    print(f"RESULTADO: Todos los tamanos probados funcionaron")
    print(f"Tamano maximo probado: {resultados[-1][0]}km ({resultados[-1][1] / (1024*1024):.2f} MB)")
    print(f"Puedes probar tamanos mayores si lo necesitas")
    print(f"{'='*60}")

