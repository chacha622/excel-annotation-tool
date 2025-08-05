# ⚠️ 请注意：本脚本基于 Streamlit 框架运行。
# 如果你在本地运行，请确保已使用 `pip install streamlit pandas xlsxwriter openpyxl` 安装依赖。
# 在线编辑器（如ChatGPT）不支持运行 Streamlit 应用。

import re
import pandas as pd
from io import BytesIO

try:
    import streamlit as st
except ImportError:
    raise ImportError("本脚本需要在支持 Streamlit 的环境中运行。请本地执行：pip install streamlit")

st.set_page_config(page_title="Excel 标注小工具", layout="wide")
st.title("📄 Excel 文本标注小工具")

# 会话状态初始化
if "df" not in st.session_state:
    st.session_state.df = None
    st.session_state.current_index = 0

# 上传页面
st.header("Step 1: 上传 Excel 文件")
uploaded_file = st.file_uploader("上传 Excel 文件", type=[".xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.session_state.df = df.copy()
    st.success(f"成功读取 {len(df)} 条数据")
    st.dataframe(df.head())

# 字段定义与处理
if st.session_state.df is not None:
    df = st.session_state.df
    st.header("Step 2: 定义字段")
    with st.form("field_definition_form"):
        text_fields = st.multiselect("请选择模型结果字段（将展示并格式处理）", df.columns.tolist())
        query_field = st.selectbox("请选择查询字段（问题/上下文）", df.columns.tolist())
        label_fields = st.multiselect("新增分类标注字段（如多分类、单选）", options=["label1", "label2", "label3"])
        text_note_fields = st.multiselect("新增备注类标注字段（可输入文本）", options=["remark1", "remark2"])
        submit_fields = st.form_submit_button("确认字段设置")

    # 新增列初始化
    for col in label_fields:
        if col not in df.columns:
            df[col] = ""
    for col in text_note_fields:
        if col not in df.columns:
            df[col] = ""

    # Step 4: 格式处理
    def format_text(text):
        if not isinstance(text, str):
            return text
        text = text.replace("/n", "\n").replace("/t", "  ")
        text = re.sub(r"###(.*?)", r"**\\1**", text)
        return text

    st.header("Step 4: 标注页面")
    index = st.session_state.current_index
    row = df.iloc[index]

    st.markdown(f"### 当前第 {index+1}/{len(df)} 条")
    st.markdown(f"**Query：** {row[query_field]}")

    for field in text_fields:
        st.markdown(f"**{field}：**")
        st.markdown(format_text(str(row[field])), unsafe_allow_html=True)

    # 多字段标注输入
    label_inputs = {}
    for field in label_fields:
        label_inputs[field] = st.radio(f"{field}（分类标注）", ["Y", "N", "不确定"], key=f"label_{field}_{index}", index=["Y", "N", "不确定"].index(str(row.get(field, "不确定")) if str(row.get(field, "")) in ["Y", "N"] else "不确定"))

    text_inputs = {}
    for field in text_note_fields:
        text_inputs[field] = st.text_area(f"{field}（备注说明）", value=row.get(field, ""), key=f"remark_{field}_{index}")

    # 按钮
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("⬅ 上一个") and index > 0:
            st.session_state.current_index -= 1
    with col2:
        if st.button("💾 保存本条"):
            for field, value in label_inputs.items():
                st.session_state.df.at[index, field] = value
            for field, value in text_inputs.items():
                st.session_state.df.at[index, field] = value
            st.success("已保存")
    with col3:
        if st.button("➡ 下一个") and index < len(df) - 1:
            st.session_state.current_index += 1

    # Step 5: 导出
    st.header("Step 5: 导出结果")
    def convert_df_to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="标注结果")
        processed_data = output.getvalue()
        return processed_data

    if st.download_button(
        label="📥 下载标注结果 Excel",
        data=convert_df_to_excel(st.session_state.df),
        file_name="标注结果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ):
        st.success("导出成功！")
