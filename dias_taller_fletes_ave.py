import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import sqlite3
import io

# ==========================================
# CONFIGURACIÓN DE LA BASE DE DATOS SQLITE
# ==========================================
def init_db():
    conn = sqlite3.connect('taller_fletes_ave.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Tabla de Registros de Taller
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_creacion TEXT,
            operador TEXT,
            actividades TEXT,
            dias REAL,
            valor_unitario REAL,
            total REAL,
            estado TEXT,
            fecha_aprobacion_operaciones TEXT,
            fecha_aprobacion_gerencia TEXT
        )
    ''')
    
    # Tabla de Operadores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operadores (
            nombre TEXT UNIQUE
        )
    ''')
    
    # Tabla de Configuración (Tarifa)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            clave TEXT UNIQUE,
            valor REAL
        )
    ''')
    
    # Insertar valores iniciales si están vacíos
    cursor.execute("SELECT COUNT(*) FROM operadores")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO operadores (nombre) VALUES (?)", ("Octavio Rodrigo Serrano Saavedra",))
        cursor.execute("INSERT INTO operadores (nombre) VALUES (?)", ("Operador 1",))
        cursor.execute("INSERT INTO operadores (nombre) VALUES (?)", ("Operador 2",))
        
    cursor.execute("SELECT COUNT(*) FROM config WHERE clave = 'valor_dia'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO config (clave, valor) VALUES ('valor_dia', 416.67)")
        
    conn.commit()
    conn.close()

init_db()

# Funciones de apoyo para interactuar con la Base de Datos
def obtener_conexion():
    return sqlite3.connect('taller_fletes_ave.db', check_same_thread=False)

def cargar_operadores():
    conn = obtener_conexion()
    df_ops = pd.read_sql("SELECT nombre FROM operadores", conn)
    conn.close()
    return df_ops['nombre'].tolist()

def obtener_tarifa():
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM config WHERE clave = 'valor_dia'")
    val = cursor.fetchone()[0]
    conn.close()
    return float(val)

def cargar_registros():
    conn = obtener_conexion()
    df = pd.read_sql("SELECT * FROM registros", conn)
    conn.close()
    return df.to_dict('records')

st.set_page_config(page_title="Sistema de Control - Taller Fletes AVE", layout="wide")

st.title("🚜 SISTEMA DE CONTROL DE DÍAS DE TALLER - FLETES AVE")

# Selector de Perfil / Rol en la barra lateral
st.sidebar.header("🔐 Control de Acceso y Perfiles")
perfil = st.sidebar.selectbox(
    "Seleccione su Rol:", 
    ["1. Capturista", "2. Jefe de Operaciones (Admin)", "3. Gerente"]
)

# Control de Autenticación por Contraseña
acceso_concedido = True

if perfil == "2. Jefe de Operaciones (Admin)":
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔒 Autenticación Requerida")
    password_admin = st.sidebar.text_input("Contraseña de Administrador:", type="password")
    if password_admin != "AdminAve2026":
        acceso_concedido = False
        if password_admin != "":
            st.sidebar.error("❌ Contraseña incorrecta.")
        else:
            st.sidebar.warning("⚠️ Ingrese la contraseña para acceder al módulo.")

elif perfil == "3. Gerente":
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔒 Autenticación Requerida")
    password_gerente = st.sidebar.text_input("Contraseña de Gerencia:", type="password")
    if password_gerente != "GerenciaAve2026":
        acceso_concedido = False
        if password_gerente != "":
            st.sidebar.error("❌ Contraseña incorrecta.")
        else:
            st.sidebar.warning("⚠️ Ingrese la contraseña para acceder al módulo.")

st.markdown("---")

# ==========================================
# 1. PERFIL: CAPTURISTA
# ==========================================
if perfil == "1. Capturista":
    st.subheader("📝 Módulo: Capturista (Registro Inicial)")
    st.markdown("Todos los campos marcados con asterisco (**\***) son **obligatorios** para poder registrar la información.")
    
    lista_operadores = cargar_operadores()
    valor_unitario_actual = obtener_tarifa()
    
    col1, col2 = st.columns(2)
    
    with col1:
        opciones_operadores = ["-- Seleccione un operador --"] + lista_operadores
        operador = st.selectbox("Seleccione el Operador: *", opciones_operadores)
        dias_taller = st.number_input("Días de Taller: *", min_value=0.0, step=0.5, format="%.1f", value=0.0)
        
    with col2:
        st.info(f"💵 Valor Unitario Estándar Actual: ${valor_unitario_actual:,.2f} MXN")
        
    actividades = st.text_area("ACTIVIDADES DESEMPEÑADAS: *", placeholder="Describa a detalle las tareas realizadas...")
    evidencia = st.file_uploader("EVIDENCIA (Imagen/Fotografía obligatoria): *", type=["png", "jpg", "webp"])
    st.markdown("---")

    if st.button("Guardar y Enviar Registro", type="primary"):
        if operador == "-- Seleccione un operador --":
            st.error("⚠️ El campo **Operador** es obligatorio. Por favor seleccione uno.")
        elif float(dias_taller) <= 0:
            st.error("⚠️ Debe capturar al menos **0.5 días de taller** válidos.")
        elif not actividades.strip():
            st.error("⚠️ El campo **Actividades Desempeñadas** es obligatorio.")
        elif evidencia is None:
            st.error("⚠️ Debe adjuntar una **Evidencia (Imagen/Fotografía)** obligatoria para poder continuar.")
        else:
            total_taller = float(dias_taller) * valor_unitario_actual
            fecha_creacion = datetime.now(ZoneInfo("America/Monterrey")).strftime("%Y-%m-%d %H:%M")
            estado_inicial = "Pendiente de Aprobación (Operaciones)"
            
            conn = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO registros (fecha_creacion, operador, actividades, dias, valor_unitario, total, estado, fecha_aprobacion_operaciones, fecha_aprobacion_gerencia)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (fecha_creacion, operador, actividades, float(dias_taller), valor_unitario_actual, total_taller, estado_inicial, "", ""))
            conn.commit()
            conn.close()
            
            st.success("✅ ¡Registro guardado exitosamente y enviado al Jefe de Operaciones para su revisión!")

# ==========================================
# 2. PERFIL: JEFE DE OPERACIONES (ADMIN)
# ==========================================
elif perfil == "2. Jefe de Operaciones (Admin)":
    if not acceso_concedido:
        st.info("👈 Por favor ingrese la contraseña correcta en la barra lateral para acceder a este módulo.")
    else:
        st.subheader("👨‍💼 Módulo: Jefe de Operaciones (Administrador)")
        st.write("Gestione autorizaciones operativas, catálogo de operadores, tarifas, edición de registros y descargas.")
        
        registros = cargar_registros()
        lista_operadores = cargar_operadores()
        valor_unitario_actual = obtener_tarifa()
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "✍️ Autorizaciones", 
            "⚙️ Operadores y Tarifas", 
            "🛠️ Modificar / Eliminar", 
            "📊 Historial y Descargas"
        ])
        
        with tab1:
            pendientes_ops = [r["id"] for r in registros if r["estado"] == "Pendiente de Aprobación (Operaciones)"]
            
            if not pendientes_ops:
                st.success("🎉 No hay registros pendientes de autorización por parte de Operaciones.")
            else:
                reg_id = st.selectbox("Seleccione el ID del Registro a Autorizar:", pendientes_ops, key="auth_op")
                reg_sel = next((r for r in registros if r["id"] == reg_id), None)
                
                if reg_sel:
                    st.write(f"**Operador:** {reg_sel['operador']}")
                    st.write(f"**Actividades:** {reg_sel['actividades']}")
                    st.write(f"**Días de Taller:** {reg_sel['dias']}")
                    
                    nuevo_val_unit = st.number_input("Modificar Valor Unitario ($):", value=float(reg_sel['valor_unitario']), format="%.2f", key="val_unit_auth")
                    nuevo_total = reg_sel['dias'] * nuevo_val_unit
                    st.write(f"**Total Ajustado:** ${nuevo_total:,.2f} MXN")
                    
                    if st.button("✔️ Autorizar como Jefe de Operaciones"):
                        fecha_op = datetime.now(ZoneInfo("America/Monterrey")).strftime("%Y-%m-%d %H:%M")
                        conn = obtener_conexion()
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE registros 
                            SET valor_unitario = ?, total = ?, estado = ?, fecha_aprobacion_operaciones = ?
                            WHERE id = ?
                        ''', (nuevo_val_unit, nuevo_total, "Pendiente de Aprobación (Gerencia)", fecha_op, reg_id))
                        conn.commit()
                        conn.close()
                        st.success(f"¡Registro #{reg_id} autorizado por Operaciones! Ahora pasó al módulo de Gerencia.")
                        st.rerun()

        with tab2:
            st.markdown("### ⚙️ Configuración del Sistema")
            
            nuevo_costo_base = st.number_input(
                "Modificar Costo Estándar por Día de Taller ($ MXN):", 
                value=float(valor_unitario_actual), 
                format="%.2f",
                step=10.0
            )
            if st.button("💾 Actualizar Tarifa Estándar"):
                conn = obtener_conexion()
                cursor = conn.cursor()
                cursor.execute("UPDATE config SET valor = ? WHERE clave = 'valor_dia'", (nuevo_costo_base,))
                conn.commit()
                conn.close()
                st.success(f"✅ Tarifa estándar actualizada a ${nuevo_costo_base:,.2f} MXN.")
                st.rerun()

            st.markdown("---")
            st.markdown("### ➕ Agregar Nuevo Operador")
            nuevo_operador_nombre = st.text_input("Nombre del Nuevo Operador:", key="input_nuevo_op")
            if st.button("Registrar Operador"):
                if nuevo_operador_nombre.strip():
                    try:
                        conn = obtener_conexion()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO operadores (nombre) VALUES (?)", (nuevo_operador_nombre.strip(),))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Operador '{nuevo_operador_nombre.strip()}' agregado correctamente.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.warning("⚠️ Este operador ya se encuentra registrado.")
                else:
                    st.error("⚠️ Ingrese un nombre válido para el operador.")
            
            st.markdown("---")
            st.markdown("### 🗑️ Eliminar Operador Existente")
            if not lista_operadores:
                st.info("No hay operadores registrados.")
            else:
                operador_a_eliminar = st.selectbox("Seleccione el Operador a Eliminar:", lista_operadores, key="del_op_select")
                if st.button("🗑️ Eliminar Operador Seleccionado", type="primary"):
                    if len(lista_operadores) > 1:
                        conn = obtener_conexion()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM operadores WHERE nombre = ?", (operador_a_eliminar,))
                        conn.commit()
                        conn.close()
                        st.success(f"🗑️ El operador '{operador_a_eliminar}' ha sido eliminado correctamente.")
                        st.rerun()
                    else:
                        st.warning("⚠️ Debe mantener al menos un operador en el sistema.")

            st.markdown("---")
            st.markdown("#### 📋 Operadores Actuales Registrados:")
            st.write(", ".join(lista_operadores))

        with tab3:
            st.markdown("### 🛠️ Modificar o Eliminar Registros Existentes")
            if not registros:
                st.info("ℹ️ No hay registros en la base de datos.")
            else:
                ids_disponibles = [r["id"] for r in registros]
                id_a_editar = st.selectbox("Seleccione el ID del Registro a Editar o Eliminar:", ids_disponibles, key="edit_del_id")
                
                registro_encontrado = next((r for r in registros if r["id"] == id_a_editar), None)
                
                if registro_encontrado:
                    with st.form("form_edicion_registro"):
                        op_edit = st.selectbox("Operador:", lista_operadores, index=lista_operadores.index(registro_encontrado["operador"]) if registro_encontrado["operador"] in lista_operadores else 0)
                        dias_edit = st.number_input("Días de Taller:", value=float(registro_encontrado["dias"]), step=0.5, format="%.1f")
                        act_edit = st.text_area("Actividades Desempeñadas:", value=registro_encontrado["actividades"])
                        val_unit_edit = st.number_input("Valor Unitario ($):", value=float(registro_encontrado["valor_unitario"]), format="%.2f")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        actualizar_btn = col_btn1.form_submit_button("💾 Guardar Cambios")
                        eliminar_btn = col_btn2.form_submit_button("🗑️ Eliminar Registro", type="primary")
                        
                        if actualizar_btn:
                            nuevo_total = float(dias_edit) * float(val_unit_edit)
                            conn = obtener_conexion()
                            cursor = conn.cursor()
                            cursor.execute('''
                                UPDATE registros 
                                SET operador = ?, dias = ?, actividades = ?, valor_unitario = ?, total = ?
                                WHERE id = ?
                            ''', (op_edit, float(dias_edit), act_edit, float(val_unit_edit), nuevo_total, id_a_editar))
                            conn.commit()
                            conn.close()
                            st.success(f"✅ ¡Registro #{id_a_editar} actualizado con éxito!")
                            st.rerun()
                            
                        if eliminar_btn:
                            conn = obtener_conexion()
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM registros WHERE id = ?", (id_a_editar,))
                            conn.commit()
                            conn.close()
                            st.success(f"🗑️ ¡Registro #{id_a_editar} eliminado correctamente!")
                            st.rerun()

        with tab4:
            st.markdown("### 🗂️ Historial General de Registros")
            conn = obtener_conexion()
            df_mostrar = pd.read_sql("SELECT * FROM registros", conn)
            conn.close()
            st.dataframe(df_mostrar, use_container_width=True)
            
            st.markdown("### 📥 Descargar Reportes")
            formato_descarga = st.radio("Seleccione el formato de descarga:", ["Excel (.xlsx)", "CSV (.csv)"], horizontal=True, key="formato_rep")
            fecha_actual = datetime.now(ZoneInfo("America/Monterrey")).strftime('%Y%m%d')
            
            if formato_descarga == "Excel (.xlsx)":
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_mostrar.to_excel(writer, index=False, sheet_name='Historial Taller')
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📥 Descargar Historial en Excel (.xlsx)",
                    data=excel_data,
                    file_name=f"historial_taller_fletes_ave_{fecha_actual}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                csv_data = df_mostrar.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar Historial en CSV (.csv)",
                    data=csv_data,
                    file_name=f"historial_taller_fletes_ave_{fecha_actual}.csv",
                    mime="text/csv"
                )

