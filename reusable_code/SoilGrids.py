import json
import requests
import pandas as pd
import numpy as np

def horizontalizar_data(df, lat, lon):
  '''
  Devuelve los resultados de SoilGrids procesados
  '''
  # Lista para recolectar los nuevos valores
  new_data = {}
  
  for _, row in df.iterrows():
      var = row['variable']
      depth = row['depth']
      mean_col = f"{var}_{depth}_mean"
      uncertainty_col = f"{var}_{depth}_uncertainty"
      new_data[mean_col] = row['mean']
  
  # Convertimos el diccionario en un DataFrame de una sola fila
  result = pd.DataFrame([new_data])
  result['latitud'] = lat
  result['longitud'] = lon
  return result

def get_soilgrids_data(lat, lon):
  '''
  Devuelve un Data Frame con las variables de la composición del suelo estimados por SoilGrids para la coordenada 
  específicada.
  '''
  url = "https://rest.isric.org/soilgrids/v2.0/properties/query"
  
  params = {
      "lat": lat,
      "lon": lon,
      "property": ["bdod", "phh2o", "clay", "soc", "ocd", "ocs"],
      "depth": ["0-5cm", "5-15cm", "15-30cm","0-30cm"],  # corregido el espacio
      "value": ["mean", "uncertainty"]
  }
  
  response = requests.get(url, params=params)
  
  if response.status_code == 200:
      try:
          data = response.json()
          rows = []
  
          for layer in data['properties']['layers']:
              variable = layer['name']
              for depth in layer['depths']:
                  depth_label = depth['label']
                  values = depth['values']
                  mean = values.get('mean')
                  uncertainty = values.get('uncertainty')
  
                  row = {
                      'variable': variable,
                      'depth': depth_label,
                      'mean': mean,
                      'uncertainty': uncertainty
                  }
                  rows.append(row)
  
          return horizontalizar_data(pd.DataFrame(rows), lat, lon)
      except Exception as e:
          print(f"⚠️ Error procesando JSON: {e}")
          return None
  else:
      return pd.DataFrame([{
      'bdod_0-5cm_mean': None,
      'bdod_5-15cm_mean': None,
      'bdod_15-30cm_mean': None,
      'clay_0-5cm_mean': None,
      'clay_5-15cm_mean': None,
      'clay_15-30cm_mean': None,
      'ocd_0-5cm_mean': None,
      'ocd_5-15cm_mean': None,
      'ocd_15-30cm_mean': None,
      'ocs_0-30cm_mean': None,
      'phh2o_0-5cm_mean': None,
      'phh2o_5-15cm_mean': None,
      'phh2o_15-30cm_mean': None,
      'soc_0-5cm_mean': None,
      'soc_5-15cm_mean': None,
      'soc_15-30cm_mean': None,
      'latitud': lat,
      'longitud': lon}])
