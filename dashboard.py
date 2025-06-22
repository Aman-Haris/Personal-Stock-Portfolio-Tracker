import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import numpy as np
from streamlit.components.v1 import html

# Marquee component
def marquee(content):
    return html(f"""
    <div style="
        width: 100%;
        padding: 10px 0;
        background-color: #f0f2f6;
        border-radius: 5px;
        overflow: hidden;
        white-space: nowrap;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    ">
        <marquee behavior="scroll" direction="left">
            {content}
        </marquee>
    </div>
    """, height=50)

# Card component
def metric_card(title, value, delta=None, delta_color="normal"):
    color_map = {
        "normal": "",
        "inverse": "color: white; background-color: #4CAF50;" if (isinstance(delta, str) and ('%' in delta) and (float(delta.strip('%')))>= 0) else "color: white; background-color: #F44336;"
    }
    
    delta_style = color_map.get(delta_color, "")
    
    return html(f"""
    <div style="
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        background-color: #f8f9fa;
        margin: 10px;
    ">
        <div style="font-size: 14px; color: #555;">{title}</div>
        <div style="font-size: 24px; font-weight: bold;">{value}</div>
        {f'<div style="font-size: 14px; {delta_style}">{delta}</div>' if delta else ''}
    </div>
    """)

# Set page config
st.set_page_config(
    page_title="Stock Portfolio Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Google Sheets API setup
def connect_to_google_sheets():
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    
    gc = gspread.authorize(credentials)
    return gc

# Load data from Google Sheets
@st.cache_data(ttl=600)
def load_data_from_gsheets():
    try:
        gc = connect_to_google_sheets()
        sh = gc.open("My Stock Portfolio")
        
        # Get worksheets
        open_pos_sheet = sh.worksheet("Open Positions")
        closed_pos_sheet = sh.worksheet("Closed Positions")
        
        # Get all records
        open_pos_data = open_pos_sheet.get_all_records()
        closed_pos_data = closed_pos_sheet.get_all_records()
        
        # Convert to DataFrames
        open_pos = pd.DataFrame(open_pos_data)
        closed_pos = pd.DataFrame(closed_pos_data)
        
        return open_pos, closed_pos
    
    except Exception as e:
        st.error(f"Error loading data from Google Sheets: {str(e)}")
        st.stop()

# Data preprocessing with enhanced type conversion
def preprocess_data(open_df, closed_df):
    # Convert date columns to datetime
    date_columns = ['Buying Date', 'Selling Date']
    
    for col in date_columns:
        if col in open_df.columns:
            open_df[col] = pd.to_datetime(open_df[col], format='mixed', dayfirst=True, errors='coerce')
        if col in closed_df.columns:
            closed_df[col] = pd.to_datetime(closed_df[col], format='mixed', dayfirst=True, errors='coerce')
    
    # Ensure numeric columns
    numeric_cols = ['Buying Price', 'No.of Shares bought', 'Investment Amount', 
                   'Current Share Price', 'Current Value', 'Profit/Loss', 'Growth(%)',
                   'Selling Price', 'Selling Value', 'Profit/Loss Booked', 'Investment Days',
                   'Possible Profit/Loss', "Today's Growth"]
    
    for col in numeric_cols:
        if col in open_df.columns:
            open_df[col] = pd.to_numeric(open_df[col], errors='coerce')
        if col in closed_df.columns:
            closed_df[col] = pd.to_numeric(closed_df[col], errors='coerce')
    
    # Handle serial numbers/IDs
    for df in [open_df, closed_df]:
        if 'S1.No' in df.columns:
            df['S1.No'] = pd.to_numeric(df['S1.No'], errors='coerce').fillna(0).astype(int)
        if 'S1 No' in df.columns:
            df['S1 No'] = pd.to_numeric(df['S1 No'], errors='coerce').fillna(0).astype(int)
    
    # Calculate investment days if not present or invalid
    if 'Investment Days' not in open_df.columns or open_df['Investment Days'].isnull().all():
        if 'Buying Date' in open_df.columns:
            open_df['Investment Days'] = (pd.to_datetime('today') - open_df['Buying Date']).dt.days
    
    if 'Investment Days' not in closed_df.columns or closed_df['Investment Days'].isnull().all():
        if 'Buying Date' in closed_df.columns and 'Selling Date' in closed_df.columns:
            closed_df['Investment Days'] = (closed_df['Selling Date'] - closed_df['Buying Date']).dt.days
    
    # Fill NaN values for visualization
    for col in ['Investment Days', 'Growth(%)', 'Possible Profit/Loss', "Today's Growth"]:
        if col in open_df.columns:
            open_df[col] = open_df[col].fillna(0)
        if col in closed_df.columns:
            closed_df[col] = closed_df[col].fillna(0)
    
    return open_df, closed_df

# Safe formatting function
def safe_format(value, format_str):
    if pd.isna(value):
        return ""
    try:
        if isinstance(value, (int, float)):
            return format_str.format(value)
        return str(value)
    except (ValueError, TypeError):
        return str(value)

# Make dataframe Arrow-compatible
def make_dataframe_arrow_compatible(df):
    df = df.copy()
    
    # Convert object columns to string
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].astype(str)
    
    # Convert numeric columns with NaN to float
    for col in df.select_dtypes(include=[np.number]).columns:
        if df[col].isna().any():
            df[col] = df[col].astype(float)
    
    return df

