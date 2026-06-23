import streamlit as st
import streamlit.components.v1 as components
import json
import base64
import os

st.set_page_config(page_title="Forklift Twin Pro", layout="wide", page_icon="🚜")

st.title("🚜 Gemelo Digital Operacional - Montacargas Pro")
st.markdown("Ecosistema de Mantenimiento 4.0. Haz clic directamente sobre las piezas del modelo 3D para auditar su historial técnico.")

# 1. BASE DE DATOS EN PYTHON
historial_mantenimiento = {
    "default": {
        "titulo": "Instrucciones de Inspección",
        "detalles": "Haz clic en cualquier componente del montacargas (llantas, torre, cabina) para desplegar las órdenes de servicio asociadas al código QR de planta."
    },
    "wheel": {
        "titulo": "Sistema de Rodamiento (Llantas)",
        "detalles": "🔴 2026-06-15: Reporte QR indica desgaste excesivo en banda de rodadura. Técnico: M. Gómez.<br>🟢 2026-03-10: Rotación y balanceo preventivo general."
    },
    "mast": {
        "titulo": "Mástil de Elevación e Hidráulicos",
        "detalles": "🟢 2026-05-22: Lubricación de cadenas de carga con grasa grafitada. Ajuste de mangueras de alta presión. Técnico: Ing. Silva."
    },
    "body": {
        "titulo": "Estructura Principal y Chasis",
        "detalles": "🟢 2026-01-10: Inspección de soldaduras críticas y anclajes de motor. Sin novedades estructurales."
    }
}

json_data = json.dumps(historial_mantenimiento)

# ======================================================================
# 2. LECTURA Y CONVERSIÓN AUTOMÁTICA DESDE TU CARPETA DE DESCARGAS
# ======================================================================
glb_base64 = ""

# 'os.path.expanduser("~")' encuentra automáticamente la carpeta principal de tu usuario en Windows/Mac
ruta_en_descargas_con_assets = os.path.expanduser("~/Downloads/assets/forklift_low_poly.glb")
ruta_en_descargas_suelto = os.path.expanduser("~/Downloads/forklift_low_poly.glb")

# 1. Intentamos buscarlo dentro de la carpeta assets en Descargas
if os.path.exists(ruta_en_descargas_con_assets):
    ruta_final = ruta_en_descargas_con_assets
# 2. Si no, lo buscamos suelto directamente en Descargas
elif os.path.exists(ruta_en_descargas_suelto):
    ruta_final = ruta_en_descargas_suelto
else:
    ruta_final = None
    st.error("⚠️ No encontré el archivo .glb en tu carpeta de Descargas. Asegúrate de que se llame exactamente 'forklift_low_poly.glb'")

# Si lo encontró, lo procesamos para el lienzo 3D
if ruta_final:
    with open(ruta_final, "rb") as f:
        glb_base64 = base64.b64encode(f.read()).decode("utf-8")
