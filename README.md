# 📊 Personal Stock Portfolio Tracker (Streamlit + Power BI)

An interactive personal stock portfolio dashboard that helps you track open and closed positions, analyze profit/loss performance, and gain insight into your investment behavior—all in real-time.

Originally developed in **Power BI**, this upgraded version uses **Streamlit** with integrated Google Sheets and Plotly for dynamic visualizations.

---

## 🚀 Live Features

- 📈 **Open Positions Dashboard**
  - Summary cards for investment, holding days, and gainers/losers
  - Pie and bar charts for investment distribution and performance
  - Interactive dataframe explorer

- 📉 **Closed Positions Dashboard**
  - Realized and potential profits overview
  - Scatter & box plots for performance over time and by sector
  - Highlights of top-performing and poor-performing stocks

- ☁️ **Cloud Sync**
  - Auto-syncs data from **Google Sheets** portfolio
  - Manual refresh button with real-time update

- 📚 **Total Investment Summary** in sidebar:
  - Net performance
  - Cumulative invested amount
  - Total days capital was deployed

---

## 🧠 Tech Stack

| Component          | Tools / Libraries               |
|-------------------|---------------------------------|
| Frontend UI       | Streamlit                       |
| Visualizations    | Plotly + Streamlit Extras       |
| Data Backend      | Google Sheets (via gspread API) |
| Analytics         | pandas, NumPy                   |
| Design Theme      | Custom CSS for modern UI        |

---

## 📁 Project Structure

```
personal-stock-tracker/
├── dashboard.py                  # Main Streamlit app
├── Stock Portfolio Visualization.pbix  # Original Power BI file
├── requirements.txt              # Python dependencies
├── .streamlit/secrets.toml      # GCP credentials for Google Sheets
└── README.md

```

---

## 🛠️ Setup Instructions

### 1. Clone the repo

  ```
  git clone https://github.com/yourusername/personal-stock-portfolio-tracker.git
  cd personal-stock-portfolio-tracker
  ```

### 2. Install dependencies

  ```
  pip install -r requirements.txt
  ```

### 3. Configure Google Sheets

Create a `.streamlit/secrets.toml` file with your Google Service Account:

```toml
[gcp_service_account]
type = "service_account"
project_id = "your_project_id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
...
```

Make sure your service account has access to the Google Sheet titled `"My Stock Portfolio"`.

### 4. Run the app

  ```
  streamlit run dashboard.py
  ```

---

## 📈 Metrics Tracked

* Investment Amount (open + closed)
* Profit/Loss (unrealized & booked)
* Growth %
* Holding Days
* Sector-wise performance
* Investment decisions by rationale

---

## 🧪 Future Enhancements

* 🔔 Email alerts for target price triggers
* 📊 Quarterly CAGR breakdown
* 📅 Transaction timeline view
* 💸 Tax calculator for realized gains
* 📈 Integration with Zerodha, Groww, or Kite API for live data

---

## 🙌 Author

**Aman Haris**

🌐 [Portfolio](https://aman-haris-portfolio.onrender.com)

📧 [amanharisofficial@protonmail.com](mailto:amanharisofficial@protonmail.com)

---

## 📝 License

This project is licensed for personal/educational use.

For commercial or enterprise use, please contact the author.
