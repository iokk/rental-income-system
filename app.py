import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
import time
from io import BytesIO

# ====== 页面配置 ======
st.set_page_config(
    page_title="🏢 小韩租赁收入智能分析系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

FUN_TIPS = [
    "熬大夜，上大分！",
    "让数据说话，我们倾听！",
    "精准计算，智慧决策！",
    "数据不会说谎，但需要我们正确解读！",
    "每一分租金都值得精确计算！",
    "租赁分析的艺术在于细节！"
]

class RentalIncomeCalculator:
    def __init__(self):
        self.month_days = {1:31,2:28,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}
        self.detailed_logs = []

    def is_leap_year(self, year):
        return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

    def get_month_days(self, year, month):
        if month == 2 and self.is_leap_year(year):
            return 29
        return self.month_days[month]

    def get_fun_tip(self):
        return np.random.choice(FUN_TIPS)

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.detailed_logs.append(f"[{timestamp}] [{level}] {message}")

    def convert_date(self, date_val):
        if pd.isna(date_val) or str(date_val).strip() in ['', '-', '/', 'nan', 'None', '—', '——', '//']:
            return None

        if isinstance(date_val, (int, float)):
            try:
                base_date = datetime(1899, 12, 30)  # Excel 1900 系统
                return (base_date + timedelta(days=float(date_val))).strftime('%Y-%m-%d')
            except Exception:
                return None

        date_str = str(date_val).strip()

        chinese_patterns = [
            (r'(\d{4})年(\d{1,2})月(\d{1,2})日?', '%Y年%m月%d日'),
            (r'(\d{4})年(\d{1,2})月', '%Y年%m月'),
            (r'(\d{4})年', '%Y年')
        ]
        for pattern, fmt in chinese_patterns:
            match = re.match(pattern, date_str)
            if match:
                try:
                    if '日' in fmt:
                        year, month, day = match.groups()
                        return f"{year}-{int(month):02d}-{int(day):02d}"
                    elif '月' in fmt:
                        year, month = match.groups()
                        return f"{year}-{int(month):02d}-01"
                    else:
                        year = match.group(1)
                        return f"{year}-01-01"
                except Exception:
                    continue

        formats = [
            '%Y/%m/%d', '%Y.%m.%d', '%Y-%m-%d',
            '%Y/%m', '%Y.%m', '%Y-%m',
            '%Y%m%d', '%Y-%m-%d %H:%M:%S'
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        return None

    def safe_float_conversion(self, value):
        if pd.isna(value) or str(value).strip() in ['', '-', '/']:
            return 0.0
        try:
            value_str = str(value).strip()
            value_str = re.sub(r'[元㎡]', '', value_str)
            return float(value_str)
        except Exception:
            return 0.0

    def calculate_monthly_rent(self, rent_price, area, year, month):
        return rent_price * area / 10000

    def get_effective_rent_price(self, row, target_date):
        try:
            base_price = self.safe_float_conversion(row.get('租金（㎡/元）', 0))
            if base_price == 0:
                return 0
            increases = []
            inc1_time = self.convert_date(row.get('租金递增时间', ''))
            inc1_price = self.safe_float_conversion(row.get('递增后单价', 0))
            if inc1_time and inc1_price > 0: increases.append((inc1_time, inc1_price))
            inc2_time = self.convert_date(row.get('二次递增时间', ''))
            inc2_price = self.safe_float_conversion(row.get('二次递增租金', 0))
            if inc2_time and inc2_price > 0: increases.append((inc2_time, inc2_price))
            inc3_time = self.convert_date(row.get('三次递增时间', ''))
            inc3_price = self.safe_float_conversion(row.get('三次递增租金', 0))
            if inc3_time and inc3_price > 0: increases.append((inc3_time, inc3_price))
            increases.sort(key=lambda x: x[0])
            current_price = base_price
            for inc_time, inc_price in increases:
                if inc_time and inc_time <= target_date:
                    current_price = inc_price
            return current_price
        except Exception as e:
            self.log(f"租金单价计算错误: {e}", "ERROR")
            return 0

    def calculate_contract_rent(self, row, start_date, end_date, area):
        try:
            monthly_rents = {}
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            total_2025 = 0.0
            for month in range(1, 11):
                year = 2025
                month_start = datetime(year, month, 1)
                month_end = datetime(year, month, self.get_month_days(year, month))
                if start_dt <= month_end and end_dt >= month_start:
                    target_date = f"{year}-{month:02d}-01"
                    rent_price = self.get_effective_rent_price(row, target_date)
                    monthly_rent = self.calculate_monthly_rent(rent_price, area, year, month)
                    monthly_rents[f"{year}-{month:02d}"] = monthly_rent
                    total_2025 += monthly_rent
                else:
                    monthly_rents[f"{year}-{month:02d}"] = 0.0

            for month in range(1, 13):
                year = 2026
                month_start = datetime(year, month, 1)
                month_end = datetime(year, month, self.get_month_days(year, month))
                if start_dt <= month_end and end_dt >= month_start:
                    target_date = f"{year}-{month:02d}-01"
                    rent_price = self.get_effective_rent_price(row, target_date)
                    monthly_rent = self.calculate_monthly_rent(rent_price, area, year, month)
                    monthly_rents[f"{year}-{month:02d}"] = monthly_rent
                else:
                    monthly_rents[f"{year}-{month:02d}"] = 0.0

            return total_2025, monthly_rents
        except Exception as e:
            self.log(f"合同租金计算错误: {e}", "ERROR")
            return 0.0, {}

    def process_data(self, df):
        self.detailed_logs = []
        results = []
        errors = []
        start_time = time.time()
        self.log("开始处理租赁数据")
        self.log(f"共 {len(df)} 条记录需要处理")

        required_fields = ['计租面积（㎡）', '租金（㎡/元）', '合同起租时间', '合同到期时间']
        missing_fields = [f for f in required_fields if f not in df.columns]
        if missing_fields:
            errors.append(f"缺少必填字段: {', '.join(missing_fields)}")
            self.log(errors[-1], "ERROR")
            return pd.DataFrame(), errors

        for idx, row in df.iterrows():
            try:
                if (idx + 1) % 50 == 0:
                    self.log(f"正在处理第 {idx+1}/{len(df)} 条记录")

                missing_values = []
                for field in required_fields:
                    v = row.get(field)
                    if pd.isna(v) or str(v).strip() in ['', '-']:
                        missing_values.append(field)
                if missing_values:
                    msg = f"行 {idx+1}: 必填字段为空 ({', '.join(missing_values)})"
                    errors.append(msg); self.log(msg, "WARNING"); continue

                start_date = self.convert_date(row['合同起租时间'])
                end_date = self.convert_date(row['合同到期时间'])
                if not start_date or not end_date:
                    msg = f"行 {idx+1}: 日期格式错误 (起租: {row['合同起租时间']}, 到期: {row['合同到期时间']})"
                    errors.append(msg); self.log(msg, "WARNING"); continue

                area = self.safe_float_conversion(row['计租面积（㎡）'])
                if area <= 0:
                    msg = f"行 {idx+1}: 计租面积无效 ({row['计租面积（㎡）']})"
                    errors.append(msg); self.log(msg, "WARNING"); continue

                total_2025, monthly_rents = self.calculate_contract_rent(row, start_date, end_date, area)

                result = {
                    '客户名称': row.get('企业名称', '未知客户'),
                    '租赁起租日': start_date,
                    '租赁截止日': end_date,
                    '在租面积(㎡)': area,
                    '初始租金(元/㎡)': self.safe_float_conversion(row['租金（㎡/元）']),
                    '2025年租金之和': total_2025
                }
                result.update(monthly_rents)
                results.append(result)
                self.log(f"行 {idx+1} 处理成功: {row.get('企业名称', '未知客户')}")
            except Exception as e:
                msg = f"行 {idx+1} 处理错误: {str(e)}"
                errors.append(msg); self.log(msg, "ERROR")

        if results:
            result_df = pd.DataFrame(results)
            amount_columns = [c for c in result_df.columns if '租金' in c or re.match(r'^202[56]-\d{2}$', c)]
            for col in amount_columns:
                if col in result_df.columns:
                    result_df[col] = result_df[col].apply(lambda x: f"{float(x):.6f}" if str(x).strip() != '' else "0.000000")
            processing_time = time.time() - start_time
            self.log(f"数据处理完成! 共处理 {len(df)} 条记录，成功计算 {len(result_df)} 条")
            self.log(f"处理耗时: {processing_time:.2f}秒")
            return result_df, errors
        else:
            self.log("没有成功计算的数据记录", "WARNING")
            return pd.DataFrame(), errors

def main():
    st.title("🏢 租赁收入智能分析系统")
    st.markdown("上传租赁数据文件，系统将自动计算租金收入并生成统计报表")

    calculator = RentalIncomeCalculator()
    st.info(f"💡 **小贴士**: {calculator.get_fun_tip()}")

    uploaded_file = st.file_uploader("上传数据文件 (CSV/Excel)", type=["csv", "xlsx", "xls"], key="file_uploader")

    if st.button("🔄 重新上传文件"):
        st.experimental_rerun()

    if uploaded_file is not None:
        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("📤 读取文件中...")
        progress_bar.progress(10)

        try:
            if uploaded_file.name.lower().endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            if df.empty:
                st.error("文件读取失败，请检查文件格式和内容")
                return

            with st.expander("🔍 查看原始数据预览", expanded=False):
                st.write(f"数据形状: {df.shape}")
                st.write("列名:", list(df.columns))
                st.dataframe(df.head(3))
        except Exception as e:
            st.error(f"文件读取失败: {str(e)}")
            return

        status_text.text("🔧 数据读取完成，开始处理...")
        progress_bar.progress(30)

        result_df, errors = calculator.process_data(df)

        status_text.text("✅ 数据处理完成!")
        progress_bar.progress(100)
        time.sleep(0.3)
        progress_bar.empty(); status_text.empty()

        st.success(f"数据处理完成! 共处理 {len(df)} 条记录，成功计算 {len(result_df) if result_df is not None else 0} 条")

        if errors:
            with st.expander("⚠️ 处理过程中发现错误", expanded=True):
                for error in errors:
                    st.error(error)
        else:
            st.info("✅ 未发现数据处理错误")

        with st.expander("📝 查看详细处理日志", expanded=False):
            for log in calculator.detailed_logs:
                if "ERROR" in log: st.error(log)
                elif "WARNING" in log: st.warning(log)
                else: st.info(log)

        if result_df is not None and not result_df.empty:
            st.subheader("📊 租赁收入统计结果")

            display_columns = ['客户名称', '租赁起租日', '租赁截止日', '在租面积(㎡)', '初始租金(元/㎡)', '2025年租金之和']
            monthly_2025_cols = [f'2025-{m:02d}' for m in range(1, 11)]
            display_columns.extend(monthly_2025_cols)
            monthly_2026_cols = [f'2026-{m:02d}' for m in range(1, 13)]
            display_columns.extend(monthly_2026_cols)

            available_cols = [c for c in display_columns if c in result_df.columns]
            display_df = result_df[available_cols]
            st.dataframe(display_df)

            st.subheader("💾 导出结果")
            col1, col2 = st.columns(2)

            with col1:
                csv = display_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="下载结果 (CSV)",
                    data=csv,
                    file_name='租赁收入统计.csv',
                    mime='text/csv'
                )
            with col2:
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    display_df.to_excel(writer, index=False, sheet_name='租赁收入统计')
                excel_data = output.getvalue()
                st.download_button(
                    label="下载结果 (Excel)",
                    data=excel_data,
                    file_name='租赁收入统计.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

            st.info("💡 点击下载按钮后，浏览器会提示您选择保存位置")

            st.subheader("📈 统计摘要")
            col1, col2, col3 = st.columns(3)

            total_2025 = 0.0
            if '2025年租金之和' in result_df.columns:
                total_2025 = pd.to_numeric(result_df['2025年租金之和'], errors='coerce').fillna(0.0).astype(float).sum()

            total_2026 = 0.0
            existing_2026_cols = [c for c in monthly_2026_cols if c in result_df.columns]
            if existing_2026_cols:
                total_2026 = pd.to_numeric(result_df[existing_2026_cols].stack(), errors='coerce').fillna(0.0).astype(float).sum()

            col1.metric("成功计算记录数", len(result_df))
            col2.metric("2025年总租金(万元)", f"{total_2025:.6f}")
            col3.metric("2026年预估总租金(万元)", f"{total_2026:.6f}")

            st.subheader("📅 2026年月度租金趋势")
            if existing_2026_cols:
                monthly_2026_data = pd.to_numeric(result_df[existing_2026_cols].astype(str).replace('', '0'), errors='coerce').fillna(0.0).astype(float).sum()
                monthly_2026_data.index = [f'{i+1}月' for i in range(len(existing_2026_cols))]
                st.bar_chart(monthly_2026_data)

            st.subheader("🏢 客户租金排名（2025年）")
            if '客户名称' in result_df.columns and '2025年租金之和' in result_df.columns:
                top_clients = (result_df
                               .assign(v=pd.to_numeric(result_df['2025年租金之和'], errors='coerce').fillna(0.0))
                               .groupby('客户名称')['v'].sum()
                               .sort_values(ascending=False).head(10))
                st.bar_chart(top_clients)

            st.subheader("⚠️ 常见错误提示")
            st.warning("1. 合同起租日在当月1日之后：系统只计算合同有效月份，不会重复计算")
            st.warning("2. 合同截止日在当月最后一日之前：系统会计算整个月租金")
            st.warning("3. 递增时间格式错误：请确保使用标准日期格式")
            st.warning("4. 面积或租金为0：系统会自动跳过这些记录")
        else:
            st.warning("没有成功计算的数据记录，请检查数据格式和内容")

if __name__ == "__main__":
    main()
