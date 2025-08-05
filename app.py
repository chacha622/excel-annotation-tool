# 注意：本脚本需运行在 streamlit 环境下（如 streamlit.io 或本地安装后使用 streamlit run）

try:
    import streamlit as st
    import pandas as pd
    import json
    import io
    import re
except ModuleNotFoundError:
    raise ModuleNotFoundError("请在含有 streamlit 的 Python 环境中运行此程序，或使用 'pip install streamlit pandas openpyxl xlsxwriter' 安装所需依赖")

# 状态持久化
if 'data' not in st.session_state:
    st.session_state.data = None
if 'field_types' not in st.session_state:
    st.session_state.field_types = {}
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'annotations' not in st.session_state:
    st.session_state.annotations = {}
if 'step' not in st.session_state:
    st.session_state.step = 1

st.title("在线模型结果标注工具")

# 步骤导航栏
step = st.sidebar.radio("操作步骤", ["1. 上传文件", "2. 字段配置", "3. 开始标注", "4. 导出结果"])
if step.startswith("1"):
    st.session_state.step = 1
elif step.startswith("2"):
    st.session_state.step = 2
elif step.startswith("3"):
    st.session_state.step = 3
elif step.startswith("4"):
    st.session_state.step = 4

# 一、上传文件
def upload_data():
    uploaded_file = st.file_uploader("上传数据文件 (支持 Excel/CSV/JSON)", type=["xlsx", "csv", "json"])
    if uploaded_file:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith(".json"):
            df = pd.read_json(uploaded_file)
        else:
            st.error("不支持的文件格式")
            return
        st.session_state.data = df
        st.session_state.field_types = {}
        st.session_state.annotations = {}
        st.session_state.current_index = 0
        st.success(f"成功读取 {len(df)} 条数据")
        st.session_state.step = 2
        st.experimental_rerun()

# 二、定义字段类型

def configure_fields():
    df = st.session_state.data
    st.subheader("字段类型配置")

    label_choices = ["问题（仅展示）", "模型结果（展示+处理）", "标注项（单选）", "备注项（文本输入）", "忽略此列"]
    selected_mapping = {}

    for label_type in ["问题（仅展示）", "模型结果（展示+处理）", "标注项（单选）", "备注项（文本输入）"]:
        candidates = st.multiselect(f"选择对应为【{label_type}】的列", df.columns, key=f"multi_{label_type}")
        for col in candidates:
            selected_mapping[col] = label_type

    # 显示配置输入框
    types = {}
    for col in df.columns:
        col_type = selected_mapping.get(col, "忽略此列")
        if col_type == "忽略此列":
            continue
        st.markdown(f"### 字段: `{col}` → {col_type}")
        types[col] = {'type': col_type}
        if col_type == "标注项（单选）":
            options = st.text_input(f"设置 `{col}` 可选项（用英文逗号分隔）", "正确,错误,不确定", key=f"opts_{col}")
            types[col]['options'] = [o.strip() for o in options.split(",")]
        elif col_type == "备注项（文本输入）":
            types[col]['max_length'] = 50

    if st.button("完成配置"):
        st.session_state.field_types = types
        st.success("配置完成，可前往下一步开始标注")

# 格式化模型结果文本
def format_model_output(text):
    text = str(text)
    text = text.replace("/n", "\n").replace("/t", "  ")
    lines = text.splitlines()
    formatted = []
    for line in lines:
        if line.startswith("###"):
            formatted.append(f"**{line[3:].strip()}**")
        elif line.startswith("##"):
            formatted.append(f"**{line[2:].strip()}**")
        elif line.startswith("#"):
            formatted.append(f"**{line[1:].strip()}**")
        else:
            formatted.append(line)
    return "\n".join(formatted)

# 三、标注页面
def annotation_page():
    df = st.session_state.data
    index = st.session_state.current_index
    config = st.session_state.field_types

    st.subheader(f"当前第 {index + 1} / {len(df)} 条数据")
    row = df.iloc[index]
    annotation = st.session_state.annotations.get(index, {})

    for col, meta in config.items():
        if meta['type'] == "问题（仅展示）":
            st.markdown(f"**{col}:** {row[col]}")
        elif meta['type'] == "模型结果（展示+处理）":
            content = format_model_output(row[col])
            st.markdown(f"**{col}:**\n{content}")
        elif meta['type'] == "标注项（单选）":
            selected = st.radio(f"{col}", meta['options'], key=f"{index}_{col}_radio", index=meta['options'].index(annotation.get(col, meta['options'][0])) if annotation.get(col) else 0)
            annotation[col] = selected
        elif meta['type'] == "备注项（文本输入）":
            note = st.text_input(f"{col} (最多 {meta['max_length']} 字)", value=annotation.get(col, ""), max_chars=meta['max_length'], key=f"{index}_{col}_note")
            annotation[col] = note

    def save_current():
        st.session_state.annotations[index] = annotation

    if st.button("保存"):
        save_current()
        st.success("保存成功")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("上一条") and index > 0:
            save_current()
            st.session_state.current_index -= 1
    with col2:
        if st.button("下一条") and index < len(df) - 1:
            save_current()
            st.session_state.current_index += 1

    st.progress((index + 1) / len(df))

# 四、导出结果
def export_results():
    df = st.session_state.data.copy()
    for idx, annotation in st.session_state.annotations.items():
        for col, val in annotation.items():
            df.at[idx, f"标注_{col}"] = val

    st.subheader("导出标注结果")
    export_format = st.selectbox("选择导出格式", ["Excel", "CSV", "JSON"])
    if st.button("导出"):
        if export_format == "Excel":
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button("下载 Excel 文件", data=output.getvalue(), file_name="annotation_result.xlsx")
        elif export_format == "CSV":
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("下载 CSV 文件", data=csv, file_name="annotation_result.csv")
        elif export_format == "JSON":
            json_data = df.to_json(orient='records', force_ascii=False)
            st.download_button("下载 JSON 文件", data=json_data, file_name="annotation_result.json")

# 页面逻辑控制
if st.session_state.step == 1:
    upload_data()
elif st.session_state.step == 2:
    if st.session_state.data is not None:
        configure_fields()
    else:
        st.warning("请先上传文件")
elif st.session_state.step == 3:
    if st.session_state.data is not None and st.session_state.field_types:
        annotation_page()
    else:
        st.warning("请完成字段配置")
elif st.session_state.step == 4:
    if st.session_state.data is not None:
        export_results()
    else:
        st.warning("暂无数据可导出")
