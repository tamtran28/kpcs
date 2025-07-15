import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Hệ thống Báo cáo KPCS Tự động")
st.title("📊 Hệ thống Báo cáo Tự động")

# ==============================================================================
# PHẦN 1: CÁC HÀM LOGIC CHO CHỨC NĂNG "TẠO 7 BÁO CÁO (TỔNG HỢP)"
# ==============================================================================

def calculate_summary_metrics(dataframe, groupby_cols, year_start_date, quarter_start_date, quarter_end_date):
    if not isinstance(groupby_cols, list):
        raise TypeError("groupby_cols phải là một danh sách (list)")

    def agg(data_filtered, cols):
        if data_filtered.empty:
            return 0 if not cols else pd.Series(dtype=int)
        if not cols:
            return len(data_filtered)
        return data_filtered.groupby(cols).size()

    ton_dau_quy = agg(dataframe[(dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] < quarter_start_date) & ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= quarter_start_date))], groupby_cols)
    phat_sinh_quy = agg(dataframe[(dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] >= quarter_start_date) & (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= quarter_end_date)], groupby_cols)
    khac_phuc_quy = agg(dataframe[(dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= quarter_start_date) & (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] <= quarter_end_date)], groupby_cols)
    phat_sinh_nam = agg(dataframe[(dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] >= year_start_date) & (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= quarter_end_date)], groupby_cols)
    khac_phuc_nam = agg(dataframe[(dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= year_start_date) & (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] <= quarter_end_date)], groupby_cols)
    ton_dau_nam = agg(dataframe[(dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] < year_start_date) & ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= year_start_date))], groupby_cols)

    if not groupby_cols:
        summary = pd.DataFrame({'Tồn đầu quý': [ton_dau_quy], 'Phát sinh quý': [phat_sinh_quy], 'Khắc phục quý': [khac_phuc_quy], 'Tồn đầu năm': [ton_dau_nam], 'Phát sinh năm': [phat_sinh_nam], 'Khắc phục năm': [khac_phuc_nam]})
    else:
        summary = pd.DataFrame({'Tồn đầu quý': ton_dau_quy, 'Phát sinh quý': phat_sinh_quy, 'Khắc phục quý': khac_phuc_quy, 'Tồn đầu năm': ton_dau_nam, 'Phát sinh năm': phat_sinh_nam, 'Khắc phục năm': khac_phuc_nam}).fillna(0).astype(int)

    summary['Tồn cuối quý'] = summary['Tồn đầu quý'] + summary['Phát sinh quý'] - summary['Khắc phục quý']
    
    df_actually_outstanding = dataframe[(dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= quarter_end_date) & ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] > quarter_end_date))]
    qua_han_khac_phuc = agg(df_actually_outstanding[df_actually_outstanding['Thời hạn hoàn thành (mm/dd/yyyy)'] < quarter_end_date], groupby_cols)
    qua_han_tren_1_nam = agg(df_actually_outstanding[df_actually_outstanding['Thời hạn hoàn thành (mm/dd/yyyy)'] < (quarter_end_date - pd.DateOffset(years=1))], groupby_cols)

    summary['Quá hạn khắc phục'] = qua_han_khac_phuc
    summary['Trong đó quá hạn trên 1 năm'] = qua_han_tren_1_nam
    summary = summary.fillna(0).astype(int)

    denominator = summary['Tồn đầu quý'] + summary['Phát sinh quý']
    summary['Tỷ lệ chưa KP đến cuối Quý'] = (summary['Tồn cuối quý'] / denominator).replace([np.inf, -np.inf], 0).fillna(0)
    
    final_cols_order = ['Tồn đầu năm', 'Phát sinh năm', 'Khắc phục năm', 'Tồn đầu quý', 'Phát sinh quý', 'Khắc phục quý', 'Tồn cuối quý', 'Quá hạn khắc phục', 'Trong đó quá hạn trên 1 năm', 'Tỷ lệ chưa KP đến cuối Quý']
    summary = summary.reindex(columns=final_cols_order, fill_value=0)
    return summary

