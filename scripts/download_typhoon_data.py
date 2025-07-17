import csv
import io
import requests
import os
import sys
# 移除了對 flask, jsonify, request 的導入，因為此腳本不需要它們

def main():
    # 從環境變數獲取路徑，這些變數將由 GitHub Actions 設定
    csv_path = os.environ.get('CSV_PATH')
    kml_path = os.environ.get('KML_PATH')

    print(f'Reading CSV from: {csv_path}')
    try:
        # 以 UTF-8-SIG 編碼讀取 CSV 內容，處理可能的 BOM
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            csv_content = f.read()
    except FileNotFoundError:
        print(f'Error: CSV file not found at {csv_path}')
        sys.exit(1) # 如果 CSV 檔案不存在，則退出

    # 嘗試使用 utf-8-sig 解碼，如果失敗則嘗試 big5
    try:
        csv_file = io.StringIO(csv_content)
        reader = csv.reader(csv_file)
        header = next(reader) # 讀取標頭行
    except Exception:
        try:
            # 如果 utf-8-sig 失敗，嘗試用 latin-1 讀取原始位元組，再用 big5 解碼
            csv_file = io.StringIO(csv_content.encode('latin-1').decode('big5'))
            reader = csv.reader(csv_file)
            header = next(reader)
        except Exception as e_big5:
            print(f'CSV parsing failed for both UTF-8 and Big5. Error: {e_big5}')
            sys.exit(1) # 如果 CSV 解析失敗，則退出

    data_link_index = -1
    description_index = -1

    try:
        # 找到 '資料連結' 和 '說明' 欄位的索引
        data_link_index = header.index('資料連結')
        description_index = header.index('說明')
    except ValueError:
        print('CSV header missing required columns (資料連結 or 說明).')
        sys.exit(1) # 如果標頭欄位缺失，則退出

    kml_data_url = None
    # 遍歷 CSV 內容，尋找包含颱風路徑的連結
    for row in reader:
        if len(row) > max(data_link_index, description_index):
            description = row[description_index]
            # 關鍵字搜尋更寬鬆，以防描述文字變化
            if any(keyword in description for keyword in ['颱風路徑', '熱帶氣旋', '預測路徑', 'Typhoon Track', 'Typhoon_KML']):
                kml_data_url = row[data_link_index]
                break

    if kml_data_url:
        print(f'Found KML URL: {kml_data_url}')
        try:
            # 下載 KML，並禁用 SSL 憑證驗證 (verify=False)，因為它可能指向 mas.nstc.gov.tw
            kml_response = requests.get(kml_data_url, timeout=30, verify=False)
            kml_response.raise_for_status() # 檢查 HTTP 錯誤
            # 將 KML 內容寫入檔案
            with open(kml_path, 'w', encoding='utf-8') as f:
                f.write(kml_response.text)
            print(f'Downloaded KML to {kml_path}')
        except Exception as e:
            print(f'Error downloading KML from {kml_data_url}: {e}')
            # 如果 KML 下載失敗，不退出，但會記錄錯誤
            # 確保即使 KML 下載失敗，也不會導致整個 Action 失敗
            # 這樣至少 CSV 會被更新，並且舊的 KML 會被移除
            if os.path.exists(kml_path):
                os.remove(kml_path) # 移除可能不完整的 KML 檔案
    else:
        print('No KML URL found in CSV.')
        # 如果沒有找到 KML 連結，確保 KML 檔案被移除，避免提交舊的或空的 KML
        if os.path.exists(kml_path):
            os.remove(kml_path)

if __name__ == '__main__':
    main()
