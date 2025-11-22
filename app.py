import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
import traceback

# ======================================
# CONFIGURACIÓN GENERAL
# ======================================
st.set_page_config(page_title="Formulario con Escaneo", layout="centered")

# ========== AUTENTICACIÓN (NO TOCO TUS CREDENCIALES) ==========
# Sigue usando st.secrets["gcp_service_account"]
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)

# Hojas
sheet = client.open("FormularioEscaneo")
base_datos = sheet.worksheet("base_datos")
registros = sheet.worksheet("registros")

# Cargar base_datos como dataframe (safe)
try:
    df = pd.DataFrame(base_datos.get_all_records())
except Exception:
    df = pd.DataFrame(columns=["documento", "nombre completo", "celular"])

# Control de navegación
if "fase" not in st.session_state:
    st.session_state.fase = "formulario"

# Inicializaciones para códigos
if "codigo_detectado" not in st.session_state:
    st.session_state.codigo_detectado = None
if "codigo_escaneado" not in st.session_state:
    st.session_state.codigo_escaneado = None
if "codigos_guardados" not in st.session_state:
    # intentamos cargar los códigos ya guardados en la hoja 'registros' (columna 5 si existe)
    try:
        vals = registros.get_all_values()
        # asumimos que la columna del código es la 5ª (índice 4) como en tu estructura
        existentes = [row[4] for row in vals[1:] if len(row) >= 5 and row[4] != ""]
        st.session_state.codigos_guardados = set(existentes)
    except Exception:
        st.session_state.codigos_guardados = set()

# -------------------------------
# FASE 1: FORMULARIO BÚSQUEDA
# -------------------------------
if st.session_state.fase == "formulario":
    st.title("📋 Formulario con escaneo")
    documento = st.text_input("Número de documento")

    if documento:
        resultado = df[df["documento"].astype(str) == documento]

        # Si existe el documento
        if not resultado.empty:
            nombre = resultado.iloc[0]["nombre completo"]
            celular = resultado.iloc[0]["celular"]

            st.success(f"Nombre: {nombre}")
            st.success(f"Celular: {celular}")

            st.session_state.documento = str(documento)
            st.session_state.nombre = str(nombre)
            st.session_state.celular = str(celular)

            if st.button("Siguiente: escanear código"):
                st.session_state.fase = "escaneo"
                st.rerun()

        # Si NO existe
        else:
            st.warning("Documento no encontrado en la base de datos.")

            if st.button("Registrar nuevo usuario"):
                st.session_state.nuevo_documento = str(documento)
                st.session_state.fase = "nuevo_registro"
                st.rerun()

# -------------------------------
# FASE 2: REGISTRAR NUEVO USUARIO
# -------------------------------
elif st.session_state.fase == "nuevo_registro":
    st.title("📝 Registrar nuevo usuario")

    documento = st.session_state.get("nuevo_documento", "")
    st.text_input("Documento", value=documento, disabled=True)

    nombre = st.text_input("Nombre completo")
    celular = st.text_input("Celular")

    if st.button("Guardar nuevo usuario"):
        if nombre.strip() == "" or celular.strip() == "":
            st.warning("Debe ingresar todos los datos.")
        else:
            try:
                # Guardar como strings
                base_datos.append_row([str(documento), str(nombre), str(celular)])
                st.success("Usuario registrado correctamente.")
            except Exception as e:
                st.error("Error guardando en base_datos. Revisa permisos / credenciales.")
                st.error(traceback.format_exc())
                st.stop()

            st.session_state.documento = str(documento)
            st.session_state.nombre = str(nombre)
            st.session_state.celular = str(celular)

            st.session_state.fase = "escaneo"
            st.rerun()

    if st.button("Cancelar"):
        st.session_state.fase = "formulario"
        st.rerun()