# Load and preprocess data
open_pos, closed_pos = load_data_from_gsheets()
open_pos, closed_pos = preprocess_data(open_pos, closed_pos)

# Calculate summary metrics
def calculate_metrics(open_df, closed_df):
    metrics = {}
    
    # Open positions metrics
    metrics['total_invested_open'] = open_df['Investment Amount'].sum()
    metrics['total_pl_open'] = open_df['Profit/Loss'].sum()
    metrics['total_growth_open'] = ((metrics['total_pl_open']) / 
                                  metrics['total_invested_open'] * 100 if metrics['total_invested_open'] != 0 else 0)
    metrics['total_days_open'] = open_df['Investment Days'].sum()
    
    # Closed positions metrics
    metrics['total_invested_closed'] = closed_df['Investment Amount'].sum()
    metrics['total_sold_closed'] = closed_df['Selling Value'].sum()
    metrics['total_pl_closed'] = closed_df['Profit/Loss Booked'].sum()
    metrics['total_growth_closed'] = ((metrics['total_pl_closed']) / 
                                   metrics['total_invested_closed'] * 100 if metrics['total_invested_closed'] != 0 else 0)
    metrics['total_possible_pl'] = closed_df['Possible Profit/Loss'].sum()
    metrics['total_days_closed'] = closed_df['Investment Days'].sum()
    
    # Combined metrics
    metrics['total_invested_all'] = metrics['total_invested_open'] + metrics['total_invested_closed']
    metrics['total_pl_all'] = metrics['total_pl_open'] + metrics['total_pl_closed']
    metrics['total_days_all'] = metrics['total_days_open'] + metrics['total_days_closed']
    
    return metrics

metrics = calculate_metrics(open_pos, closed_pos)

