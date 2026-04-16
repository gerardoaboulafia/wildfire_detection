import pyproj
import numpy as np
import osmnx as ox
import pandas as pd
import geopandas as gpd
from osmnx.utils_geo import buffer_geometry
from shapely.geometry import Point, LineString
from osmnx.features import features_from_polygon

def que_estado(geom):
  '''
  Determina el estado de Estados Unidos al cual pertenece el punto geografico
  '''
  estados_gdf = gpd.read_file("data/estados_usa.gpkg", layer="estados")
  estado = estados_gdf[estados_gdf.contains(geom)].iloc[0]["codigo"]
  if estado == "":
      estado = None # No se encontró un estado
      print("⚠️ No se encontró un estado para el punto dado.")
  
  return estado  

def get_bbox(lon, lat, m):
  '''
  Devuelve un boudingbox del buffer generado al rededor de la latitud y longitud dada.
  lon: longitud
  lat: latitud
  m: radio del buffer en metros
  '''
  gdf = gpd.GeoDataFrame(geometry=[Point(lon, lat)], crs="EPSG:4326")
  gdf_proj = gdf.to_crs('EPSG:3857')
  buffer = gdf_proj.buffer(m)
  
  return buffer.total_bounds

def caracterizar_rutas_detallado(point):
  '''
  Devuelve un pandas Serie con los km de camino de tres categorias: principales, urbanos y rurales
  '''
  principales = ['primary', 'motorway', 'trunk','secondary','motorway_link','trunk_link','primary_link',"secondary_link",'tertiary','tertiary_link']  # ejemplo, ajustá según tu data
  urbanos = ['living_street', 'residential',"pedestrian","busway"]
  rural = ['track',"bridleway","footway","path","steps","track_grade5","track_grade4","track_grade3","track_grade2","track_grade1"]
  
  # creamos el buffer con 7500 metros cuadrados
  buffer = ox.utils_geo.buffer_geometry(point, dist=5000)
  
  # Convertir a GeoSeries para trabajar con proyección. Esto devuelve una tupla (punto projectado, CRS)
  project_point = ox.projection.project_geometry(point, crs="EPSG:4326", to_crs="EPSG:3857")
  project_point = project_point[0]
  
  # combinamos las etiquetas
  roads_tags = principales + urbanos + rural
  tags = {'highway': roads_tags}
  
  # obtenemos los tags dentro del buffer
  try:
    roads = ox.features.features_from_polygon(buffer, tags)
  except ox._errors.InsufficientResponseError:
    return pd.Series({
          'km_principales': 0,
          'km_urbanos': 0,
          'km_rural': 0,
      #    "min_distance_to_road": None
      })
  
  if roads.empty:
      return pd.Series({
          'km_principales': 0,
          'km_urbanos': 0,
          'km_rural': 0,
      #    "min_distance_to_road": None
      })
  
  roads = roads.to_crs(3857)
  
  # Filtrar por tipo
  rutas_principales = roads[roads['highway'].isin(principales)]
  rutas_urbanos = roads[roads['highway'].isin(urbanos)]
  rutas_rural = roads[roads['highway'].isin(rural)]
  
  # Calcular longitudes (metros)
  longitud_principales = rutas_principales.geometry.length.sum()
  longitud_urbanos = rutas_urbanos.geometry.length.sum()
  longitud_rural = rutas_rural.geometry.length.sum()
  
  # Calcular distancia mínima a ruta principal
  roads['dist'] = roads.geometry.distance(project_point)
  distancia_min_km = round(roads['dist'].min() / 1000, 3)
  
  return pd.Series({
      'km_principales': round(longitud_principales / 1000, 3),
      'km_urbanos': round(longitud_urbanos / 1000, 3),
      'km_rural': round(longitud_rural / 1000, 3)
      #"min_distance_to_road": distancia_min_km #Si se desea devolver distancias minimas
  })

