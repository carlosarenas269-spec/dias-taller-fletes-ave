from datetime import datetime
import io
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
import psycopg2
from sqlalchemy import create_engine

# ==========================================
# CONFIGURACIÓN DE LA BASE DE DATOS SUPABASE (POSTGRESQL)
# ==========================================
def obtener_conexion():
    """
    Crea la conexión a Supabase usando la URL guardada en los secretos de Streamlit.
    """
    db_url = st.secrets["postgres"]["url"]
    # Usamos SQLAlchemy para mantener compatibilidad con pd.read_sql
    engine = create_engine(db_url)
    return engine.connect()

def init_db():
    """
    Inicializa las tablas necesarias en Supabase si no existen.
    """
    db_url = st.secrets["postgres"]["url"]
    engine = create_engine(db_url)
    
    with engine.begin() as conn:
        # Tabla de Registros de Taller
        conn.execute(pd.text("""
            CREATE TABLE IF NOT EXISTS registros (
                id SERIAL PRIMARY KEY,
                fecha_creacion TEXT,
                operador TEXT,
                actividades TEXT,
                dias DOUBLE PRECISION,
                valor_unitario DOUBLE PRECISION,
                total DOUBLE PRECISION,
                estado TEXT,
                fecha_aprobacion_operaciones TEXT,
                fecha_aprobacion_gerencia TEXT,
                evidencia BYTEA
            )
        """))

        # Tabla de Operadores
        conn.execute(pd.text("""
            CREATE TABLE IF NOT EXISTS operadores (
                nombre TEXT UNIQUE
            )
        """))

        # Tabla de Configuración (Tarifa)
        conn.execute(pd.text("""
            CREATE TABLE IF NOT EXISTS config (
                clave TEXT UNIQUE,
                valor DOUBLE PRECISION
            )
        """))

        # Insertar valores iniciales si están vacíos los operadores
        result = conn.execute(pd.text("SELECT COUNT(*) FROM operadores")).fetchone()
        if result[0] == 0:
            conn.execute(pd.text("INSERT INTO operadores (nombre) VALUES (:nombre)"), {"nombre": "Octavio Rodrigo Serrano Saavedra"})
            conn.execute(pd.text("INSERT INTO operadores (nombre) VALUES (:nombre)"), {"nombre": "Operador 1"})
            conn.execute(pd.text("INSERT INTO operadores (nombre) VALUES (:nombre)"), {"nombre": "Operador 2"})

        # Insertar valor inicial de la tarifa si no existe
        result_config = conn.execute(pd.text("SELECT COUNT(*) FROM config WHERE clave = 'valor_dia'")).fetchone()
        if result_config[0] == 0:
            conn.execute(pd.text("INSERT INTO config (clave, valor) VALUES ('valor_dia', 416.67)"))

init_db()

# Funciones de apoyo para interactuar con la Base de Datos
def cargar_operadores():
    engine = create_engine(st.secrets["postgres"]["url"])
    df_ops = pd.read_sql("SELECT nombre FROM operadores", engine)
    return df_ops["nombre"].tolist()

def obtener_tarifa():
    engine = create_engine(st.secrets["postgres"]["url"])
    with engine.connect() as conn:
        res = conn.execute(pd.text("SELECT valor FROM config WHERE clave = 'valor_dia'")).fetchone()
        val = res[0] if res else 416.67
    return float(val)

def cargar_registros():
    engine = create_engine(st.secrets["postgres"]["url"])
    df = pd.read_sql("SELECT * FROM registros", engine)
    # Convertir BYTEA de Postgres a bytes legibles en python si es necesario
    return df.to_dict("records")

st.set_page_config(
    page_title="Sistema de Control - Taller Fletes AVE", layout="wide"
)

# ==========================================
# GESTIÓN DE ESTADOS PARA PERSONALIZACIÓN
# ==========================================
if "custom_title" not in st.session_state:
    st.session_state.custom_title = "🚜 SISTEMA DE CONTROL DE DÍAS DE TALLER - FLETES AVE"
if "custom_logo" not in st.session_state:
    st.session_state.custom_logo = None
if "custom_cover" not in st.session_state:
    st.session_state.custom_cover = None
if "cover_width" not in st.session_state:
    st.session_state.cover_width = 100

# --- RENDERIZADO DINÁMICO DE PORTADA Y TÍTULO ---
if st.session_state.custom_cover is not None:
    ancho_portada = st.session_state.cover_width
    if ancho_portada == 100:
        st.image(st.session_state.custom_cover, use_container_width=True)
    else:
        _, col_img, _ = st.columns([
            (100 - ancho_portada) / 200,
            ancho_portada / 100,
            (100 - ancho_portada) / 200,
        ])
        with col_img:
            st.image(st.session_state.custom_cover, use_container_width=True)