# Custom styling
def apply_custom_styles():
    st.markdown("""
    <style>
    .stMetric {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stMetric label {
        font-size: 14px !important;
        color: #555 !important;
    }
    .stMetric div {
        font-size: 20px !important;
        font-weight: bold !important;
    }
    .css-1v0mbdj {
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stDataFrame {
        border-radius: 10px;
    }
    .st-emotion-cache-1v0mbdj {
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

apply_custom_styles()

# Create tabs
tab1, tab2 = st.tabs(["📈 Open Positions", "📉 Closed Positions"])

with tab1:
    st.header("Open Positions Analysis")
    
    # Marquee with stock performance
    marquee_content = " | ".join(
        f"{row['Stock Name']}: {row.get('Today\'s Growth', 0)}%" 
        for _, row in open_pos.iterrows()
    )
    marquee(marquee_content)
    
    # Summary cards row 1
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Invested", f"₹{metrics['total_invested_open']:,.2f}")
    with col2:
        st.metric("Profit/Loss", f"₹{metrics['total_pl_open']:,.2f}", 
                 delta=f"{metrics['total_growth_open']:.2f}%")
    with col3:
        st.metric("Total Invested Days", f"{metrics['total_days_open']:,.0f}")
    with col4:
        avg_days = open_pos['Investment Days'].mean()
        st.metric("Avg Holding Days", f"{avg_days:.0f} days")
    
    # Top Gainers/Losers cards
    st.subheader("Performance Highlights")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Top Gainers**")
        top_gainers = open_pos.nlargest(3, 'Growth(%)')
        for _, row in top_gainers.iterrows():
            metric_card(
                title=row['Stock Name'],
                value=f"₹{row['Profit/Loss']:,.2f}",
                delta=f"{row['Growth(%)']:.2f}%",
                delta_color="inverse"
            )
    
    with col2:
        st.markdown("**Top Losers**")
        top_losers = open_pos.nsmallest(3, 'Growth(%)')
        for _, row in top_losers.iterrows():
            metric_card(
                title=row['Stock Name'],
                value=f"₹{row['Profit/Loss']:,.2f}",
                delta=f"{row['Growth(%)']:.2f}%",
                delta_color="inverse"
            )
    
    # First row of charts
    col1, col2 = st.columns(2)
    with col1:
        # Investment by Industry
        industry_investment = open_pos.groupby('Industry')['Investment Amount'].sum().reset_index()
        fig = px.pie(industry_investment, values='Investment Amount', names='Industry', 
                     title='Investment by Industry', hole=0.3)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Investment by Cap Size
        cap_investment = open_pos.groupby('Cap Size')['Investment Amount'].sum().reset_index()
        fig = px.pie(cap_investment, values='Investment Amount', names='Cap Size', 
                     title='Investment by Market Cap Size', hole=0.3)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed table
    st.subheader("Detailed Open Positions")
    display_open = open_pos.copy()
    
    # Apply formatting
    for col in ['Buying Price', 'Current Share Price']:
        if col in display_open.columns:
            display_open[col] = display_open[col].apply(lambda x: safe_format(x, '{:.2f}'))
    
    for col in ['Investment Amount', 'Profit/Loss']:
        if col in display_open.columns:
            display_open[col] = display_open[col].apply(lambda x: safe_format(x, '₹{:,.2f}'))
    
    for col in ['Growth(%)']:
        if col in display_open.columns:
            display_open[col] = display_open[col].apply(lambda x: safe_format(x, '{:.2f}%'))
    
    # Make dataframe Arrow-compatible
    display_open = make_dataframe_arrow_compatible(display_open)
    
    st.dataframe(
        display_open.style
        .apply(lambda x: ['color: red' if isinstance(v, (int, float)) and v < 0 else '' for v in x], 
               subset=['Profit/Loss', 'Growth(%)'])
        .apply(lambda x: ['color: green' if isinstance(v, (int, float)) and v >= 0 else '' for v in x], 
               subset=['Profit/Loss', 'Growth(%)']),
        use_container_width=True,
        height=400
    )

with tab2:
    st.header("Closed Positions Analysis")
    
    # Marquee with stock performance
    marquee_content = " | ".join(
        f"{row['Stock Name']}: {row.get('Today\'s Growth', 0)}%" 
        for _, row in closed_pos.iterrows()
    )
    marquee(marquee_content)
    
    # Summary cards row 1
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Invested", f"₹{metrics['total_invested_closed']:,.2f}")
    with col2:
        st.metric("Profit/Loss Booked", f"₹{metrics['total_pl_closed']:,.2f}", 
                 delta=f"{metrics['total_growth_closed']:.2f}%")
    with col3:
        st.metric("Possible P/L", f"₹{metrics['total_possible_pl']:,.2f}")
    with col4:
        st.metric("Total Invested Days", f"{metrics['total_days_closed']:,.0f}")
    
    # Top Gainers/Losers cards
    st.subheader("Performance Highlights")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Top Gainers**")
        top_gainers = closed_pos.nlargest(3, 'Growth(%)')
        for _, row in top_gainers.iterrows():
            metric_card(
                title=row['Stock Name'],
                value=f"₹{row['Profit/Loss Booked']:,.2f}",
                delta=f"{row['Growth(%)']:.2f}%",
                delta_color="inverse"
            )
    
    with col2:
        st.markdown("**Top Losers**")
        top_losers = closed_pos.nsmallest(3, 'Growth(%)')
        for _, row in top_losers.iterrows():
            metric_card(
                title=row['Stock Name'],
                value=f"₹{row['Profit/Loss Booked']:,.2f}",
                delta=f"{row['Growth(%)']:.2f}%",
                delta_color="inverse"
            )
    
    # First row of charts
    col1, col2 = st.columns(2)
    with col1:
        # Investment by Industry
        industry_investment = closed_pos.groupby('Industry')['Investment Amount'].sum().reset_index()
        fig = px.pie(industry_investment, values='Investment Amount', names='Industry', 
                     title='Investment by Industry (Closed Positions)', hole=0.3)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Holding Period vs Growth
        closed_pos['Investment Amount Clean'] = closed_pos['Investment Amount'].fillna(0)
        fig = px.scatter(closed_pos, x='Investment Days', y='Growth(%)',
                        color='Cap Size', size='Investment Amount Clean',
                        title='Holding Period vs Growth %',
                        hover_name='Stock Name',
                        hover_data=['Industry', 'Profit/Loss Booked'])
        fig.update_layout(xaxis_title="Holding Days", yaxis_title="Growth (%)")
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed table
    st.subheader("Detailed Closed Positions")
    display_closed = closed_pos.copy()
    
    # Apply formatting
    for col in ['Buying Price', 'Selling Price']:
        if col in display_closed.columns:
            display_closed[col] = display_closed[col].apply(lambda x: safe_format(x, '{:.2f}'))
    
    for col in ['Investment Amount', 'Selling Value', 'Profit/Loss Booked', 'Possible Profit/Loss']:
        if col in display_closed.columns:
            display_closed[col] = display_closed[col].apply(lambda x: safe_format(x, '₹{:,.2f}'))
    
    for col in ['Growth(%)']:
        if col in display_closed.columns:
            display_closed[col] = display_closed[col].apply(lambda x: safe_format(x, '{:.2f}%'))
    
    # Make dataframe Arrow-compatible
    display_closed = make_dataframe_arrow_compatible(display_closed)
    
    st.dataframe(
        display_closed.style
        .apply(lambda x: ['color: red' if isinstance(v, (int, float)) and v < 0 else '' for v in x], 
               subset=['Profit/Loss Booked', 'Growth(%)'])
        .apply(lambda x: ['color: green' if isinstance(v, (int, float)) and v >= 0 else '' for v in x], 
               subset=['Profit/Loss Booked', 'Growth(%)']),
        use_container_width=True,
        height=600
    )

# Sidebar with overall metrics
st.sidebar.header("Overall Portfolio Summary")
st.sidebar.metric("Total Invested", f"₹{metrics['total_invested_all']:,.2f}")
st.sidebar.metric("Net Profit/Loss", f"₹{metrics['total_pl_all']:,.2f}",
                 delta=f"{((metrics['total_pl_all']) / metrics['total_invested_all'] * 100 if metrics['total_invested_all'] != 0 else 0):.2f}%")
st.sidebar.metric("Total Invested Days", f"{metrics['total_days_all']:,.0f}")

# Add refresh button and last updated time
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.write(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# Add footer
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Disclaimer:**  
Quotes are not sourced from all markets and may be delayed.  
Information is provided 'as is' and solely for informational purposes,  
not for trading purposes or advice.
""")