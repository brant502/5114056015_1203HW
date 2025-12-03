import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import crawler  # 匯入我們寫好的 crawler.py

# 設定網頁標題與排版
st.set_page_config(page_title="台灣即時氣溫地圖", layout="wide")

DB_NAME = "weather.db"

def load_data_from_db():
    """從資料庫讀取資料轉成 DataFrame"""
    try:
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql("SELECT * FROM temp_data", conn)
        conn.close()
        
        # === 關鍵修正 1: 資料清洗 ===
        # 氣象署的異常值通常是 -99 或 -999，我們只保留合理的氣溫 (例如 > -50 度)
        if not df.empty:
            df = df[df['temperature'] > -50]
            
        return df
    except Exception:
        return pd.DataFrame()

# ================= 網頁介面開始 =================

st.title("🇹🇼 台灣全島即時溫度觀測網")


# --- 側邊欄：控制區 ---
with st.sidebar:
    st.header("控制面板")
    
    # 更新資料按鈕
    if st.button("🔄 立即更新氣象資料"):
        with st.spinner("正在連線至中央氣象署抓取資料..."):
            try:
                conn = crawler.init_db()
                data = crawler.fetch_data()
                crawler.save_to_db(conn, data)
                conn.close()
                st.success("資料更新完成！")
            except Exception as e:
                st.error(f"更新失敗: {e}")
        st.rerun()

    st.write("---")
    
    df = load_data_from_db()
    
    if not df.empty:
        cities = ["全台灣"] + list(df['city'].unique())
        selected_city = st.selectbox("選擇縣市", cities)
    else:
        st.warning("資料庫目前沒有資料，請點選上方按鈕更新。")
        selected_city = "全台灣"

# --- 主畫面：地圖與數據 ---

if not df.empty:
    if selected_city != "全台灣":
        display_df = df[df['city'] == selected_city]
        zoom_level = 9
        center_coords = None
    else:
        display_df = df
        zoom_level = 6.3
        center_coords = {"lat": 23.7, "lon": 120.95}

    # 1. 關鍵指標 (KPI)
    st.subheader("📊 即時觀測數據")
    col1, col2, col3 = st.columns(3)
    
    avg_temp = display_df['temperature'].mean()
    # 避免空資料報錯
    if not display_df.empty:
        max_row = display_df.loc[display_df['temperature'].idxmax()]
        min_row = display_df.loc[display_df['temperature'].idxmin()]
        col1.metric("平均氣溫", f"{avg_temp:.1f} °C")
        col2.metric("最高溫", f"{max_row['temperature']} °C", f"{max_row['city']} {max_row['name']}")
        col3.metric("最低溫", f"{min_row['temperature']} °C", f"{min_row['city']} {min_row['name']}")

    st.divider()

    # 2. 溫度地圖
    st.subheader(f"📍 {selected_city} 溫度分布圖")
    
    # === 關鍵修正 2: 移除 size="temperature" 並改用 scatter_map ===
    # 舊版 scatter_mapbox 有 deprecation warning，新版建議用 scatter_map
    # size 參數移除，避免負溫或 0 度造成崩潰
    try:
        fig = px.scatter_mapbox(
            display_df,
            lat="lat",
            lon="lon",
            color="temperature",
            # size="temperature",  <-- 這一行移除了，這是造成錯誤的主因
            size_max=15,          # 設定點的最大尺寸限制
            color_continuous_scale="RdYlBu_r",
            range_color=[10, 35],
            hover_name="name",
            hover_data={"city": True, "town": True, "temperature": True, "obs_time": True, "lat": False, "lon": False},
            zoom=zoom_level,
            center=center_coords,
            mapbox_style="carto-positron",
            height=600
        )
        # 為了讓點點不要太小，統一設定一個固定大小
        fig.update_traces(marker={'size': 12})
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"地圖繪製失敗: {e}")

    # 3. 詳細資料表
    with st.expander("查看詳細資料表"):
        st.dataframe(
            display_df[['obs_time', 'city', 'town', 'name', 'temperature']]
            .sort_values(by='temperature', ascending=False),
            use_container_width=True
        )

else:
    st.info("👋 歡迎！這是第一次執行，請點擊左側 sidebar 的 **「立即更新氣象資料」** 按鈕來抓取數據。")