col_logo_h, col_tit_h = st.columns([0.08, 0.92])
with col_logo_h:
    if st.session_state.custom_logo is not None:
        st.image(st.session_state.custom_logo, width=60)
with col_tit_h:
    st.title(st.session_state.custom_title)

# Selector de Perfil / Rol en la barra lateral
st.sidebar.header("🔐 Control de Acceso y Perfiles")
perfil = st.sidebar.selectbox(
    "Seleccione su Rol:",
    ["1. Capturista", "2. Jefe de Operaciones (Admin)", "3. Gerente"],
)

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

    actividades = st.text_area(
        "ACTIVIDADES DESEMPEÑADAS: *",
        placeholder="Describa a detalle las tareas realizadas...",
    )
    evidencia = st.file_uploader(
        "EVIDENCIA (Imagen/Fotografía obligatoria): *",
        type=["png", "jpg", "webp"],
    )
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
            evidencia_bytes = evidencia.read()

            engine = create_engine(st.secrets["postgres"]["url"])
            with engine.begin() as conn:
                conn.execute(
                    pd.text("""
                        INSERT INTO registros (fecha_creacion, operador, actividades, dias, valor_unitario, total, estado, fecha_aprobacion_operaciones, fecha_aprobacion_gerencia, evidencia)
                        VALUES (:fecha_creacion, :operador, :actividades, :dias, :valor_unitario, :total, :estado, :fecha_op, :fecha_ger, :evidencia)
                    """),
                    {
                        "fecha_creacion": fecha_creacion,
                        "operador": operador,
                        "actividades": actividades,
                        "dias": float(dias_taller),
                        "valor_unitario": valor_unitario_actual,
                        "total": total_taller,
                        "estado": estado_inicial,
                        "fecha_op": "",
                        "fecha_ger": "",
                        "evidencia": evidencia_bytes
                    }
                )

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

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "✍️ Autorizaciones",
            "⚙️ Operadores y Tarifas",
            "🛠️ Modificar / Eliminar",
            "📊 Historial y Descargas",
            "🎨 Personalización Visual",
        ])

        with tab1:
            pendientes_ops = [
                r["id"] for r in registros
                if r["estado"] == "Pendiente de Aprobación (Operaciones)"
            ]

            if not pendientes_ops:
                st.success("🎉 No hay registros pendientes de autorización por parte de Operaciones.")
            else:
                reg_id = st.selectbox("Seleccione el ID del Registro a Autorizar:", pendientes_ops, key="auth_op")
                reg_sel = next((r for r in registros if r["id"] == reg_id), None)

                if reg_sel:
                    st.write(f"**Operador:** {reg_sel['operador']}")
                    st.write(f"**Actividades:** {reg_sel['actividades']}")
                    st.write(f"**Días de Taller:** {reg_sel['dias']}")

                    if reg_sel["evidencia"] is not None:
                        st.markdown("**📸 Evidencia Adjunta:**")
                        st.image(reg_sel["evidencia"], caption=f"Evidencia Registro #{reg_id}", width=400)

                    nuevo_val_unit = st.number_input(
                        "Modificar Valor Unitario ($):",
                        value=float(reg_sel["valor_unitario"]),
                        format="%.2f",
                        key="val_unit_auth",
                    )
                    nuevo_total = reg_sel["dias"] * nuevo_val_unit
                    st.write(f"**Total Ajustado:** ${nuevo_total:,.2f} MXN")

                    if st.button("✔️ Autorizar como Jefe de Operaciones"):
                        fecha_op = datetime.now(ZoneInfo("America/Monterrey")).strftime("%Y-%m-%d %H:%M")
                        engine = create_engine(st.secrets["postgres"]["url"])
                        with engine.begin() as conn:
                            conn.execute(
                                pd.text("""
                                    UPDATE registros 
                                    SET valor_unitario = :val_unit, total = :tot, estado = :est, fecha_aprobacion_operaciones = :f_op
                                    WHERE id = :rid
                                """),
                                {
                                    "val_unit": nuevo_val_unit,
                                    "tot": nuevo_total,
                                    "est": "Pendiente de Aprobación (Gerencia)",
                                    "f_op": fecha_op,
                                    "rid": reg_id
                                }
                            )
                        st.success(f"¡Registro #{reg_id} autorizado por Operaciones! Ahora pasó al módulo de Gerencia.")
                        st.rerun()

        with tab2:
            st.markdown("### ⚙️ Configuración del Sistema")

            nuevo_costo_base = st.number_input(
                "Modificar Costo Estándar por Día de Taller ($ MXN):",
                value=float(valor_unitario_actual),
                format="%.2f",
                step=10.0,
            )
            if st.button("💾 Actualizar Tarifa Estándar"):
                engine = create_engine(st.secrets["postgres"]["url"])
                with engine.begin() as conn:
                    conn.execute(
                        pd.text("UPDATE config SET valor = :val WHERE clave = 'valor_dia'"),
                        {"val": nuevo_costo_base}
                    )
                st.success(f"✅ Tarifa estándar actualizada a ${nuevo_costo_base:,.2f} MXN.")
                st.rerun()

            st.markdown("---")
            st.markdown("### ➕ Agregar Nuevo Operador")
            nuevo_operador_nombre = st.text_input("Nombre del Nuevo Operador:", key="input_nuevo_op")
            if st.button("Registrar Operador"):
                if nuevo_operador_nombre.strip():
                    try:
                        engine = create_engine(st.secrets["postgres"]["url"])
                        with engine.begin() as conn:
                            conn.execute(
                                pd.text("INSERT INTO operadores (nombre) VALUES (:nombre)"),
                                {"nombre": nuevo_operador_nombre.strip()}
                            )
                        st.success(f"✅ Operador '{nuevo_operador_nombre.strip()}' agregado correctamente.")
                        st.rerun()
                    except Exception:
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
                        engine = create_engine(st.secrets["postgres"]["url"])
                        with engine.begin() as conn:
                            conn.execute(
                                pd.text("DELETE FROM operadores WHERE nombre = :nombre"),
                                {"nombre": operador_a_eliminar}
                            )
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
                    if registro_encontrado["evidencia"] is not None:
                        st.markdown("**📸 Evidencia actual guardada:**")
                        st.image(registro_encontrado["evidencia"], width=300)

                    with st.form("form_edicion_registro"):
                        op_edit = st.selectbox(
                            "Operador:",
                            lista_operadores,
                            index=(lista_operadores.index(registro_encontrado["operador"]) if registro_encontrado["operador"] in lista_operadores else 0),
                        )
                        dias_edit = st.number_input("Días de Taller:", value=float(registro_encontrado["dias"]), step=0.5, format="%.1f")
                        act_edit = st.text_area("Actividades Desempeñadas:", value=registro_encontrado["actividades"])
                        val_unit_edit = st.number_input("Valor Unitario ($):", value=float(registro_encontrado["valor_unitario"]), format="%.2f")

                        col_btn1, col_btn2 = st.columns(2)
                        actualizar_btn = col_btn1.form_submit_button("💾 Guardar Cambios")
                        eliminar_btn = col_btn2.form_submit_button("🗑️ Eliminar Registro", type="primary")

                        if actualizar_btn:
                            nuevo_total = float(dias_edit) * float(val_unit_edit)
                            engine = create_engine(st.secrets["postgres"]["url"])
                            with engine.begin() as conn:
                                conn.execute(
                                    pd.text("""
                                        UPDATE registros 
                                        SET operador = :op, dias = :dias, actividades = :act, valor_unitario = :vu, total = :tot
                                        WHERE id = :rid
                                    """),
                                    {
                                        "op": op_edit,
                                        "dias": float(dias_edit),
                                        "act": act_edit,
                                        "vu": float(val_unit_edit),
                                        "tot": nuevo_total,
                                        "rid": id_a_editar
                                    }
                                )
                            st.success(f"✅ ¡Registro #{id_a_editar} actualizado con éxito!")
                            st.rerun()

                        if eliminar_btn:
                            engine = create_engine(st.secrets["postgres"]["url"])
                            with engine.begin() as conn:
                                conn.execute(
                                    pd.text("DELETE FROM registros WHERE id = :rid"),
                                    {"rid": id_a_editar}
                                )
                            st.success(f"🗑️ ¡Registro #{id_a_editar} eliminado correctamente!")
                            st.rerun()

        with tab4:
            st.markdown("### 🗂️ Historial General de Registros")
            engine = create_engine(st.secrets["postgres"]["url"])
            df_mostrar = pd.read_sql(
                "SELECT id, fecha_creacion, operador, actividades, dias, valor_unitario, total, estado, fecha_aprobacion_operaciones, fecha_aprobacion_gerencia FROM registros",
                engine,
            )
            st.dataframe(df_mostrar, use_container_width=True)

            st.markdown("### 📥 Descargar Reportes")
            formato_descarga = st.radio("Seleccione el formato de descarga:", ["Excel (.xlsx)", "CSV (.csv)"], horizontal=True, key="formato_rep")
            fecha_actual = datetime.now(ZoneInfo("America/Monterrey")).strftime("%Y%m%d")

            if formato_descarga == "Excel (.xlsx)":
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df_mostrar.to_excel(writer, index=False, sheet_name="Historial Taller")
                excel_data = output.getvalue()

                st.download_button(
                    label="📥 Descargar Historial en Excel (.xlsx)",
                    data=excel_data,
                    file_name=f"historial_taller_fletes_ave_{fecha_actual}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                csv_data = df_mostrar.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Descargar Historial en CSV (.csv)",
                    data=csv_data,
                    file_name=f"historial_taller_fletes_ave_{fecha_actual}.csv",
                    mime="text/csv",
                )

        with tab5:
            st.markdown("### 🎨 Personalización de Apariencia del Sistema")
            st.write("Modifica el título principal, agrega logotipos, configura la imagen de portada y guarda los cambios.")

            with st.form("form_personalizacion_visual"):
                nuevo_titulo_input = st.text_input("Editar Título Principal:", value=st.session_state.custom_title)

                st.markdown("---")
                subir_logo = st.file_uploader("Cargar Logotipo de la Empresa (PNG/JPG):", type=["png", "jpg", "webp"], key="up_logo")

                st.markdown("---")
                subir_portada = st.file_uploader("Cargar Imagen de Portada (PNG/JPG):", type=["png", "jpg", "webp"], key="up_cover")

                st.markdown("#### 📐 Ajustar Tamaño de la Imagen de Portada")
                nuevo_ancho_portada = st.slider("Ancho de la portada (%):", min_value=20, max_value=100, value=st.session_state.cover_width, step=5)

                st.markdown("---")
                btn_guardar_visual = st.form_submit_button("💾 Guardar Cambios Visuales", type="primary")

                if btn_guardar_visual:
                    st.session_state.custom_title = nuevo_titulo_input
                    st.session_state.cover_width = nuevo_ancho_portada

                    if subir_logo is not None:
                        st.session_state.custom_logo = subir_logo

                    if subir_portada is not None:
                        st.session_state.custom_cover = subir_portada

                    st.success("¡Cambios visuales guardados y aplicados exitosamente!")
                    st.rerun()

            st.markdown("---")
            st.markdown("### ⚙️ Opciones de Limpieza Visual")
            col_del1, col_del2 = st.columns(2)

            with col_del1:
                if st.session_state.custom_logo is not None:
                    if st.button("🗑️ Eliminar Logotipo Actual"):
                        st.session_state.custom_logo = None
                        st.success("Logotipo eliminado.")
                        st.rerun()
                else:
                    st.info("No hay logotipo activo.")

            with col_del2:
                if st.session_state.custom_cover is not None:
                    if st.button("🗑️ Eliminar Imagen de Portada Actual"):
                        st.session_state.custom_cover = None
                        st.success("Imagen de portada eliminada.")
                        st.rerun()
                else:
                    st.info("No hay imagen de portada activa.")

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
        pendientes_gerencia = [
            r["id"] for r in registros
            if r["estado"] == "Pendiente de Aprobación (Gerencia)"
        ]

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

                if reg_sel_ger["evidencia"] is not None:
                    st.markdown("**📸 Evidencia Adjunta:**")
                    st.image(reg_sel_ger["evidencia"], caption=f"Evidencia Registro #{reg_id_ger}", width=400)

                if st.button("✔️ Otorgar Autorización Final (Gerencia)"):
                    fecha_ger = datetime.now(ZoneInfo("America/Monterrey")).strftime("%Y-%m-%d %H:%M")
                    engine = create_engine(st.secrets["postgres"]["url"])
                    with engine.begin() as conn:
                        conn.execute(
                            pd.text("""
                                UPDATE registros 
                                SET estado = :est, fecha_aprobacion_gerencia = :f_ger
                                WHERE id = :rid
                            """),
                            {
                                "est": "Completado y Autorizado (Gerencia)",
                                "f_ger": fecha_ger,
                                "rid": reg_id_ger
                            }
                        )
                    st.success(f"🎉 ¡El registro #{reg_id_ger} ha sido totalmente autorizado por Gerencia!")
                    st.rerun()

        st.markdown("---")
        st.markdown("### 📋 Historial de Registros Autorizados")
        engine = create_engine(st.secrets["postgres"]["url"])
        df_aut = pd.read_sql(
            "SELECT id, fecha_creacion, operador, actividades, dias, valor_unitario, total, estado, fecha_aprobacion_operaciones, fecha_aprobacion_gerencia FROM registros WHERE estado = 'Completado y Autorizado (Gerencia)'",
            engine,
        )
        if not df_aut.empty:
            st.dataframe(df_aut, use_container_width=True)
        else:
            st.write("Aún no hay registros completamente autorizados por gerencia.")