def caracterizar_uso_suelo(point):
  '''
  Devuelve un pandas serie con la proporcion de uso del suelo en tres categorias: los de alto uso, de uso urbano y los de bajo uso.
  Como asi tambien devuelve la categoria predominante en un buffer de radio de 5km al rededor del punto geografico.
  '''
  landuse_high = ["farm","grass","scrub","vineyard","farmland","farmyard","shrub", "shrubbery", "heath"]
  landuse_urban = ["recreation_ground","allotments","park", "residential", "industrial"]
  landuse_low = ["forest","meadow", "nature_reserve", "national_reserve", "national_park","tree", "tree_row", "wood","grassland","flowerbed","brownfield"]
  
  # creamos el buffer con 7600 metros cuadrados
  buffer = ox.utils_geo.buffer_geometry(point, dist=7500)
  
  # combinamos las etiquetas
  landuse_tags = landuse_high + landuse_low + landuse_urban
  tags = {
      'landuse': landuse_tags,
      'natural': landuse_tags,
      'surface':landuse_tags,
      'boundary':landuse_tags,
      'boundary':landuse_tags,
      'leisure':landuse_tags,
      'water':landuse_tags
  }
  # obtenemos los tags dentro del buffer
  try:
    landuse = ox.features.features_from_polygon(buffer, tags)
    #print(landuse)
  except ox._errors.InsufficientResponseError:
    return pd.Series({
      'pct_low': 0.0,
      'pct_urban': 0.0,
      'pct_high': 0.0,
      'clase_dominante': None
    })
  
  # Filtrar solo los polígonos (algunos datos pueden ser puntos o líneas)
  #landuse = landuse[landuse.geometry.type.isin(['Polygon', 'MultiPolygon'])]
  # Unificar en 'landuse' el primer valor no nulo por fila
  cols_prioritarias = ['landuse', 'natural', 'surface', 'leisure', 'boundary', 'water']
  cols_presentes = [col for col in cols_prioritarias if col in landuse.columns]
  
  landuse['landuse'] = landuse[cols_presentes].bfill(axis=1).iloc[:, 0]
  #print(landuse['landuse'].value_counts())
  landuse = landuse.to_crs(3857)
  
  if landuse.empty:
      return pd.Series({
          'pct_low': 0.0,
          'pct_urban': 0.0,
          'pct_high': 0.0,
          'clase_dominante': None
      })
  
  # 5. Calcular el área de cada polígono
  landuse['area_m2'] = landuse.geometry.area
  
  # 6. Agrupar por tipo de landuse y sumar el área
  landuse_summary = (
      landuse
      .groupby('landuse')['area_m2']
      .sum()
      .reset_index()
  )
  
  # 7. Calcular proporción respecto al total del área del buffer ocupado por usos de suelo
  total_area = landuse_summary['area_m2'].sum()
  if total_area == 0:
    return pd.Series({
      'pct_low': 0.0,
      'pct_urban': 0.0,
      'pct_high': 0.0,
      'clase_dominante': None
    })
  
  def clasificar(fclass):
      if fclass in landuse_high:
          return 'high'
      elif fclass in landuse_low:
          return 'low'
      elif fclass in landuse_urban:
          return 'urban'
      else:
          return 'otro'
  
  landuse_summary['grupo'] = landuse_summary['landuse'].apply(clasificar)
  area_por_grupo = landuse_summary.groupby('grupo')['area_m2'].sum()
  
  pct_low = round(area_por_grupo.get('low', 0) / total_area * 100, 2)
  pct_urban = round(area_por_grupo.get('urban', 0) / total_area * 100, 2)
  pct_high = round(area_por_grupo.get('high', 0) / total_area * 100, 2)
  
  if not landuse_summary.empty:
      clase_dominante = landuse_summary.groupby('landuse')['area_m2'].sum().idxmax()
  else:
      clase_dominante = None
  
  return pd.Series({
      'pct_low': pct_low,
      'pct_urban': pct_urban,
      'pct_high': pct_high,
      'clase_dominante': clase_dominante
  })

