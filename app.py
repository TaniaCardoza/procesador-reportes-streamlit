<<<<<<< HEAD
﻿
import streamlit as st
=======
﻿import streamlit as st
>>>>>>> 7ed0a62f621f034b93322e9fc6383cd4acbf9a9b
import pandas as pd
import numpy as np
from io import BytesIO
import zipfile

st.set_page_config(page_title="Procesador de Ventas", layout="wide")
st.title(" Procesador de Reportes de Ventas y Compras")

# Campos requeridos por defecto para VENTAS
CAMPOS_ORIGINALES_VENTAS = [
    "Fecha de emisión",
    "Fecha Vcto/Pago",
    "Tipo CP/Doc.",
    "Serie del CDP",
    "Nro CP o Doc. Nro Inicial (Rango)",  
    "Nro Doc Identidad",
    "Apellidos Nombres/ Razón Social",
    "BI Gravada",
    "IGV / IPM",
    "Total CP",
    "Moneda",
]

# Campos requeridos por defecto para COMPRAS
CAMPOS_ORIGINALES_COMPRAS = [
    "Fecha de emisión",
    "Fecha Vcto/Pago",
    "Tipo CP/Doc.",
    "Serie del CDP",
    "Nro CP o Doc. Nro Inicial (Rango)",
    "Tipo Doc Identidad",
    "Nro Doc Identidad",
    "Apellidos Nombres/ Razón  Social",
    "BI Gravado DG",
    "IGV / IPM DG",
    "Valor Adq. NG",
    "Total CP",
    "Moneda",
    "Fecha Emisión Doc Modificado",
    "Serie CP Modificado",
    "Nro CP Modificado",
]


RENOMBRAR = {
    "Tipo CP/Doc.": "Tipo Doc",
    "Serie del CDP": "Serie",
    "Nro CP o Doc. Nro Inicial (Rango)":"Nro",
}


opcion = st.radio("Selecciona el tipo de archivo que deseas procesar:", ["Ventas", "Compras"], horizontal=True)



def read_file(f):
    if f.name.lower().endswith(".zip"):
        with zipfile.ZipFile(f) as z:
    
            csv_files = [name for name in z.namelist() if name.lower().endswith(".csv")]
            if not csv_files:
                st.error("El archivo ZIP no contiene archivos CSV.")
                return None
            with z.open(csv_files[0]) as csv_file:
                try:
                
                    return pd.read_csv(csv_file, encoding="utf-8", engine="python")
                except pd.errors.ParserError as e:
                    st.warning(f"Error de formato detectado: {str(e)}")
                    st.info("🔧 Intentando leer con configuración alternativa...")
                    csv_file.seek(0)
                    return pd.read_csv(csv_file, encoding="utf-8", engine="python", 
                                    on_bad_lines='skip', sep=',', quotechar='"')
    elif f.name.lower().endswith(".csv"):
        try:
            return pd.read_csv(f, encoding="utf-8", engine="python")
        except pd.errors.ParserError as e:
            st.warning(f"Error de formato detectado: {str(e)}")
            st.info("🔧 Intentando leer con configuración alternativa...")
            f.seek(0)
            return pd.read_csv(f, encoding="utf-8", engine="python", 
                            on_bad_lines='skip', sep=',', quotechar='"')
    return pd.read_excel(f)

def clean_numeric_series(s):
    return pd.to_numeric(s.astype(str).str.replace(r'[^\d\.\-]', '', regex=True), errors="coerce")

def detect_missing_correlatives(df, serie_col="Serie", numero_col="Nro"):
    """
    Detecta números correlativos faltantes en las boletas por serie
    """
    missing_report = []
    
    for serie in df[serie_col].unique():
        serie_data = df[df[serie_col] == serie].copy()

        try:
            numeros = pd.to_numeric(serie_data[numero_col], errors='coerce').dropna().astype(int)
            numeros = sorted(numeros.unique())
            
            if len(numeros) > 1:

                min_num = min(numeros)
                max_num = max(numeros)

                secuencia_completa = set(range(min_num, max_num + 1))
                numeros_existentes = set(numeros)
                
                faltantes = sorted(secuencia_completa - numeros_existentes)
                
                if faltantes:
                    missing_report.append({
                        'Serie': serie,
                        'Rango': f"{min_num}-{max_num}",
                        'Faltantes': faltantes,
                        'Total_Faltantes': len(faltantes)
                    })
        except:
            continue
    
    return missing_report

