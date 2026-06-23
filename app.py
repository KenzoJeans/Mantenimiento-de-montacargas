import streamlit as st
import streamlit.components.v1 as components
import json
import base64
import pathlib

st.set_page_config(page_title="Forklift Twin Pro", layout="wide", page_icon="🚜")

st.title("🚜 Gemelo Digital Operacional - Montacargas Pro")
st.markdown("Ecosistema de Mantenimiento 4.0. Haz clic directamente sobre las piezas del modelo 3D para auditar su historial técnico.")

# 1. BASE DE DATOS DE MANTENIMIENTO
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

# 2. LECTURA DEL MODELO .glb DESDE LA CARPETA assets/ DEL REPOSITORIO
# ✅ Funciona tanto localmente como en Streamlit Cloud
glb_base64 = ""

ruta_glb = pathlib.Path(__file__).parent / "assets" / "forklift_low_poly.glb"

if ruta_glb.exists():
    with open(ruta_glb, "rb") as f:
        glb_base64 = base64.b64encode(f.read()).decode("utf-8")
else:
    st.error(
        "⚠️ Modelo 3D no encontrado en `assets/forklift_low_poly.glb`. "
        "Asegúrate de subir el archivo al repositorio dentro de la carpeta `assets/`."
    )

# 3. INTERFAZ HTML + THREE.JS
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
        <div id="debug-log">Estado: Decodificando modelo 3D...</div>
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

        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(container.clientWidth, 550);
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.shadowMap.enabled = true;
        container.appendChild(renderer.domElement);

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;

        // ILUMINACIÓN
        scene.add(new THREE.AmbientLight(0xffffff, 0.9));
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight.position.set(5, 20, 10);
        scene.add(dirLight);

        const loader = new THREE.GLTFLoader();
        let forkliftModel = null;

        // DECODIFICAR BASE64 → ArrayBuffer → Three.js (sin llamadas HTTP)
        const rawBase64 = "{glb_base64}";

        if (rawBase64 !== "") {{
            const binaryString = window.atob(rawBase64);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {{
                bytes[i] = binaryString.charCodeAt(i);
            }}

            loader.parse(bytes.buffer, '', function(gltf) {{
                forkliftModel = gltf.scene;
                scene.add(forkliftModel);

                // Centrar y enfocar cámara automáticamente
                const box = new THREE.Box3().setFromObject(forkliftModel);
                const center = box.getCenter(new THREE.Vector3());
                const size = box.getSize(new THREE.Vector3());

                forkliftModel.position.sub(center);

                const maxDim = Math.max(size.x, size.y, size.z);
                const dist = maxDim * 1.8;
                camera.position.set(dist, dist * 0.8, dist);
                camera.lookAt(0, 0, 0);
                controls.target.set(0, 0, 0);
                controls.update();

                log.innerText = "✅ Gemelo digital activo — toca una pieza";
            }}, function(error) {{
                log.innerText = "❌ Error al procesar la geometría 3D";
                console.error(error);
            }});
        }} else {{
            log.innerText = "❌ Cadena base64 vacía — revisa que el archivo .glb está en assets/";
        }}

        // DETECCIÓN DE CLIC SOBRE PIEZAS
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
                    const pieza = intersects[0].object;
                    const nombre = pieza.name.toLowerCase();
                    log.innerText = "ID de pieza: " + pieza.name;

                    let encontrada = false;
                    for (let clave in baseDatos) {{
                        if (nombre.includes(clave)) {{
                            document.getElementById('part-title').innerText = baseDatos[clave].titulo;
                            document.getElementById('part-details').innerHTML = baseDatos[clave].detalles;
                            encontrada = true;
                            break;
                        }}
                    }}

                    if (!encontrada) {{
                        document.getElementById('part-title').innerText = "Pieza: " + pieza.name;
                        document.getElementById('part-details').innerHTML =
                            "<i>Operando bajo parámetros nominales. No registra alertas en el sistema QR.</i>";
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
