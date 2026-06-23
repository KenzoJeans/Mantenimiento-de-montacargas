import streamlit as st
import streamlit.components.v1 as components
import json
import base64
import pathlib
import pandas as pd

# Configuración de la página de Streamlit
st.set_page_config(page_title="Forklift Twin Pro", layout="wide", page_icon="🚜")

st.title("🚜 Gemelo Digital Operacional - Montacargas Pro")
st.markdown("Ecosistema de Mantenimiento 4.0. Haz clic directamente sobre las piezas del modelo 3D para auditar su historial técnico.")

# =====================================================================
# 1. CONEXIÓN EN VIVO A GOOGLE SHEETS (RESPUESTAS DEL FORMULARIO)
# =====================================================================
def cargar_historial_desde_google_sheets():
    # Estructura base inicial obligatoria para el visor
    historial = {
        "default": {
            "titulo": "Instrucciones de Inspección",
            "detalles": "Haz clic en cualquier componente del montacargas para desplegar las órdenes de servicio asociadas al código QR de planta."
        }
    }
    
    # ID extraído de tu enlace de Google Sheets
    ID_HOJA = "1uHS0iWNUf2ER5v67dQaoyM8284Ba5hUfEuKX7xt0lLQ" 
    SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv"
    
    try:
        # Leer la hoja de cálculo en tiempo real
        df = pd.read_csv(SHEET_CSV_URL)
        
        # Limpieza de espacios en blanco en las cabeceras
        df.columns = df.columns.str.strip()
        
        # Ordenar por 'Marca temporal' de forma descendente para ver lo más reciente primero
        if 'Marca temporal' in df.columns:
            df = df.sort_values(by='Marca temporal', ascending=False)

        # Recorrer las filas de la hoja para agrupar los reportes técnicos
        for _, fila in df.iterrows():
            parte          = str(fila.get('COMPONENTE', '')).strip().lower()
            nombre_visible = str(fila.get('NOMBRE DE LA PIEZA', 'Componente'))
            fecha          = str(fila.get('FECHA', '---'))
            tecnico        = str(fila.get('NOMBRE DEL OPERARIO', 'No asignado'))
            descripcion    = str(fila.get('DESCRIPCION DEL MANTENIMIENTO', 'Sin detalles'))
            
            # Formatear visualmente el tipo de mantenimiento con emojis
            estado_raw = str(fila.get('ESTADO', '')).strip().upper()
            if "CRIT" in estado_raw or "MALO" in estado_raw:
                estado = "🔴 " + estado_raw
            elif "ALER" in estado_raw or "REVIS" in estado_raw:
                estado = "🟡 " + estado_raw
            else:
                estado = "🟢 " + estado_raw
            
            # Ignorar filas vacías
            if not parte or parte == 'nan':
                continue
                
            # Si el componente no está en nuestro diccionario, lo inicializamos
            if parte not in historial:
                historial[parte] = {
                    "titulo": nombre_visible,
                    "detalles": ""
                }
            
            # Formateamos cada reporte como una línea de tiempo acumulativa en HTML
            linea_reporte = f"{estado} <b>{fecha}</b>: {descripcion} <i>(Técnico: {tecnico})</i><br><br>"
            historial[parte]["detalles"] += linea_reporte
            
    except Exception as e:
        # En caso de error, muestra el aviso sin tumbar la aplicación
        st.sidebar.error(f"⚠️ Error conectando con Google Sheets: {e}")
        
    return json.dumps(historial)

# Cargamos los datos vivos de la planta para inyectarlos en el script 3D
json_data = cargar_historial_desde_google_sheets()

# =====================================================================
# 2. LEER EL MODELO Y CONVERTIR A BASE64 EN PYTHON
# =====================================================================
glb_data_uri = ""
ruta_glb = pathlib.Path(__file__).parent / "static" / "forklift_low_poly.glb"
 
