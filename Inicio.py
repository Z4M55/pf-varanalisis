import pandas as pd
import streamlit as st
from PIL import Image
import numpy as np
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Monitor Sensor de Gas - Mi Ciudad",
    page_icon="🟠",
    layout="wide"
)

# --- Custom CSS (mejoras visuales) ---
st.markdown("""
    <style>
    .main {
        padding: 1.5rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    .big-metric .stMetricValue {
        font-size: 28px !important;
    }
    .warn {
        background-color: rgba(255,165,0,0.12);
        padding: 8px;
        border-radius: 6px;
    }
    .danger {
        background-color: rgba(255,0,0,0.08);
        padding: 8px;
        border-radius: 6px;
    }
    </style>
""", unsafe_allow_html=True)

# Title and description
st.title('🟠 Monitor de Sensor de Gas - Mi Ciudad')
st.markdown("""
    Esta aplicación permite analizar lecturas de un sensor de gas (ppm).
    - Soporta archivos CSV con una columna de tiempo (`Time`) o sin ella.
    - Renombra automáticamente la columna de lectura a `variable`.
""")

# Sidebar: configuraciones del sensor
with st.sidebar:
    st.header("Configuración del sensor")
    unidad = st.selectbox("Unidad de medición", ["ppm", "mg/m³ (estimado)"], index=0)
    critical_threshold = st.number_input("Umbral crítico (alarma)", value=200.0, step=1.0, format="%.1f")
    warning_threshold = st.number_input("Umbral advertencia", value=100.0, step=1.0, format="%.1f")
    rolling_window = st.slider("Ventana media móvil (nº lecturas)", 1, 120, 10)
    st.markdown("---")
    st.write("📍 Ubicación por defecto:")
    st.write("**Universidad EAFIT**")
    st.write("Lat: 6.2006  •  Lon: -75.5783")

# Create map data for EAFIT (kept)
eafit_location = pd.DataFrame({
    'lat': [6.2006],
    'lon': [-75.5783],
    'location': ['Universidad EAFIT']
})

# Display map as a small widget
with st.expander("📍 Ver ubicación de sensores (EAFIT)"):
    st.map(eafit_location, zoom=15)

# File uploader
uploaded_file = st.file_uploader('Seleccione archivo CSV (Time opcional, columna de lectura)', type=['csv'])

