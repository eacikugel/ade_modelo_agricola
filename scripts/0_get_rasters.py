"""
Script para descargar imágenes satelitales de Google Earth Engine
- 12 imágenes NDVI mensuales (junio 2023 - junio 2024, día 1 de cada mes)
- 1 imagen Sentinel-2 completa (13 bandas) del 1 de enero de 2024
Ubicación: Tres Arroyos, Buenos Aires, Argentina
"""

import ee
import os
import datetime
from pathlib import Path
import requests
from tqdm import tqdm
import time

# Configuración
# Ruta relativa a la raíz del proyecto
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw" / "sentinel_23_24"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Coordenadas de Tres Arroyos, Buenos Aires, Argentina
TRES_ARROYOS_LON = -60.2793
TRES_ARROYOS_LAT = -38.3731

# Inicializar Google Earth Engine
# Nota: Si tienes un proyecto de Google Cloud, puedes especificarlo aquí
# Ejemplo: ee.Initialize(project='tu-proyecto-gcp')
# O configúralo con: earthengine set_project TU_PROYECTO

def inicializar_gee():
    """Inicializa Google Earth Engine con manejo de errores"""
    # Intentar inicializar sin proyecto primero
    try:
        ee.Initialize()
        print("Google Earth Engine inicializado correctamente")
        return True
    except Exception as e:
        error_msg = str(e)
        if "no project found" in error_msg.lower():
            print("="*60)
            print("ERROR: No se encontró un proyecto de Google Cloud")
            print("="*60)
            print("\nGoogle Earth Engine requiere un proyecto de Google Cloud.")
            print("\nPasos para solucionarlo:")
            print("1. Ve a https://console.cloud.google.com/")
            print("2. Crea un nuevo proyecto (o usa uno existente)")
            print("3. Anota el ID del proyecto (ejemplo: 'mi-proyecto-123456')")
            print("4. Ejecuta: earthengine set_project TU_PROYECTO_ID")
            print("\nO modifica este script y agrega tu proyecto en la línea:")
            print("   ee.Initialize(project='tu-proyecto-id')")
            print("="*60)
        else:
            print(f"Error al inicializar GEE: {e}")
        return False

if not inicializar_gee():
    print("\nEl script no puede continuar sin un proyecto configurado.")
    print("Por favor, configura un proyecto y vuelve a ejecutar el script.")
    raise SystemExit(1)

# Área de interés: buffer de 14 km alrededor del punto central
# (Probado: 14km es el máximo que funciona con getDownloadURL, archivos ~26 MB, límite ~50 MB)
# Convertir a bounding box fijo para asegurar recortes consistentes
buffer_metros = 14000
punto_central = ee.Geometry.Point([TRES_ARROYOS_LON, TRES_ARROYOS_LAT])
AOI_buffer = punto_central.buffer(buffer_metros)

# Obtener el bounding box del buffer y convertirlo a un rectángulo fijo
# Esto asegura que todas las imágenes tengan exactamente la misma extensión
bbox = AOI_buffer.bounds()
AOI = bbox  # Usar el bounding box en lugar del buffer circular

# Proyección fija para todas las descargas (UTM Zone 21S para Argentina)
# Esto asegura que todas las imágenes tengan la misma proyección y transformación
PROYECCION_FIJA = 'EPSG:32721'  # UTM Zone 21S (cubre Tres Arroyos)


def calcular_ndvi(imagen):
    """Calcula el NDVI a partir de las bandas NIR (B8) y Red (B4) de Sentinel-2"""
    ndvi = imagen.normalizedDifference(['B8', 'B4']).rename('NDVI')
    return ndvi


