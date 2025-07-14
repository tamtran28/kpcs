# import streamlit as st
# import pandas as pd
# import numpy as np
# from io import BytesIO # Dùng để xử lý file trong bộ nhớ

# # --- CẤU HÌNH TRANG WEB ---
# st.set_page_config(layout="wide", page_title="Hệ thống Báo cáo KPCS Tự động")
# st.title("📊 Hệ thống Báo cáo Tình hình KPCS Tự động")

# # ==============================================================================
# # PHẦN 1: CÁC HÀM LOGIC CỐT LÕI (Gần như không thay đổi từ code Colab)
# # ==============================================================================

# def calculate_summary_metrics(dataframe, groupby_cols, year_start_date, quarter_start_date, quarter_end_date):
#     """
#     Hàm tính toán các chỉ số với logic đã được sửa lại.
#     Hàm này giờ là "thuần khiết", không phụ thuộc vào biến toàn cục.
#     """
#     if not isinstance(groupby_cols, list):
#         raise TypeError("groupby_cols phải là một danh sách (list)")

#     def agg(data_filtered, cols):
#         if data_filtered.empty:
#             return 0 if not cols else pd.Series(dtype=int)
#         if not cols:
#             return len(data_filtered)
#         return data_filtered.groupby(cols).size()

#     # --- A. TÍNH TOÁN CÁC CHỈ SỐ DÒNG CHẢY (FLOW METRICS) ---
#     ton_dau_quy = agg(dataframe[
#         (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] < quarter_start_date) &
#         ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= quarter_start_date))
#     ], groupby_cols)

#     phat_sinh_quy = agg(dataframe[
#         (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] >= quarter_start_date) &
#         (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= quarter_end_date)
#     ], groupby_cols)

#     khac_phuc_quy = agg(dataframe[
#         (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= quarter_start_date) &
#         (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] <= quarter_end_date)
#     ], groupby_cols)
    
#     phat_sinh_nam = agg(dataframe[
#         (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] >= year_start_date) &
#         (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= quarter_end_date)
#     ], groupby_cols)

#     khac_phuc_nam = agg(dataframe[
#         (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= year_start_date) &
#         (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] <= quarter_end_date)
#     ], groupby_cols)
    
#     ton_dau_nam = agg(dataframe[
#         (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] < year_start_date) &
#         ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= year_start_date))
#     ], groupby_cols)


#     # --- B. TỔNG HỢP BẢNG VÀ TÍNH TOÁN CÁC CHỈ SỐ TRẠNG THÁI (STATE METRICS) ---
#     summary = pd.DataFrame({
#         'Tồn đầu quý': ton_dau_quy, 'Phát sinh quý': phat_sinh_quy, 'Khắc phục quý': khac_phuc_quy,
#         'Tồn đầu năm': ton_dau_nam, 'Phát sinh năm': phat_sinh_nam, 'Khắc phục năm': khac_phuc_nam,
#     }).fillna(0).astype(int)

#     # 1. Tính Tồn cuối quý (đây là phương pháp đúng)
#     summary['Tồn cuối quý'] = summary['Tồn đầu quý'] + summary['Phát sinh quý'] - summary['Khắc phục quý']
#     summary['Kiến nghị chưa khắc phục'] = summary['Tồn cuối quý']

#     # 2. Xác định chính xác các kiến nghị còn tồn tại cuối quý
#     df_actually_outstanding = dataframe[
#         (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= quarter_end_date) &
#         ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] > quarter_end_date))
#     ]

#     # 3. Tính toán các chỉ số Quá hạn DỰA TRÊN các kiến nghị thực sự còn tồn
#     qua_han_khac_phuc = agg(df_actually_outstanding[df_actually_outstanding['Thời hạn hoàn thành (mm/dd/yyyy)'] < quarter_end_date], groupby_cols)
#     qua_han_tren_1_nam = agg(df_actually_outstanding[df_actually_outstanding['Thời hạn hoàn thành (mm/dd/yyyy)'] < (quarter_end_date - pd.DateOffset(years=1))], groupby_cols)

#     summary['Quá hạn khắc phục'] = qua_han_khac_phuc
#     summary['Trong đó quá hạn trên 1 năm'] = qua_han_tren_1_nam
#     summary = summary.fillna(0).astype(int)

#     # 4. Tính tỷ lệ
#     denominator = summary['Tồn đầu quý'] + summary['Phát sinh quý']
#     summary['Tỷ lệ chưa KP đến cuối Quý'] = (summary['Tồn cuối quý'] / denominator).replace([np.inf, -np.inf], 0).fillna(0)
    
