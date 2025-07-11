import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(layout="wide", page_title="Hệ thống Báo cáo KPCS Tự động")
st.title("📊 Hệ thống Báo cáo Tình hình KPCS Tự động")

# --- HÀM TÍNH TOÁN CỐT LÕI ---
# THAY ĐỔI: Hàm này giờ nhận thêm các biến thời gian làm tham số
def calculate_summary_metrics(dataframe, groupby_cols, year_start_date, quarter_start_date, quarter_end_date):
    if not isinstance(groupby_cols, list): raise TypeError("groupby_cols phải là một danh sách (list)")
    def agg(data_filtered, cols):
        if not cols: return len(data_filtered)
        else: return data_filtered.groupby(cols).size()

    ton_dau_nam = agg(dataframe[(dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] < year_start_date) & ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= year_start_date))], groupby_cols)
    phat_sinh_nam = agg(dataframe[(dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] >= year_start_date)], groupby_cols)
    khac_phuc_nam = agg(dataframe[(dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= year_start_date)], groupby_cols)
    ton_dau_quy = agg(dataframe[(dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] < quarter_start_date) & ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= quarter_start_date))], groupby_cols)
    phat_sinh_quy = agg(dataframe[(dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] >= quarter_start_date) & (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= quarter_end_date)], groupby_cols)
    khac_phuc_quy = agg(dataframe[(dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= quarter_start_date) & (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] <= quarter_end_date)], groupby_cols)
    cond_chua_ht_cuoi_quy = dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()
    chua_khac_phuc = agg(dataframe[cond_chua_ht_cuoi_quy], groupby_cols)
    cond_qua_han = dataframe['Thời hạn hoàn thành (mm/dd/yyyy)'] < quarter_end_date
    qua_han_khac_phuc = agg(dataframe[cond_chua_ht_cuoi_quy & cond_qua_han], groupby_cols)
    cond_qua_han_1_nam = dataframe['Thời hạn hoàn thành (mm/dd/yyyy)'] < (quarter_end_date - pd.DateOffset(years=1))
    qua_han_tren_1_nam = agg(dataframe[cond_chua_ht_cuoi_quy & cond_qua_han_1_nam], groupby_cols)
    
    if not groupby_cols:
        summary = pd.DataFrame([{'Tồn đầu năm': ton_dau_nam, 'Phát sinh năm': phat_sinh_nam, 'Khắc phục năm': khac_phuc_nam, 'Tồn đầu quý': ton_dau_quy, 'Phát sinh quý': phat_sinh_quy, 'Khắc phục quý': khac_phuc_quy, 'Kiến nghị chưa khắc phục': chua_khac_phuc, 'Quá hạn khắc phục': qua_han_khac_phuc, 'Trong đó quá hạn trên 1 năm': qua_han_tren_1_nam}])
    else:
        summary = pd.DataFrame({'Tồn đầu năm': ton_dau_nam, 'Phát sinh năm': phat_sinh_nam, 'Khắc phục năm': khac_phuc_nam, 'Tồn đầu quý': ton_dau_quy, 'Phát sinh quý': phat_sinh_quy, 'Khắc phục quý': khac_phuc_quy, 'Kiến nghị chưa khắc phục': chua_khac_phuc, 'Quá hạn khắc phục': qua_han_khac_phuc, 'Trong đó quá hạn trên 1 năm': qua_han_tren_1_nam}).fillna(0).astype(int)

    summary['Tồn cuối quý'] = summary['Tồn đầu quý'] + summary['Phát sinh quý'] - summary['Khắc phục quý']
    denominator = summary['Tồn đầu quý'] + summary['Phát sinh quý']
    summary['Tỷ lệ chưa KP đến cuối Quý'] = (summary['Tồn cuối quý'] / denominator).replace([np.inf, -np.inf], 0).fillna(0)
    return summary

