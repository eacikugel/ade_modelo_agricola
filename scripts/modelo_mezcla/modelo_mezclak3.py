import numpy as np
import rasterio
from sklearn.preprocessing import StandardScaler
from sklearn.mixture import GaussianMixture
import matplotlib.pyplot as plt

# ============================================================
# CONFIGURACIÓN
# ============================================================

# Raster de entrada (ajustá si querés)
raster_path = r"C:\Users\eugea\Downloads\11_NDVI_inta_verano.tif"

# Archivo de salida (se guarda localmente)
output_clusters_path = r"C:\Users\eugea\Downloads\11_NDVI_inta_verano_gmm_k3(n_ver).tif"

print("Usando raster:", raster_path)
print("Guardando resultado en:", output_clusters_path)

# ============================================================
# CARGA DEL RASTER
# ============================================================
# ==============================
# LEER RASTER
# ==============================
print("Leyendo raster...")

with rasterio.open(raster_path) as src:
    bandas = src.read()       # shape = (12, H, W)
    meta = src.meta.copy()

H, W = bandas.shape[1], bandas.shape[2]
print(f"Dimensiones raster: {H} x {W}")
print(f"Bandas disponibles: {bandas.shape[0]}")

# Usar SOLO bandas 2 a 12 → índices 1:12
data = bandas[1:12, :, :]     # (11 bandas, H, W)


# ==============================
# CONVERTIR A MATRIZ (N_pix × 11)
# ==============================
print("Reformando raster a matriz...")

X = data.reshape(11, -1).T    # (pixels, bands)

# Mask de NODATA / NaN
mask_valid = ~np.any(np.isnan(X), axis=1)

X_valid = X[mask_valid]

print(f"Pixeles válidos: {X_valid.shape[0]:,} / {X.shape[0]:,}")


# ==============================
# NORMALIZACIÓN
# ==============================
print("Normalizando variables...")

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_valid)


# ==============================
# MODELO DE MEZCLA GAUSSIANA (GMM)
# ==============================
print("Ajustando modelo GMM k=3...")

gmm = GaussianMixture(n_components=3, covariance_type="full", random_state=42)
clusters = gmm.fit_predict(X_scaled)

print("Modelo ajustado correctamente.")


# ==============================
# RECONSTRUIR RASTER DE CLASES
# ==============================
clusters_full = np.full(X.shape[0], -1, dtype=np.int16)
clusters_full[mask_valid] = clusters

clusters_raster = clusters_full.reshape(H, W)

# Guardar raster
meta.update({
    "count": 1,
    "dtype": "int16",
    "nodata": -1
})

with rasterio.open(output_clusters_path, "w", **meta) as dst:
    dst.write(clusters_raster, 1)

print(f"\n✔ Raster GMM guardado en:\n  {output_clusters_path}")