#     final_cols_order = [
#         'Tồn đầu năm', 'Phát sinh năm', 'Khắc phục năm', 'Tồn đầu quý', 'Phát sinh quý', 
#         'Khắc phục quý', 'Tồn cuối quý', 'Kiến nghị chưa khắc phục', 'Quá hạn khắc phục', 
#         'Trong đó quá hạn trên 1 năm', 'Tỷ lệ chưa KP đến cuối Quý'
#     ]
#     # Đảm bảo tất cả các cột đều tồn tại trước khi sắp xếp lại
#     summary = summary.reindex(columns=final_cols_order, fill_value=0)
#     return summary

# def create_summary_table(dataframe, groupby_col, dates, **kwargs):
#     summary = calculate_summary_metrics(dataframe, [groupby_col], **dates)
#     if not summary.empty:
#         total_row = pd.DataFrame(summary.sum(numeric_only=True)).T
#         total_row.index = ['TỔNG CỘNG']
#         total_denom = total_row.at['TỔNG CỘNG', 'Tồn đầu quý'] + total_row.at['TỔNG CỘNG', 'Phát sinh quý']
#         total_row['Tỷ lệ chưa KP đến cuối Quý'] = (total_row.at['TỔNG CỘNG', 'Tồn cuối quý'] / total_denom) if total_denom != 0 else 0
#         summary = pd.concat([summary, total_row])
#     return summary

# def create_top_n_table(dataframe, n, dates, **kwargs):
#     CHILD_COL = 'Đơn vị thực hiện KPCS trong quý'
#     summary = calculate_summary_metrics(dataframe, [CHILD_COL], **dates)
#     return summary.sort_values(by='Quá hạn khắc phục', ascending=False).head(n)

# def create_hierarchical_table(dataframe, parent_col, child_col, dates, **kwargs):
#     summary = calculate_summary_metrics(dataframe, [child_col], **dates)
#     if summary.empty: return pd.DataFrame()
#     parent_mapping = dataframe[[child_col, parent_col]].drop_duplicates().set_index(child_col)
#     summary_with_parent = summary.join(parent_mapping)
#     parent_summary = calculate_summary_metrics(dataframe, [parent_col], **dates)
#     final_report = []
#     for parent_name in dataframe[parent_col].unique():
#         if parent_name not in parent_summary.index: continue
#         parent_row = parent_summary.loc[[parent_name]].reset_index().rename(columns={parent_col: 'Tên Đơn vị'})
#         parent_row['Phân cấp'] = 'Cha'
#         final_report.append(parent_row)
#         children_df = summary_with_parent[summary_with_parent[parent_col] == parent_name].reset_index().rename(columns={child_col: 'Tên Đơn vị'})
#         children_df['Phân cấp'] = 'Con'
#         final_report.append(children_df)
#     if not final_report: return pd.DataFrame()
#     full_report_df = pd.concat(final_report, ignore_index=True)
#     cols = full_report_df.columns.tolist()
#     cols.insert(0, cols.pop(cols.index('Phân cấp')))
#     cols.insert(1, cols.pop(cols.index('Tên Đơn vị')))
#     return full_report_df[cols]

# # ==============================================================================
# # PHẦN 2: GIAO DIỆN VÀ LUỒNG THỰC THI CỦA STREAMLIT
# # ==============================================================================

# # --- Giao diện thanh bên (Sidebar) để người dùng nhập liệu ---
# with st.sidebar:
#     st.header("⚙️ Tùy chọn báo cáo")
#     input_year = st.number_input("Chọn Năm báo cáo", min_value=2020, max_value=2030, value=2024)
#     input_quarter = st.selectbox("Chọn Quý báo cáo", options=[1, 2, 3, 4], index=3)
#     uploaded_file = st.file_uploader("📂 Tải lên file Excel dữ liệu thô", type=["xlsx", "xls"])

# # --- Luồng chính của ứng dụng ---
# if uploaded_file is not None:
#     st.success(f"✅ Đã tải lên thành công file: **{uploaded_file.name}**")
    
#     @st.cache_data
#     def load_data(file):
#         df = pd.read_excel(file)
#         # Chuyển đổi kiểu dữ liệu cho các cột ngày tháng
#         date_cols = [
#             'Ngày, tháng, năm ban hành (mm/dd/yyyy)',
#             'NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)',
#             'Thời hạn hoàn thành (mm/dd/yyyy)'
#         ]
#         for col in date_cols:
#             df[col] = pd.to_datetime(df[col], errors='coerce')
#         return df

