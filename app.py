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

# ========== AUTENTICACIÓN ==========
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)

# Hojas
sheet = client.open("FormularioEscaneo")
base_datos = sheet.worksheet("base_datos")
registros = sheet.worksheet("registros")

# Cargar base_datos
try:
    df = pd.DataFrame(base_datos.get_all_records())
except Exception:
    df = pd.DataFrame(columns=["documento", "nombre completo", "celular"])

# Control navegación
if "fase" not in st.session_state:
    st.session_state.fase = "formulario"

if "codigo_detectado" not in st.session_state:
    st.session_state.codigo_detectado = None
if "codigo_escaneado" not in st.session_state:
    st.session_state.codigo_escaneado = None

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
            st.warning("Documento no encontrado.")

            if st.button("Registrar nuevo usuario"):
                st.session_state.nuevo_documento = str(documento)
                st.session_state.fase = "nuevo_registro"
                st.rerun()

# -------------------------------
# FASE 2: NUEVO REGISTRO
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
                base_datos.append_row([str(documento), str(nombre), str(celular)])
                st.success("Usuario registrado correctamente.")
            except Exception:
                st.error("Error guardando en base_datos.")
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
# FASE 3: ESCANEO
# -------------------------------
elif st.session_state.fase == "escaneo":
    st.title("📷 Escanear código")
    st.markdown("Apunta la cámara al código. Cuando suene, aparecerá el botón para continuar.")

    # Audio
    st.markdown("""
        <audio id="beep" src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg"></audio>
    """, unsafe_allow_html=True)

    # Escáner
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
                            parent.document.getElementById('beep').play();
                            localStorage.setItem("codigo_detectado", result.text);
                            codeReader.reset();
                        }
                    });
                })();
            </script>

        </body>
        </html>
        """,
        height=350,
    )

    # Capturar código desde localStorage
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

    # Pasar código a URL
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

    # Recuperar param
    params = st.experimental_get_query_params()
    if "codigo" in params:
        st.session_state.codigo_detectado = params["codigo"][0]
        st.experimental_set_query_params()  # limpiar

    # Mostrar resultado
    if st.session_state.codigo_detectado:
        st.success(f"✔ Código detectado: **{st.session_state.codigo_detectado}**")

        if st.button("➡ Usar código escaneado"):
            st.session_state.codigo_escaneado = st.session_state.codigo_detectado
            st.session_state.fase = "confirmar"
            st.rerun()
    else:
        st.info("📲 Escanee el código para continuar…")

    # Manual
    st.markdown("---")
    manual = st.text_input("Ingreso manual del código")

    if st.button("Usar código manual"):
        if manual.strip() == "":
            st.warning("Ingrese un código válido.")
        else:
            st.session_state.codigo_escaneado = manual.strip()
            st.session_state.fase = "confirmar"
            st.rerun()

    if st.button("Volver"):
        st.session_state.fase = "formulario"
        st.rerun()

# ======================================
# FASE 4: CONFIRMAR Y GUARDAR (+ VALIDACIÓN)
# ======================================
elif st.session_state.fase == "confirmar":
    st.title("✅ Confirmar registro")

    codigo = st.session_state.codigo_escaneado
    documento = st.session_state.documento

    st.success(f"Código detectado: {codigo}")

    # Cargar registros existentes
    df_reg = pd.DataFrame(registros.get_all_records())

    # ============================
    # VALIDACIONES NUEVAS
    # ============================

    # 1️⃣ El documento ya registró un código
    if not df_reg.empty and documento in df_reg["documento"].astype(str).values:
        st.error("🚫 Este documento YA registró un código.")
        if st.button("Volver al inicio"):
            st.session_state.fase = "formulario"
            st.rerun()
        st.stop()

    # 2️⃣ El código está repetido
    if not df_reg.empty and codigo in df_reg["codigo"].astype(str).values:
        st.error("🚫 Este código ya fue registrado por OTRA persona.")
        st.warning("Debe escanear un código diferente.")

        if st.button("Volver a escanear"):
            st.session_state.fase = "escaneo"
            st.rerun()

        st.stop()

    # =====================================
    # GUARDAR SI TODO ES VÁLIDO
    # =====================================
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
        st.rerun()