def create_summary_table(dataframe, groupby_col, dates):
    summary = calculate_summary_metrics(dataframe, [groupby_col], **dates)
    if not summary.empty:
        total_row = pd.DataFrame(summary.sum(numeric_only=True)).T
        total_row.index = ['TỔNG CỘNG']
        total_denom = total_row.at['TỔNG CỘNG', 'Tồn đầu quý'] + total_row.at['TỔNG CỘNG', 'Phát sinh quý']
        total_row['Tỷ lệ chưa KP đến cuối Quý'] = (total_row.at['TỔNG CỘNG', 'Tồn cuối quý'] / total_denom) if total_denom != 0 else 0
        summary = pd.concat([summary, total_row])
    return summary

def create_top_n_table(dataframe, n, dates):
    CHILD_COL = 'Đơn vị thực hiện KPCS trong quý'
    full_summary = calculate_summary_metrics(dataframe, [CHILD_COL], **dates)
    top_n = full_summary.sort_values(by='Quá hạn khắc phục', ascending=False).head(n)
    total_row = pd.DataFrame(full_summary.sum(numeric_only=True)).T
    total_row.index = ['TỔNG CỘNG CỦA NHÓM']
    total_denom = total_row.at['TỔNG CỘNG CỦA NHÓM', 'Tồn đầu quý'] + total_row.at['TỔNG CỘNG CỦA NHÓM', 'Phát sinh quý']
    total_row['Tỷ lệ chưa KP đến cuối Quý'] = (total_row.at['TỔNG CỘNG CỦA NHÓM', 'Tồn cuối quý'] / total_denom) if total_denom != 0 else 0
    return pd.concat([top_n, total_row])

def create_hierarchical_table_7_reports(dataframe, parent_col, child_col, dates):
    summary_cols_template = ['Tồn đầu năm', 'Phát sinh năm', 'Khắc phục năm', 'Tồn đầu quý', 'Phát sinh quý', 'Khắc phục quý', 'Tồn cuối quý', 'Quá hạn khắc phục', 'Trong đó quá hạn trên 1 năm', 'Tỷ lệ chưa KP đến cuối Quý']
    cols_order = ['Tên Đơn vị'] + summary_cols_template

    if dataframe.empty or parent_col not in dataframe.columns or child_col not in dataframe.columns:
        return pd.DataFrame(columns=cols_order)

    summary = calculate_summary_metrics(dataframe, [child_col], **dates)
    parent_mapping = dataframe[[child_col, parent_col]].drop_duplicates().set_index(child_col)
    summary_with_parent = summary.join(parent_mapping)
    parent_summary = calculate_summary_metrics(dataframe, [parent_col], **dates)
    final_report_rows = []
    unique_parents = dataframe[parent_col].dropna().unique()

    for parent_name in unique_parents:
        if parent_name not in parent_summary.index: continue
        parent_row = parent_summary.loc[[parent_name]].reset_index().rename(columns={parent_col: 'Tên Đơn vị'})
        parent_row['Tên Đơn vị'] = f"**{parent_name}**"
        final_report_rows.append(parent_row)
        children_df = summary_with_parent[summary_with_parent[parent_col] == parent_name].reset_index().rename(columns={child_col: 'Tên Đơn vị'})
        children_df['Tên Đơn vị'] = "  •  " + children_df['Tên Đơn vị'].astype(str)
        final_report_rows.append(children_df)
    
    if not final_report_rows: return pd.DataFrame(columns=cols_order)
    
    full_report_df = pd.concat(final_report_rows, ignore_index=True)
    grand_total_row = calculate_summary_metrics(dataframe, [], **dates)
    grand_total_row['Tên Đơn vị'] = '**TỔNG CỘNG TOÀN BỘ**'
    full_report_df = pd.concat([full_report_df, grand_total_row], ignore_index=True)

    return full_report_df.reindex(columns=cols_order)

# ==============================================================================
# PHẦN 2: CÁC HÀM LOGIC CHO CHỨC NĂNG "KẾT QUẢ KIỂM TOÁN QUÝ" (MỚI THÊM)
# ==============================================================================

