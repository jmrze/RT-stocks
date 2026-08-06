import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import yfinance as yf
import datetime as dt

st.set_page_config(
    'stretch',
    layout='wide'
)

#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=
#               DFS
#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=

#=#=#=#=#=#=#=#=#=#= SELECTION FILTERS #=#=#=#=#=#=#=#=#=#=
ticker_list = ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA", "META", "NVDA", "BRK.B", "DIS", "NFLX", "GOOG", "INTC", "AMD", "BA", "V", "MA", "CSCO", "PYPL", "SPY", "TSM"]

etf_tickers_list=['SPY', 'IVV', 'VOO'] 

stocks = st.multiselect(
    'Top 20 Ticker (Stocks)',
    ticker_list
)

etfs = st.multiselect(
    'S&P500',
    etf_tickers_list
)

tickers = stocks + etfs

dates = st.date_input(
    'Select date range',
    value=(),
    format="MM.DD.YYYY",
    max_value='today'
)

# initialise df as none to catch no df
df = None

if not tickers or len(dates) != 2:
    st.warning('Select tickers and date range')
else:
    st.write(f'Tickers: {', '.join([ticker for ticker in tickers])}')

    try:
        start_date, end_date = dates

        diff_from_today = (dt.datetime.now().date() - start_date).days
        day_diff = (end_date - start_date).days

        # use 30m intervals if recent data
        if diff_from_today < 60:
            interval = '30m'
        else:
            interval = '1d'

        st.write('Date: ', dt.datetime.now().date())
        st.write('Date range: ', start_date, '-', end_date)
        st.write('Number of Days: ', day_diff)
        #st.write('Today - start: ', diff_from_today)
        # download 
        df = yf.download(tickers=tickers,
                         auto_adjust=False,
                         start=start_date,
                         end=end_date,
                         interval=interval)

        if df.empty:
            print('Select Tickers')

        else:
            # unpivot multi-column headers
            df = df.stack(level=1).rename_axis(['Date', 'Ticker']).reset_index(level=1)

            num_tickers = len(df['Ticker'].unique())
            # remove tstamp
            df = df.reset_index(names='Date')
            #df['Time'] = df['Date'].dt.time
            #df['Date'] = df['Date'].dt.date
            df['Returns'] = df.groupby('Ticker')['Close'].pct_change()
            df['logReturns'] = np.log(1 + df['Returns'])
            df['Volatility'] = df['Returns'].rolling(window=14).std() * np.sqrt(14)
            df['logReturns'] = np.log(1 + df['Returns'])
            df['maShort'] = df.groupby('Ticker')['Close'].transform(lambda x: x.rolling(10).mean())
            df['maLong'] = df.groupby('Ticker')['Close'].transform(lambda x: x.rolling(30).mean())
            #st.write(df['logReturns'])

# throw error if df returns na
    except Exception as e:
        st.error(f'No ticker data: {e}')

#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=
#               BODY
#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=

st.title('Real Time ETF Tracker')

#=#=#=#=#=#=#=#=#=#= S&P500 #=#=#=#=#=#=#=#=#=#= 
st.header('ETF summary - S&P 500')

st.subheader('Summary')

# selection
ticker_select = alt.selection_multi(fields=['Ticker'], bind='legend')

# nearest hover for tootip
def line_chart_tab1(variable):
    custom_scale= alt.Scale(domain=df['Ticker'].unique(), scheme='dark2')
    chart = alt.Chart(df).mark_line().encode(
        y=alt.Y(variable,
                scale=alt.Scale(zero=False)
                ),
        x='Date',
        color=alt.Color('Ticker',scale=custom_scale),
        opacity=alt.condition(ticker_select, alt.value(1.0), alt.value(0.25)),
        tooltip=[variable,'Ticker', 'Date']
    ).properties(
        title=alt.TitleParams(variable),
        height=500,width=500
    ).add_params(
        ticker_select
    ).transform_filter(
        ticker_select
    ).interactive()
    
    return chart

def bar_chart_tab1(x, y):
    custom_scale= alt.Scale(domain=df['Ticker'].unique())
    chart = alt.Chart(df).mark_bar().encode(
        y=alt.Y(y,
                scale=alt.Scale(zero=False)
                ),
        x=x,
        color=alt.Color('Ticker',scale=custom_scale),
        opacity=alt.condition(ticker_select, alt.value(1.0), alt.value(0.25)),
        tooltip=[y,'Ticker', 'Date']
    ).properties(
        title=alt.TitleParams(y),
        height=500,width=500
    ).add_params(
        ticker_select
    ).transform_filter(
        ticker_select
    ).interactive()
    
    return chart
# no data selected/available
if df is None or df.empty:
    st.warning('No data available')

# create and plot otherwise
else:
    close_chart = line_chart_tab1('Close')
    vol_chart = bar_chart_tab1('Date', 'Volume')
    rets_chart = line_chart_tab1('Returns')
    logrets_chart = line_chart_tab1('logReturns')
    volat_chart = line_chart_tab1('Volatility')

    ret_hist = alt.Chart(df).mark_bar().encode(
            x=alt.X('Returns', bin=alt.Bin(maxbins=50), title='Returns'),  # Binned returns
            y='count()',  # Count of returns in each bin
            color='Ticker'
        ).properties(
            title='Return Distribution',
            height=500, width=500
        ).interactive()
    
    logret_hist = alt.Chart(df).mark_bar().encode(
            x=alt.X('logReturns', bin=alt.Bin(maxbins=50), title='logReturns'),  # Binned returns
            y='count()',  # Count of returns in each bin
            color='Ticker'
        ).properties(
            title='Return Distribution',
            height=500, width=500
        ).interactive()

    dashboard = (((close_chart | vol_chart) & (rets_chart | logrets_chart) & (ret_hist | logret_hist) & (volat_chart))).configure_legend(orient='top')
    st.altair_chart(dashboard, use_container_width = True)

    st.dataframe(
        data=df,
        width='stretch'
    )