def descargar_imagen_gee(imagen, nombre_archivo, escala=10, usar_export=False):
    """
    Descarga una imagen de GEE.
    
    Si usar_export=True o el archivo es >48MB, usa Export.image.toDrive()
    Si usar_export=False, intenta getDownloadURL() primero (más rápido para archivos pequeños)
    """
    try:
        # Verificar que la imagen existe
        try:
            imagen.getInfo()
        except Exception as e:
            raise Exception(f"La imagen no existe o esta vacia: {e}")
        
        # Si se especifica usar export o si queremos archivos grandes, usar Export
        if usar_export:
            return descargar_con_export(imagen, nombre_archivo, escala)
        
        # Intentar primero con getDownloadURL (más rápido para archivos pequeños)
        try:
            url = imagen.getDownloadURL({
                'scale': escala,
                'crs': PROYECCION_FIJA,  # Usar proyección fija en lugar de EPSG:4326
                'region': AOI,
                'format': 'GEO_TIFF'
            })
            
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
            
            print(f"Descargado: {nombre_archivo} ({ruta_completa.stat().st_size / (1024*1024):.2f} MB)")
            return ruta_completa
            
        except Exception as e:
            error_msg = str(e)
            if "must be less than or equal to 50331648 bytes" in error_msg:
                print(f"Archivo muy grande para getDownloadURL, usando Export...")
                return descargar_con_export(imagen, nombre_archivo, escala)
            else:
                raise
        
    except Exception as e:
        print(f"Error al descargar {nombre_archivo}: {e}")
        return None


def descargar_con_export(imagen, nombre_archivo, escala=10):
    """
    Descarga usando Export.image.toDrive() para archivos grandes
    """
    try:
        nombre_tarea = nombre_archivo.replace('.tif', '').replace('-', '_')[:100]
        
        # Exportar a Google Drive con proyección fija
        tarea = ee.batch.Export.image.toDrive(
            image=imagen,
            description=nombre_tarea,
            folder='GEE_Exports',
            fileNamePrefix=nombre_tarea,
            scale=escala,
            region=AOI,
            crs=PROYECCION_FIJA,  # Especificar proyección fija
            fileFormat='GeoTIFF',
            maxPixels=1e9
        )
        
        tarea.start()
        print(f"Tarea iniciada: {nombre_tarea}")
        print("Esperando a que complete la exportacion (esto puede tardar varios minutos)...")
        
        # Esperar a que complete
        estado_anterior = None
        while tarea.active():
            estado = tarea.state
            if estado != estado_anterior:
                print(f"Estado: {estado}")
                estado_anterior = estado
            time.sleep(10)  # Verificar cada 10 segundos
        
        estado_final = tarea.state
        if estado_final == 'COMPLETED':
            print(f"Exportacion completada: {nombre_tarea}")
            print("NOTA: El archivo se exporto a Google Drive en la carpeta 'GEE_Exports'")
            print("Debes descargarlo manualmente desde Drive o usar la API de Google Drive")
            print("Para descargar automaticamente, necesitas configurar la API de Google Drive")
            return True
        elif estado_final == 'FAILED':
            error = tarea.status().get('error_message', 'Error desconocido')
            raise Exception(f"La tarea fallo: {error}")
        else:
            raise Exception(f"La tarea termino con estado: {estado_final}")
        
    except Exception as e:
        print(f"Error en exportacion: {e}")
        return None


def obtener_imagen_sentinel2(fecha_inicio, fecha_fin, calcular_ndvi_band=False):
    """
    Obtiene una imagen Sentinel-2 para un rango de fechas
    Busca en un rango más amplio si no encuentra imágenes el día exacto
    """
    # Buscar imágenes en el rango de fechas
    coleccion = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                 .filterDate(fecha_inicio, fecha_fin)
                 .filterBounds(AOI)
                 .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))  # Máximo 30% de nubes
                 .sort('CLOUDY_PIXEL_PERCENTAGE'))
    
    # Verificar que hay imágenes
    count = coleccion.size().getInfo()
    if count == 0:
        fecha_inicio_str = fecha_inicio.format('YYYY-MM-dd').getInfo()
        fecha_fin_str = fecha_fin.format('YYYY-MM-dd').getInfo()
        raise Exception(f"No se encontraron imágenes en el rango {fecha_inicio_str} - {fecha_fin_str}")
    
    # Obtener la imagen con menos nubes
    imagen = coleccion.first()
    
    if calcular_ndvi_band:
        # Calcular NDVI y retornar solo esa banda
        ndvi = calcular_ndvi(imagen)
        return ndvi
    else:
        # Retornar todas las bandas (13 bandas de Sentinel-2)
        return imagen.select([
            'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B11', 'B12', 'QA60'
        ])