def calculate_kqkt_metrics(df_group, group_by_col=None):
    if df_group.empty: return pd.DataFrame()
    RISK_COL = 'Xếp hạng rủi ro  (Nhập theo định nghĩa ở Sheet DANHMUC)'
    ISSUE_DATE_COL = 'Ngày, tháng, năm ban hành (mm/dd/yyyy)'
    FIXED_COL = 'Đã khắc phục (Nếu đã khắc phục trong thời gian kiểm toán thì đánh dấu X)'

    if group_by_col is None:
        summary = pd.DataFrame([{'Tổng kiến nghị': len(df_group), 'Đã khắc phục': (df_group[FIXED_COL] == 'X').sum()}])
    else:
        summary = df_group.groupby(group_by_col).agg(
            **{'Thời gian phát hành báo cáo': (ISSUE_DATE_COL, 'first'),
               'Tổng kiến nghị': (group_by_col, 'size'),
               'Đã khắc phục': (FIXED_COL, lambda x: (x == 'X').sum())})
    
    if group_by_col:
        risk_breakdown = pd.crosstab(df_group[group_by_col], df_group[RISK_COL])
    else:
        risk_breakdown = df_group[RISK_COL].value_counts().to_frame().T.reset_index(drop=True)

    summary = summary.join(risk_breakdown, how='left')
    summary['Kiến nghị còn lại phải khắc phục'] = summary['Tổng kiến nghị'] - summary['Đã khắc phục']
    
    expected_risk_cols = ['Rất cao', 'Cao', 'Trung bình', 'Thấp']
    for col in expected_risk_cols:
        if col not in summary.columns: summary[col] = 0
    
    summary = summary.fillna(0)
    for col in summary.select_dtypes(include=np.number).columns:
        summary[col] = summary[col].astype(int)
        
    return summary.reset_index()