def caracterizar_uso_agua_detallado(point, ancho_promedio_m=10):
  '''
  Devuelve un data frame con el procentaje de cuerpos de agua que hay en un radio de 5km alrededor del foco del incendio
  y el tipo del mismo cuerpo de agua.
  '''
  project_point = gpd.GeoSeries([point], crs='EPSG:4326').to_crs(epsg=3857)
  
  # creamos el buffer con 5000 metros cuadrados
  buffer = ox.utils_geo.buffer_geometry(point, dist=5000)
  project_buffer = project_point.buffer(5000).iloc[0]
  buffer_area = project_buffer.area # m²
  
      # Convertir a GeoSeries para trabajar con proyección. Esto devuelve una tupla (punto projectado, CRS)
      #project_point = ox.projection.project_geometry(point, crs="EPSG:4326", to_crs="EPSG:3857")[0]
  
      # combinamos las etiquetas
  tags = {
          "natural": ["water","wetland","spring","floodplain","bay","strait","reef"],
          "water": True,
          "waterway":True,
          "landuse": ["reservoir"]  # Embalses
      }
  
  # obtenemos los tags dentro del buffer
  try:
    water = ox.features.features_from_polygon(buffer, tags)
  
    # separar en dos GeoDataFrames según el tipo de geometría
    waterway = water[water.geom_type.isin(['LineString', 'MultiLineString'])]
    waters   = water[~water.geom_type.isin(['LineString', 'MultiLineString'])]
  
    # --- 1) Asegurarnos de que todo use la misma proyección métrica -----------
    crs_metrica = "EPSG:3857"
    buffer_poly = gpd.GeoSeries([project_buffer], crs=crs_metrica)
  
    waterway_proj = waterway.to_crs(crs_metrica)
    waters_proj   = waters.to_crs(crs_metrica)
  
    # --- 2) Recortar (clip) al interior del buffer ----------------------------
    waterway_clip = gpd.clip(waterway_proj, buffer_poly)
    waters_clip   = gpd.clip(waters_proj,   buffer_poly)
  
    # --- 3) Cálculos ----------------------------------------------------------
    # Longitud total (m)  ➜  km
    total_len_m  = waterway_clip.length.sum()
    total_len_km = total_len_m / 1_000
  
    # Área total (m²)
    total_area_m2 = waters_clip.area.sum()
  
    try:
      water_counts = waters_clip["water"].dropna().astype(str).value_counts().to_dict()
      clase_dominante_water = max(water_counts, key=water_counts.get) if water_counts else None
    except:
      clase_dominante_water = None
  
    # --- 4) Resultados --------------------------------------------------------
    resultado = pd.Series({
        'pct_water':    total_area_m2 / 1000000,   # m² de polígono de agua dentro del buffer
        'pct_waterways_equiv': total_len_m   / 1000,   # km de líneas de waterway dentro del buffer
        'clase_dominante_water': clase_dominante_water
  
    })
    return resultado
  except:
    return pd.Series({
          'pct_water': 0,
          'pct_waterways_equiv': 0,
          'clase_dominante_water': None
      })
  
