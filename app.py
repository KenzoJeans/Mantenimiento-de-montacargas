import streamlit as st
import streamlit.components.v1 as components
import base64
import pathlib
import pandas as pd
import json

# Configuración de la interfaz de Streamlit
st.set_page_config(page_title="Forklift Twin Pro", layout="wide", page_icon="🚜")

st.title("🚜 Gemelo Digital Operacional - Montacargas Pro")
st.markdown("Ecosistema de Mantenimiento 4.0. Haz clic en los **pines interactivos** del modelo 3D para auditar los reportes en tiempo real.")

# =====================================================================
# 1. CONEXIÓN EN VIVO A GOOGLE SHEETS + TRADUCCIÓN A ESPAÑOL
# =====================================================================
def cargar_historial_desde_google_sheets():
    historial = {
        "default": {
            "titulo": "Instrucciones del Gemelo Digital",
            "detalles": "Selecciona cualquiera de los pines flotantes sobre el montacargas para desplegar las órdenes de servicio de planta en tiempo real."
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
            parte_raw = str(fila.get('COMPONENTE', '')).strip().lower()
            parte = parte_raw.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
            
            # Mapeo de términos para homologación en español
            if parte in ['wheel', 'llantas', 'ruedas']:
                parte = 'llantas'
            elif parte in ['mast', 'mastil']:
                parte = 'mastil'
            elif parte in ['fork', 'unas', 'horquillas']:
                parte = 'unas'
            elif parte in ['loader_car', 'body', 'chasis', 'estructura']:
                parte = 'chasis'
            elif parte in ['horometro', 'tablero', 'horas']:
                parte = 'horometro'
            
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
            
            linea_reporte = f"{estado} <b>{fecha}</b>: {descripcion} <br><small style='color:#64748b;'>👤 Operario: {tecnico}</small><br><br><hr style='border:0;border-top:1px dashed #e2e8f0;'>"
            historial[parte]["detalles"] += linea_reporte
            
    except Exception as e:
        print(f"Error procesando base de datos: {e}")
        
    return json.dumps(historial)

json_data = cargar_historial_desde_google_sheets()

# =====================================================================
# 2. PROCESAMIENTO DEL MODELO 3D
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
# 3. INTERFAZ INTEGRADA (EVITA EL BLOQUEO DE CLICS)
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
        #canvas-container {{ width: 65%; height: 620px; position: relative; }}
        #sidebar-panel {{
            width: 35%; height: 620px; background: #ffffff;
            box-shadow: -5px 0 20px rgba(0,0,0,0.05); padding: 25px;
            box-sizing: border-box; overflow-y: auto; border-left: 2px solid #e2e8f0;
        }}
        
        /* Estilos de Indicadores Métricos */
        .metrics-container {{ display: flex; gap: 15px; margin-bottom: 25px; margin-top: 10px; }}
        .metric-card {{
            flex: 1; background: #f8fafc; padding: 14px; border-radius: 8px; border: 1px solid #e2e8f0;
        }}
        .metric-label {{ font-size: 12px; color: #64748b; font-weight: 600; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #0f172a; margin: 4px 0; }}
        .metric-delta {{ font-size: 11px; color: #16a34a; background: #dcfce7; display: inline-block; padding: 2px 6px; border-radius: 4px; font-weight: 500; }}
        
        /* Buscador manual */
        .selector-label {{ font-size: 13px; font-weight: 600; color: #475569; display: block; margin-bottom: 6px; }}
        .custom-select {{
            width: 100%; padding: 10px; border-radius: 6px; border: 1px solid #cbd5e1; background-color: #fff;
            font-size: 14px; color: #334155; margin-bottom: 20px; outline: none; transition: border 0.2s;
        }}
        .custom-select:focus {{ border-color: #6366f1; }}

        /* Tarjeta de Historial */
        .history-box {{
            background: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; min-height: 200px;
        }}
        .badge {{
            background: #0f172a; color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;
        }}
        h3 {{ color: #0f172a; margin-top: 12px; font-size: 18px; }}
        h4 {{ color: #0f172a; margin: 0 0 10px 0; font-size: 16px; }}
        p {{ color: #334155; line-height: 1.6; font-size: 14px; margin: 0; }}
        #status {{
            position: absolute; bottom: 15px; left: 15px; background: rgba(15, 23, 42, 0.9); color: #fff;
            padding: 6px 12px; border-radius: 6px; font-family: monospace; font-size: 11px; pointer-events: none; z-index: 10;
        }}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
    <div id="canvas-container">
        <div id="status">⏳ Sincronizando componentes de planta...</div>
    </div>
    
    <div id="sidebar-panel">
        <h4>📊 Indicadores Críticos</h4>
        <div class="metrics-container">
            <div class="metric-card">
                <div class="metric-label">⏱️ Horómetro Actual</div>
                <div class="metric-value">1,482 Hrs</div>
                <div class="metric-delta">↑ +42 Hrs esta sem.</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">🔋 Vida de Batería</div>
                <div class="metric-value">94%</div>
                <div class="metric-delta">↑ Óptimo</div>
            </div>
        </div>
        
        <hr style="border:0; border-top:1px solid #e2e8f0; margin:20px 0;">
        
        <label class="selector-label">🔎 Buscar componente manualmente:</label>
        <select id="selector-componente" class="custom-select" onchange="seleccionarDesdeMenu(this.value)">
            <option value="default">Seleccionar zona...</option>
            <option value="llantas">🛞 Sistema de Rodamiento (Llantas)</option>
            <option value="chasis">🚜 Estructura Principal y Chasis</option>
            <option value="mastil">🏗️ Mástil de Elevación</option>
            <option value="unas">🔱 Horquillas / Uñas de Carga</option>
            <option value="horometro">⏱️ Horómetro y Tablero Digital</option>
        </select>

        <div class="history-box">
            <span class="badge">HISTORIAL EN VIVO</span>
            <h3 id="part-title">Instrucciones del Gemelo Digital</h3>
            <hr style="border:0; border-top:1px solid #e2e8f0; margin:12px 0;">
            <div id="part-details">
                <p>Selecciona cualquiera de los pines flotantes sobre el montacargas para desplegar las órdenes de servicio de planta en tiempo real.</p>
            </div>
        </div>
    </div>
 
    <script>
    const baseDatos = {json_data};
    const container = document.getElementById('canvas-container');
    const status    = document.getElementById('status');
 
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8fafc);
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / 620, 0.01, 10000);
 
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(container.clientWidth, 620);
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
        const mat = new THREE.MeshBasicMaterial({{ color: colorHex, transparent: true, opacity: 0.85 }});
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
                const radioProporcional = dimensionMaxima * 0.035;
 
                const pX = size.x;
                const pY = size.y;
                const pZ = size.z;
 
                // Ubicaciones de precisión acopladas al chasis
                agregarPin3D('llantas',    pX * 0.32,  -pY * 0.20,   pZ * 0.15, 0x00adb5, radioProporcional); 
                agregarPin3D('chasis',     0.0,         pY * 0.05,  -pZ * 0.12, 0x3f51b5, radioProporcional); 
                agregarPin3D('mastil',     0.0,         pY * 0.08,   pZ * 0.30, 0xff9800, radioProporcional); 
                agregarPin3D('unas',       0.0,        -pY * 0.32,   pZ * 0.46, 0xe91e63, radioProporcional); 
                agregarPin3D('horometro',  0.0,         pY * 0.18,  -pZ * 0.02, 0x9c27b0, radioProporcional);
 
                status.innerText = "🎯 Sistema Activo — Selecciona un pin interactivo";
            }});
        }}, 50);
    }}
 
    // FUNCIÓN CENTRAL DE ACTUALIZACIÓN DE DATOS (Conecta clics y buscador)
    function actualizarContenedorInformativo(clave) {{
        document.getElementById('selector-componente').value = clave;
        
        if (baseDatos[clave]) {{
            document.getElementById('part-title').innerText   = baseDatos[clave].titulo;
            document.getElementById('part-details').innerHTML = baseDatos[clave].detalles;
        }} else {{
            const titulosAlternativos = {{
                'llantas': '🛞 Sistema de Rodamiento (Llantas)',
                'chasis': '🚜 Estructura Principal y Chasis',
                'mastil': '🏗️ Mástil de Elevación',
                'unas': '🔱 Horquillas / Uñas de Carga',
                'horometro': '⏱️ Horómetro y Tablero Digital'
            }};
            document.getElementById('part-title').innerText   = titulosAlternativos[clave] || "Componente";
            document.getElementById('part-details').innerHTML = "<i>No se registran órdenes de servicio activas para esta sección en Google Sheets.</i>";
        }}
        status.innerText = "📍 Componente auditado: " + clave.toUpperCase();
    }}
 
    function seleccionarDesdeMenu(val) {{
        actualizarContenedorInformativo(val);
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
 
            actualizarContenedorInformativo(clave);
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

# Renderizado de la aplicación unificada
components.html(three_js_interface, height=630)
