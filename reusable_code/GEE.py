import ee
import json
import streamlit as st
from datetime import datetime
from google.oauth2 import service_account

# Leer el secreto desde st.secrets
def get_credentials():
  '''
  Obtiene las credenciales de la cuenta de servicio de Google Earth Engine
  '''
  service_account_info = json.loads(st.secrets["google_service_account"]["json"])
  
  credentials = service_account.Credentials.from_service_account_info(
      service_account_info,
      scopes=["https://www.googleapis.com/auth/earthengine"]
  )
  return credentials

ee.Initialize(get_credentials())

def get_slope(lon, lat, scale=10):
  """
  Devuelve la pendiente (grados) en lon, lat vía reduceRegion.
  """
  dem   = ee.Image('USGS/3DEP/10m')
  terrain = ee.Terrain.slope(dem)
  pt = ee.Geometry.Point([lon, lat])
  try:
      info = terrain.reduceRegion(
          reducer   = ee.Reducer.first(),
          geometry  = pt.buffer(10),  # pequeño buffer
          scale     = scale,
          maxPixels = 1e13
      ).getInfo()
      slope = info.get('slope')
      if slope is None:
          print(f"⚠️ No se encontró pendiente en ({lon}, {lat})")
      slope = 0
  except Exception as e:
      print(f"❌ Error al obtener pendiente: {e}")
      slope = 0
  return slope

def scale_l5_factors(image):
  '''
  Aplica el escalado a las imagenes de Landsat 5
  '''
  optical_bands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
  thermal_bands = image.select('ST_B6').multiply(0.00341802).add(149.0)
  return image.addBands(optical_bands, None, True).addBands(
      thermal_bands, None, True
  )

def mask_l5_clouds(image):
  
  """Scales Landsat 5 image collection.
  
  Args:
      image (ee.Image): A Landsat 5 image.
  
  Returns:
      ee.Image: A scaled Landsat 5 image.
  """
  try:
    qa = image.select('QA_PIXEL')
  except Exception as e:
    return scale_l5_factors(image)
    
  # Bits a considerar (en este caso: 3 = cloud, 4 = cloud shadow)
  cloud = 1 << 3
  shadow = 1 << 4
  
  # Crear máscara: nubes y sombra deben estar apagadas (bit = 0)
  mask = qa.bitwiseAnd(cloud).eq(0).And(
          qa.bitwiseAnd(shadow).eq(0))
  
  return scale_l5_factors(image.updateMask(mask))

def mask_s2_clouds(image):
  """Masks clouds in a Sentinel-2 image using the QA band.
  
  Args:
      image (ee.Image): A Sentinel-2 image.
  
  Returns:
      ee.Image: A cloud-masked Sentinel-2 image.
  """
  try:
    qa = image.select('QA60')
  except Exception as e:
    return image.divide(10000)
  
  # Bits 10 and 11 are clouds and cirrus, respectively.
  cloud_bit_mask = 1 << 10
  cirrus_bit_mask = 1 << 11
  
  # Both flags should be set to zero, indicating clear conditions.
  mask = (
      qa.bitwiseAnd(cloud_bit_mask)
      .eq(0)
      .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    )
  
  return image.updateMask(mask).divide(10000)

def get_image(lat, lon, fecha=None):
  '''
  Devuelve la mediana de una colección de imagenes satelitales para las coordenadas [lat, lon] en una fecha específica.
  Si la fecha no se define, se utiliza por default la fecha actual. Si la fecha es posterior a 2015, se utiliza el servicio de Sentinel 2, en el caso
  contrario se emplea Landsat 5. 
  '''
  
  if fecha is None:
    fecha = ee.Date(datetime.now())
    h = -30
  else:
    fecha = ee.Date(fecha)
    h = -60
  
  if fecha.get('year').getInfo() < 2015:
    service = "LANDSAT/LT05/C02/T1_L2"
    maper = mask_l5_clouds
    cloud_coverage_property = "CLOUD_COVER"
  else:
    service = "COPERNICUS/S2_SR_HARMONIZED"
    maper = mask_s2_clouds
    cloud_coverage_property = "CLOUDY_PIXEL_PERCENTAGE"
  
  collection = ee.ImageCollection(service) \
          .filterBounds(ee.Geometry.Point(lon, lat).buffer(10000)) \
          .filterDate(fecha.advance(h, 'day'), fecha) \
          .filter(ee.Filter.lt(cloud_coverage_property, 20)) \
          .map(maper)
  
  image = collection.median()
  
  return image, service

def get_gee_data(lat, lon, fecha=None):
  '''
  Dado una coordenada geografíca, devuelve las siguientes imagenes procesadas de get_image:
  NDVI: Índice de vegetacion de diferencia normalizada
  NDWI: Índice de agua de diferencia normalizada
  NDMI: Índice de humedad de diferencia normalizada
  NBI: Índice de calcinacion normalizada
  '''
  
  image, service = get_image(lat, lon, fecha)
  if service == "LANDSAT/LT05/C02/T1_L2":
    NIR = image.select('SR_B4')
    SWIR1 = image.select('SR_B5')
    SWIR2 = image.select('SR_B7')
    Green = image.select('SR_B2')
    Red = image.select('SR_B3')
  else:
    NIR = image.select('B8')
    SWIR1 = image.select('B11')
    SWIR2 = image.select('B12')
    Red = image.select('B4')
    Green = image.select('B3')
  
  NDVI = NIR.subtract(Red).divide(NIR.add(Red)).rename('NDVI')
  NDWI = Green.subtract(NIR).divide(Green.add(NIR)).rename('NDWI')
  NDMI = NIR.subtract(SWIR1).divide(NIR.add(SWIR1)).rename('NDMI')
  NBI = NIR.subtract(SWIR2).divide(NIR.add(SWIR2)).rename('NBI')
  return image, NDVI, NDWI, NDMI, NBI

def get_stats(lat, lon, image, m=5000):
  '''
  Devuelve el punto mínimo y máximo de una imagen según el buffer considerado. Útil para una mejor visualización
  '''
  punto = ee.Geometry.Point([lon, lat])
  buffer = punto.buffer(m)
  
  stats = image.reduceRegion(
      reducer=ee.Reducer.minMax(), # funcion de reduccion
      geometry=buffer,  # un polígono o punto
      scale=30,
      maxPixels=1e9
  ).getInfo()
  
  return stats
