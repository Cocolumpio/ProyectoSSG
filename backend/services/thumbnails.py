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


def generate_ply_thumbnail(ply_path: str, output_path: str, width: int = 600, height: int = 300) -> bool:
    """
    Genera una miniatura de una nube de puntos PLY con 3 vistas (perspectiva, superior, frontal).
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
        
        # Submuestrear si hay muchos puntos (máximo 30,000 para el thumbnail)
        indices = None
        if num_points > 30000:
            indices = np.random.choice(num_points, 30000, replace=False)
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
        
        # Crear la figura con 3 subplots (perspectiva, superior, frontal)
        fig = plt.figure(figsize=(width/100, height/100), dpi=100)
        fig.patch.set_facecolor('#1a1a2e')
        
        # Vista 1: Perspectiva (isométrica)
        ax1 = fig.add_subplot(131, projection='3d')
        ax1.set_facecolor('#1a1a2e')
        if colors is not None:
            ax1.scatter(x, y, z, c=colors, s=0.2, alpha=0.8)
        else:
            ax1.scatter(x, y, z, c='#994B49', s=0.2, alpha=0.8)
        ax1.view_init(elev=30, azim=45)
        ax1.set_axis_off()
        ax1.set_title('Perspectiva', color='white', fontsize=8, pad=2)
        
        # Vista 2: Superior (planta)
        ax2 = fig.add_subplot(132, projection='3d')
        ax2.set_facecolor('#1a1a2e')
        if colors is not None:
            ax2.scatter(x, y, z, c=colors, s=0.2, alpha=0.8)
        else:
            ax2.scatter(x, y, z, c='#994B49', s=0.2, alpha=0.8)
        ax2.view_init(elev=90, azim=0)  # Vista desde arriba
        ax2.set_axis_off()
        ax2.set_title('Superior', color='white', fontsize=8, pad=2)
        
        # Vista 3: Frontal
        ax3 = fig.add_subplot(133, projection='3d')
        ax3.set_facecolor('#1a1a2e')
        if colors is not None:
            ax3.scatter(x, y, z, c=colors, s=0.2, alpha=0.8)
        else:
            ax3.scatter(x, y, z, c='#994B49', s=0.2, alpha=0.8)
        ax3.view_init(elev=0, azim=0)  # Vista frontal
        ax3.set_axis_off()
        ax3.set_title('Frontal', color='white', fontsize=8, pad=2)
        
        # Ajustar límites para todas las vistas
        max_range = max(np.max(np.abs(x)), np.max(np.abs(y)), np.max(np.abs(z))) * 1.1
        for ax in [ax1, ax2, ax3]:
            ax.set_xlim([-max_range, max_range])
            ax.set_ylim([-max_range, max_range])
            ax.set_zlim([-max_range, max_range])
        
        plt.tight_layout(pad=0.5)
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
