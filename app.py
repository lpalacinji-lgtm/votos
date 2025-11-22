import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components

# ======================================
# CONFIGURACIÓN GENERAL
# ======================================
st.set_page_config(page_title="Formulario con Escaneo", layout="centered")

# Autenticación Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)

# Hojas de cálculo
sheet = client.open("FormularioEscaneo")
base_datos = sheet.worksheet("base_datos")
registros = sheet.worksheet("registros")
df = pd.DataFrame(base_datos.get_all_records())

# Control de navegación
if "fase" not in st.session_state:
    st.session_state.fase = "formulario"

# ======================================
# FASE 1: BÚSQUEDA DE DOCUMENTO
# ======================================
if st.session_state.fase == "formulario":
    st.title("📋 Formulario con escaneo")
    documento = st.text_input("Número de documento")

    if documento:
        resultado = df[df["documento"].astype(str) == documento]

        # SI existe
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

        # SI NO existe → Registrar nuevo usuario
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
# FASE 3: ESCANEO
# ======================================
elif st.session_state.fase == "escaneo":
    st.title("📷 Escanear código de barras")
    st.markdown("Apunta la cámara al código del certificado electoral.")

    # Inicializar lista de códigos si no existe
    if "codigos_escaneados" not in st.session_state:
        st.session_state.codigos_escaneados = []

    # Zona donde se mostrará el código
    codigo_placeholder = st.empty()
    boton_placeholder = st.empty()
    sonido = """
        <audio id="beep">
            <source src="https://actions.google.com/sounds/v1/cartoon/wood_plank_flicks.ogg" type="audio/ogg">
        </audio>
    """

    st.markdown(sonido, unsafe_allow_html=True)

    # IFRAME DEL ESCÁNER
    components.html(
        """
        <html>
        <body style="margin:0">
            <video id="video" width="100%" height="280" style="border:1px solid gray; border-radius:10px;"></video>
            <br>
            <button id="flashBtn" style="padding:8px;border-radius:8px;margin-top:6px;">
                🔦 Flash ON/OFF
            </button>

            <script type="text/javascript" src="https://unpkg.com/@zxing/library@latest"></script>

            <script>
                const codeReader = new ZXing.BrowserBarcodeReader();
                let currentStream = null;

                async function startScanner() {
                    currentStream = await navigator.mediaDevices.getUserMedia({
                        video: { facingMode: "environment" }
                    });

                    document.getElementById("video").srcObject = currentStream;

                    codeReader.decodeFromVideoDevice(null, "video", (result, err) => {
                        if (result) {
                            // Reproduce sonido
                            document.getElementById("beep").play();

                            // Enviar a Streamlit
                            window.parent.postMessage(
                                JSON.stringify({codigo: result.text}),
                                "*"
                            );
                        }
                    });
                }

                startScanner();

                // Flash ON/OFF
                document.getElementById("flashBtn").onclick = () => {
                    const track = currentStream.getVideoTracks()[0];
                    const capabilities = track.getCapabilities();

                    if (capabilities.torch) {
                        const current = track.getSettings().torch || false;
                        track.applyConstraints({ advanced: [{ torch: !current }] });
                    } else {
                        alert("Este dispositivo no soporta flash.");
                    }
                };
            </script>
        </body>
        </html>
        """,
        height=380
    )

    # JS PARA RECIBIR EL CÓDIGO
    st.markdown(
        """
        <script>
        window.addEventListener("message", (event) => {
            const data = JSON.parse(event.data);
            const codigo = data.codigo;

            // Llamar a Streamlit
            window.parent.postMessage(
              { isStreamlitMessage: true, type: "streamlit:setComponentValue", value: codigo },
              "*"
            );
        });
        </script>
        """,
        unsafe_allow_html=True,
    )

    # ESCUCHAMOS EL CÓDIGO
    codigo = st.experimental_get_query_params().get("codigo_manual", [None])[0]

    # Streamlit recibe mensajes enviados desde JS
    if codigo := st.session_state.get("component_value"):
        # Mostrar código
        codigo_placeholder.success(f"📌 Código detectado: **{codigo}**")

        # Validar repetido
        if codigo in st.session_state.codigos_escaneados:
            boton_placeholder.error("⚠️ Este código ya fue registrado.")
        else:
            # Botón continuar
            if boton_placeholder.button("Continuar ➜", type="primary"):
                st.session_state.codigos_escaneados.append(codigo)
                st.session_state.codigo_escaneado = codigo
                st.session_state.fase = "confirmar"
                st.rerun()

# ======================================
# FASE 4: INGRESO MANUAL
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

        st.success("Registro guardado correctamente.")
        st.session_state.fase = "formulario"
        st.experimental_set_query_params()
        st.rerun()



