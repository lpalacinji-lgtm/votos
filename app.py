import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components

# ======================================
# CONFIGURACIÓN GENERAL
# ======================================
st.set_page_config(page_title="Formulario con escaneo", layout="centered")

# Autenticación
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)

# Hojas
sheet = client.open("FormularioEscaneo")
base_datos = sheet.worksheet("base_datos")
registros = sheet.worksheet("registros")
df = pd.DataFrame(base_datos.get_all_records())

# Control de navegación
if "fase" not in st.session_state:
    st.session_state.fase = "formulario"

# ======================================
# FASE 1: FORMULARIO BÚSQUEDA
# ======================================
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

            st.session_state.documento = documento
            st.session_state.nombre = nombre
            st.session_state.celular = celular

            if st.button("Siguiente: escanear código"):
                st.session_state.fase = "escaneo"
                st.rerun()

        # Si NO existe
        else:
            st.warning("Documento no encontrado en la base de datos.")

            if st.button("Registrar nuevo usuario"):
                st.session_state.nuevo_documento = documento
                st.session_state.fase = "nuevo_registro"
                st.rerun()

# ======================================
# FASE 2: REGISTRAR NUEVO USUARIO
# ======================================
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
            base_datos.append_row([documento, nombre, celular])
            st.success("Usuario registrado correctamente.")

            st.session_state.documento = documento
            st.session_state.nombre = nombre
            st.session_state.celular = celular

            st.session_state.fase = "escaneo"
            st.rerun()

    if st.button("Cancelar"):
        st.session_state.fase = "formulario"
        st.rerun()

# ======================================
# FASE 3: ESCANEO CON CÁMARA
# ======================================
elif st.session_state.fase == "escaneo":
    st.title("📷 Escanear código de barras")
    st.markdown("Apunta la cámara al código del certificado electoral.")

    # Escáner ZXing
    components.html(
        """
        <iframe srcdoc='
        <html>
        <head>
            <script type="text/javascript" src="https://unpkg.com/@zxing/library@latest"></script>
        </head>
        <body>
            <video id="video" width="100%" height="300" style="border:1px solid gray;"></video>
            <p id="result">Esperando escaneo...</p>
            <script>
                const codeReader = new ZXing.BrowserBarcodeReader();
                codeReader.decodeFromVideoDevice(null, "video", (result, err) => {
                    if (result) {
                        document.getElementById("result").innerText = result.text;
                        window.parent.postMessage(result.text, "*");
                        codeReader.reset();
                    }
                });
            </script>
        </body>
        </html>'
        width="100%" height="400" style="border:none;" allow="camera">
        </iframe>
        """,
        height=420,
    )

    # Parámetros URL (CORRECTO)
    params = st.experimental_get_query_params()
    codigo = params.get("codigo", [None])[0]


    if codigo:
        st.session_state.codigo_escaneado = codigo
        st.session_state.fase = "confirmar"
        st.experimental_set_query_params()
        st.rerun()

    st.markdown(
        """
        <script>
        window.addEventListener("message", (event) => {
            const codigo = event.data;
            const url = new URL(window.location);
            url.searchParams.set("codigo", codigo);
            window.location.href = url.toString();
        });
        </script>
        """,
        unsafe_allow_html=True,
    )

    # ---- OPCIÓN MANUAL ----
    st.write("---")
    st.subheader("¿Problemas con la cámara?")

    if st.button("Ingresar código manualmente"):
        st.session_state.fase = "manual"
        st.rerun()

# ======================================
# FASE 4: INGRESO MANUAL DEL CÓDIGO
# ======================================
elif st.session_state.fase == "manual":
    st.title("✍️ Ingreso manual del código")

    codigo_manual = st.text_input("Ingrese el código del certificado electoral")

    if st.button("Continuar"):
        if codigo_manual.strip() == "":
            st.warning("Debe ingresar un código válido.")
        else:
            st.session_state.codigo_escaneado = codigo_manual
            st.session_state.fase = "confirmar"
            st.rerun()

    if st.button("Volver al escáner"):
        st.session_state.fase = "escaneo"
        st.rerun()

# ======================================
# FASE 5: CONFIRMAR Y GUARDAR
# ======================================
elif st.session_state.fase == "confirmar":
    st.title("✅ Código escaneado")
    st.success(f"Código: {st.session_state.codigo_escaneado}")

    if st.button("Guardar registro"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        registros.append_row([
            now,
            st.session_state.documento,
            st.session_state.nombre,
            st.session_state.celular,
            st.session_state.codigo_escaneado
        ])

        st.success("✅ Registro guardado correctamente.")
        st.session_state.fase = "formulario"
        st.experimental_set_query_params()
        st.rerun()



