import streamlit as st
import streamlit.components.v1 as components
import base64
import pathlib
import html
import re
import pandas as pd
import json
 
# Configuración de la interfaz de Streamlit
st.set_page_config(page_title="Forklift Twin Pro", layout="wide", page_icon="🚜")
 
st.title("🚜 Gemelo Digital Operacional - Montacargas Pro")
st.markdown("Ecosistema de Mantenimiento 4.0. Haz clic en los **pines interactivos** del modelo 3D para auditar los reportes en tiempo real.")
 
# =====================================================================
# MAPEO CENTRALIZADO DE SINÓNIMOS DE COMPONENTES
# (antes vivía disperso en un if/elif; ahora es un solo diccionario
#  fácil de extender si en el formulario aparece un término nuevo)
# =====================================================================
SINONIMOS_COMPONENTE = {
    "wheel": "llantas", "llantas": "llantas", "ruedas": "llantas",
    "mast": "mastil", "mastil": "mastil",
    "fork": "unas", "unas": "unas", "horquillas": "unas",
    "loader_car": "chasis", "body": "chasis", "chasis": "chasis", "estructura": "chasis",
    "horometro": "horometro", "tablero": "horometro", "horas": "horometro",
}
 
def normalizar_componente(valor_crudo: str) -> str:
    parte = str(valor_crudo).strip().lower()
    for viejo, nuevo in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")]:
        parte = parte.replace(viejo, nuevo)
    return SINONIMOS_COMPONENTE.get(parte, parte)
 
 
def limpiar_numero(valor) -> float | None:
    """Convierte '69.180', '69,180', '69180 hrs', etc. a un número.
    Se queda solo con los dígitos (el horómetro se registra en horas
    enteras), evitando ambigüedades entre '.' y ',' como separador
    de miles según la configuración regional de la hoja."""
    if valor is None:
        return None
    solo_digitos = re.sub(r"[^\d]", "", str(valor))
    if not solo_digitos:
        return None
    return float(solo_digitos)
 
 
# =====================================================================
# 1. CONEXIÓN EN VIVO A GOOGLE SHEETS + TRADUCCIÓN Y MÉTRICAS DINÁMICAS
# =====================================================================
@st.cache_data(ttl=30)
def cargar_historial_y_metricas():
    historial = {
        "default": {
            "titulo": "Instrucciones del Gemelo Digital",
            "detalles": "Selecciona cualquiera de los pines flotantes sobre el montacargas para desplegar las órdenes de servicio de planta en tiempo real."
        }
    }
 
    ID_HOJA = "1uHS0iWNUf2ER5v67dQaoyM8284Ba5hUfEuKX7xt0lLQ"
    SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv"
 
    horometro_val = None
    total_reportes = 0
    pct_preventivo = "0%"
    error_msg = None
 
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        df.columns = df.columns.str.strip()
 
        # --- Parseo correcto de fecha (antes se ordenaba como texto,
        #     lo cual rompía el orden cuando había días/meses de un
        #     solo dígito: "9/6/2026" quedaba "después" de "10/6/2026") ---
        if "Marca temporal" in df.columns:
            df["_fecha_dt"] = pd.to_datetime(
                df["Marca temporal"], errors="coerce", dayfirst=True
            )
            df = df.sort_values(by="_fecha_dt", ascending=False, na_position="last")
 
        total_reportes = len(df)
 
        # --- Horómetro: se usa el valor MÁXIMO registrado, no el de
        #     "la fila más reciente por fecha". El horómetro de un
        #     motor solo puede subir, así que el máximo es inmune a
        #     cualquier problema de orden/parseo de fechas y es la
        #     forma más confiable de saber la lectura actual. ---
        if "HOROMETRO" in df.columns:
            horo_series = df["HOROMETRO"].apply(limpiar_numero).dropna()
            if not horo_series.empty:
                horometro_val = horo_series.max()
 
        if "ESTADO" in df.columns and total_reportes > 0:
            preventivos = df["ESTADO"].astype(str).str.upper().str.contains("PREV").sum()
            pct_preventivo = f"{(preventivos / total_reportes * 100):.0f}%"
 
        for _, fila in df.iterrows():
            parte = normalizar_componente(fila.get("COMPONENTE", ""))
            if not parte or parte == "nan":
                continue
 
            # Todo el contenido que viene del formulario se escapa antes
            # de insertarse en el HTML del panel lateral: si alguien pega
            # texto con "<" o ">" en el formulario, ya no rompe el layout
            # ni se interpreta como HTML/JS dentro del iframe.
            nombre_visible = html.escape(str(fila.get("NOMBRE DE LA PIEZA", "Componente")))
            fecha = html.escape(str(fila.get("FECHA", "---")))
            tecnico = html.escape(str(fila.get("NOMBRE DEL OPERARIO", "No asignado")))
            descripcion = html.escape(str(fila.get("DESCRIPCION DEL MANTENIMIENTO", "Sin detalles")))
 
            estado_raw = str(fila.get("ESTADO", "")).strip().upper()
            if "CRIT" in estado_raw or "MALO" in estado_raw:
                estado = "🔴 " + html.escape(estado_raw)
            elif "ALER" in estado_raw or "REVIS" in estado_raw:
                estado = "🟡 " + html.escape(estado_raw)
            else:
                estado = "🟢 " + html.escape(estado_raw)
 
            if parte not in historial:
                historial[parte] = {"titulo": nombre_visible, "detalles": ""}
 
            linea_reporte = (
                f"{estado} <b style='color:#f8fafc;'>{fecha}</b>: "
                f"<span style='color:#cbd5e1;'>{descripcion}</span><br>"
                f"<small style='color:#94a3b8;'>👤 Operario: {tecnico}</small><br><br>"
                f"<hr style='border:0;border-top:1px dashed #334155;'>"
            )
            historial[parte]["detalles"] += linea_reporte
 
    except Exception as e:
        error_msg = str(e)
 
    horometro_txt = f"{horometro_val:,.0f} Hrs" if horometro_val is not None else "Sin datos"
    return json.dumps(historial), horometro_txt, total_reportes, pct_preventivo, error_msg
 
 
