import streamlit as st
import streamlit.components.v1 as components
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Configuración
st.set_page_config(page_title="Escaneo", layout="centered")

# Conexión con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
client = gspread.authorize(creds)

registros = client.open("FormularioEscaneo").worksheet("registros")

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

# Captura del código
codigo = st.experimental_get_query_params().get("codigo", [None])[0]

# Escucha JS
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

# Mostrar y guardar
if codigo:
    st.success(f"Código escaneado: {codigo}")

    if st.button("Guardar registro"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        registros.append_row([
            now,
            st.session_state.get("documento", ""),
            st.session_state.get("nombre", ""),
            st.session_state.get("celular", ""),
            codigo
        ])
        st.success("✅ Registro guardado correctamente.")