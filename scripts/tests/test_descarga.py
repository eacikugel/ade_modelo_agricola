"""
Script de prueba para verificar que la descarga de imágenes desde GEE funcione correctamente
"""

import ee
import requests
from pathlib import Path
from tqdm import tqdm
import datetime

# Configuración
OUTPUT_DIR = Path("../data/raw/sentinel_23_24")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Coordenadas de Tres Arroyos
TRES_ARROYOS_LON = -60.2793
TRES_ARROYOS_LAT = -38.3731

# Inicializar Google Earth Engine
def inicializar_gee():
    try:
        ee.Initialize()
        print("Google Earth Engine inicializado correctamente")
        return True
    except Exception as e:
        print(f"Error al inicializar GEE: {e}")
        return False

if not inicializar_gee():
    raise SystemExit("No se pudo inicializar Google Earth Engine")

# Probar con diferentes tamaños de área
tamanos_buffer = [5000, 7000, 10000]  # 5km, 7km, 10km

def calcular_ndvi(imagen):
    """Calcula el NDVI"""
    ndvi = imagen.normalizedDifference(['B8', 'B4']).rename('NDVI')
    return ndvi

def descargar_con_getDownloadURL(imagen, nombre_archivo, escala=10):
    """Intenta descargar usando getDownloadURL"""
    try:
        # Obtener URL de descarga
        url = imagen.getDownloadURL({
            'scale': escala,
            'crs': 'EPSG:4326',
            'region': AOI,
            'format': 'GEO_TIFF'
        })
        
        print(f"URL obtenida, descargando...")
        
        # Descargar el archivo
        r = requests.get(url, stream=True, timeout=300)
        r.raise_for_status()
        
        ruta_completa = OUTPUT_DIR / nombre_archivo
        
        # Guardar con barra de progreso
        total_size = int(r.headers.get('content-length', 0))
        with open(ruta_completa, 'wb') as f:
            if total_size == 0:
                f.write(r.content)
            else:
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=nombre_archivo) as pbar:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
        
        print(f"Descargado exitosamente: {nombre_archivo}")
        print(f"  Tamaño del archivo: {ruta_completa.stat().st_size / (1024*1024):.2f} MB")
        return True
        
    except Exception as e:
        error_msg = str(e)
        if "must be less than or equal to 50331648 bytes" in error_msg:
            print(f"Area demasiado grande (limite ~50MB): {e}")
            return False
        else:
            print(f"Error: {e}")
            return False

# Probar con una fecha específica (junio 2023)
fecha_prueba = datetime.date(2023, 6, 1)
fecha_inicio_ee = ee.Date(str(fecha_prueba))
fecha_fin_ee = fecha_inicio_ee.advance(15, 'day')

print("\n" + "="*60)
print("PRUEBA DE DESCARGA - TRES ARROYOS")
print("="*60)
print(f"Fecha de prueba: {fecha_prueba}")
print(f"Buscando imágenes en primeros 15 días del mes\n")

# Buscar imagen
coleccion = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
             .filterDate(fecha_inicio_ee, fecha_fin_ee)
             .filterBounds(ee.Geometry.Point([TRES_ARROYOS_LON, TRES_ARROYOS_LAT]).buffer(10000))
             .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
             .sort('CLOUDY_PIXEL_PERCENTAGE'))

count = coleccion.size().getInfo()
if count == 0:
    print("No se encontraron imagenes para la fecha de prueba")
    raise SystemExit(1)

print(f"Se encontraron {count} imagen(es)")
imagen = coleccion.first()
ndvi = calcular_ndvi(imagen)

# Probar con diferentes tamaños de buffer
print("\n" + "-"*60)
print("Probando diferentes tamaños de área...")
print("-"*60)

exito = False
for buffer_size in tamanos_buffer:
    print(f"\nProbando con buffer de {buffer_size/1000:.0f}km...")
    AOI = ee.Geometry.Point([TRES_ARROYOS_LON, TRES_ARROYOS_LAT]).buffer(buffer_size)
    
    nombre_archivo = f"TEST_NDVI_{fecha_prueba.strftime('%Y-%m')}_{buffer_size}m.tif"
    
    if descargar_con_getDownloadURL(ndvi, nombre_archivo, escala=10):
        print(f"\nEXITO con buffer de {buffer_size/1000:.0f}km")
        exito = True
        break
    else:
        print(f"Fallo con buffer de {buffer_size/1000:.0f}km, probando tamano menor...")

if exito:
    print("\n" + "="*60)
    print("PRUEBA EXITOSA")
    print("="*60)
    print(f"El tamano de buffer que funciona es: {buffer_size/1000:.0f}km")
    print("Puedes usar este tamano en el script principal")
else:
    print("\n" + "="*60)
    print("PRUEBA FALLIDA")
    print("="*60)
    print("Ningun tamano de buffer funciono con getDownloadURL")
    print("Sera necesario usar Export.image.toDrive()")