# -------------------------------
# FASE 3: ESCANEO CON CÁMARA (NUEVA)
# -------------------------------
elif st.session_state.fase == "escaneo":
    st.title("📷 Escanear código")
    st.markdown("Apunta la cámara al código. Cuando suene, aparecerá el botón para continuar.")

    # ====================
    #    SONIDO DEL BEEP
    # ====================
    st.markdown("""
        <audio id="beep" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg"></audio>
    """, unsafe_allow_html=True)

    # ====================
    #   ESCÁNER ZXING
    # ====================
    components.html(
        """
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <script src="https://unpkg.com/@zxing/library@latest"></script>
            <style>
                video { width:100%; height:260px; border-radius:10px; border:1px solid #ccc; }
            </style>
        </head>
        <body>
            <video id="video" autoplay muted playsinline></video>

            <script>
                (async () => {
                    const codeReader = new ZXing.BrowserBarcodeReader();

                    codeReader.decodeFromVideoDevice(null, 'video', (result, err) => {
                        if (result) {
                            // sonido
                            parent.document.getElementById('beep').play();

                            // guardar temporalmente
                            localStorage.setItem("codigo_detectado", result.text);

                            // detener cámara
                            codeReader.reset();
                        }
                    });
                })();
            </script>
        </body>
        </html>
        """,
        height=340,
    )

    # ===============================================
    #   CAPTURAR EL CÓDIGO DESDE LOCALSTORAGE
    # ===============================================
    st.markdown("""
    <script>
        setInterval(() => {
            const code = localStorage.getItem("codigo_detectado");
            if (code) {
                window.parent.postMessage({type:"set_codigo", codigo:code}, "*");
                localStorage.removeItem("codigo_detectado");
            }
        }, 500);
    </script>
    """, unsafe_allow_html=True)

    # ===============================================
    #   PASAR EL CÓDIGO A LOS PARAMS DE LA URL
    # ===============================================
    st.markdown("""
    <script>
    window.addEventListener("message", (event) => {
        if (event.data?.type === "set_codigo") {
            const url = new URL(window.location);
            url.searchParams.set("codigo", event.data.codigo);
            window.location.href = url;
        }
    });
    </script>
    """, unsafe_allow_html=True)

    # ===============================================
    # Recuperar el código desde la URL
    # ===============================================
    params = st.experimental_get_query_params()

    if "codigo" in params:
        st.session_state.codigo_detectado = params["codigo"][0]

        # limpiar URL
        st.experimental_set_query_params()

    # ===============================================
    #  MOSTRAR RESULTADO + BOTÓN CONTINUAR
    # ===============================================
    if st.session_state.codigo_detectado:
        codigo = st.session_state.codigo_detectado
        st.success(f"✔ Código detectado: **{codigo}**")

        if st.button("➡ Usar código escaneado"):
            st.session_state.codigo_escaneado = codigo
            st.session_state.fase = "confirmar"
            st.rerun()

    else:
        st.info("📲 Escanee el código para continuar…")

    # ===============================================
    #   OPCIÓN MANUAL
    # ===============================================
    st.markdown("---")
    manual = st.text_input("Ingreso manual del código")

    if st.button("Usar código manual"):
        if manual.strip() == "":
            st.warning("Ingrese un código válido.")
        else:
            st.session_state.codigo_escaneado = manual.strip()
            st.session_state.fase = "confirmar"
            st.rerun()

    # ===============================================
    # BOTÓN VOLVER
    # ===============================================
    if st.button("Volver"):
        st.session_state.fase = "formulario"
        st.rerun()


# ======================================
# FASE 4: CONFIRMAR Y GUARDAR
# ======================================
elif st.session_state.fase == "confirmar":
    st.title("✅ Código escaneado")
    codigo = st.session_state.codigo_escaneado
    documento = st.session_state.documento

    st.success(f"Código: {codigo}")

    # Cargar registros existentes para validar duplicados
    df_registros = pd.DataFrame(registros.get_all_records())

    # Verificar si el documento ya registró un código
    ya_registrado = False
    if not df_registros.empty:
        ya_registrado = documento in df_registros["documento"].astype(str).values

    if ya_registrado:
        st.error("🚫 Este documento YA registró un código. No puede registrar otro.")
        st.info("Si deseas volver al inicio, presiona el botón de abajo.")

        if st.button("Volver al inicio"):
            st.session_state.fase = "formulario"
            st.experimental_set_query_params()
            st.rerun()

    else:
        # Si NO está registrado → permitir guardar
        if st.button("Guardar registro"):
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            registros.append_row([
                now,
                documento,
                st.session_state.nombre,
                st.session_state.celular,
                codigo
            ])

            st.success("✅ Registro guardado correctamente.")
            st.balloons()

            st.session_state.fase = "formulario"
            st.experimental_set_query_params()
            st.rerun()





