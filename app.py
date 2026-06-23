import streamlit as st
import streamlit.components.v1 as components
import base64
import pathlib
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Forklift Twin Pro", layout="wide", page_icon="🚜")

st.title("🚜 Gemelo Digital Operacional - Montacargas Pro")
st.markdown("Ecosistema de Mantenimiento 4.0 conectado en vivo con Google Forms y Sheets.")

# =====================================================================
# 1. CARGA DE DATOS EN VIVO DESDE GOOGLE SHEETS
# =====================================================================
@st.cache_data(ttl=10)  # Se actualiza automáticamente cada 10 segundos
def obtener_datos_planta():
    ID_HOJA = "1uHS0iWNUf2ER5v67dQaoyM8284Ba5hUfEuKX7xt0lLQ" 
    SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv"
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        df.columns = df.columns.str.strip()
        if 'Marca temporal' in df.columns:
            df = df.sort_values(by='Marca temporal', ascending=False)
        return df
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return pd.DataFrame()

df_planta = obtener_datos_planta()

# =====================================================================
# 2. DISEÑO DE LA INTERFAZ EN COLUMNAS (VISOR vs CONTROL)
# =====================================================================
col_visor, col_historial = st.columns([3, 2])

# --- COLUMNA IZQUIERDA: EL GEMELO DIGITAL 3D ---
with col_visor:
    st.subheader("🌐 Vista del Gemelo Digital")
    
    # Leer archivo 3D y convertir a Base64
    glb_data_uri = ""
    ruta_glb = pathlib.Path(__file__).parent / "static" / "forklift_low_poly.glb"
     
    if ruta_glb.exists():
        with open(ruta_glb, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        glb_data_uri = f"data:model/gltf-binary;base64,{b64}"
        
        # Interfaz HTML limpia (eliminado el raycasting problemático)
        html_viewer = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ margin: 0; padding: 0; overflow: hidden; background: #f1f5f9; }}
                #canvas-container {{ width: 100%; height: 500px; position: relative; }}
                #status {{
                    position: absolute; bottom: 10px; left: 10px;
                    background: rgba(0,32,74,0.85); color: #fff;
                    padding: 6px 12px; border-radius: 4px;
                    font-family: monospace; font-size: 11px; pointer-events: none;
                }}
            </style>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
        </head>
        <body>
            <div id="canvas-container">
                <div id="status">⏳ Cargando modelo 3D...</div>
            </div>
         
            <script>
            const container = document.getElementById('canvas-container');
            const status = document.getElementById('status');
         
            const scene = new THREE.Scene();
            scene.background = new THREE.Color(0xf1f5f9);
            const camera = new THREE.PerspectiveCamera(45, container.clientWidth / 500, 0.01, 10000);
         
            const renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(container.clientWidth, 500);
            renderer.setPixelRatio(window.devicePixelRatio);
            container.appendChild(renderer.domElement);
         
            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
         
            scene.add(new THREE.AmbientLight(0xffffff, 0.9));
            const dir = new THREE.DirectionalLight(0xffffff, 0.7);
            dir.position.set(5, 20, 10);
            scene.add(dir);
         
            const loader = new THREE.GLTFLoader();
            const dataURI = "{glb_data_uri}";
         
            setTimeout(() => {{
                const b64 = dataURI.split(',')[1];
                const binary = atob(b64);
                const bytes = new Uint8Array(binary.length);
                for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
         
                loader.parse(bytes.buffer, '', (gltf) => {{
                    const model = gltf.scene;
                    scene.add(model);
         
                    const box = new THREE.Box3().setFromObject(model);
                    const center = box.getCenter(new THREE.Vector3());
                    const size = box.getSize(new THREE.Vector3());
                    model.position.sub(center);
         
                    const dist = Math.max(size.x, size.y, size.z) * 1.8;
                    camera.position.set(dist, dist * 0.8, dist);
                    camera.lookAt(0, 0, 0);
                    controls.target.set(0, 0, 0);
                    controls.update();
         
                    status.innerText = "✅ Sistema 3D Activo";
                }}, (err) => {{ status.innerText = "❌ Error al cargar"; }});
            }}, 50);
         
            (function animate() {{
                requestAnimationFrame(animate);
                controls.update();
                renderer.render(scene, camera);
            }})();
            </script>
        </body>
        </html>
        """
        components.html(html_viewer, height=510)
    else:
        st.error("⚠️ Archivo `static/forklift_low_poly.glb` no detectado.")

# --- COLUMNA DERECHA: SELECCIÓN E HISTORIAL DE MANTENIMIENTO ---
with col_historial:
    st.subheader("📋 Auditoría de Componentes")
    
    # Selector Amigable para el Operario
    opciones_componentes = {
        "wheel": "🛞 Sistema de Rodamiento (Llantas)",
        "loader_car": "🚜 Chasis, Motor, Gasolina y Batería",
        "mast": "🏗️ Mástil de Elevación e Hidráulicos",
        "fork": "🔱 Horquillas y Uñas de Carga"
    }
    
    seleccion = st.selectbox(
        "Selecciona el componente que deseas auditar:",
        options=list(opciones_componentes.keys()),
        format_func=lambda x: opciones_componentes[x]
    )
    
    st.divider()
    
    # Filtrar datos en tiempo real basados en la selección
    if not df_planta.empty and 'COMPONENTE' in df_planta.columns:
        df_filtrado = df_planta[df_planta['COMPONENTE'].str.strip().str.lower() == seleccion]
        
        if not df_filtrado.empty:
            st.success(f"Se encontraron {len(df_filtrado)} registros para esta pieza:")
            
            # Renderizar cada mantenimiento como una tarjeta estilizada
            for _, fila in df_filtrado.iterrows():
                estado_raw = str(fila.get('ESTADO', '')).strip().upper()
                
                # Definir color del contenedor según el estado
                if "CRIT" in estado_raw or "MALO" in estado_raw:
                    tipo_alerta = "error"
                    emoji = "🔴"
                elif "ALER" in estado_raw or "REVIS" in estado_raw:
                    tipo_alerta = "warning"
                    emoji = "🟡"
                else:
                    tipo_alerta = "info"
                    emoji = "🟢"
                
                # Contenedor visual nativo de Streamlit
                with st.container():
                    st.markdown(f"### {emoji} {fila.get('NOMBRE DE LA PIEZA', 'Componente')}")
                    st.caption(f"📅 **Fecha:** {fila.get('FECHA', '---')}  |  👤 **Técnico:** {fila.get('NOMBRE DEL OPERARIO', 'No asignado')}")
                    st.info(f"**Descripción:** {fila.get('DESCRIPCION DEL MANTENIMIENTO', 'Sin detalles')}")
                    st.divider()
        else:
            st.info("ℹ️ No hay mantenimientos registrados aún para este componente a través de Google Forms.")
    else:
        st.warning("No se pudieron extraer datos de la hoja de cálculo. Revisa la configuración de compartir.")