def generate_kqkt_report(df, year, quarter):
    q_start_date = pd.to_datetime(f'{year}-{(quarter-1)*3 + 1}-01')
    q_end_date = q_start_date + pd.offsets.QuarterEnd(0)
    df_quarter = df[(df['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] >= q_start_date) & 
                    (df['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= q_end_date)].copy()

    main_group_col = 'Đoàn KT/GSTX'
    group_order_and_names = {'Đoàn KT': 'I. Đoàn kiểm toán', 'BKS': 'II. Ban Kiểm Soát', 'GSTX': 'III. Giám sát từ xa (GSTX)'}
    report_parts = []
    
    for group_key, group_display_name in group_order_and_names.items():
        df_main_group = df_quarter[df_quarter[main_group_col] == group_key]
        if df_main_group.empty: continue

        header_row = calculate_kqkt_metrics(df_main_group, group_by_col=None)
        header_row.rename(columns={'index': 'Tên Đoàn kiểm toán'}, inplace=True)
        header_row['Tên Đoàn kiểm toán'] = group_display_name
        report_parts.append(header_row)

        detail_rows = calculate_kqkt_metrics(df_main_group, group_by_col='Tên Đoàn kiểm toán')
        detail_rows.rename(columns={'index': 'Tên Đoàn kiểm toán'}, inplace=True)
        report_parts.append(detail_rows)

    if not report_parts: return pd.DataFrame()

    result_df = pd.concat(report_parts, ignore_index=True)
    grand_total_row = calculate_kqkt_metrics(df_quarter, group_by_col=None)
    grand_total_row['Tên Đoàn kiểm toán'] = 'TỔNG CỘNG (I+II+III)'
    result_df = pd.concat([result_df, grand_total_row], ignore_index=True)
    
    final_cols_order = ['Tên Đoàn kiểm toán', 'Thời gian phát hành báo cáo', 'Tổng kiến nghị', 'Rất cao', 'Cao', 'Trung bình', 'Thấp', 'Đã khắc phục', 'Kiến nghị còn lại phải khắc phục']
    result_df = result_df.reindex(columns=final_cols_order).fillna('')

    date_col_name = 'Thời gian phát hành báo cáo'
    result_df[date_col_name] = pd.to_datetime(result_df[date_col_name], errors='coerce').dt.strftime('%d/%m/%Y')
    result_df = result_df.fillna('')

    result_df.insert(0, 'Stt', range(1, len(result_df) + 1))
    result_df = result_df.rename(columns={'Tên Đoàn kiểm toán': 'Tên Đoàn kiểm toán/Báo cáo', 'Đã khắc phục': 'Đã khắc phục trong thời gian'})
    return result_df

# ==============================================================================
# PHẦN 3: GIAO DIỆN VÀ LUỒNG THỰC THI CỦA STREAMLIT
# ==============================================================================

with st.sidebar:
    st.header("⚙️ Tùy chọn báo cáo")
    input_year = st.number_input("Chọn Năm báo cáo", min_value=2020, max_value=2030, value=2024, help="Năm để tạo báo cáo.")
    input_quarter = st.selectbox("Chọn Quý báo cáo", options=[1, 2, 3, 4], index=3, help="Quý để tạo báo cáo.")
    uploaded_file = st.file_uploader("📂 Tải lên file Excel dữ liệu thô", type=["xlsx", "xls"])

if uploaded_file is not None:
    st.success(f"✅ Đã tải lên thành công file: **{uploaded_file.name}**")
    
    @st.cache_data
    def load_data(file):
        df = pd.read_excel(file)
        date_cols = ['Ngày, tháng, năm ban hành (mm/dd/yyyy)', 'NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)', 'Thời hạn hoàn thành (mm/dd/yyyy)']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        return df

    df_raw = load_data(uploaded_file)
    st.write("Xem trước 5 dòng dữ liệu đầu tiên:")
    st.dataframe(df_raw.head())

    # SỬA ĐỔI: TẠO 2 CỘT CHO 2 NÚT BẤM
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Tạo 7 Báo cáo (Tổng hợp)"):
            with st.spinner("⏳ Đang xử lý và tạo 7 báo cáo..."):
                df = df_raw.copy()
                dates = {'year_start_date': pd.to_datetime(f'{input_year}-01-01'), 'quarter_start_date': pd.to_datetime(f'{input_year}-{(input_quarter-1)*3 + 1}-01'), 'quarter_end_date': pd.to_datetime(f'{input_year}-{(input_quarter-1)*3 + 1}-01') + pd.offsets.QuarterEnd(0)}
                for col in ['Đơn vị thực hiện KPCS trong quý', 'SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)', 'ĐVKD, AMC, Hội sở (Nhập ĐVKD hoặc Hội sở hoặc AMC)']:
                    if col in df.columns: df[col] = df[col].astype(str).str.strip().replace('nan', '')
                df['Nhom_Don_Vi'] = np.where(df['ĐVKD, AMC, Hội sở (Nhập ĐVKD hoặc Hội sở hoặc AMC)'] == 'Hội sở', 'Hội sở', 'ĐVKD, AMC')
                df_hoiso = df[df['Nhom_Don_Vi'] == 'Hội sở'].copy()
                df_dvdk_amc = df[df['Nhom_Don_Vi'] == 'ĐVKD, AMC'].copy()
                PARENT_COL = 'SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)'
                CHILD_COL = 'Đơn vị thực hiện KPCS trong quý'

                df1 = create_summary_table(df, 'Nhom_Don_Vi', dates)
                df2 = create_summary_table(df_hoiso, PARENT_COL, dates)
                df3 = create_top_n_table(df_hoiso, 5, dates)
                df4 = create_hierarchical_table_7_reports(df_hoiso, PARENT_COL, CHILD_COL, dates)
                df5 = create_summary_table(df_dvdk_amc, PARENT_COL, dates)
                df6 = create_top_n_table(df_dvdk_amc, 10, dates)
                df7 = create_hierarchical_table_7_reports(df_dvdk_amc, PARENT_COL, CHILD_COL, dates)

                output_stream = BytesIO()
                with pd.ExcelWriter(output_stream, engine='xlsxwriter') as writer:
                    workbook = writer.book
                    border_format = workbook.add_format({'border': 1, 'valign': 'vcenter'})
                    def write_to_sheet(df_to_write, sheet_name, index=True):
                        df_to_write.to_excel(writer, sheet_name=sheet_name, index=index)
                        worksheet = writer.sheets[sheet_name]
                        num_rows, num_cols = df_to_write.shape
                        worksheet.conditional_format(0, 0, num_rows, num_cols + (1 if index else 0) - 1, {'type': 'no_blanks', 'format': border_format})
                        for idx, col in enumerate(df_to_write.columns):
                            series = df_to_write[col]
                            max_len = max((series.astype(str).map(len).max(), len(str(series.name)))) + 2
                            worksheet.set_column(idx + (1 if index else 0), idx + (1 if index else 0), max_len)
                        if index:
                            max_len_idx = max(df_to_write.index.astype(str).map(len).max(), len(str(df_to_write.index.name))) + 2
                            worksheet.set_column(0, 0, max_len_idx)
                    write_to_sheet(df1, "1_TH_ToanHang", index=True)
                    write_to_sheet(df2, "2_TH_HoiSo", index=True)
                    write_to_sheet(df3, "3_Top5_HoiSo", index=True)
                    write_to_sheet(df4, "4_PhanCap_HoiSo", index=False)
                    write_to_sheet(df5, "5_TH_DVDK_KhuVuc", index=True)
                    write_to_sheet(df6, "6_Top10_DVDK", index=True)
                    write_to_sheet(df7, "7_ChiTiet_DVDK", index=False)
                excel_data = output_stream.getvalue()
            st.success("🎉 Đã tạo xong file Excel Tổng hợp!")
            st.download_button(label="📥 Tải xuống File Excel Tổng hợp", data=excel_data, file_name=f"Tong_hop_Bao_cao_KPCS_Q{input_quarter}_{input_year}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with col2:
        if st.button("📊 Tạo Báo cáo KQ Kiểm toán quý"):
            with st.spinner("⏳ Đang xử lý và tạo báo cáo KQKT..."):
                df = df_raw.copy()
                # Chạy hàm tạo báo cáo KQKT
                kqkt_df = generate_kqkt_report(df, year=input_year, quarter=input_quarter)
                
                output_stream_kqkt = BytesIO()
                with pd.ExcelWriter(output_stream_kqkt, engine='xlsxwriter') as writer:
                    workbook = writer.book
                    border_format = workbook.add_format({'border': 1, 'valign': 'vcenter'})
                    # Định dạng tiêu đề chính
                    header_format = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter'})
                    # Viết tiêu đề
                    worksheet = writer.book.add_worksheet("KQ_KiemToan_Quy")
                    writer.sheets["KQ_KiemToan_Quy"] = worksheet
                    worksheet.merge_range('A1:J1', 'KẾT QUẢ KIỂM TOÁN TRONG QUÝ', header_format)
                    
                    # Ghi DataFrame xuống, bắt đầu từ dòng 3 (để có khoảng trống)
                    kqkt_df.to_excel(writer, sheet_name="KQ_KiemToan_Quy", startrow=2, index=False)
                    # Thêm kẻ khung và tự động điều chỉnh độ rộng
                    worksheet = writer.sheets["KQ_KiemToan_Quy"]
                    num_rows, num_cols = kqkt_df.shape
                    worksheet.conditional_format(2, 0, 2 + num_rows, num_cols - 1, {'type': 'no_blanks', 'format': border_format})
                    for idx, col in enumerate(kqkt_df.columns):
                        series = kqkt_df[col]
                        max_len = max((series.astype(str).map(len).max(), len(str(series.name)))) + 2
                        worksheet.set_column(idx, idx, max_len)

                excel_data_kqkt = output_stream_kqkt.getvalue()
            st.success("🎉 Đã tạo xong file Excel KQKT!")
            st.download_button(label="📥 Tải xuống File KQKT Quý", data=excel_data_kqkt, file_name=f"KQ_KiemToan_Quy_{input_quarter}_{input_year}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("💡 Vui lòng tải lên file Excel chứa dữ liệu thô để bắt đầu.")
