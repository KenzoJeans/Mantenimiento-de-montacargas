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
# MAPEO CENTRALIZADO DE COMPONENTES
# (antes vivía disperso en un if/elif; ahora es un solo lugar fácil de
#  extender). Se reconocen las opciones NUEVAS y exactas del formulario
#  ("Llantas y ruedas", "Sistema hidráulico", etc.) por palabra clave, y
#  además se conservan los valores VIEJOS en inglés (wheel/mast/fork/...)
#  por si quedan reportes históricos guardados con esos valores.
# =====================================================================

# Valores históricos exactos (formulario anterior) → clave interna
LEGADO_COMPONENTE = {
    "wheel": "llantas", "loader_car": "chasis", "body": "chasis",
    "mast": "mastil", "fork": "unas", "horas": "horometro", "tablero": "horometro",
}

# Palabras clave del formulario NUEVO → clave interna. Se revisan en orden
# y basta con que la palabra clave aparezca dentro del texto de la opción
# (tolera variaciones menores de redacción en el formulario).
REGLAS_COMPONENTE_NUEVO = [
    (["llanta", "rueda"], "llantas"),
    (["mastil", "cadena"], "mastil"),
    (["horquilla"], "unas"),
    (["hidraulico"], "hidraulico"),
    (["motor"], "motor"),
    (["freno"], "frenos"),
    (["direccion"], "direccion"),
    (["chasis", "estructura", "techo"], "chasis"),
    (["luces", "bocina", "alarma"], "luces"),
    (["horometro", "tablero"], "horometro"),
]

def normalizar_componente(valor_crudo: str) -> str:
    parte = str(valor_crudo).strip().lower()
    for viejo, nuevo in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")]:
        parte = parte.replace(viejo, nuevo)

    if parte in LEGADO_COMPONENTE:
        return LEGADO_COMPONENTE[parte]

    for palabras_clave, clave_interna in REGLAS_COMPONENTE_NUEVO:
        if any(palabra in parte for palabra in palabras_clave):
            return clave_interna

    return parte  # valor no reconocido: se conserva tal cual como respaldo


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


# Nombre EXACTO de la pregunta "Subir archivos" en el formulario. Si
# cambias el texto de la pregunta en Google Forms, el encabezado de la
# columna en la hoja cambia también, y hay que actualizarlo aquí.
COLUMNA_FOTO = "EVIDENCIA DEL MANTENIMIENTO"


def _extraer_id_drive(url: str) -> str | None:
    m = re.search(r"[?&]id=([\w-]+)", url) or re.search(r"/d/([\w-]+)", url)
    return m.group(1) if m else None


