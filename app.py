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
# FASE 3: ESCANEO (FUNCIONAL)
# ======================================
elif st.session_state.fase == "escaneo":
    st.title("📷 Escanear código de barras")
    st.markdown("Apunta la cámara al código del certificado electoral.")

    if "codigo_detectado" not in st.session_state:
        st.session_state.codigo_detectado = None

    if "codigos_guardados" not in st.session_state:
        st.session_state.codigos_guardados = []

    placeholder_codigo = st.empty()
    placeholder_boton = st.empty()

    # 🟢 SONIDO
    st.markdown("""
        <audio id="beep">
            <source src="https://actions.google.com/sounds/v1/cartoon/clang_and_wobble.ogg" type="audio/ogg">
        </audio>
    """, unsafe_allow_html=True)

    # 🟢 IFRAME ESCÁNER 100% FUNCIONAL
    components.html("""
        <html>
        <body style="margin:0;">
            <video id="preview" style="width:100%; height:260px; border:2px solid #4CAF50; border-radius:12px;"></video>

            <script type="text/javascript" src="https://unpkg.com/@zxing/library@latest"></script>
            <script>
                const codeReader = new ZXing.BrowserBarcodeReader();
                codeReader.decodeFromVideoDevice(null, 'preview', (result, err) => {
                    if(result){
                        // SONIDO
                        document.getElementById("beep").play();

                        // ENVIAR A STREAMLIT
                        window.parent.postMessage(JSON.stringify({
                            type: "codigo",
                            value: result.text
                        }), "*");
                    }
                });
            </script>
        </body>
        </html>
    """, height=300)

    # 🟢 RECIBE CÓDIGOS DEL IFRAME
    st.markdown("""
        <script>
        window.addEventListener("message", (event) => {
            const data = JSON.parse(event.data);
            if(data.type === "codigo"){
                const codigo = data.value;
                window.parent.postMessage(
                    { isStreamlitMessage: true, type: "streamlit:setComponentValue", value: codigo },
                    "*"
                );
            }
        });
        </script>
    """, unsafe_allow_html=True)

    codigo = st.session_state.get("component_value")

    if codigo:
        st.session_state.codigo_detectado = codigo
        placeholder_codigo.success(f"📌 Código detectado: **{codigo}**")

        if codigo in st.session_state.codigos_guardados:
            placeholder_boton.error("⚠️ Este código ya existe.")
        else:
            if placeholder_boton.button("Continuar ➜", type="primary"):
                st.session_state.codigos_guardados.append(codigo)
                st.session_state.codigo_escaneado = codigo
                st.session_state.fase = "confirmar"
                st.rerun()

    st.divider()
    st.subheader("Ingreso manual")

    manual = st.text_input("Digite el número del código", max_chars=30)

    if st.button("Guardar código manual"):
        if manual.strip() == "":
            st.warning("Debe ingresar un valor.")
        elif manual in st.session_state.codigos_guardados:
            st.error("⚠️ Este código ya fue registrado.")
        else:
            st.session_state.codigo_escaneado = manual
            st.session_state.codigos_guardados.append(manual)
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




