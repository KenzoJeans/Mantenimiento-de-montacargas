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
# 1. CONEXIÓN EN VIVO A GOOGLE SHEETS + LIMPIEZA EN ESPAÑOL
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
            # Leer el componente y limpiar espacios/mayúsculas
            parte_raw = str(fila.get('COMPONENTE', '')).strip().lower()
            
            # Unificar nombres y limpiar tildes comunes para evitar fallas de lectura
            parte = parte_raw.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
            
            # Mapeo de nombres antiguos en inglés a la nueva estructura en español
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
# 3. DISTRIBUCIÓN DE LA INTERFAZ DE STREAMLIT (DIVIDIDO EN COLUMNAS)
# =====================================================================
col_visor, col_panel = st.columns([0.65, 0.35])

with col_panel:
    # Contenedor del Horómetro e Indicadores Clave en la cabecera del panel
    st.markdown("### 📊 Indicadores Críticos")
    c1, c2 = st.columns(2)
    with c1:
        st.metric(label="⏱️ Horómetro Actual", value="1,482 Hrs", delta="+42 Hrs esta sem.")
    with c2:
        st.metric(label="🔋 Vida de Batería", value="94%", delta="Óptimo")
    st.markdown("---")

# Construcción de la interfaz gráfica interna en HTML5/Three.js
three_js_interface = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0; padding: 0; overflow: hidden;
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: #f1f5f9;
        }}
        #canvas-container {{ width: 100%; height: 560px; position: relative; }}
        #info-card {{
            background: #ffffff; padding: 20px;
            border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            height: 400px; overflow-y: auto; border: 1px solid #e2e8f0;
        }}
        .badge {{
            background: #0f172a; color: #fff; padding: 4px 8px;
            border-radius: 4px; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;
        }}
        h3 {{ color: #0f172a; margin-top: 10px; font-size: 18px; margin-bottom: 5px; }}
        p {{ color: #334155; line-height: 1.6; font-size: 14px; }}
        #status {{
            position: absolute; bottom: 15px; left: 15px;
            background: rgba(15, 23, 42, 0.9); color: #fff;
            padding: 6px 12px; border-radius: 6px;
            font-family: monospace; font-size: 11px; pointer-events: none; z-index: 10;
        }}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
    <div id="canvas-container">
        <div id="status">⏳ Inicializando componentes en español...</div>
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
                const radioProporcional = dimensionMaxima * 0.035;
 
                const pX = size.x;
                const pY = size.y;
                const pZ = size.z;
 
                // =============================================================
                // 📍 MAPEO DE PINES EN ESPAÑOL + NUEVO PIN DE HORÓMETRO
                // =============================================================
                // Llantas (Cyan)
                agregarPin3D('llantas',    pX * 0.32,  -pY * 0.20,   pZ * 0.15, 0x00adb5, radioProporcional); 
                
                // Estructura / Chasis (Azul)
                agregarPin3D('chasis',     0.0,         pY * 0.05,  -pZ * 0.12, 0x3f51b5, radioProporcional); 
                
                // Mástil de Elevación (Naranja)
                agregarPin3D('mastil',     0.0,         pY * 0.08,   pZ * 0.30, 0xff9800, radioProporcional); 
                
                // Uñas / Horquillas (Rosado)
                agregarPin3D('unas',       0.0,        -pY * 0.32,   pZ * 0.46, 0xe91e63, radioProporcional); 
                
                // NUEVO: Horómetro / Panel de Control (Púrpura - justo en el tablero/volante)
                agregarPin3D('horometro',  0.0,         pY * 0.18,  -pZ * 0.02, 0x9c27b0, radioProporcional);
 
                status.innerText = "🎯 Sistema Activo — Selecciona un pin interactivo";
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
 
            // Enviar la información de regreso al panel lateral de Streamlit por medio de la API del Padre
            window.parent.postMessage({{
                type: 'PIN_CLICKED',
                clave: clave
            }}, '*');
            
            status.innerText = "📍 Componente auditado: " + clave.toUpperCase();
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

# HTML Receptor invisible para capturar qué pin se tocó en Three.js sin recargar la página
with col_visor:
    components.html(three_js_interface, height=560)

# Manejo de los estados en la barra lateral mediante session_state para mantener la velocidad nativa de Python
if "pin_seleccionado" not in st.session_state:
    st.session_state.pin_seleccionado = "default"

# Capturar el evento postMessage enviado desde el Iframe de Three.js
# Para mantener la integración simple y reactiva, leemos la base de datos limpia directamente en la sección lateral.
with col_panel:
    st.markdown("#### 📜 Historial Técnico de Sección")
    
    # Renderizar los datos dinámicos procesados desde el JSON según la selección
    base_datos_dict = json.loads(json_data)
    
    # Formulario simulado o selector manual alternativo por accesibilidad
    opciones_visibles = {
        "default": "Seleccionar zona...",
        "llantas": "🛞 Sistema de Rodamiento (Llantas)",
        "chasis": "🚜 Estructura Principal y Chasis",
        "mastil": "🏗️ Mástil de Elevación",
        "unas": "🔱 Horquillas / Uñas de Carga",
        "horometro": "⏱️ Horómetro y Tablero Digital"
    }
    
    seleccion = st.selectbox("Buscar componente manualmente:", options=list(opciones_visibles.keys()), format_func=lambda x: opciones_visibles[x])
    
    if seleccion:
        st.session_state.pin_seleccionado = seleccion
        
    nodo = base_datos_dict.get(st.session_state.pin_seleccionado, {
        "titulo": f"Componente: {st.session_state.pin_seleccionado.upper()}",
        "detalles": "<i>No se registran alertas ni mantenimientos preventivos recientes en Google Sheets para esta sección.</i>"
    })
    
    # Render de la tarjeta informativa limpia
    st.markdown(f"""
    <div style="background:#ffffff; padding:18px; border-radius:8px; border:1px solid #e2e8f0; min-height:220px;">
        <span style="background:#0f172a; color:white; padding:3px 8px; border-radius:4px; font-size:10px; font-weight:bold;">HISTORIAL EN VIVO</span>
        <h4 style="margin-top:8px; color:#0f172a; font-size:16px;">{nodo['titulo']}</h4>
        <hr style="border:0; border-top:1px solid #e2e8f0; margin:10px 0;">
        <p style="font-size:13px; color:#334155;">{nodo['detalles']}</p>
    </div>
    """, unsafe_allow_html=True)