def extraer_urls_fotos(valor_crudo) -> list[str]:
    """Convierte lo que Google Forms guarda para una pregunta de 'Subir
    archivos' (uno o varios links de Drive separados por coma) en URLs
    de miniatura que sí se pueden usar directamente en un <img src=...>.
    Cualquier valor que no sea un link real de Drive se descarta."""
    if valor_crudo is None:
        return []
    texto = str(valor_crudo).strip()
    if not texto or texto.lower() == "nan":
        return []
    urls = []
    for enlace in texto.split(","):
        enlace = enlace.strip()
        if not enlace.startswith("https://drive.google.com"):
            continue
        file_id = _extraer_id_drive(enlace)
        if file_id:
            urls.append(f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000")
    return urls


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
    registros_tabla = []

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

            # Evidencia fotográfica: cada foto se muestra como miniatura
            # clicable (abre el tamaño real en una pestaña nueva). Las
            # URLs ya vienen validadas (solo links reales de Drive), pero
            # igual se escapan al insertarlas por seguridad.
            urls_fotos = extraer_urls_fotos(fila.get(COLUMNA_FOTO, ""))
            fotos_html = ""
            if urls_fotos:
                miniaturas = "".join(
                    f"<a href='{html.escape(u)}' target='_blank' rel='noopener'>"
                    f"<img src='{html.escape(u)}' loading='lazy' "
                    f"style='width:88px;height:88px;object-fit:cover;border-radius:6px;"
                    f"margin:6px 6px 0 0;border:1px solid #334155;'></a>"
                    for u in urls_fotos
                )
                fotos_html = f"<div>{miniaturas}</div>"

            if parte not in historial:
                historial[parte] = {"titulo": nombre_visible, "detalles": ""}

            linea_reporte = (
                f"{estado} <b style='color:#f8fafc;'>{fecha}</b>: "
                f"<span style='color:#cbd5e1;'>{descripcion}</span><br>"
                f"<small style='color:#94a3b8;'>👤 Operario: {tecnico}</small>"
                f"{fotos_html}"
                f"<br><br><hr style='border:0;border-top:1px dashed #334155;'>"
            )
            historial[parte]["detalles"] += linea_reporte

            # Fila para la tabla-resumen que va debajo del visor 3D.
            # Se usa el texto SIN escapar (el escape de arriba es solo
            # para insertar en el HTML del iframe); st.dataframe ya
            # maneja el texto de forma segura por su cuenta.
            registros_tabla.append({
                "Fecha": str(fila.get("FECHA", fila.get("Marca temporal", "---"))),
                "Operario": str(fila.get("NOMBRE DEL OPERARIO", "—")),
                "Componente": str(fila.get("NOMBRE DE LA PIEZA", "—")),
                "Estado": estado_raw,
                "Horómetro": limpiar_numero(fila.get("HOROMETRO")),
                "Foto": urls_fotos[0] if urls_fotos else None,
            })

    except Exception as e:
        error_msg = str(e)

    horometro_txt = f"{horometro_val:,.0f} Hrs" if horometro_val is not None else "Sin datos"
    return json.dumps(historial), horometro_txt, total_reportes, pct_preventivo, error_msg, registros_tabla


col_titulo, col_boton = st.columns([6, 1])
with col_boton:
    if st.button("🔄 Actualizar ahora"):
        cargar_historial_y_metricas.clear()

json_data, horometro_val, total_reportes, pct_preventivo, error_msg, registros_tabla = cargar_historial_y_metricas()

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
            <option value="llantas">🛞 Llantas y ruedas</option>
            <option value="mastil">🏗️ Mástil y cadenas elevadoras</option>
            <option value="unas">🔱 Horquillas / uñas</option>
            <option value="hidraulico">🛢️ Sistema hidráulico</option>
            <option value="motor">⚙️ Motor</option>
            <option value="frenos">🛑 Sistema de frenos</option>
            <option value="direccion">🎯 Dirección</option>
            <option value="chasis">🚜 Chasis / estructura / techo protector</option>
            <option value="luces">💡 Luces, bocina y alarma</option>
            <option value="horometro">⏱️ Horómetro y tablero</option>
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

    // --- Estado para el "camera framing" al cambiar de componente ---
    let distanciaGeneral = 10;
    let vistaGeneralPos = new THREE.Vector3(10, 7, 10);
    let vistaGeneralTarget = new THREE.Vector3(0, 0, 0);
    let animacionCamaraId = null;

    // Si el usuario agarra el mouse/touch mientras la cámara se está
    // moviendo sola, se cancela la animación para que no "peleen" entre sí.
    controls.addEventListener('start', () => {{
        if (animacionCamaraId) {{
            cancelAnimationFrame(animacionCamaraId);
            animacionCamaraId = null;
        }}
    }});

    function facilitarSuavizado(t) {{
        // easeInOutQuad
        return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    }}

    function animarCamaraHacia(posicionObjetivo, objetivoMirada, duracionMs = 700) {{
        if (animacionCamaraId) cancelAnimationFrame(animacionCamaraId);

        const posInicial = camera.position.clone();
        const miraInicial = controls.target.clone();
        const inicio = performance.now();

        function paso(ahora) {{
            const t = Math.min((ahora - inicio) / duracionMs, 1);
            const avance = facilitarSuavizado(t);

            camera.position.lerpVectors(posInicial, posicionObjetivo, avance);
            controls.target.lerpVectors(miraInicial, objetivoMirada, avance);
            controls.update();

            if (t < 1) {{
                animacionCamaraId = requestAnimationFrame(paso);
            }} else {{
                animacionCamaraId = null;
            }}
        }}
        animacionCamaraId = requestAnimationFrame(paso);
    }}

    function enfocarComponente(clave) {{
        if (clave === 'default') {{
            animarCamaraHacia(vistaGeneralPos, vistaGeneralTarget);
            return;
        }}
        const pin = listaPines.find(p => p.name === clave);
        if (!pin) return;

        // Distancia de acercamiento proporcional al tamaño del modelo,
        // más cerca que la vista general pero sin "meterse" en la geometría.
        const distanciaAcercamiento = distanciaGeneral * 0.4;
        const direccion = new THREE.Vector3(0.9, 0.55, 0.9).normalize();
        const posicionObjetivo = pin.position.clone().add(direccion.multiplyScalar(distanciaAcercamiento));

        animarCamaraHacia(posicionObjetivo, pin.position.clone());
    }}

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

                // Se guarda la vista general para poder volver a ella
                // cuando el usuario elija "Seleccionar zona..." de nuevo.
                distanciaGeneral = dist;
                vistaGeneralPos = camera.position.clone();
                vistaGeneralTarget = controls.target.clone();

                const dimensionMaxima = Math.max(size.x, size.y, size.z);
                const radioProporcional = dimensionMaxima * 0.035;

                const pX = size.x;
                const pY = size.y;
                const pZ = size.z;

                // Posiciones proporcionales estimadas (0 = centro del modelo).
                // +Z = frente (lado de las horquillas), -Z = atrás (contrapeso).
                // Son un punto de partida razonable para un montacargas de
                // contrapeso típico — pruébalas contra tu .glb real y ajusta
                // los multiplicadores si algún pin queda mal ubicado.
                agregarPin3D('llantas',    pX * 0.32,  -pY * 0.20,   pZ * 0.15, 0x00f2fe, radioProporcional);
                agregarPin3D('mastil',     0.0,         pY * 0.08,   pZ * 0.30, 0xf59e0b, radioProporcional);
                agregarPin3D('unas',       0.0,        -pY * 0.32,   pZ * 0.46, 0xec4899, radioProporcional);
                agregarPin3D('hidraulico', pX * 0.15,  -pY * 0.10,   pZ * 0.05, 0x06b6d4, radioProporcional);
                agregarPin3D('motor',      0.0,        -pY * 0.05,  -pZ * 0.35, 0xef4444, radioProporcional);
                agregarPin3D('frenos',    -pX * 0.32,  -pY * 0.20,   pZ * 0.15, 0xf97316, radioProporcional);
                agregarPin3D('direccion',  0.0,         pY * 0.30,   pZ * 0.05, 0x84cc16, radioProporcional);
                agregarPin3D('chasis',     0.0,         pY * 0.05,  -pZ * 0.12, 0x3b82f6, radioProporcional);
                agregarPin3D('luces',      pX * 0.20,   pY * 0.35,   pZ * 0.20, 0xfacc15, radioProporcional);
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
                'llantas': '🛞 Llantas y ruedas',
                'mastil': '🏗️ Mástil y cadenas elevadoras',
                'unas': '🔱 Horquillas / uñas',
                'hidraulico': '🛢️ Sistema hidráulico',
                'motor': '⚙️ Motor',
                'frenos': '🛑 Sistema de frenos',
                'direccion': '🎯 Dirección',
                'chasis': '🚜 Chasis / estructura / techo protector',
                'luces': '💡 Luces, bocina y alarma',
                'horometro': '⏱️ Horómetro y tablero'
            }};
            document.getElementById('part-title').innerText   = titulosAlternativos[clave] || "Componente";
            document.getElementById('part-details').innerHTML = "<i style='color:#94a3b8;'>No se registran órdenes de servicio activas para esta sección en Google Sheets.</i>";
        }}
        status.innerText = "📍 Componente auditado: " + clave.toUpperCase();
        enfocarComponente(clave);
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

# =====================================================================
# 4. TABLA RESUMEN DE EVIDENCIAS (Google Drive)
# =====================================================================
st.markdown("---")
st.subheader("📁 Resumen de evidencias fotográficas")

if registros_tabla:
    df_tabla = pd.DataFrame(registros_tabla)
    st.dataframe(
        df_tabla,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Foto": st.column_config.ImageColumn(
                "Evidencia", help="Foto de evidencia del mantenimiento"
            ),
            "Horómetro": st.column_config.NumberColumn(
                "Horómetro (Hrs)", format="%.0f"
            ),
        },
    )
    st.caption(
        "Haz clic en una foto para verla más grande. Esta tabla lee la misma "
        "hoja de Google que alimenta el visor 3D — se actualiza con el botón "
        "'🔄 Actualizar ahora' de arriba."
    )
else:
    st.info("Todavía no hay reportes con evidencia fotográfica registrados.")
