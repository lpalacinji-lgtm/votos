import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components

# Configuración de la página
st.set_page_config(page_title="Formulario con escaneo", layout="centered")

# Conexión con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
client = gspread.authorize(creds)

# Acceso a las hojas
sheet = client.open("FormularioEscaneo")
base_datos = sheet.worksheet("base_datos")
registros = sheet.worksheet("registros")
df = pd.DataFrame(base_datos.get_all_records())

# Control de navegación
if "fase" not in st.session_state:
    st.session_state.fase = "formulario"

# FASE 1: FORMULARIO
if st.session_state.fase == "formulario":
    st.title("📋 Formulario con escaneo")
    documento = st.text_input("Número de documento")

    if documento:
        resultado = df[df["documento"].astype(str) == documento]
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
        else:
            st.warning("Documento no encontrado en la base de datos.")

# FASE 2: ESCANEO
elif st.session_state.fase == "escaneo":
    st.title("📷 Escanear código de barras")
    st.markdown("Apunta la cámara al código. El contenido se insertará automáticamente.")

    # Escáner HTML5
    components.html(
        """
        <script src="https://unpkg.com/html5-qrcode" type="text/javascript"></script>
        <div id="reader" style="width: 300px;"></div>
        <p id="result">Esperando escaneo...</p>
        <script>
            function onScanSuccess(decodedText, decodedResult) {
                document.getElementById("result").innerText = decodedText;
                window.parent.postMessage(decodedText, "*");
            }
            new Html5Qrcode("reader").start(
                { facingMode: "environment" },
                { fps: 10, qrbox: 250 },
                onScanSuccess
            );
        </script>
        """,
        height=400,
    )

    # Captura del código desde la URL
    params = st.query_params
    codigo = params.get("codigo", [None])[0]

    if codigo:
        if st.session_state.get("fase") != "confirmar":
            st.session_state.codigo_escaneado = codigo
            st.session_state.fase = "confirmar"
            st.experimental_set_query_params()  # Limpia la URL
            st.rerun()

    # Escucha JS para insertar el código en la URL
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

# FASE 3: CONFIRMAR Y GUARDAR
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
        st.experimental_set_query_params()  # Limpia la URL
        st.rerun()