import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components

# Configuración de la página
st.set_page_config(page_title="Formulario con escaneo", layout="centered")

# Autenticación con Google Sheets usando st.secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
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
    st.markdown("Apunta la cámara al código de barras del certificado electoral.")

    # Escáner con QuaggaJS para códigos de barras lineales
    components.html(
        """
        <iframe srcdoc='
        <html>
        <head>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/quagga/0.12.1/quagga.min.js"></script>
        </head>
        <body>
            <div id="scanner" style="width: 100%; height: 300px;"></div>
            <p id="result">Esperando escaneo...</p>
            <script>
                Quagga.init({
                    inputStream: {
                        name: "Live",
                        type: "LiveStream",
                        target: document.querySelector("#scanner"),
                        constraints: {
                            facingMode: "environment"
                        }
                    },
                    decoder: {
                        readers: ["code_128_reader", "ean_reader", "ean_8_reader"]
                    }
                }, function(err) {
                    if (err) {
                        document.getElementById("result").innerText = "Error: " + err;
                        return;
                    }
                    Quagga.start();
                });

                Quagga.onDetected(function(data) {
                    const code = data.codeResult.code;
                    document.getElementById("result").innerText = code;
                    window.parent.postMessage(code, "*");
                });
            </script>
        </body>
        </html>'
        width="100%" height="400" style="border:none;" allow="camera">
        </iframe>
        """,
        height=420,
    )

    # Captura del código desde la URL
    params = st.query_params
    codigo = params.get("codigo", [None])[0]

    if codigo:
        if st.session_state.get("fase") != "confirmar":
            st.session_state.codigo_escaneado = codigo
            st.session_state.fase = "confirmar"
            st.experimental_set_query_params()
            st.rerun()

    # Listener para recibir el código escaneado
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
        st.experimental_set_query_params()
        st.rerun()
