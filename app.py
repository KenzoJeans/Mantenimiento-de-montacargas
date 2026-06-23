import streamlit as st
import streamlit.components.v1 as components
import base64
import pathlib
import pandas as pd
import json

# Configuración de la página de Streamlit
st.set_page_config(page_title="Forklift Twin Pro", layout="wide", page_icon="🚜")

st.title("🚜 Gemelo Digital Operacional - Montacargas Pro")
st.markdown("Ecosistema de Mantenimiento 4.0. Haz clic en los **pines flotantes intermitentes** del modelo 3D para auditar los reportes de Google Sheets.")

# =====================================================================
# 1. CONEXIÓN EN VIVO A GOOGLE SHEETS
# =====================================================================
def cargar_historial_desde_google_sheets():
    historial = {
        "default": {
            "titulo": "Instrucciones del Gemelo Digital",
            "detalles": "Selecciona cualquiera de los pines flotantes de color sobre el montacargas para desplegar las órdenes de servicio de planta en tiempo real."
        }
    }
    
    ID_HOJA = "1uHS0iWNUf2ER5v67dQaoyM8284Ba5hUfEuKX7xt0lLQ" 
    SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv"
    
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        df.columns = df.columns.str.strip()
        
        if 'Marca temporal' in df.columns:
            df = df.sort_values(by='Marca temporal', ascending=False)

        for _, fila in df.iterrows():
            parte          = str(fila.get('COMPONENTE', '')).strip().lower()
            nombre_visible = str(fila.get('NOMBRE DE LA PIEZA', 'Componente'))
            fecha          = str(fila.get('FECHA', '---'))
            tecnico        = str(fila.get('NOMBRE DEL OPERARIO', 'No asignado'))
            descripcion    = str(fila.get('DESCRIPCION DEL MANTENIMIENTO', 'Sin detalles'))
            
            estado_raw = str(fila.get('ESTADO', '')).strip().upper()
            if "CRIT" in estado_raw or "MALO" in estado_raw:
                estado = "🔴 " + estado_raw
            elif "ALER" in estado_raw or "REVIS" in estado_raw:
                estado = "🟡 " + estado_raw
            else:
                estado = "🟢 " + estado_raw
            
            if not parte or parte == 'nan':
                continue
                
            if parte not in historial:
                historial[parte] = {
                    "titulo": nombre_visible,
                    "detalles": ""
                }
            
            linea_reporte = f"{estado} <b>{fecha}</b>: {descripcion} <br><small style='color:#64748b;'>👤 Operario: {tecnico}</small><br><br><hr style='border:0;border-top:1px dashed #e2e8f0;'>"""
            historial[parte]["detalles"] += linea_reporte
            
    except Exception as e:
        print(f"Error mapeando Google Sheets: {e}")
        
    return json.dumps(historial)

json_data = cargar_historial_desde_google_sheets()

# =====================================================================
# 2. LEER EL MODELO Y CONVERTIR A BASE64
# =====================================================================
glb_data_uri = ""
ruta_glb = pathlib.Path(__file__).parent / "static" / "forklift_low_poly.glb"
 