#     df = load_data(uploaded_file)
#     st.write("Xem trước 5 dòng dữ liệu đầu tiên:")
#     st.dataframe(df.head())

#     # Chỉ hiển thị nút bấm sau khi đã tải file lên
#     if st.button("🚀 Tạo Báo cáo & Xuất Excel"):
#         with st.spinner("⏳ Đang xử lý dữ liệu và tạo các báo cáo... Vui lòng chờ trong giây lát."):
#             # 1. Thiết lập thời gian tập trung từ input của người dùng
#             dates = {
#                 'year_start_date': pd.to_datetime(f'{input_year}-01-01'),
#                 'quarter_start_date': pd.to_datetime(f'{input_year}-{(input_quarter-1)*3 + 1}-01'),
#                 'quarter_end_date': pd.to_datetime(f'{input_year}-{(input_quarter-1)*3 + 1}-01') + pd.offsets.QuarterEnd(0)
#             }

#             # 2. Chuẩn bị và phân tách dữ liệu
#             for col in ['Đơn vị thực hiện KPCS trong quý', 'SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)', 'ĐVKD, AMC, Hội sở (Nhập ĐVKD hoặc Hội sở hoặc AMC)']:
#                 if col in df.columns:
#                     df[col] = df[col].astype(str).str.strip().replace('nan', '')

#             df['Nhom_Don_Vi'] = np.where(df['ĐVKD, AMC, Hội sở (Nhập ĐVKD hoặc Hội sở hoặc AMC)'] == 'Hội sở', 'Hội sở', 'ĐVKD, AMC')
#             df_hoiso = df[df['Nhom_Don_Vi'] == 'Hội sở'].copy()
#             df_dvdk_amc = df[df['Nhom_Don_Vi'] == 'ĐVKD, AMC'].copy()
#             PARENT_COL = 'SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)'
#             CHILD_COL = 'Đơn vị thực hiện KPCS trong quý'

#             # 3. Tạo file Excel trong BỘ NHỚ
#             output_stream = BytesIO()
#             with pd.ExcelWriter(output_stream, engine='xlsxwriter') as writer:
#                 # Bảng 1-7
#                 create_summary_table(df, 'Nhom_Don_Vi', dates).to_excel(writer, sheet_name="1_TH_ToanHang")
#                 create_summary_table(df_hoiso, PARENT_COL, dates).to_excel(writer, sheet_name="2_TH_HoiSo")
#                 create_top_n_table(df_hoiso, 5, dates).to_excel(writer, sheet_name="3_Top5_HoiSo")
#                 create_hierarchical_table(df_hoiso, PARENT_COL, CHILD_COL, dates).to_excel(writer, sheet_name="4_PhanCap_HoiSo", index=False)
#                 create_summary_table(df_dvdk_amc, PARENT_COL, dates).to_excel(writer, sheet_name="5_TH_DVDK_KhuVuc")
#                 create_top_n_table(df_dvdk_amc, 10, dates).to_excel(writer, sheet_name="6_Top10_DVDK")
#                 create_hierarchical_table(df_dvdk_amc, PARENT_COL, CHILD_COL, dates).to_excel(writer, sheet_name="7_ChiTiet_DVDK", index=False)
            
#             excel_data = output_stream.getvalue()

#         st.success("🎉 Đã tạo xong file Excel chứa 7 báo cáo!")
        
#         # 4. Cung cấp nút tải xuống
#         st.download_button(
#             label="📥 Tải xuống File Excel Tổng hợp",
#             data=excel_data,
#             file_name=f"Tong_hop_Bao_cao_KPCS_Q{input_quarter}_{input_year}.xlsx",
#             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#         )
# else:
#     st.info("Vui lòng tải lên file Excel chứa dữ liệu thô để bắt đầu.")

#1407
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(layout="wide", page_title="Hệ thống Báo cáo KPCS Tự động")
st.title("📊 Hệ thống Báo cáo Tình hình KPCS Tự động")