def to_excel_bytes_with_title(df_, title):
    from openpyxl.styles import Font, Alignment
    
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        
        df_.to_excel(writer, index=False, startrow=1, sheet_name="Reporte")
        worksheet = writer.sheets["Reporte"]
        
    
        worksheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(df_.columns))
        cell = worksheet.cell(row=1, column=1)
        cell.value = title
        cell.font = Font(name="Arial", bold=True, size=9)
        cell.alignment = Alignment(horizontal="center")
        for col_idx, column in enumerate(df_.columns, start=1):
            max_length = len(str(column))
            for row in df_.values:
                if row[col_idx-1] is not None:
                    max_length = max(max_length, len(str(row[col_idx-1])))
            adjusted_width = min(max_length + 2, 50) 
            worksheet.column_dimensions[worksheet.cell(row=2, column=col_idx).column_letter].width = adjusted_width

            header_cell = worksheet.cell(row=2, column=col_idx)
            header_cell.font = Font(name="Arial", bold=True, size=9)
        for row in worksheet.iter_rows(min_row=3, max_row=worksheet.max_row, min_col=1, max_col=len(df_.columns)):
            for cell in row:
                cell.font = Font(name="Arial", size=9)
    
    return out.getvalue()

if opcion == "Ventas":
    st.header("Subir archivo de Ventas")
    uploaded_file = st.file_uploader("Sube tu archivo CSV, Excel o ZIP (conteniendo un CSV)", type=["csv", "xlsx", "zip"], key="ventas")

    if uploaded_file:
        df = read_file(uploaded_file)
        if st.checkbox(" Mostrar vista previa del archivo original"):
            st.subheader(" Vista previa del archivo")
            st.dataframe(df.head(10))
        columnas_existentes = [c for c in CAMPOS_ORIGINALES_VENTAS if c in df.columns]
        faltantes = [c for c in CAMPOS_ORIGINALES_VENTAS if c not in df.columns]

        if faltantes:
            st.warning(f"No se encontraron estas columnas en tu archivo: {faltantes}")
        extra_cols = st.multiselect("Selecciona columnas adicionales (si deseas)", [c for c in df.columns if c not in columnas_existentes])
        df = df[columnas_existentes + extra_cols].copy()
        df = df.rename(columns=RENOMBRAR)
        for c in ["BI Gravada", "IGV / IPM", "Total CP"]:
            if c in df.columns:
                df[c] = clean_numeric_series(df[c])
        totals = df.select_dtypes(include=np.number).sum()
        total_row = {col: "" for col in df.columns}
        total_row["Apellidos Nombres/ Razón Social"] = "TOTAL VENTAS"
        for c in totals.index:
            total_row[c] = round(totals[c], 2)

        df_with_total = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

        st.subheader("Reporte final con Totales")
        st.dataframe(df_with_total)
        st.subheader("Descargar Reporte con Totales- SIN AGRUPAR")
        title = "REPORTE DE VENTAS"
        xlsx_bytes_totales = to_excel_bytes_with_title(df_with_total, title)
        st.download_button("⬇Descargar Excel con Totales", xlsx_bytes_totales, file_name="reporte_ventas_totales.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="ventas_totales")
        if st.checkbox("Agrupar boletas por fecha"):
            if "Tipo Doc" in df.columns and "Fecha de emisión" in df.columns:
                mask_boleta = df["Tipo Doc"] == 3  
                boletas = df[mask_boleta]
                otros = df[~mask_boleta]  
                if not boletas.empty:
                    missing_correlatives = detect_missing_correlatives(boletas)
                    
                    if missing_correlatives:
                        st.warning("**ADVERTENCIA: Se detectaron números correlativos faltantes en las boletas**")
                        st.subheader(" Números de Boletas Faltantes por Serie")
                        
                        for item in missing_correlatives:
                            st.error(f"**Serie {item['Serie']}** (Rango: {item['Rango']})")
                            st.write(f" **Números faltantes ({item['Total_Faltantes']}):** {', '.join(map(str, item['Faltantes']))}")
                            st.write("---")
                    else:
                        st.success(" **Secuencia correlativa completa - No se detectaron números faltantes**")

                if mask_boleta.any():
                    grouped_boletas = (
                        boletas
                        .groupby([boletas["Fecha de emisión"], "Serie"])
                        .agg({
                            "Nro": lambda x: f"{min(x)}-{max(x)}", 
                            "BI Gravada": lambda x: round(x.sum(), 2),
                            "IGV / IPM": lambda x: round(x.sum(), 2),
                            "Total CP": lambda x: round(x.sum(), 2),
                            "Moneda": lambda x: x.iloc[0] if len(set(x)) == 1 else "VARIAS"
                        })
                        .reset_index()
                    )
                    grouped_boletas["Apellidos Nombres/ Razón Social"] = "CLIENTE VARIOS"
                    grouped_boletas["Tipo Doc"] = 3 
                else:
                    grouped_boletas = pd.DataFrame()

                final_report = pd.concat([
                    otros[otros["Tipo Doc"] == 1],  
                    otros[otros["Tipo Doc"] == 7], 
                    grouped_boletas,  
                    otros[(otros["Tipo Doc"] != 1) & (otros["Tipo Doc"] != 7)] 
                ], ignore_index=True)

                def calculate_totals(df, exclude_columns):
                    numeric_columns = df.select_dtypes(include=np.number).columns
                    columns_to_sum = [col for col in numeric_columns if col not in exclude_columns]
                    return df[columns_to_sum].sum()

                exclude_columns = ["Tipo Doc", "Nro Doc Identidad"]

                total_facturas = calculate_totals(final_report[final_report["Tipo Doc"] == 1], exclude_columns)
                total_boletas = calculate_totals(final_report[final_report["Tipo Doc"] == 3], exclude_columns)

                total_general = total_facturas + total_boletas
                total_general_row = {col: "" for col in final_report.columns}
                total_general_row.update({
                    "Apellidos Nombres/ Razón Social": "TOTAL GENERAL VENTAS"
                })
                for col in total_general.index:
                    total_general_row[col] = round(total_general[col], 2)
                total_facturas_row = {col: "" for col in final_report.columns}
                total_facturas_row.update({
                    "Apellidos Nombres/ Razón Social": "TOTAL FACTURAS"
                })
                for col in total_facturas.index:
                    total_facturas_row[col] = round(total_facturas[col], 2)
                total_boletas_row = {col: "" for col in final_report.columns}
                total_boletas_row.update({
                    "Apellidos Nombres/ Razón Social": "TOTAL BOLETAS"
                })
                for col in total_boletas.index:
                    total_boletas_row[col] = round(total_boletas[col], 2)
                facturas = final_report[final_report["Tipo Doc"] == 1]
                boletas = final_report[final_report["Tipo Doc"] == 3]
                otros = final_report[(final_report["Tipo Doc"] != 1) & (final_report["Tipo Doc"] != 3)]
                final_report = pd.concat([
                    pd.DataFrame([{col: "" for col in final_report.columns}]).assign(**{"Fecha de emisión": "FACTURAS"}), 
                    facturas,
                    pd.DataFrame([total_facturas_row]),
                    pd.DataFrame([{col: "" for col in final_report.columns}]).assign(**{"Fecha de emisión": "BOLETAS"}),  
                    boletas,
                    pd.DataFrame([total_boletas_row]),
                    pd.DataFrame([total_general_row]),
                    otros
                ], ignore_index=True)

                st.subheader(" Reporte final con agrupación y totales generales")
                st.dataframe(final_report)

                title = "REPORTE DE VENTAS"
                xlsx_bytes = to_excel_bytes_with_title(final_report, title)
                st.download_button("⬇Descargar Excel AGRUPADO", xlsx_bytes, file_name="reporte_ventas_agrupado.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="ventas_agrupado")


elif opcion == "Compras":
                st.header("Subir archivo de Compras")
                uploaded_file = st.file_uploader("Sube tu archivo CSV, Excel o ZIP (conteniendo un CSV)", type=["csv", "xlsx", "zip"], key="compras")

                if uploaded_file:
                    df = read_file(uploaded_file)

                    if st.checkbox("Mostrar vista previa del archivo"):
                        st.subheader("Vista previa del archivo")
                        st.dataframe(df.head(10))

                    columnas_existentes = [c for c in CAMPOS_ORIGINALES_COMPRAS if c in df.columns]
                    faltantes = [c for c in CAMPOS_ORIGINALES_COMPRAS if c not in df.columns]

                    if faltantes:
                        st.warning(f" No se encontraron estas columnas en tu archivo: {faltantes}")
                    extra_cols = st.multiselect("Selecciona columnas adicionales (si deseas)", [c for c in df.columns if c not in columnas_existentes])
                    
                    cols_to_remove = st.multiselect(" Selecciona columnas que deseas QUITAR (si deseas)", columnas_existentes)
                    
                    columnas_finales = [c for c in columnas_existentes if c not in cols_to_remove]

                    df = df[columnas_finales + extra_cols].copy()

                    df = df.rename(columns=RENOMBRAR)
                    columnas_numericas_compras = ["BI Gravado DG", "IGV / IPM DG", "Valor Adq. NG", "Total CP"]
                    for c in columnas_numericas_compras:
                        if c in df.columns:
                            df[c] = clean_numeric_series(df[c])

                    def calculate_totals_compras(df, exclude_columns):
                        numeric_columns = df.select_dtypes(include=np.number).columns
                        columns_to_sum = [col for col in numeric_columns if col not in exclude_columns]
                        return df[columns_to_sum].sum()

                    exclude_columns_compras = ["Tipo Doc", "Nro", "Tipo Doc Identidad", "Nro Doc Identidad", "Nro CP Modificado"]
                    totals = calculate_totals_compras(df, exclude_columns_compras)

                    total_row = {col: "" for col in df.columns}
                    total_row["Apellidos Nombres/ Razón  Social"] = "TOTAL COMPRAS"
                    for c in totals.index:
                        total_row[c] = round(totals[c], 2)

                    df_with_total = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

                    st.subheader("Reporte final con Totales")
                    st.dataframe(df_with_total)
                    title = "REPORTE DE COMPRAS"
                    xlsx_bytes = to_excel_bytes_with_title(df_with_total, title)
                    st.download_button(
                        "⬇ Descargar Excel final",
                        xlsx_bytes,
                        file_name="reporte_compras.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="compras_final"
                    )