if uploaded_file is not None:
    try:
        # Load and process data
        df1 = pd.read_csv(uploaded_file)

        # Renombrar la columna a 'variable'
        # Si existe 'Time', renombrar la primera otra columna a 'variable'
        if 'Time' in df1.columns:
            other_columns = [col for col in df1.columns if col != 'Time']
            if len(other_columns) > 0:
                df1 = df1.rename(columns={other_columns[0]: 'variable'})
        else:
            # Si no existe Time, renombrar la primera columna a 'variable'
            df1 = df1.rename(columns={df1.columns[0]: 'variable'})

        # Procesar columna de tiempo si existe
        if 'Time' in df1.columns:
            df1['Time'] = pd.to_datetime(df1['Time'], errors='coerce')
            # Si hay filas con Time inválido, avisamos pero seguimos
            if df1['Time'].isna().any():
                st.warning("Algunas filas tienen 'Time' inválido y fueron convertidas a NaT.")
            df1 = df1.set_index('Time').sort_index()
        else:
            # Si no hay Time, crear índice con rango como fallback
            df1.index = pd.RangeIndex(start=0, stop=len(df1), step=1)

        # Asegurar que 'variable' sea numérica
        df1['variable'] = pd.to_numeric(df1['variable'], errors='coerce')
        if df1['variable'].isna().all():
            st.error("La columna de lecturas no es numérica o está vacía.")
            st.stop()

        # Calcular métricas clave
        last_time = df1.index.max() if 'Time' in df1.columns or isinstance(df1.index, pd.DatetimeIndex) else None
        last_value = float(df1['variable'].iloc[-1])
        mean_value = float(df1['variable'].mean())
        std_value = float(df1['variable'].std())

        # Determinar estado según umbrales
        status = "OK"
        status_color = "success"
        if last_value >= critical_threshold:
            status = "CRÍTICO"
            status_color = "danger"
        elif last_value >= warning_threshold:
            status = "ADVERTENCIA"
            status_color = "warn"

        # Create tabs for different analyses
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Visualización", "📊 Estadísticas", "🔍 Filtros & Descarga", "🗺️ Info del Sitio"])

        with tab1:
            st.subheader('Visualización de lecturas')

            # Top row: últimas métricas y estado
            col1, col2, col3, col4 = st.columns([2,2,2,2])
            with col1:
                st.metric(label=f"Última lectura ({unidad})", value=f"{last_value:.2f}")
                if last_time is not None:
                    st.caption(f"Timestamp: {last_time}")
            with col2:
                st.metric("Media", f"{mean_value:.2f}")
                st.caption(f"Desv. estándar: {std_value:.2f}")
            with col3:
                # media móvil
                rolling = df1['variable'].rolling(window=rolling_window, min_periods=1).mean()
                last_rolling = rolling.iloc[-1]
                st.metric(f"Media móvil ({rolling_window})", f"{last_rolling:.2f}")
            with col4:
                # Estado visual
                if status == "CRÍTICO":
                    st.markdown(f"<div class='danger'><strong>⚠️ ESTADO: {status}</strong></div>", unsafe_allow_html=True)
                elif status == "ADVERTENCIA":
                    st.markdown(f"<div class='warn'><strong>⚠ {status}</strong></div>", unsafe_allow_html=True)
                else:
                    st.success(f"✅ ESTADO: {status}")

            # Chart type selector
            chart_type = st.selectbox(
                "Seleccione tipo de gráfico",
                ["Línea (lecturas)", "Línea (media móvil)", "Área", "Histograma"]
            )

            if chart_type == "Línea (lecturas)":
                st.line_chart(df1["variable"])
            elif chart_type == "Línea (media móvil)":
                chart_df = pd.DataFrame({
                    'lectura': df1['variable'],
                    f'media_{rolling_window}': rolling
                })
                st.line_chart(chart_df)
            elif chart_type == "Área":
                st.area_chart(df1["variable"])
            else:
                st.subheader("Distribución de valores")
                st.bar_chart(pd.cut(df1['variable'], bins=30).value_counts().sort_index())

            # Mostrar datos crudos con opción
            if st.checkbox('Mostrar datos crudos'):
                st.write(df1)

        with tab2:
            st.subheader('Análisis Estadístico y Resumen')
            stats_df = df1["variable"].describe().to_frame().rename(columns={'variable':'valor'})
            col1, col2 = st.columns([2,1])
            with col1:
                st.dataframe(stats_df)
            with col2:
                st.write("### Indicadores")
                st.write(f"- Unidad: **{unidad}**")
                st.write(f"- Última lectura: **{last_value:.2f} {unidad}**")
                st.write(f"- Media: **{mean_value:.2f} {unidad}**")
                st.write(f"- Máx: **{df1['variable'].max():.2f} {unidad}**")
                st.write(f"- Mín: **{df1['variable'].min():.2f} {unidad}**")
                st.write(f"- Desviación estándar: **{std_value:.2f}**")
                st.markdown("---")
                st.write("### Umbrales configurados")
                st.write(f"- Advertencia: {warning_threshold} {unidad}")
                st.write(f"- Crítico: {critical_threshold} {unidad}")

            # Small histogram
            st.subheader("Histograma de lecturas")
            hist_vals = np.histogram(df1['variable'].dropna(), bins=30)
            st.bar_chart(hist_vals[0])

        with tab3:
            st.subheader('Filtros de Datos y Descarga')

            # Calcular rango de valores
            min_value = float(df1["variable"].min())
            max_value = float(df1["variable"].max())
            mean_value = float(df1["variable"].mean())

            # Filtros por rango
            if min_value == max_value:
                st.warning(f"⚠️ Todos los valores en el dataset son iguales: {min_value:.2f}")
                st.info("No es posible aplicar filtros cuando no hay variación en los datos.")
                st.dataframe(df1)
            else:
                col1, col2 = st.columns(2)
                with col1:
                    min_val = st.slider(
                        'Valor mínimo (filtrar por >)',
                        min_value,
                        max_value,
                        min_value,
                        key="min_val"
                    )
                    filtrado_df_min = df1[df1["variable"] > min_val]
                    st.write(f"Registros con valor > {min_val:.2f}: {len(filtrado_df_min)}")
                    st.dataframe(filtrado_df_min.head(200))
                with col2:
                    max_val = st.slider(
                        'Valor máximo (filtrar por <)',
                        min_value,
                        max_value,
                        max_value,
                        key="max_val"
                    )
                    filtrado_df_max = df1[df1["variable"] < max_val]
                    st.write(f"Registros con valor < {max_val:.2f}: {len(filtrado_df_max)}")
                    st.dataframe(filtrado_df_max.head(200))

                # Filtrar por rango combinado
                combined = st.checkbox("Aplicar filtro combinado (min < valor < max)")
                if combined:
                    filtrado_completo = df1[(df1["variable"] > min_val) & (df1["variable"] < max_val)]
                    st.write(f"Registros en rango ({min_val:.2f}, {max_val:.2f}): {len(filtrado_completo)}")
                    st.dataframe(filtrado_completo.head(300))
                else:
                    filtrado_completo = pd.concat([filtrado_df_min, filtrado_df_max]).drop_duplicates()

                # Download filtered data
                csv = filtrado_completo.to_csv().encode('utf-8')
                st.download_button(
                    label="📥 Descargar datos filtrados (CSV)",
                    data=csv,
                    file_name='datos_filtrados_sensor_gas.csv',
                    mime='text/csv',
                )

                # Quick export summary
                if st.button("📄 Exportar resumen estadístico (TXT)"):
                    resumen = stats_df.to_string()
                    st.download_button(
                        label="Descargar resumen (TXT)",
                        data=resumen,
                        file_name='resumen_sensor_gas.txt',
                        mime='text/plain'
                    )

        with tab4:
            st.subheader("Información del Sitio de Medición")

            col1, col2 = st.columns(2)
            with col1:
                st.write("### Ubicación del Sensor")
                st.write("**Universidad EAFIT**")
                st.write("- Latitud: 6.2006")
                st.write("- Longitud: -75.5783")
                st.write("- Altitud aproximada: ~1,495 m.s.n.m.")
                if last_time is not None:
                    st.write(f"- Última lectura registrada: {last_time}")
            with col2:
                st.write("### Detalles del Sensor")
                st.write("- Tipo: ESP32 (ejemplo)")
                st.write("- Variable medida: Gas (ppm)")
                st.write("- Frecuencia de medición: según configuración del dispositivo")
                st.write("- Notas: Ajuste los umbrales en la barra lateral para definir advertencia/alarma.")

    except Exception as e:
        st.error(f'Error al procesar el archivo: {str(e)}')
        st.info('Asegúrese de que el archivo CSV tenga al menos una columna con datos numéricos.')
else:
    st.warning('Por favor, cargue un archivo CSV para comenzar el análisis.')

# Footer
st.markdown("""
    ---
    Desarrollado para monitoreo de sensores de gas en entornos urbanos.
    Ubicación por defecto: Universidad EAFIT, Medellín, Colombia
""")