# ==============================================================================
# PHẦN 1: CÁC HÀM LOGIC CỐT LÕI (Không thay đổi)
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

    summary = pd.DataFrame({'Tồn đầu quý': ton_dau_quy, 'Phát sinh quý': phat_sinh_quy, 'Khắc phục quý': khac_phuc_quy, 'Tồn đầu năm': ton_dau_nam, 'Phát sinh năm': phat_sinh_nam, 'Khắc phục năm': khac_phuc_nam}).fillna(0).astype(int)
    summary['Tồn cuối quý'] = summary['Tồn đầu quý'] + summary['Phát sinh quý'] - summary['Khắc phục quý']
    summary['Kiến nghị chưa khắc phục'] = summary['Tồn cuối quý']

    df_actually_outstanding = dataframe[(dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= quarter_end_date) & ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] > quarter_end_date))]
    qua_han_khac_phuc = agg(df_actually_outstanding[df_actually_outstanding['Thời hạn hoàn thành (mm/dd/yyyy)'] < quarter_end_date], groupby_cols)
    qua_han_tren_1_nam = agg(df_actually_outstanding[df_actually_outstanding['Thời hạn hoàn thành (mm/dd/yyyy)'] < (quarter_end_date - pd.DateOffset(years=1))], groupby_cols)

    summary['Quá hạn khắc phục'] = qua_han_khac_phuc
    summary['Trong đó quá hạn trên 1 năm'] = qua_han_tren_1_nam
    summary = summary.fillna(0).astype(int)

    denominator = summary['Tồn đầu quý'] + summary['Phát sinh quý']
    summary['Tỷ lệ chưa KP đến cuối Quý'] = (summary['Tồn cuối quý'] / denominator).replace([np.inf, -np.inf], 0).fillna(0)
    
    final_cols_order = ['Tồn đầu năm', 'Phát sinh năm', 'Khắc phục năm', 'Tồn đầu quý', 'Phát sinh quý', 'Khắc phục quý', 'Tồn cuối quý', 'Kiến nghị chưa khắc phục', 'Quá hạn khắc phục', 'Trong đó quá hạn trên 1 năm', 'Tỷ lệ chưa KP đến cuối Quý']
    summary = summary.reindex(columns=final_cols_order, fill_value=0)
    return summary

# ==============================================================================
# PHẦN 2: CÁC HÀM TẠO BÁO CÁO (ĐÃ CẬP NHẬT THEO YÊU CẦU MỚI)
# ==============================================================================

def create_summary_table(dataframe, groupby_col, dates):
    """Bảng tóm tắt phẳng, luôn có dòng tổng cộng."""
    summary = calculate_summary_metrics(dataframe, [groupby_col], **dates)
    if not summary.empty:
        total_row = pd.DataFrame(summary.sum(numeric_only=True)).T
        total_row.index = ['TỔNG CỘNG']
        total_denom = total_row.at['TỔNG CỘNG', 'Tồn đầu quý'] + total_row.at['TỔNG CỘNG', 'Phát sinh quý']
        total_row['Tỷ lệ chưa KP đến cuối Quý'] = (total_row.at['TỔNG CỘNG', 'Tồn cuối quý'] / total_denom) if total_denom != 0 else 0
        summary = pd.concat([summary, total_row])
    return summary

def create_top_n_table(dataframe, n, dates):
    """SỬA ĐỔI: Bảng Top N, có dòng tổng cộng của toàn bộ nhóm."""
    CHILD_COL = 'Đơn vị thực hiện KPCS trong quý'
    full_summary = calculate_summary_metrics(dataframe, [CHILD_COL], **dates)
    
    top_n = full_summary.sort_values(by='Quá hạn khắc phục', ascending=False).head(n)
    
    total_row = pd.DataFrame(full_summary.sum(numeric_only=True)).T
    total_row.index = ['TỔNG CỘNG CỦA NHÓM']
    total_denom = total_row.at['TỔNG CỘNG CỦA NHÓM', 'Tồn đầu quý'] + total_row.at['TỔNG CỘNG CỦA NHÓM', 'Phát sinh quý']
    total_row['Tỷ lệ chưa KP đến cuối Quý'] = (total_row.at['TỔNG CỘNG CỦA NHÓM', 'Tồn cuối quý'] / total_denom) if total_denom != 0 else 0
    
    return pd.concat([top_n, total_row])

