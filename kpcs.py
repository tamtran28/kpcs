import pandas as pd
import numpy as np
from google.colab import files

# Các tham số thời gian
current_year = 2025
current_quarter_number = 2
year_start_date = pd.to_datetime(f'{current_year}-01-01')
year_end_date = pd.to_datetime(f'{current_year}-12-31')
quarter_start_date = pd.to_datetime(f'{current_year}-{(current_quarter_number-1)*3 + 1}-01')
quarter_end_date = quarter_start_date + pd.offsets.QuarterEnd(0)

# Làm sạch và chuẩn bị dữ liệu
for col in ['Đơn vị thực hiện KPCS trong quý', 'SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)', 'ĐVKD, AMC, Hội sở (Nhập ĐVKD hoặc Hội sở hoặc AMC)']:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()

df['Nhom_Don_Vi'] = np.where(df['ĐVKD, AMC, Hội sở (Nhập ĐVKD hoặc Hội sở hoặc AMC)'] == 'Hội sở', 'Hội sở', 'ĐVKD, AMC')
df_hoiso = df[df['Nhom_Don_Vi'] == 'Hội sở'].copy()
df_dvdk_amc = df[df['Nhom_Don_Vi'] == 'ĐVKD, AMC'].copy()

# --- 2. HÀM TÍNH TOÁN CỐT LÕI (Không thay đổi) ---
def calculate_summary_metrics(dataframe, groupby_cols):
    """Hàm tính toán tất cả các chỉ số.
       Nếu groupby_cols rỗng, tính tổng cho cả dataframe.
    """
    if not isinstance(groupby_cols, list): raise TypeError("groupby_cols phải là một danh sách (list)")
    def agg(data_filtered, cols):
        if not cols: return len(data_filtered)
        else: return data_filtered.groupby(cols).size()

    ton_dau_nam = agg(dataframe[(dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] < year_start_date) & ((dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'].isnull()) | (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= year_start_date))], groupby_cols)
    phat_sinh_nam = agg(dataframe[(dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] >= year_start_date) & (dataframe['Ngày, tháng, năm ban hành (mm/dd/yyyy)'] <= year_end_date)], groupby_cols)
    khac_phuc_nam = agg(dataframe[(dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] >= year_start_date) & (dataframe['NGÀY HOÀN TẤT KPCS (mm/dd/yyyy)'] <= year_end_date)], groupby_cols)
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

# --- 3. CÁC HÀM TẠO BÁO CÁO ---
def create_summary_table(dataframe, groupby_col, title, excel_writer, sheet_name):
    """Hàm tạo báo cáo tổng hợp dạng phẳng."""
    print(f"--- Đang tạo: {title} ---")
    summary = calculate_summary_metrics(dataframe, [groupby_col])
    summary.loc['TỔNG CỘNG'] = summary.sum(numeric_only=True)
    # Re-calculate ratio for total row
    total_denom = summary.loc['TỔNG CỘNG', 'Tồn đầu quý'] + summary.loc['TỔNG CỘNG', 'Phát sinh quý']
    summary.loc['TỔNG CỘNG', 'Tỷ lệ chưa KP đến cuối Quý'] = (summary.loc['TỔNG CỘNG', 'Tồn cuối quý'] / total_denom) if total_denom != 0 else 0
    
    summary.to_excel(excel_writer, sheet_name=sheet_name)
    print(f"✅ Đã lưu '{title}' vào sheet '{sheet_name}'")

def create_top_n_table(dataframe, n, title, excel_writer, sheet_name):
    """Hàm tạo báo cáo Top N."""
    print(f"--- Đang tạo: {title} ---")
    CHILD_COL = 'Đơn vị thực hiện KPCS trong quý'
    summary = calculate_summary_metrics(dataframe, [CHILD_COL])
    top_n = summary.sort_values(by='Quá hạn khắc phục', ascending=False).head(n)
    top_n.loc['TỔNG CỘNG'] = top_n.sum()
    
    top_n.to_excel(excel_writer, sheet_name=sheet_name)
    print(f"✅ Đã lưu '{title}' vào sheet '{sheet_name}'")

def create_hoiso_hierarchical_table(excel_writer, sheet_name):
    """Hàm tạo báo cáo phân cấp cho Hội sở."""
    title = "Chi tiết KPCS từng Phòng Ban Hội sở (phân cấp)"
    print(f"--- Đang tạo: {title} ---")
    PARENT_COL = 'SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)'
    CHILD_COL = 'Đơn vị thực hiện KPCS trong quý'
    
    summary = calculate_summary_metrics(df_hoiso, [CHILD_COL])
    parent_mapping = df_hoiso[[CHILD_COL, PARENT_COL]].drop_duplicates().set_index(CHILD_COL)
    summary_with_parent = summary.join(parent_mapping)
    summary_with_parent['is_parent_row'] = (summary_with_parent.index == summary_with_parent[PARENT_COL])
    
    custom_order = [cat for cat in df_hoiso[PARENT_COL].unique() if cat in summary_with_parent[PARENT_COL].unique()]
    summary_with_parent[PARENT_COL] = pd.Categorical(summary_with_parent[PARENT_COL], categories=custom_order, ordered=True)
    
    sorted_summary = summary_with_parent.sort_values(by=[PARENT_COL, 'is_parent_row', CHILD_COL], ascending=[True, False, True])
    sorted_summary = sorted_summary.reset_index().rename(columns={CHILD_COL: 'Tên Đơn vị'})
    sorted_summary['Tên Đơn vị'] = sorted_summary.apply(lambda row: f"**{row['Tên Đơn vị']}**" if row['is_parent_row'] else f"    {row['Tên Đơn vị']}", axis=1)
    
    sorted_summary.to_excel(excel_writer, sheet_name=sheet_name, index=False)
    print(f"✅ Đã lưu '{title}' vào sheet '{sheet_name}'")

# (Các hàm tạo báo cáo khác có thể thêm vào đây)

# --- 4. THỰC THI VÀ XUẤT FILE EXCEL ---
output_filename = "Tong_hop_Bao_cao_KPCS.xlsx"
with pd.ExcelWriter(output_filename, engine='xlsxwriter') as writer:
    print("🚀 Bắt đầu tạo các báo cáo...")
    
    # Bảng 1: Tổng hợp toàn hàng (Hội sở vs ĐVKD)
    create_summary_table(df, 'Nhom_Don_Vi', "BC Tình hình KPCS toàn hàng", writer, "1_TH_ToanHang")
    
    # Bảng 2: Tổng hợp chi tiết các đơn vị Hội sở (dạng phẳng)
    create_summary_table(df_hoiso, 'SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)', "BC Tình hình KPCS các ĐV Hội sở", writer, "2_TH_HoiSo")

    # Bảng 3: Top 5 đơn vị Hội sở quá hạn
    create_top_n_table(df_hoiso, 5, "BC Top 5 ĐV Hội sở quá hạn", writer, "3_Top5_HoiSo")

    # Bảng 4: Báo cáo phân cấp Hội sở
    create_hoiso_hierarchical_table(writer, "4_PhanCap_HoiSo")

    # Bảng 5: Tổng hợp ĐVKD và AMC theo Khu vực
    create_summary_table(df_dvdk_amc, 'SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)', "BC ĐVKD & AMC theo Khu vực", writer, "5_TH_DVDK_KhuVuc")

    # Bảng 6: Top 10 ĐVKD quá hạn
    create_top_n_table(df_dvdk_amc, 10, "BC Top 10 ĐVKD quá hạn", writer, "6_Top10_DVDK")
    
    # Bảng 7: Báo cáo phân cấp ĐVKD và AMC (có thể thêm hàm riêng cho bảng này nếu cần)
    # Tạm thời dùng bảng tổng hợp phẳng cho Bảng 7
    print("--- Đang tạo: Chi tiết ĐVKD theo Khu vực (phẳng) ---")
    dvdk_amc_detail = calculate_summary_metrics(df_dvdk_amc, ['SUM (THEO Khối, KV, ĐVKD, Hội sở, Ban Dự Án QLTS)', 'Đơn vị thực hiện KPCS trong quý'])
    dvdk_amc_detail.to_excel(writer, sheet_name="7_ChiTiet_DVDK")
    print("✅ Đã lưu 'Chi tiết ĐVKD theo Khu vực (phẳng)' vào sheet '7_ChiTiet_DVDK'")

    print("\n🎉 Đã tạo xong file Excel!")