if ruta_glb.exists():
    with open(ruta_glb, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    glb_data_uri = f"data:model/gltf-binary;base64,{b64}"
else:
    st.error("⚠️ No se encontró `static/forklift_low_poly.glb` en el repositorio.")
 
# =====================================================================
# 3. INTERFAZ HTML + THREE.JS (VISOR INTERACTIVO)
# =====================================================================
three_js_interface = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0; padding: 0; overflow: hidden;
            font-family: 'Segoe UI', sans-serif;
            background: #f8fafc; display: flex;
        }}
        #canvas-container {{ width: 65%; height: 550px; position: relative; }}
        #sidebar-panel {{
            width: 35%; height: 530px; background: #fff;
            box-shadow: -4px 0 15px rgba(0,0,0,0.05); padding: 20px;
            box-sizing: border-box; overflow-y: auto; border-left: 2px solid #e2e8f0;
        }}
        .badge {{
            background: #008891; color: #fff; padding: 5px 10px;
            border-radius: 4px; font-size: 12px; font-weight: bold;
        }}
        h3 {{ color: #00204A; margin-top: 10px; }}
        p {{ color: #475569; line-height: 1.5; font-size: 14px; }}
        #status {{
            position: absolute; bottom: 10px; left: 10px;
            background: rgba(0,32,74,0.9); color: #fff;
            padding: 8px 12px; border-radius: 4px;
            font-family: monospace; font-size: 11px;
            pointer-events: none; z-index: 100;
        }}
        #progress-bar {{
            position: absolute; bottom: 0; left: 0;
            height: 3px; background: #008891;
            width: 0%; transition: width 0.3s ease;
            z-index: 101;
        }}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
    <div id="canvas-container">
        <div id="status">⏳ Inicializando visor 3D...</div>
        <div id="progress-bar"></div>
    </div>
    <div id="sidebar-panel">
        <span class="badge">HISTORIAL DE PLANTA</span>
        <h3 id="part-title">Instrucciones de Inspección</h3>
        <hr style="border:0;border-top:1px solid #e2e8f0;margin:15px 0;">
        <p id="part-details">Haz clic en cualquier componente del montacargas para desplegar las órdenes de servicio.</p>
    </div>
 
    <script>
    const baseDatos = {json_data};
    const container = document.getElementById('canvas-container');
    const status    = document.getElementById('status');
    const bar       = document.getElementById('progress-bar');
 
    // --- ESCENA ---
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf1f5f9);
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / 550, 0.01, 10000);
 
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(container.clientWidth, 550);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);
 
    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
 
    scene.add(new THREE.AmbientLight(0xffffff, 0.9));
    const dir = new THREE.DirectionalLight(0xffffff, 0.8);
    dir.position.set(5, 20, 10);
    scene.add(dir);
 
    // --- CARGA POR DATA URI ---
    let forkliftModel = null;
    const loader = new THREE.GLTFLoader();
    const dataURI = "{glb_data_uri}";
 
    if (!dataURI) {{
        status.innerText = "❌ Modelo no encontrado en static/";
    }} else {{
        status.innerText = "⏳ Decodificando geometría...";
        bar.style.width = "10%";
 
        setTimeout(() => {{
            const b64 = dataURI.split(',')[1];
            const binary = atob(b64);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
 
            bar.style.width = "40%";
            status.innerText = "⏳ Construyendo geometría 3D...";
 
            loader.parse(bytes.buffer, '', (gltf) => {{
                forkliftModel = gltf.scene;
                scene.add(forkliftModel);
 
                const box    = new THREE.Box3().setFromObject(forkliftModel);
                const center = box.getCenter(new THREE.Vector3());
                const size   = box.getSize(new THREE.Vector3());
                forkliftModel.position.sub(center);
 
                const dist = Math.max(size.x, size.y, size.z) * 1.8;
                camera.position.set(dist, dist * 0.8, dist);
 
                camera.lookAt(0, 0, 0);
                controls.target.set(0, 0, 0);
                controls.update();
 
                bar.style.width = "100%";
                setTimeout(() => bar.style.display = 'none', 600);
                status.innerText = "✅ Gemelo digital activo — toca una pieza";
            }}, (err) => {{
                status.innerText = "❌ Error al parsear el modelo";
                console.error(err);
            }});
        }}, 50);
    }}
 
    // --- RAYCASTING (DETECTAR CLICS EN PIEZAS) ---
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
 
    window.addEventListener('click', (event) => {{
        const rect = renderer.domElement.getBoundingClientRect();
        mouse.x =  ((event.clientX - rect.left) / rect.width)  * 2 - 1;
        mouse.y = -((event.clientY - rect.top)  / rect.height) * 2 + 1;
        raycaster.setFromCamera(mouse, camera);
 
        if (forkliftModel) {{
            const hits = raycaster.intersectObjects(forkliftModel.children, true);
            if (hits.length > 0) {{
                const pieza  = hits[0].object;
                const nombre = pieza.name.toLowerCase();
                status.innerText = "ID: " + pieza.name;
 
                let found = false;
                for (let key in baseDatos) {{
                    if (nombre.includes(key)) {{
                        document.getElementById('part-title').innerText   = baseDatos[key].titulo;
                        document.getElementById('part-details').innerHTML = baseDatos[key].detalles;
                        found = true; break;
                    }}
                }}
                if (!found) {{
                    document.getElementById('part-title').innerText   = "Pieza: " + pieza.name;
                    document.getElementById('part-details').innerHTML = "<i>Sin alertas registradas en el sistema QR.</i>";
                }}
            }}
        }}
    }});
 
    // --- LOOP DE RENDER ---
    (function animate() {{
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }})();
    </script>
</body>
</html>
"""
 
components.html(three_js_interface, height=560)
