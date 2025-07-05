import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import numpy as np

# Set page config with modern theme
st.set_page_config(
    page_title="Stock Portfolio Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Stock Portfolio Tracker v2.0"
    }
)

# Apply modern theme with improved styling
def apply_modern_theme():
    st.markdown("""
    <style>
    /* Main container */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
    }
    
    /* Content area */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        background: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        margin: 1rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
    }
    
    /* Metrics styling */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border: 1px solid #e9ecef;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    [data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #2c3e50 0%, #3498db 100%);
    }
    
    [data-testid="stSidebar"] .css-1d391kg {
        color: white;
    }
    
    /* Charts container */
    .plot-container {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
    }
    
    /* DataFrames */
    .dataframe {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 8px;
        color: white;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* Cards */
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #667eea;
    }
    
    .positive-card {
        border-left-color: #28a745;
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
    }
    
    .negative-card {
        border-left-color: #dc3545;
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #2c3e50;
        font-weight: 600;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
    }
    </style>
    """, unsafe_allow_html=True)

apply_modern_theme()

# Custom metric card function
def create_metric_card(title, value, delta=None, delta_color="normal"):
    delta_class = ""
    if delta:
        if delta_color == "positive" or (delta_color == "normal" and str(delta).replace('-', '').replace('.', '').isdigit() and float(delta) > 0):
            delta_class = "positive-card"
        elif delta_color == "negative" or (delta_color == "normal" and str(delta).replace('-', '').replace('.', '').isdigit() and float(delta) < 0):
            delta_class = "negative-card"
    
    st.markdown(f"""
    <div class="metric-card {delta_class}">
        <h4 style="margin: 0; color: #6c757d; font-size: 0.9rem;">{title}</h4>
        <h2 style="margin: 0.5rem 0; color: #2c3e50;">{value}</h2>
        {f'<p style="margin: 0; color: #6c757d; font-size: 0.8rem;">{delta}</p>' if delta else ''}
    </div>
    """, unsafe_allow_html=True)

# Function to clean and format dataframe
def clean_and_format_dataframe(df, format_config=None):
    """Clean dataframe and apply formatting"""
    if df.empty:
        return df
    
    # Remove completely empty columns
    df_clean = df.dropna(axis=1, how='all')
    
    # Remove columns that are all zeros or empty strings
    for col in df_clean.columns:
        if df_clean[col].dtype == 'object':
            if df_clean[col].str.strip().eq('').all() or df_clean[col].isna().all():
                df_clean = df_clean.drop(columns=[col])
        elif df_clean[col].dtype in ['int64', 'float64']:
            if df_clean[col].eq(0).all() and col not in ['Profit/Loss', 'Growth(%)']:
                df_clean = df_clean.drop(columns=[col])
    
    # Apply formatting if provided
    if format_config:
        display_df = df_clean.copy()
        for col, formatter in format_config.items():
            if col in display_df.columns:
                if 'currency' in formatter:
                    display_df[col] = display_df[col].apply(lambda x: f'₹{x:,.2f}' if pd.notna(x) else 'N/A')
                elif 'percentage' in formatter:
                    display_df[col] = display_df[col].apply(lambda x: f'{x:.2f}%' if pd.notna(x) else 'N/A')
        return display_df
    
    return df_clean

# Google Sheets API setup
@st.cache_data(ttl=600)
def load_data():
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        gc = gspread.authorize(creds)
        
        sh = gc.open("My Stock Portfolio")
        open_pos = pd.DataFrame(sh.worksheet("Open Positions").get_all_records())
        closed_pos = pd.DataFrame(sh.worksheet("Closed Positions").get_all_records())
        
        return open_pos, closed_pos
    except Exception as e:
        st.error(f"Data loading error: {str(e)}")
        # Return sample data for demonstration
        st.warning("Using sample data for demonstration")
        
        sample_open = pd.DataFrame({
            'Stock Name': ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN'],
            'Industry': ['Technology', 'Technology', 'Technology', 'Automotive', 'E-commerce'],
            'Buying Date': ['2023-01-15', '2023-02-20', '2023-03-10', '2023-04-05', '2023-05-12'],
            'Buying Price': [150.00, 2500.00, 250.00, 200.00, 3000.00],
            'Investment Amount': [15000, 25000, 12500, 10000, 30000],
            'Profit/Loss': [2500, -1500, 1800, -800, 2200],
            'Growth(%)': [16.67, -6.00, 14.40, -8.00, 7.33],
            'Investment Days': [365, 320, 280, 240, 200]
        })
        
        sample_closed = pd.DataFrame({
            'Stock Name': ['META', 'NVDA', 'NFLX'],
            'Industry': ['Technology', 'Technology', 'Entertainment'],
            'Buying Date': ['2022-01-10', '2022-03-15', '2022-06-20'],
            'Selling Date': ['2023-01-10', '2023-03-15', '2023-06-20'],
            'Investment Amount': [20000, 15000, 8000],
            'Selling Value': [22000, 18000, 7200],
            'Profit/Loss Booked': [2000, 3000, -800],
            'Growth(%)': [10.00, 20.00, -10.00],
            'Investment Days': [365, 365, 365],
            'Reason for selling': ['Profit booking', 'Target achieved', 'Stop loss'],
            'Possible Profit/Loss': [2500, 3500, -600]
        })
        
        return sample_open, sample_closed