# 3. INTERFAZ EN EMBED CON ENTRADA BINARIA
three_js_interface = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0; padding: 0; overflow: hidden;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f8fafc; display: flex;
        }}
        #canvas-container {{ width: 65%; height: 550px; position: relative; }}
        #sidebar-panel {{
            width: 35%; height: 530px; background: #ffffff;
            box-shadow: -4px 0 15px rgba(0,0,0,0.05); padding: 20px;
            box-sizing: border-box; overflow-y: auto; border-left: 2px solid #e2e8f0;
        }}
        .badge {{
            background: #008891; color: white; padding: 5px 10px;
            border-radius: 4px; font-size: 12px; font-weight: bold;
        }}
        h3 {{ color: #00204A; margin-top: 10px; }}
        p {{ color: #475569; line-height: 1.5; font-size: 14px; }}
        #debug-log {{
            position: absolute; bottom: 10px; left: 10px;
            background: rgba(0, 32, 74, 0.9); color: #ffffff;
            padding: 8px 12px; border-radius: 4px;
            font-family: monospace; font-size: 11px; pointer-events: none; z-index: 100;
        }}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>

    <div id="canvas-container">
        <div id="debug-log">Estado: Decodificando binario local...</div>
    </div>
    
    <div id="sidebar-panel">
        <span class="badge">HISTORIAL DE PLANTA</span>
        <h3 id="part-title">Instrucciones de Inspección</h3>
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 15px 0;">
        <p id="part-details">Haz clic en cualquier componente del montacargas para desplegar las órdenes de servicio asociadas al código QR de planta.</p>
    </div>

    <script>
        const baseDatos = {json_data};
        const container = document.getElementById('canvas-container');
        const log = document.getElementById('debug-log');

        // CONFIGURACIÓN DE ESCENA
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf1f5f9);

        const camera = new THREE.PerspectiveCamera(45, container.clientWidth / 550, 0.01, 10000);
        
        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
        renderer.setSize(container.clientWidth, 550);
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.shadowMap.enabled = true;
        container.appendChild(renderer.domElement);

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;

        // ILUMINACIÓN
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
        scene.add(ambientLight);
        
        const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight1.position.set(5, 20, 10);
        scene.add(dirLight1);

        const loader = new THREE.GLTFLoader();
        let forkliftModel = null;

        // PROCESAR STRING BASE64 DESDE PYTHON
        const rawBase64 = "{glb_base64}";

        if (rawBase64 !== "") {{
            // Conversión interna a ArrayBuffer para Three.js
            const binaryString = window.atob(rawBase64);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {{
                bytes[i] = binaryString.charCodeAt(i);
            }}
            const arrayBuffer = bytes.buffer;

            // Inyección directa del modelo sin llamadas HTTP externo
            loader.parse(arrayBuffer, '', function(gltf) {{
                forkliftModel = gltf.scene;
                scene.add(forkliftModel);
                
                // Enfoque automático de cámara
                const box = new THREE.Box3().setFromObject(forkliftModel);
                const center = box.getCenter(new THREE.Vector3());
                const size = box.getSize(new THREE.Vector3());
                
                forkliftModel.position.x += (forkliftModel.position.x - center.x);
                forkliftModel.position.y += (forkliftModel.position.y - center.y);
                forkliftModel.position.z += (forkliftModel.position.z - center.z);
                
                const maxDim = Math.max(size.x, size.y, size.z);
                const cameraDist = maxDim * 1.8;
                
                camera.position.set(cameraDist, cameraDist * 0.8, cameraDist);
                camera.lookAt(0, 0, 0);
                
                controls.target.set(0, 0, 0);
                controls.update();
                
                log.innerText = "Estado: ¡Gemelo digital activo! Toca una pieza.";
            }}, function(error) {{
                log.innerText = "Error crítico al procesar la geometría 3D.";
                console.error(error);
            }});
        }} else {{
            log.innerText = "Error: Falta la cadena binaria del modelo.";
        }}

        // EVENTO DE CLIC
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();

        window.addEventListener('click', function(event) {{
            const rect = renderer.domElement.getBoundingClientRect();
            mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

            raycaster.setFromCamera(mouse, camera);
            if (forkliftModel) {{
                const intersects = raycaster.intersectObjects(forkliftModel.children, true);
                
                if (intersects.length > 0) {{
                    const piezaTocada = intersects[0].object;
                    const nombrePieza = piezaTocada.name.toLowerCase();
                    
                    log.innerText = "ID de Pieza: " + piezaTocada.name;

                    let encontrada = false;
                    for (let clave in baseDatos) {{
                        if (nombrePieza.includes(clave)) {{
                            document.getElementById('part-title').innerText = baseDatos[clave].titulo;
                            document.getElementById('part-details').innerHTML = baseDatos[clave].detalles;
                            encontrada = true;
                            break;
                        }}
                    }}
                    
                    if(!encontrada) {{
                        document.getElementById('part-title').innerText = "Pieza: " + piezaTocada.name;
                        document.getElementById('part-details').innerHTML = "<i>Operando bajo parámetros nominales. No registra alertas en el sistema QR.</i>";
                    }}
                }}
            }}
        }});

        function animate() {{
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }}
        animate();
    </script>
</body>
</html>
"""

components.html(three_js_interface, height=560)