# ==========================================
# 3. PERFIL: GERENTE
# ==========================================
elif perfil == "3. Gerente":
    if not acceso_concedido:
        st.info("👈 Por favor ingrese la contraseña correcta en la barra lateral para acceder a este módulo.")
    else:
        st.subheader("👔 Módulo: Gerente (Autorización Final)")
        st.write("Autorice los registros que ya fueron aprobados previamente por el Jefe de Operaciones.")
        
        registros = cargar_registros()
        pendientes_gerencia = [r["id"] for r in registros if r["estado"] == "Pendiente de Aprobación (Gerencia)"]
        
        if not pendientes_gerencia:
            st.info("ℹ️ No hay registros pendientes de autorización gerencial en este momento.")
        else:
            reg_id_ger = st.selectbox("Seleccione el ID del Registro para Visto Bueno Gerencial:", pendientes_gerencia, key="ger_auth")
            reg_sel_ger = next((r for r in registros if r["id"] == reg_id_ger), None)
            
            if reg_sel_ger:
                st.write(f"**Operador:** {reg_sel_ger['operador']}")
                st.write(f"**Actividades:** {reg_sel_ger['actividades']}")
                st.write(f"**Días de Taller:** {reg_sel_ger['dias']}")
                st.write(f"**Total Autorizado por Operaciones:** ${reg_sel_ger['total']:,.2f} MXN")
                st.write(f"**Fecha Visto Bueno Operaciones:** {reg_sel_ger['fecha_aprobacion_operaciones']}")
                
                if st.button("✔️ Otorgar Autorización Final (Gerencia)"):
                    fecha_ger = datetime.now(ZoneInfo("America/Monterrey")).strftime("%Y-%m-%d %H:%M")
                    conn = obtener_conexion()
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE registros 
                        SET estado = ?, fecha_aprobacion_gerencia = ?
                        WHERE id = ?
                    ''', ("Completado y Autorizado (Gerencia)", fecha_ger, reg_id_ger))
                    conn.commit()
                    conn.close()
                    st.success(f"🎉 ¡El registro #{reg_id_ger} ha sido totalmente autorizado por Gerencia!")
                    st.rerun()
                    
        st.markdown("---")
        st.markdown("### 📋 Historial de Registros Autorizados")
        conn = obtener_conexion()
        df_aut = pd.read_sql("SELECT * FROM registros WHERE estado = 'Completado y Autorizado (Gerencia)'", conn)
        conn.close()
        if not df_aut.empty:
            st.dataframe(df_aut, use_container_width=True)
        else:
            st.write("Aún no hay registros completamente autorizados por gerencia.")