# Data processing
def process_data(open_df, closed_df):
    # Convert dates and numeric columns
    date_cols = ['Buying Date', 'Selling Date']
    num_cols = ['Buying Price', 'Investment Amount', 'Profit/Loss', 'Growth(%)', 
               'Selling Value', 'Profit/Loss Booked', 'Investment Days']
    
    for df in [open_df, closed_df]:
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Calculate metrics
    metrics = {
        'open_invested': open_df['Investment Amount'].sum(),
        'open_pl': open_df['Profit/Loss'].sum(),
        'closed_invested': closed_df['Investment Amount'].sum(),
        'closed_pl': closed_df['Profit/Loss Booked'].sum() if 'Profit/Loss Booked' in closed_df.columns else 0,
        'possible_pl': closed_df['Possible Profit/Loss'].sum() if 'Possible Profit/Loss' in closed_df.columns else 0,
        'total_days': open_df['Investment Days'].sum() + closed_df['Investment Days'].sum()
    }
    
    return open_df, closed_df, metrics

# Load and process data
open_pos, closed_pos, metrics = process_data(*load_data())

# Main dashboard header
st.title("📊 Stock Portfolio Dashboard")
st.markdown("---")

# Overall portfolio summary
st.subheader("📈 Portfolio Overview")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Invested",
        f"₹{metrics['open_invested'] + metrics['closed_invested']:,.2f}",
        f"₹{metrics['open_invested']:,.2f} Active"
    )

with col2:
    total_pl = metrics['open_pl'] + metrics['closed_pl']
    st.metric(
        "Net P&L",
        f"₹{total_pl:,.2f}",
        f"{(total_pl/(metrics['open_invested'] + metrics['closed_invested'])*100):.2f}%" if (metrics['open_invested'] + metrics['closed_invested']) > 0 else "0%"
    )

with col3:
    st.metric(
        "Active Positions",
        len(open_pos),
        f"₹{metrics['open_pl']:,.2f} Unrealized"
    )

with col4:
    st.metric(
        "Total Trading Days",
        f"{metrics['total_days']:,}",
        f"{metrics['total_days']/365:.1f} years" if metrics['total_days'] > 0 else "0 years"
    )

# Create tabs
tab1, tab2, tab3 = st.tabs(["📈 Open Positions", "📉 Closed Positions", "📊 Analytics"])

