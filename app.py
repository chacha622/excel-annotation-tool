# ⚠️ 请注意：本脚本基于 Streamlit 框架运行。
# 如果你在本地运行，请确保已使用 `pip install streamlit pandas xlsxwriter openpyxl` 安装依赖。

import re
import pandas as pd
from io import BytesIO
import json

try:
    import streamlit as st
except ImportError:
    raise ImportError("本脚本需要在支持 Streamlit 的环境中运行。请本地执行：pip install streamlit")

st.set_page_config(page_title="Excel 标注小工具", layout="wide")
st.title("📄 Excel 文本标注小工具")

# 初始化状态
if "df" not in st.session_state:
    st.session_state.df = None
    st.session_state.current_index = 0
    st.session_state.settings_confirmed = False
    st.session_state.column_roles = {}

# 上传页面
st.header("Step 1: 上传文件")
uploaded_file = st.file_uploader("上传 Excel/CSV/JSON 文件", type=[".xlsx", ".csv", ".json"])

df = None  # ✅ 避免 NameError

if uploaded_file:
    if uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    elif uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith(".json"):
        df = pd.read_json(uploaded_file)
    else:
        st.error("不支持的文件格式")
        df = None

   # Step 1: 上传并读取文件
if df is not None:
    # 仅在首次上传或新文件时重置
    if st.session_state.df is None or not df.equals(st.session_state.df):
        st.session_state.df = df.copy()
        st.success(f"成功读取 {len(df)} 条数据")
        st.dataframe(df.head())
        st.session_state.settings_confirmed = False  # ✅ 只在首次/新文件时重置配置

# Step 2: 定义字段类型
confirm = False  # 预设变量，避免未定义错误

if st.session_state.df is not None and not st.session_state.settings_confirmed:
    df = st.session_state.df
    st.header("Step 2: 字段配置")
    with st.form("define_columns"):
        problem_columns = st.multiselect("请选择问题字段（仅展示）", df.columns.tolist())
        model_columns = st.multiselect("请选择模型结果字段（格式化展示）", df.columns.tolist())
        label_columns = st.multiselect("请选择分类标注字段（单选）", df.columns.tolist())
        note_columns = st.multiselect("请选择备注字段（限50字输入）", df.columns.tolist())
        confirm = st.form_submit_button("确认配置")

# 修改后确认配置
if confirm:
    st.session_state.column_roles = {
        "problem": problem_columns,
        "model": model_columns,
        "label": label_columns,
        "note": note_columns
    }
    for col in label_columns + note_columns:
        if col not in df.columns:
            df[col] = ""
    st.session_state.settings_confirmed = True

# 安全的延迟触发 rerun
if st.session_state.get("trigger_rerun", False):
    st.session_state.trigger_rerun = False
    st.experimental_rerun()


# Step 3: 标注界面
if st.session_state.df is not None and st.session_state.settings_confirmed:
    df = st.session_state.df
    roles = st.session_state.column_roles
    index = st.session_state.current_index
    row = df.iloc[index]

    def format_text(text):
        if not isinstance(text, str):
            return text
        text = text.replace("/n", "\n").replace("/t", "  ")
        text = re.sub(r"###(.*?)", r"**\\1**", text)
        return text

    st.header("Step 3: 标注页面")
    st.markdown(f"### 当前第 {index+1}/{len(df)} 条")

    for col in roles.get("problem", []):
        st.markdown(f"**{col}：** {row[col]}")

    for col in roles.get("model", []):
        st.markdown(f"**{col}：**")
        st.markdown(format_text(str(row[col])), unsafe_allow_html=True)

    label_inputs = {}
    for col in roles.get("label", []):
        label_inputs[col] = st.radio(
            f"{col}（分类标注）",
            ["正确", "错误", "不确定"],
            index=["正确", "错误", "不确定"].index(str(row.get(col, "不确定"))) if row.get(col) in ["正确", "错误", "不确定"] else 2,
            key=f"label_{col}_{index}"
        )

    note_inputs = {}
    for col in roles.get("note", []):
        note_inputs[col] = st.text_area(
            f"{col}（备注，限50字）",
            value=str(row.get(col, "")),
            max_chars=50,
            key=f"note_{col}_{index}"
        )

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("⬅ 上一个") and index > 0:
            st.session_state.current_index -= 1
            st.experimental_rerun()
    with col2:
        if st.button("💾 保存本条"):
            for k, v in label_inputs.items():
                df.at[index, k] = v
            for k, v in note_inputs.items():
                df.at[index, k] = v
            st.success("保存成功！")
    with col3:
if st.button("➡ 下一个"):
    if index < len(df) - 1:
        st.session_state.current_index += 1
        st.experimental_rerun()
        
if st.button("⬅ 上一个"):
    if index > 0:
        st.session_state.current_index -= 1
        st.experimental_rerun()


    st.progress((index + 1) / len(df))

# Step 4: 导出结果
if st.session_state.df is not None and st.session_state.settings_confirmed:
    st.header("Step 4: 导出结果")
    def convert_to_format(df, fmt):
        if fmt == "excel":
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="标注结果")
            return output.getvalue()
        elif fmt == "csv":
            return df.to_csv(index=False).encode("utf-8")
        elif fmt == "json":
            return df.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8")
        return None

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            "📥 导出为 Excel",
            data=convert_to_format(st.session_state.df, "excel"),
            file_name="标注结果.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with col2:
        st.download_button(
            "📥 导出为 CSV",
            data=convert_to_format(st.session_state.df, "csv"),
            file_name="标注结果.csv",
            mime="text/csv"
        )
    with col3:
        st.download_button(
            "📥 导出为 JSON",
            data=convert_to_format(st.session_state.df, "json"),
            file_name="标注结果.json",
            mime="application/json"
        )