col_titulo, col_boton = st.columns([6, 1])
with col_boton:
    if st.button("🔄 Actualizar ahora"):
        cargar_historial_y_metricas.clear()
 
json_data, horometro_val, total_reportes, pct_preventivo, error_msg = cargar_historial_y_metricas()
 
# Antes, cualquier error al leer la hoja se perdía en un print() que
# solo aparecía en la consola del servidor. Ahora se avisa en pantalla,
# para que sea evidente si el tablero está mostrando datos desactualizados.
if error_msg:
    st.warning(f"⚠️ No se pudo actualizar la información desde Google Sheets: {error_msg}")
 
# =====================================================================
# 2. PROCESAMIENTO DEL MODELO 3D
# =====================================================================
@st.cache_resource
def cargar_modelo_3d_base64():
    """Lee y codifica el .glb una sola vez por sesión de servidor,
    en vez de en cada rerun (antes se releía y re-codificaba el
    archivo binario completo con cada clic en el tablero)."""
    ruta_glb = pathlib.Path(__file__).parent / "static" / "forklift_low_poly.glb"
    if not ruta_glb.exists():
        return None
    with open(ruta_glb, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:model/gltf-binary;base64,{b64}"
 
 
glb_data_uri = cargar_modelo_3d_base64()
if not glb_data_uri:
    st.error("⚠️ Archivo `static/forklift_low_poly.glb` no detectado.")
    glb_data_uri = ""
 
# =====================================================================
# 3. INTERFAZ INTEGRADA (MODO OSCURO PRO)
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
            background: #0e1117; display: flex; color: #f8fafc;
        }}
        #canvas-container {{ width: 65%; height: 620px; position: relative; background: #0e1117; }}
        #sidebar-panel {{
            width: 35%; height: 620px; background: #161b26;
            box-shadow: -5px 0 20px rgba(0,0,0,0.5); padding: 25px;
            box-sizing: border-box; overflow-y: auto; border-left: 1px solid #262730;
        }}
 
        /* Estilos de Indicadores Métricos Oscuros */
        .metrics-container {{ display: flex; gap: 10px; margin-bottom: 20px; margin-top: 10px; }}
        .metric-card {{
            flex: 1; background: #1e2430; padding: 12px; border-radius: 8px; border: 1px solid #2d3748;
        }}
        .metric-label {{ font-size: 11px; color: #94a3b8; font-weight: 600; }}
        .metric-value {{ font-size: 20px; font-weight: bold; color: #f8fafc; margin: 4px 0; }}
        .metric-delta {{ font-size: 10px; color: #4ade80; background: rgba(74, 222, 128, 0.15); display: inline-block; padding: 2px 5px; border-radius: 4px; font-weight: 500; }}
 
        /* Buscador manual */
        .selector-label {{ font-size: 13px; font-weight: 600; color: #cbd5e1; display: block; margin-bottom: 6px; }}
        .custom-select {{
            width: 100%; padding: 10px; border-radius: 6px; border: 1px solid #334155; background-color: #1e2430;
            font-size: 14px; color: #f8fafc; margin-bottom: 20px; outline: none; transition: border 0.2s;
        }}
        .custom-select:focus {{ border-color: #6366f1; }}
 
        /* Tarjeta de Historial Oscura */
        .history-box {{
            background: #1e2430; padding: 20px; border-radius: 8px; border: 1px solid #2d3748; min-height: 200px;
        }}
        .badge {{
            background: #6366f1; color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;
        }}
        h3 {{ color: #f8fafc; margin-top: 12px; font-size: 18px; }}
        h4 {{ color: #f8fafc; margin: 0 0 10px 0; font-size: 16px; }}
        p {{ color: #cbd5e1; line-height: 1.6; font-size: 14px; margin: 0; }}
        #status {{
            position: absolute; bottom: 15px; left: 15px; background: rgba(15, 23, 42, 0.9); color: #38bdf8;
            padding: 6px 12px; border-radius: 6px; font-family: monospace; font-size: 11px; pointer-events: none; z-index: 10; border: 1px solid #0284c7;
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
                <div class="metric-value">{horometro_val}</div>
                <div class="metric-delta">↑ En vivo</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">📋 Mantenimientos</div>
                <div class="metric-value">{total_reportes}</div>
                <div class="metric-delta">Total Reg.</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">🛡️ % Preventivo</div>
                <div class="metric-value">{pct_preventivo}</div>
                <div class="metric-delta">Óptimo</div>
            </div>
        </div>
 
        <hr style="border:0; border-top:1px solid #2d3748; margin:20px 0;">
 
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
            <hr style="border:0; border-top:1px solid #2d3748; margin:12px 0;">
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
    scene.background = new THREE.Color(0x0e1117); // Fondo 3D oscuro alineado a Streamlit
 
    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / 620, 0.01, 10000);
 
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(container.clientWidth, 620);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);
 
    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
 
    // Iluminación optimizada para realzar detalles sobre fondo oscuro
    scene.add(new THREE.AmbientLight(0xffffff, 1.2));
    const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight1.position.set(10, 20, 15);
    scene.add(dirLight1);
 
    const dirLight2 = new THREE.DirectionalLight(0x38bdf8, 0.4); // Luz de acento azulada
    dirLight2.position.set(-10, -10, -10);
    scene.add(dirLight2);
 
    let forkliftModel = null;
    const loader = new THREE.GLTFLoader();
    const dataURI = "{glb_data_uri}";
    const listaPines = [];
 
    function agregarPin3D(idComponente, x, y, z, colorHex, rPin) {{
        const geo = new THREE.SphereGeometry(rPin, 16, 16);
        const mat = new THREE.MeshBasicMaterial({{ color: colorHex, transparent: true, opacity: 0.9 }});
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
 
                agregarPin3D('llantas',    pX * 0.32,  -pY * 0.20,   pZ * 0.15, 0x00f2fe, radioProporcional);
                agregarPin3D('chasis',     0.0,         pY * 0.05,  -pZ * 0.12, 0x3b82f6, radioProporcional);
                agregarPin3D('mastil',     0.0,         pY * 0.08,   pZ * 0.30, 0xf59e0b, radioProporcional);
                agregarPin3D('unas',       0.0,        -pY * 0.32,   pZ * 0.46, 0xec4899, radioProporcional);
                agregarPin3D('horometro',  0.0,         pY * 0.18,  -pZ * 0.02, 0xa855f7, radioProporcional);
 
                status.innerText = "🎯 Sistema Activo — Selecciona un pin interactivo";
            }});
        }}, 50);
    }}
 
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
            document.getElementById('part-details').innerHTML = "<i style='color:#94a3b8;'>No se registran órdenes de servicio activas para esta sección en Google Sheets.</i>";
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
            setTimeout(() => pinTocado.material.opacity = 0.9, 300);
 
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
 
components.html(three_js_interface, height=630)
