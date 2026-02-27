import numpy as np
from sklearn.cluster import KMeans

def proses_kmeans(data, k=3):
    X = np.array(data, dtype=float)
    model = KMeans(n_clusters=k, random_state=42, n_init=10)
    return model.fit_predict(X)