def main():
    print("\n" + "="*60)
    print("DESCARGA DE IMÁGENES SATELITALES - TRES ARROYOS")
    print("="*60 + "\n")
    
    # 1. Descargar 12 imágenes NDVI mensuales (junio 2023 - junio 2024)
    print("Descargando imágenes NDVI mensuales...")
    print("-" * 60)
    
    meses = []
    fecha_actual = datetime.date(2023, 6, 1)
    fecha_fin = datetime.date(2024, 6, 1)
    
    while fecha_actual <= fecha_fin:
        meses.append(fecha_actual)
        # Avanzar al primer día del siguiente mes
        if fecha_actual.month == 12:
            fecha_actual = datetime.date(fecha_actual.year + 1, 1, 1)
        else:
            fecha_actual = datetime.date(fecha_actual.year, fecha_actual.month + 1, 1)
    
    print(f"Total de meses a descargar: {len(meses)}")
    
    for fecha in meses:
        fecha_str = fecha.strftime("%Y-%m-%d")
        # Buscar imágenes en todo el mes para asegurar encontrar al menos una
        fecha_inicio_ee = ee.Date(fecha_str)
        # Calcular el último día del mes
        if fecha.month == 12:
            ultimo_dia_mes = datetime.date(fecha.year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            ultimo_dia_mes = datetime.date(fecha.year, fecha.month + 1, 1) - datetime.timedelta(days=1)
        
        fecha_fin_ee = ee.Date(str(ultimo_dia_mes)).advance(1, 'day')  # Incluir el último día
        
        print(f"\nProcesando: {fecha_str} (buscando en todo el mes)")
        
        try:
            imagen_ndvi = obtener_imagen_sentinel2(fecha_inicio_ee, fecha_fin_ee, calcular_ndvi_band=True)
            nombre_archivo = f"NDVI_{fecha.strftime('%Y-%m')}.tif"
            # usar_export=False para intentar getDownloadURL primero (más rápido para archivos pequeños)
            descargar_imagen_gee(imagen_ndvi, nombre_archivo, escala=10, usar_export=False)
        except Exception as e:
            print(f"No se pudo descargar imagen para {fecha_str}: {e}")
            continue
    
    # 2. Descargar imagen Sentinel-2 completa del 1 de enero de 2024
    print("\n" + "="*60)
    print("Descargando imagen Sentinel-2 completa (13 bandas)...")
    print("-" * 60)
    
    fecha_enero = datetime.date(2024, 1, 1)
    # Buscar en todo el mes de enero
    fecha_inicio_ee = ee.Date(str(fecha_enero))
    # Último día de enero
    ultimo_dia_enero = datetime.date(2024, 2, 1) - datetime.timedelta(days=1)
    fecha_fin_ee = ee.Date(str(ultimo_dia_enero)).advance(1, 'day')
    
    print(f"Fecha: {fecha_enero} (buscando en todo el mes de enero)")
    
    try:
        imagen_completa = obtener_imagen_sentinel2(fecha_inicio_ee, fecha_fin_ee, calcular_ndvi_band=False)
        nombre_archivo = f"Sentinel2_13bandas_{fecha_enero.strftime('%Y-%m-%d')}.tif"
        # Para Sentinel-2 completo (13 bandas), usar Export ya que será más grande
        descargar_imagen_gee(imagen_completa, nombre_archivo, escala=10, usar_export=True)
    except Exception as e:
        print(f"Error al descargar imagen completa: {e}")
    
    print("\n" + "="*60)
    print("Proceso completado")
    print(f"Archivos guardados en: {OUTPUT_DIR.absolute()}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