# --- HÀM TẠO BÁO CÁO VÀ XUẤT EXCEL ---
def generate_all_reports_to_excel(df, year, quarter):
    """Gói toàn bộ logic tạo 7 báo cáo và trả về file Excel trong bộ nhớ."""
    
    # 1. Thiết lập thời gian dựa trên input của người dùng
    year_start_date = pd.to_datetime(f'{year}-01-01')
    year_end_date = pd.to_datetime(f'{year}-12-31')
    quarter_start_date = pd.to_datetime(f'{year}-{(quarter-1)*3 + 1}-01')
    quarter_end_date = quarter_start_date + pd.offsets.QuarterEnd(0)
    
    # 2. Chuẩn bị dữ liệu
    for col in ['Đơn vị thực hiện KPCS trong quý', 'SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)', 'ĐVKD, AMC, Hội sở (Nhập ĐVKD hoặc Hội sở hoặc AMC)']:
        if col in df.columns: df[col] = df[col].astype(str).str.strip()

    df['Nhom_Don_Vi'] = np.where(df['ĐVKD, AMC, Hội sở (Nhập ĐVKD hoặc Hội sở hoặc AMC)'] == 'Hội sở', 'Hội sở', 'ĐVKD, AMC')
    df_hoiso = df[df['Nhom_Don_Vi'] == 'Hội sở'].copy()
    df_dvdk_amc = df[df['Nhom_Don_Vi'] == 'ĐVKD, AMC'].copy()

    # Hàm phụ để ghi và định dạng kẻ ô
    def write_df(writer, df_to_write, sheet_name):
        df_to_write.to_excel(writer, sheet_name=sheet_name, index=False)
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        border_format = workbook.add_format({'border': 1})
        worksheet.conditional_format(0, 0, len(df_to_write), len(df_to_write.columns) - 1, 
                                     {'type': 'no_blanks', 'format': border_format})
        # Tự động điều chỉnh độ rộng cột
        for idx, col in enumerate(df_to_write):
            series = df_to_write[col]
            max_len = max((series.astype(str).map(len).max(), len(str(series.name)))) + 2
            worksheet.set_column(idx, idx, max_len)

    # 3. Tạo file Excel trong bộ nhớ
    output_stream = BytesIO()
    with pd.ExcelWriter(output_stream, engine='xlsxwriter') as writer:
        # Bảng 1: Tổng hợp toàn hàng
        df1 = calculate_summary_metrics(df, ['Nhom_Don_Vi'], year_start_date, quarter_start_date, quarter_end_date)
        write_df(writer, df1.reset_index(), "1_TH_ToanHang")
        
        # Bảng 2: Tổng hợp Hội sở
        df2 = calculate_summary_metrics(df_hoiso, ['SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)'], year_start_date, quarter_start_date, quarter_end_date)
        write_df(writer, df2.reset_index(), "2_TH_HoiSo")

        # Bảng 3: Top 5 Hội sở
        df3 = calculate_summary_metrics(df_hoiso, ['Đơn vị thực hiện KPCS trong quý'], year_start_date, quarter_start_date, quarter_end_date).sort_values(by='Quá hạn khắc phục', ascending=False).head(5)
        write_df(writer, df3.reset_index(), "3_Top5_HoiSo")
        
        # Bảng 4: Báo cáo phân cấp Hội sở
        PARENT_COL = 'SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)'
        CHILD_COL = 'Đơn vị thực hiện KPCS trong quý'
        summary_hs_detail = calculate_summary_metrics(df_hoiso, [CHILD_COL], year_start_date, quarter_start_date, quarter_end_date)
        # (Thêm logic sắp xếp phân cấp nếu cần hiển thị đẹp trong Excel)
        write_df(writer, summary_hs_detail.reset_index(), "4_PhanCap_HoiSo")

        # Bảng 5: Tổng hợp ĐVKD và AMC theo Khu vực
        df5 = calculate_summary_metrics(df_dvdk_amc, ['SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)'], year_start_date, quarter_start_date, quarter_end_date)
        write_df(writer, df5.reset_index(), "5_TH_DVDK_KhuVuc")

        # Bảng 6: Top 10 ĐVKD
        df6 = calculate_summary_metrics(df_dvdk_amc, ['Đơn vị thực hiện KPCS trong quý'], year_start_date, quarter_start_date, quarter_end_date).sort_values(by='Quá hạn khắc phục', ascending=False).head(10)
        write_df(writer, df6.reset_index(), "6_Top10_DVDK")
        
        # Bảng 7: Chi tiết ĐVKD
        df7 = calculate_summary_metrics(df_dvdk_amc, ['SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)', 'Đơn vị thực hiện KPCS trong quý'], year_start_date, quarter_start_date, quarter_end_date)
        write_df(writer, df7.reset_index(), "7_ChiTiet_DVDK")

    return output_stream.getvalue()


# --- GIAO DIỆN NGƯỜI DÙNG STREAMLIT ---
with st.sidebar:
    st.header("⚙️ Tùy chọn báo cáo")
    input_year = st.number_input("Chọn Năm báo cáo", min_value=2020, max_value=2030, value=2025)
    input_quarter = st.selectbox("Chọn Quý báo cáo", options=[1, 2, 3, 4], index=1)
    uploaded_file = st.file_uploader("📂 Tải lên file Excel dữ liệu thô", type=["xlsx", "xls"])

if uploaded_file is not None:
    st.success(f"✅ Đã tải lên thành công file: {uploaded_file.name}")
    df_raw = pd.read_excel(uploaded_file)
    st.dataframe(df_raw.head())

    if st.button("🚀 Tạo 7 Báo cáo & Xuất Excel"):
        with st.spinner("⏳ Đang xử lý dữ liệu và tạo các báo cáo..."):
            excel_data = generate_all_reports_to_excel(df_raw, input_year, input_quarter)
            
            st.success("🎉 Đã tạo xong file Excel chứa 7 báo cáo!")
            st.download_button(
                label="📥 Tải xuống File Excel Tổng hợp",
                data=excel_data,
                file_name=f"Tong_hop_Bao_cao_KPCS_Q{input_quarter}_{input_year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
else:
    st.info("Vui lòng tải lên file Excel dữ liệu thô để bắt đầu.")