def create_hierarchical_table(dataframe, parent_col, child_col, dates):
    """SỬA ĐỔI: Bảng phân cấp, bỏ cột 'Phân cấp', dùng thụt lề và có dòng Grand Total."""
    summary = calculate_summary_metrics(dataframe, [child_col], **dates)
    if summary.empty: return pd.DataFrame()

    parent_mapping = dataframe[[child_col, parent_col]].drop_duplicates().set_index(child_col)
    summary_with_parent = summary.join(parent_mapping)
    parent_summary = calculate_summary_metrics(dataframe, [parent_col], **dates)
    
    final_report_rows = []
    unique_parents = dataframe[parent_col].dropna().unique()

    for parent_name in unique_parents:
        if parent_name not in parent_summary.index: continue
        
        # Thêm dòng cha (in đậm)
        parent_row = parent_summary.loc[[parent_name]].reset_index().rename(columns={parent_col: 'Tên Đơn vị'})
        parent_row['Tên Đơn vị'] = f"**{parent_name}**"
        final_report_rows.append(parent_row)
        
        # Thêm các dòng con (thụt lề)
        children_df = summary_with_parent[summary_with_parent[parent_col] == parent_name].reset_index().rename(columns={child_col: 'Tên Đơn vị'})
        children_df['Tên Đơn vị'] = "  •  " + children_df['Tên Đơn vị'].astype(str)
        final_report_rows.append(children_df)
    
    if not final_report_rows: return pd.DataFrame()
    
    full_report_df = pd.concat(final_report_rows, ignore_index=True)
    
    # Thêm dòng Grand Total
    grand_total = calculate_summary_metrics(dataframe, [], **dates)
    grand_total_row = pd.DataFrame(grand_total, index=['**TỔNG CỘNG TOÀN BỘ**']).reset_index().rename(columns={'index': 'Tên Đơn vị'})
    full_report_df = pd.concat([full_report_df, grand_total_row], ignore_index=True)

    # Đặt cột 'Tên Đơn vị' lên đầu tiên
    cols = ['Tên Đơn vị'] + [col for col in summary.columns if col != 'Tên Đơn vị']
    return full_report_df[cols]

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

    if st.button("🚀 Tạo Báo cáo & Xuất Excel"):
        with st.spinner("⏳ Đang xử lý dữ liệu và tạo các báo cáo... Vui lòng chờ trong giây lát."):
            df = df_raw.copy() 
            dates = {
                'year_start_date': pd.to_datetime(f'{input_year}-01-01'),
                'quarter_start_date': pd.to_datetime(f'{input_year}-{(input_quarter-1)*3 + 1}-01'),
                'quarter_end_date': pd.to_datetime(f'{input_year}-{(input_quarter-1)*3 + 1}-01') + pd.offsets.QuarterEnd(0)
            }

            for col in ['Đơn vị thực hiện KPCS trong quý', 'SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)', 'ĐVKD, AMC, Hội sở (Nhập ĐVKD hoặc Hội sở hoặc AMC)']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip().replace('nan', '')

            df['Nhom_Don_Vi'] = np.where(df['ĐVKD, AMC, Hội sở (Nhập ĐVKD hoặc Hội sở hoặc AMC)'] == 'Hội sở', 'Hội sở', 'ĐVKD, AMC')
            df_hoiso = df[df['Nhom_Don_Vi'] == 'Hội sở'].copy()
            df_dvdk_amc = df[df['Nhom_Don_Vi'] == 'ĐVKD, AMC'].copy()
            PARENT_COL = 'SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)'
            CHILD_COL = 'Đơn vị thực hiện KPCS trong quý'

            output_stream = BytesIO()
            with pd.ExcelWriter(output_stream, engine='xlsxwriter') as writer:
                # Bảng 1
                create_summary_table(df, 'Nhom_Don_Vi', dates).to_excel(writer, sheet_name="1_TH_ToanHang")
                # Bảng 2
                create_summary_table(df_hoiso, PARENT_COL, dates).to_excel(writer, sheet_name="2_TH_HoiSo")
                # Bảng 3
                create_top_n_table(df_hoiso, 5, dates).to_excel(writer, sheet_name="3_Top5_HoiSo")
                # Bảng 4
                create_hierarchical_table(df_hoiso, PARENT_COL, CHILD_COL, dates).to_excel(writer, sheet_name="4_PhanCap_HoiSo", index=False)
                # Bảng 5
                create_summary_table(df_dvdk_amc, PARENT_COL, dates).to_excel(writer, sheet_name="5_TH_DVDK_KhuVuc")
                # Bảng 6
                create_top_n_table(df_dvdk_amc, 10, dates).to_excel(writer, sheet_name="6_Top10_DVDK")
                # Bảng 7
                create_hierarchical_table(df_dvdk_amc, PARENT_COL, CHILD_COL, dates).to_excel(writer, sheet_name="7_ChiTiet_DVDK", index=False)
            
            excel_data = output_stream.getvalue()

        st.success("🎉 Đã tạo xong file Excel chứa 7 báo cáo!")
        
        st.download_button(
            label="📥 Tải xuống File Excel Tổng hợp",
            data=excel_data,
            file_name=f"Tong_hop_Bao_cao_KPCS_Q{input_quarter}_{input_year}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Vui lòng tải lên file Excel chứa dữ liệu thô để bắt đầu.")
