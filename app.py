import streamlit as st
import streamlit.components.v1 as components
import json

st.set_page_config(page_title="Forklift Twin Pro", layout="wide", page_icon="🚜")

st.title("🚜 Gemelo Digital Operacional - Montacargas Pro")
st.markdown("Ecosistema de Mantenimiento 4.0. Haz clic directamente sobre las piezas del modelo 3D para auditar su historial técnico.")

# 1. BASE DE DATOS EN PYTHON (Simulando los reportes del QR)
# NOTA: Los nombres de las claves deben coincidir con los nombres internos de las piezas del GLB.
historial_mantenimiento = {
    "default": {
        "titulo": "Instrucciones de Inspección",
        "detalles": "Haz clic en cualquier componente del montacargas (llantas, torre, cabina) para desplegar las órdenes de servicio asociadas al código QR de planta."
    },
    "wheel": {
        "titulo": "Sistema de Rodamiento (Llantas)",
        "detalles": "🔴 2026-06-15: Reporte QR indica desgaste excesivo en banda de rodadura delantera izquierda. Técnico: M. Gómez.<br>🟢 2026-03-10: Rotación y balanceo preventivo general."
    },
    "mast": {
        "titulo": "Mástil de Elevación e Hidráulicos",
        "detalles": "🟢 2026-05-22: Lubricación de cadenas de carga con grasa grafitada. Ajuste de mangueras de alta presión. Técnico: Ing. Silva."
    },
    "chassis": {
        "titulo": "Estructura Principal y Chasis",
        "detalles": "🟢 2026-01-10: Inspección de soldaduras críticas y anclajes de motor. Sin novedades estructurales."
    }
}

# Convertimos el diccionario de Python a JSON para que JavaScript lo entienda perfectamente
json_data = json.dumps(historial_mantenimiento)

# 2. CONFIGURA AQUÍ TU URL DE GITHUB
# Mientras lo subes, el código usará un modelo alternativo de pruebas para no fallar
URL_TU_MODELO_GLB = "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/master/2.0/Duck/glTF-Binary/Duck.glb" 
# REEMPLAZA por tu link de GitHub cuando esté listo:
# URL_TU_MODELO_GLB = "https://raw.githubusercontent.com/tu_usuario/tu_repo/main/assets/forklift_low_poly.glb"

# 3. INTERFAZ EN EMBED (Lienzo 3D + Panel de Datos integrados en JS)
three_js_interface = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 0;
            overflow: hidden;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f8fafc;
            display: flex;
        }}
        #canvas-container {{
            width: 65%;
            height: 550px;
            position: relative;
        }}
        #sidebar-panel {{
            width: 35%;
            height: 530px;
            background: #ffffff;
            box-shadow: -4px 0 15px rgba(0,0,0,0.05);
            padding: 20px;
            box-sizing: border-box;
            overflow-y: auto;
            border-left: 2px solid #e2e8f0;
        }}
        .badge {{
            background: #008891;
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }}
        h3 {{ color: #00204A; margin-top: 10px; }}
        p {{ color: #475569; line-height: 1.5; font-size: 14px; }}
        #debug-log {{
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(0, 32, 74, 0.8);
            color: #ffffff;
            padding: 8px 12px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 11px;
            pointer-events: none;
        }}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>

    <div id="canvas-container">
        <div id="debug-log">ID de Pieza Detectada: Ninguna (Haz clic en el modelo)</div>
    </div>
    
    <div id="sidebar-panel">
        <span class="badge">HISTORIAL DE PLANTA</span>
        <h3 id="part-title">Instrucciones de Inspección</h3>
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 15px 0;">
        <p id="part-details">Haz clic en cualquier componente del montacargas para desplegar las órdenes de servicio asociadas al código QR de planta.</p>
    </div>

    <script>
        // Cargar los datos desde Python
        const baseDatos = {json_data};

        // ESCENA, CÁMARA Y RENDERIZADOR
        const container = document.getElementById('canvas-container');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf1f5f9);

        const camera = new THREE.PerspectiveCamera(45, container.clientWidth / 550, 0.1, 1000);
        camera.position.set(4, 3, 5);

        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(container.clientWidth, 550);
        renderer.shadowMap.enabled = true;
        container.appendChild(renderer.domElement);

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;

        // LUCES
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
        scene.add(ambientLight);
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight.position.set(5, 12, 7);
        scene.add(dirLight);

        // CARGAR EL MODELO GLB DEL USUARIO
        const loader = new THREE.GLTFLoader();
        let forkliftModel = null;

        loader.load('{URL_TU_MODELO_GLB}', function(gltf) {{
            forkliftModel = gltf.scene;
            scene.add(forkliftModel);
            
            // Ajustar escala si el modelo viene muy grande o pequeño
            forkliftModel.scale.set(1.5, 1.5, 1.5); 
            
            // Centrar
            const box = new THREE.Box3().setFromObject(forkliftModel);
            const center = box.getCenter(new THREE.Vector3());
            forkliftModel.position.x += (forkliftModel.position.x - center.x);
            forkliftModel.position.z += (forkliftModel.position.z - center.z);
        }});

        // RAYCASTING (DETECCIÓN DE CLICS)
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
                    // Conseguimos la pieza exacta y su nombre técnico
                    const piezaTocada = intersects[0].object;
                    const nombrePieza = piezaTocada.name.toLowerCase();
                    
                    // Actualizamos el log de diagnóstico en pantalla
                    document.getElementById('debug-log').innerText = "ID de Pieza Detectada: " + piezaTocada.name;

                    // Buscamos si tenemos historial para esa palabra clave (ej. si el nombre contiene 'wheel' o 'mast')
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
                        document.getElementById('part-details').innerHTML = "<i>Esta pieza no tiene alertas críticas asociadas en el último reporte de mantenimiento QR.</i>";
                    }}
                }}
            }}
        }});

        // ANIMACIÓN
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

# Renderizar el ecosistema integrado en la interfaz de Streamlit
components.html(three_js_interface, height=560)