with tab1:
    st.header("Open Positions Dashboard")
    
    # Performance highlights
    if len(open_pos) > 0:
        st.subheader("🎯 Performance Highlights")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📈 Top Gainers**")
            top_gainers = open_pos.nlargest(3, 'Growth(%)')
            for _, row in top_gainers.iterrows():
                create_metric_card(
                    row['Stock Name'],
                    f"₹{row['Profit/Loss']:,.2f}",
                    f"{row['Growth(%)']:.2f}% Growth",
                    "positive"
                )
        
        with col2:
            st.markdown("**📉 Underperformers**")
            underperformers = open_pos.nsmallest(3, 'Growth(%)')
            for _, row in underperformers.iterrows():
                create_metric_card(
                    row['Stock Name'],
                    f"₹{row['Profit/Loss']:,.2f}",
                    f"{row['Growth(%)']:.2f}% Growth",
                    "negative"
                )
        
        # Visualizations
        st.subheader("📊 Portfolio Visualization")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="plot-container">', unsafe_allow_html=True)
            fig = px.pie(
                open_pos, 
                names='Industry', 
                values='Investment Amount',
                title='Investment Distribution by Industry',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#2c3e50', size=12),
                title_font=dict(color='#2c3e50', size=16),
                legend=dict(font=dict(color='#2c3e50'))
            )
            fig.update_traces(textfont_color='white', textfont_size=12)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="plot-container">', unsafe_allow_html=True)
            fig = px.bar(
                open_pos.sort_values('Profit/Loss'), 
                x='Stock Name', 
                y='Profit/Loss',
                title='Profit/Loss by Stock',
                color='Profit/Loss',
                color_continuous_scale='RdYlGn'
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#2c3e50', size=12),
                title_font=dict(color='#2c3e50', size=16),
                xaxis=dict(title_font=dict(color='#2c3e50'), tickfont=dict(color='#2c3e50')),
                yaxis=dict(title_font=dict(color='#2c3e50'), tickfont=dict(color='#2c3e50')),
                coloraxis_colorbar=dict(tickfont=dict(color='#2c3e50'))
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Portfolio details table
        st.subheader("💼 Portfolio Details")
        
        # Clean and format the dataframe
        format_config = {
            'Investment Amount': 'currency',
            'Profit/Loss': 'currency',
            'Growth(%)': 'percentage',
            'Buying Price': 'currency',
            'Current Share Price': 'currency'
        }
        
        display_df = clean_and_format_dataframe(open_pos, format_config)
        
        if len(display_df) > 0:
            st.dataframe(display_df, use_container_width=True, height=400)
    else:
        st.info("No open positions found.")

with tab2:
    st.header("Closed Positions Dashboard")
    
    if len(closed_pos) > 0:
        # Performance highlights
        st.subheader("🏆 Trading Performance")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🎯 Best Trades**")
            best_trades = closed_pos.nlargest(3, 'Profit/Loss Booked')
            for _, row in best_trades.iterrows():
                create_metric_card(
                    row['Stock Name'],
                    f"₹{row['Profit/Loss Booked']:,.2f}",
                    f"Held {row['Investment Days']} days",
                    "positive"
                )
        
        with col2:
            st.markdown("**📚 Learning Opportunities**")
            learning_trades = closed_pos.nsmallest(3, 'Profit/Loss Booked')
            for _, row in learning_trades.iterrows():
                create_metric_card(
                    row['Stock Name'],
                    f"₹{row['Profit/Loss Booked']:,.2f}",
                    f"{row.get('Reason for selling', 'N/A')}",
                    "negative"
                )
        
        # Visualizations
        st.subheader("📊 Trading Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="plot-container">', unsafe_allow_html=True)
            fig = px.scatter(
                closed_pos, 
                x='Investment Days', 
                y='Profit/Loss Booked',
                color='Industry', 
                size='Investment Amount',
                title='Holding Period vs Returns',
                hover_data=['Stock Name']
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#2c3e50', size=12),
                title_font=dict(color='#2c3e50', size=16),
                xaxis=dict(title_font=dict(color='#2c3e50'), tickfont=dict(color='#2c3e50')),
                yaxis=dict(title_font=dict(color='#2c3e50'), tickfont=dict(color='#2c3e50')),
                legend=dict(font=dict(color='#2c3e50'))
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="plot-container">', unsafe_allow_html=True)
            fig = px.box(
                closed_pos, 
                x='Industry', 
                y='Growth(%)', 
                title='Performance Distribution by Sector'
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#2c3e50', size=12),
                title_font=dict(color='#2c3e50', size=16),
                xaxis=dict(title_font=dict(color='#2c3e50'), tickfont=dict(color='#2c3e50')),
                yaxis=dict(title_font=dict(color='#2c3e50'), tickfont=dict(color='#2c3e50'))
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Transaction history table
        st.subheader("📋 Transaction History")
        
        # Clean and format the dataframe
        format_config = {
            'Investment Amount': 'currency',
            'Selling Value': 'currency',
            'Profit/Loss Booked': 'currency',
            'Growth(%)': 'percentage'
        }
        
        display_df = clean_and_format_dataframe(closed_pos, format_config)
        
        if len(display_df) > 0:
            st.dataframe(display_df, use_container_width=True, height=400)
    else:
        st.info("No closed positions found.")

with tab3:
    st.header("Portfolio Analytics")
    
    # Combined analysis
    if len(open_pos) > 0 or len(closed_pos) > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            # Sector allocation
            st.subheader("🏭 Sector Allocation")
            if len(open_pos) > 0:
                sector_data = open_pos.groupby('Industry')['Investment Amount'].sum().reset_index()
                fig = px.treemap(
                    sector_data,
                    path=['Industry'],
                    values='Investment Amount',
                    title='Current Sector Allocation'
                )
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#2c3e50', size=12),
                    title_font=dict(color='#2c3e50', size=16)
                )
                fig.update_traces(textfont_color='white', textfont_size=12)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Performance trends
            st.subheader("📈 Performance Trends")
            if len(closed_pos) > 0:
                monthly_performance = closed_pos.copy()
                if 'Selling Date' in monthly_performance.columns:
                    monthly_performance['Month'] = pd.to_datetime(monthly_performance['Selling Date']).dt.to_period('M')
                    monthly_data = monthly_performance.groupby('Month')['Profit/Loss Booked'].sum().reset_index()
                    monthly_data['Month'] = monthly_data['Month'].astype(str)
                    
                    fig = px.line(
                        monthly_data,
                        x='Month',
                        y='Profit/Loss Booked',
                        title='Monthly P&L Trend'
                    )
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#2c3e50', size=12),
                        title_font=dict(color='#2c3e50', size=16),
                        xaxis=dict(title_font=dict(color='#2c3e50'), tickfont=dict(color='#2c3e50')),
                        yaxis=dict(title_font=dict(color='#2c3e50'), tickfont=dict(color='#2c3e50'))
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        # Risk metrics
        st.subheader("⚠️ Risk Analysis")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if len(open_pos) > 0:
                concentration_risk = (open_pos['Investment Amount'].max() / open_pos['Investment Amount'].sum()) * 100
                st.metric("Concentration Risk", f"{concentration_risk:.1f}%", "Max position weight")
        
        with col2:
            if len(closed_pos) > 0:
                win_rate = (closed_pos['Profit/Loss Booked'] > 0).mean() * 100
                st.metric("Win Rate", f"{win_rate:.1f}%", "Profitable trades")
        
        with col3:
            if len(open_pos) > 0:
                avg_holding = open_pos['Investment Days'].mean()
                st.metric("Avg Holding Period", f"{avg_holding:.0f} days", "Current positions")

# Enhanced sidebar
with st.sidebar:
    st.title("🎯 Portfolio Command Center")
    
    # Net performance card
    net_performance = metrics['open_pl'] + metrics['closed_pl']
    performance_color = "positive" if net_performance >= 0 else "negative"
    
    create_metric_card(
        "Net Performance",
        f"₹{net_performance:,.2f}",
        f"Total Return: {(net_performance/(metrics['open_invested'] + metrics['closed_invested'])*100):.2f}%" if (metrics['open_invested'] + metrics['closed_invested']) > 0 else "0%",
        performance_color
    )
    
    st.markdown("---")
    
    # Key metrics
    st.subheader("📊 Key Metrics")
    st.metric("Total Invested", f"₹{metrics['open_invested'] + metrics['closed_invested']:,.2f}")
    st.metric("Active Positions", len(open_pos))
    st.metric("Completed Trades", len(closed_pos))
    st.metric("Total Trading Days", f"{metrics['total_days']:,}")
    
    st.markdown("---")
    
    # Action buttons
    st.subheader("🔧 Actions")
    if st.button("🔄 Refresh Data", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    if st.button("📊 Export Report", use_container_width=True):
        st.success("Report export feature coming soon!")
    
    st.markdown("---")
    
    # Last updated
    st.caption(f"📅 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    st.markdown("---")
    
    # Data sources and disclaimer
    st.markdown("""
    **📋 Data Sources:**
    - Google Sheets Portfolio Tracker
    - Real-time Market Data
    
    **⚠️ Disclaimer:**
    Past performance does not guarantee future results. 
    Always consult with a qualified financial advisor before making investment decisions.
    
    **🛠️ Tech Stack:**
    - Streamlit • Plotly • Pandas
    - Google Sheets API
    """)

# Installation and setup instructions
st.sidebar.markdown("---")
with st.sidebar.expander("🔧 Setup Instructions"):
    st.markdown("""
    **Required packages:**
    ```bash
    pip install streamlit plotly pandas gspread
    ```
    
    **Google Sheets Setup:**
    1. Create a Google Cloud project
    2. Enable Google Sheets API
    3. Create service account credentials
    4. Add credentials to Streamlit secrets
    """)