def analizar_punto(point):
  '''
  Devuelve un pandas serie con la distancia a la ciudad mas cercana al punto geografico, la poblacion de dicha ciudad,
  la distancia a la ciudad mas cercana con al menos una estacion de bombero, la poblacion de dicha ciudad y la cantidad de 
  estaciones de bomberos dentro de un buffer de radio de 50 km al rededor del punto
  '''
  buffer = ox.utils_geo.buffer_geometry(point, dist=100000)
  tags = {'place': ['city', 'town', 'village']}
  
  # Buscamos ciudades dentro del buffer
  try:
    places = ox.features.features_from_polygon(buffer, tags)
  except ox._errors.InsufficientResponseError:
      return pd.Series({
              'dist_ciudad': None,
              'pob_ciudad': 0,
              'pob_ciudad_bomb': 0,
              'dist_ciudad_bomb': None,
              'radio_buffer_m': None,
              'estaciones_bomberos': 0,
          #    "mean_influence": 0,
          #    "max_influence": 0
          })
  
  if places.empty:
    return pd.Series({
              'dist_ciudad': None,
              'pob_ciudad': 0,
              'pob_ciudad_bomb': 0,
              'dist_ciudad_bomb': None,
          #    'dist_bomb': None,
              'radio_buffer_m': None,
              'estaciones_bomberos': 0,
          #    "mean_influence": 0,
          #    "max_influence": 0
          })
  
  # se filtra poligonos, puntos y multipoligonos
  places = places[places.geometry.type.isin(['Point', 'Polygon', 'MultiPolygon'])]
  places.dropna(subset='population', inplace=True)
  places['population'] = places['population'].astype(int)
  places = places.to_crs(3857)
  places['geometry'] = places.geometry.centroid
  
  project_point = gpd.GeoSeries([point], crs='EPSG:4326').to_crs(3857)
  
  # calcula la distancia euclideana
  places['dist'] = places.geometry.distance(project_point[0])
  places = places.sort_values('dist')
  
  min_dist_to_place = places['dist'].iloc[0]/1000
  population_of_min_dist_place = places['population'].iloc[0]
  
  places['influence'] = places['population'] / ((places['dist']/1000) ** 2)
  max_influence = places['influence'].max()
  mean_influence = np.mean(places['influence'])
  #distancia_km_mascercana = geodesic(
  #    (punto.y, punto.x),
  #   (ciudad_mas_cercana.geometry.centroid.y, ciudad_mas_cercana.geometry.centroid.x)
  #).km
  
  # Reproyectar estaciones una sola vez
  tags = {'amenity': ['fire_station']}
  # Buscamos ciudades dentro del buffer
  try:
    fire_stations = ox.features.features_from_polygon(buffer, tags)
  except ox._errors.InsufficientResponseError:
      return pd.Series({
              'dist_ciudad': round(min_dist_to_place, 2),
              'pob_ciudad': int(population_of_min_dist_place),
              'pob_ciudad_bomb': 0,
              'dist_ciudad_bomb': None,
          #    'dist_bomb': None,
              'radio_buffer_m': None,
              'estaciones_bomberos': 0,
          #    "mean_influence": round(mean_influence, 4),
          #    "max_influence": round(max_influence, 4)
          })
  
  if fire_stations.empty:
    return pd.Series({
              'dist_ciudad': round(min_dist_to_place, 2),
              'pob_ciudad': int(population_of_min_dist_place),
              'pob_ciudad_bomb': 0,
              'dist_ciudad_bomb': None,
            #  'dist_bomb': None,
              'radio_buffer_m': None,
              'estaciones_bomberos': 0,
           #   "mean_influence": round(mean_influence, 4),
           #   "max_influence": round(max_influence, 4)
          })
  
  
  fire_stations = fire_stations.to_crs(3857)
  # Buscar ciudad más cercana con estaciones
  for _, ciudad_cercana in places.iterrows():
      poblacion = ciudad_cercana.get('population', 0) or 0
      #print(poblacion)
      # Definir radio del buffer según población
      if (poblacion < 15000):
          radio_buffer = 5000
      elif (poblacion> 15001) & (poblacion < 45000):
          radio_buffer = 10000
      elif (poblacion > 45001) & (poblacion < 100000):
          radio_buffer = 15000
      elif (poblacion > 100001) & (poblacion < 250000):
          radio_buffer = 20000
      elif (poblacion >  250001) & (poblacion < 750000):
          radio_buffer = 25000
      else:
          radio_buffer = 50000
  
      ciudad_geom_proj = gpd.GeoSeries([ciudad_cercana.geometry], crs=fire_stations.crs)
      #print((radio_buffer,poblacion))
      buffer_ciudad = ciudad_geom_proj.buffer(radio_buffer).iloc[0]
  
      estaciones_en_ciudad = fire_stations[fire_stations.intersects(buffer_ciudad)]
      cant_estaciones = len(estaciones_en_ciudad)
  
      if cant_estaciones > 0:
          #distancia_km = geodesic(
          #    (punto.y, punto.x),
          #   (ciudad_cercana.geometry.centroid.y, ciudad_cercana.geometry.centroid.x)
          #).km
          min_dist_to_fire_station = estaciones_en_ciudad.distance(project_point[0]).min()/1000
          dist_to_ciudad_cercana = ciudad_cercana.geometry.distance(project_point[0])/1000
  
          return pd.Series({
              'dist_ciudad': round(min_dist_to_place, 2),
              'pob_ciudad': int(population_of_min_dist_place),
              'pob_ciudad_bomb': int(poblacion),
              'dist_ciudad_bomb': round(dist_to_ciudad_cercana, 2),
           #   "dist_bomb": round(min_dist_to_fire_station, 2),
              'radio_buffer_m': int(radio_buffer),
              'estaciones_bomberos': int(cant_estaciones),
           #   "mean_influence": round(mean_influence, 4),
          #    "max_influence": round(max_influence, 4)
          })
  
  # Si ninguna ciudad tiene estaciones dentro del buffer
  return pd.Series({
              'dist_ciudad': round(min_dist_to_place, 2),
              'pob_ciudad': int(population_of_min_dist_place),
              'pob_ciudad_bomb': 0,
              'dist_ciudad_bomb': None,
         #     'dist_bomb': None,
              'radio_buffer_m': None,
              'estaciones_bomberos': 0,
       #       "mean_influence": round(mean_influence, 4),
       #       "max_influence": round(max_influence, 4)
          })

def get_geospatial_data(lat, lon):
  '''
  Devuelve un dataframe con las variables obtenidas a traves de las distintas funciones de OSMnx
  '''
  geom = Point(lon, lat)
  rutas = caracterizar_rutas_detallado(geom)
  agua = caracterizar_uso_agua_detallado(geom)
  servicios = analizar_punto(geom)
  suelo = caracterizar_uso_suelo(geom)
  estado = que_estado(geom)
  
  # armar el registro como dict para convertir a dataframe después
  resultado = {}  # incluye todas las columnas originales
  resultado["latitud"] = lat
  resultado["longitud"] = lon
  resultado.update(rutas)
  resultado.update(agua)
  resultado.update(servicios)
  resultado.update(suelo)
  resultado["STATE"]=estado
  
  df = pd.DataFrame([resultado])
  return df
