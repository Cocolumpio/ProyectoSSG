"""
Servicio de generación de thumbnails para modelos 3D PLY
"""
import asyncio
import logging
import numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Thread pool for CPU-intensive tasks
thumbnail_executor = ThreadPoolExecutor(max_workers=2)


def generate_ply_thumbnail(ply_path: str, output_path: str, width: int = 400, height: int = 300) -> bool:
    """
    Genera una miniatura de una nube de puntos PLY con vista superior (planta).
    Usa matplotlib y plyfile. Maneja tanto formato ASCII como binario.
    """
    try:
        import matplotlib
        matplotlib.use('Agg')  # Backend sin GUI
        import matplotlib.pyplot as plt
        from plyfile import PlyData
        
        # Leer el archivo PLY con plyfile (maneja ASCII y binario)
        plydata = PlyData.read(ply_path)
        vertex = plydata['vertex']
        
        # Extraer coordenadas
        x = np.array(vertex['x'])
        y = np.array(vertex['y'])
        z = np.array(vertex['z'])
        
        num_points = len(x)
        logging.info(f"Archivo PLY tiene {num_points} puntos")
        
        # Submuestrear si hay muchos puntos (máximo 50,000 para el thumbnail)
        indices = None
        if num_points > 50000:
            indices = np.random.choice(num_points, 50000, replace=False)
            x = x[indices]
            y = y[indices]
            z = z[indices]
        
        # Extraer colores si existen
        colors = None
        try:
            r = np.array(vertex['red']) / 255.0
            g = np.array(vertex['green']) / 255.0
            b = np.array(vertex['blue']) / 255.0
            if indices is not None:
                r = r[indices]
                g = g[indices]
                b = b[indices]
            colors = np.column_stack([r, g, b])
        except Exception:
            pass
        
        # Centrar los puntos
        x = x - np.mean(x)
        y = y - np.mean(y)
        z = z - np.mean(z)
        
        # Crear la figura con solo vista superior
        fig = plt.figure(figsize=(width/100, height/100), dpi=100)
        fig.patch.set_facecolor('#1a1a2e')
        
        # Vista Superior (planta) - vista desde arriba
        ax = fig.add_subplot(111, projection='3d')
        ax.set_facecolor('#1a1a2e')
        if colors is not None:
            ax.scatter(x, y, z, c=colors, s=0.3, alpha=0.9)
        else:
            ax.scatter(x, y, z, c='#994B49', s=0.3, alpha=0.9)
        ax.view_init(elev=90, azim=0)  # Vista desde arriba
        ax.set_axis_off()
        
        # Ajustar límites
        max_range = max(np.max(np.abs(x)), np.max(np.abs(y)), np.max(np.abs(z))) * 1.1
        ax.set_xlim([-max_range, max_range])
        ax.set_ylim([-max_range, max_range])
        ax.set_zlim([-max_range, max_range])
        
        plt.tight_layout(pad=0)
        plt.savefig(output_path, dpi=100, bbox_inches='tight', 
                   facecolor='#1a1a2e', edgecolor='none')
        plt.close(fig)
        
        logging.info(f"Thumbnail generado: {output_path} ({len(x)} puntos)")
        return True
        
    except Exception as e:
        logging.error(f"Error generando thumbnail: {e}")
        import traceback
        traceback.print_exc()
        return False


async def generate_thumbnail_async(ply_path: str, output_path: str) -> bool:
    """Wrapper async para generar thumbnail en thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thumbnail_executor, 
        generate_ply_thumbnail, 
        ply_path, 
        output_path
    )