if ruta_glb.exists():
    with open(ruta_glb, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    glb_data_uri = f"data:model/gltf-binary;base64,{b64}"
else:
    st.error("⚠️ Archivo `static/forklift_low_poly.glb` no detectado.")
 
# =====================================================================
# 3. INTERFAZ HTML + THREE.JS (Pines reubicados con precisión)
# =====================================================================
three_js_interface = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0; padding: 0; overflow: hidden;
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: #f1f5f9; display: flex;
        }}
        #canvas-container {{ width: 65%; height: 560px; position: relative; }}
        #sidebar-panel {{
            width: 35%; height: 560px; background: #ffffff;
            box-shadow: -5px 0 20px rgba(0,0,0,0.05); padding: 25px;
            box-sizing: border-box; overflow-y: auto; border-left: 2px solid #e2e8f0;
        }}
        .badge {{
            background: #0f172a; color: #fff; padding: 4px 8px;
            border-radius: 4px; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;
        }}
        h3 {{ color: #0f172a; margin-top: 12px; font-size: 20px; }}
        p {{ color: #334155; line-height: 1.6; font-size: 14px; }}
        #status {{
            position: absolute; bottom: 15px; left: 15px;
            background: rgba(15, 23, 42, 0.9); color: #fff;
            padding: 6px 12px; border-radius: 6px;
            font-family: monospace; font-size: 11px; pointer-events: none;
        }}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
    <div id="canvas-container">
        <div id="status">⏳ Inicializando Gemelo Operacional...</div>
    </div>
    <div id="sidebar-panel">
        <span class="badge">HISTORIAL EN VIVO</span>
        <h3 id="part-title">Instrucciones del Gemelo Digital</h3>
        <hr style="border:0;border-top:1px solid #e2e8f0;margin:15px 0;">
        <div id="part-details">
            <p>Selecciona cualquiera de los pines flotantes sobre el montacargas para desplegar las órdenes de servicio de planta en tiempo real.</p>
        </div>
    </div>
 
    <script>
    const baseDatos = {json_data};
    const container = document.getElementById('canvas-container');
    const status    = document.getElementById('status');
 
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8fafc);
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / 560, 0.01, 10000);
 
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(container.clientWidth, 560);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);
 
    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
 
    scene.add(new THREE.AmbientLight(0xffffff, 0.85));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.6);
    dirLight.position.set(10, 20, 15);
    scene.add(dirLight);
 
    let forkliftModel = null;
    const loader = new THREE.GLTFLoader();
    const dataURI = "{glb_data_uri}";
    const listaPines = [];
 
    function agregarPin3D(idComponente, x, y, z, colorHex, rPin) {{
        const geo = new THREE.SphereGeometry(rPin, 16, 16);
        const mat = new THREE.MeshBasicMaterial({{
            color: colorHex,
            transparent: true,
            opacity: 0.85
        }});
        const pin = new THREE.Mesh(geo, mat);
        pin.position.set(x, y, z);
        pin.name = idComponente;
        
        scene.add(pin);
        listaPines.push(pin);
    }}
 
    if (dataURI) {{
        setTimeout(() => {{
            const b64 = dataURI.split(',')[1];
            const binary = atob(b64);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
 
            loader.parse(bytes.buffer, '', (gltf) => {{
                forkliftModel = gltf.scene;
                scene.add(forkliftModel);
 
                const box    = new THREE.Box3().setFromObject(forkliftModel);
                const center = box.getCenter(new THREE.Vector3());
                const size   = box.getSize(new THREE.Vector3());
                forkliftModel.position.sub(center);
 
                const dist = Math.max(size.x, size.y, size.z) * 1.6;
                camera.position.set(dist, dist * 0.7, dist);
                camera.lookAt(0, 0, 0);
                controls.target.set(0, 0, 0);
                controls.update();
 
                const dimensionMaxima = Math.max(size.x, size.y, size.z);
                const radioProporcional = dimensionMaxima * 0.035; // Pines ligeramente más estilizados
 
                const pX = size.x;
                const pY = size.y;
                const pZ = size.z;
 
                // =============================================================
                // 📍 AJUSTE DE COORDENADAS PRECISAS
                // =============================================================
                // Llantas (Cyan): Se movieron hacia atrás en Z y más centradas al eje de la rueda delantera
                agregarPin3D('wheel',      pX * 0.32,  -pY * 0.20,   pZ * 0.15, 0x00adb5, radioProporcional); 
                
                // Cabina/Motor (Azul): Se bajó un poco más hacia el asiento/centro operativo
                agregarPin3D('loader_car', 0.0,         pY * 0.05,  -pZ * 0.12, 0x3f51b5, radioProporcional); 
                
                // Mástil (Naranja): Se bajó drásticamente para quedar sobre los rieles de elevación frontales
                agregarPin3D('mast',       0.0,         pY * 0.08,   pZ * 0.30, 0xff9800, radioProporcional); 
                
                // Uñas/Horquillas (Rosado): Se recortó su distancia en Z para que repose justo sobre el metal de la horquilla
                agregarPin3D('fork',       0.0,        -pY * 0.32,   pZ * 0.46, 0xe91e63, radioProporcional); 
 
                status.innerText = "🎯 Gemelo Digital Interactivo — Toca un Pin de color";
            }});
        }}, 50);
    }}
 
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
 
    window.addEventListener('click', (event) => {{
        const rect = renderer.domElement.getBoundingClientRect();
        mouse.x =  ((event.clientX - rect.left) / rect.width)  * 2 - 1;
        mouse.y = -((event.clientY - rect.top)  / rect.height) * 2 + 1;
        raycaster.setFromCamera(mouse, camera);
 
        const impactos = raycaster.intersectObjects(listaPines);
        
        if (impactos.length > 0) {{
            const pinTocado = impactos[0].object;
            const clave = pinTocado.name;
 
            pinTocado.material.opacity = 1.0;
            setTimeout(() => pinTocado.material.opacity = 0.85, 300);
 
            if (baseDatos[clave]) {{
                document.getElementById('part-title').innerText   = baseDatos[clave].titulo;
                document.getElementById('part-details').innerHTML = baseDatos[clave].detalles;
                status.innerText = "📍 Auditando: " + baseDatos[clave].titulo;
            }} else {{
                document.getElementById('part-title').innerText   = "Componente: " + clave;
                document.getElementById('part-details').innerHTML = "<i>No se registran órdenes de servicio activas para esta sección.</i>";
            }}
        }}
    }});
 
    let tiempo = 0;
    (function animate() {{
        requestAnimationFrame(animate);
        controls.update();
        
        tiempo += 0.05;
        const escalaPulsante = 1 + Math.sin(tiempo) * 0.15;
        listaPines.forEach(pin => {{
            pin.scale.set(escalaPulsante, escalaPulsante, escalaPulsante);
        }});
 
        renderer.render(scene, camera);
    }})();
    </script>
</body>
</html>
"""
 
components.html(three_js_interface, height=570)
