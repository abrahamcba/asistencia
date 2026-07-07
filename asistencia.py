import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import json
import io
from google import genai
from google.genai import types

# 1. Configuración de la página web
st.set_page_config(page_title="Extractor de Asistencia - Construmarz", page_icon="📝")
st.title("📝 Extractor Inteligente de Asistencia")
st.write("Sube la foto o el PDF de asistencia de Inversiones Construmarz para generar el Excel.")

# 2. Configurar la API Key de forma directa
API_KEY = "AQ.Ab8RN6IVa051nUIncU0rd0VptB7_3rEd_eusBFPZRH7GY0U63w"
client = genai.Client(api_key=API_KEY)

# 3. Botón web para subir el archivo
archivo_subido = st.file_uploader("Elige una imagen (JPG/PNG) o un PDF de asistencia", type=["png", "jpg", "jpeg", "pdf"])

if archivo_subido is not None:
    st.info(f"Archivo subido: {archivo_subido.name}. Procesando...")
    todos_los_datos = []
    
    # El mismo prompt inteligente que ya te funcionó
    prompt_instrucciones = """
    Actúa como un extractor de datos experto en listas de asistencia de construcción. 
    Analiza la imagen adjunta. Extrae la información manuscrita (a mano) fila por fila.
    Devuelve la información ESTRICTAMENTE en formato JSON (una lista de objetos).
    
    Reglas:
    1. Ignora las firmas de 'FIRMA' y 'CHARLA INFORMATIVA'.
    2. Si un campo tiene comillas (") o está vacío, repite el valor de arriba.
    3. Transcribe nombres y apellidos exactos.
    
    Estructura JSON:
    [{"Nombres_Apellidos": "...", "DNI": "...", "Categoria": "...", "Hora_Ingreso": "...", "Hora_Salida": "..."}]
    """

    try:
        bytes_archivo = archivo_subido.read()
        
        if archivo_subido.name.lower().endswith('.pdf'):
            # Procesar PDF en memoria (sin guardar archivos en el disco)
            doc = fitz.open(stream=bytes_archivo, filetype="pdf")
            total_paginas = len(doc)
            
            for num_pag in range(total_paginas):
                pagina = doc.load_page(num_pag)
                pix = pagina.get_pixmap(dpi=150)
                imagen_ia = types.Part.from_bytes(data=pix.tobytes(output="png"), mime_type="image/png")
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[imagen_ia, prompt_instrucciones],
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )
                datos_pagina = json.loads(response.text)
                for fila in datos_pagina:
                    fila["Página"] = num_pag + 1
                    todos_los_datos.append(fila)
        else:
            # Procesar imagen directa
            mime = "image/png" if archivo_subido.name.lower().endswith('.png') else "image/jpeg"
            imagen_ia = types.Part.from_bytes(data=bytes_archivo, mime_type=mime)
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[imagen_ia, prompt_instrucciones],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            todos_los_datos = json.loads(response.text)

        # 4. Mostrar resultados y dar botón de descarga
        if todos_los_datos:
            df = pd.DataFrame(todos_los_datos)
            columnas_orden = ["Página", "Nombres_Apellidos", "DNI", "Categoria", "Hora_Ingreso", "Hora_Salida"]
            df = df[[col for col in columnas_orden if col in df.columns]]
            
            # Mostrar una vista previa de la tabla en la web
            st.success("¡Datos extraídos con éxito!")
            st.dataframe(df)
            
            # Convertir el Excel a bytes en memoria para la descarga web
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            # Botón de descarga de Streamlit
            st.download_button(
                label="📥 Descargar Reporte en Excel",
                data=buffer.getvalue(),
                file_name="asistencia_web.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"Ocurrió un error: {e}")
