import streamlit as st
import pandas as pd
import altair as alt
import time
import datetime
import yfinance as yf
from Balans import *
from sqlalchemy import create_engine

# password = st.sidebar.text_input("Password:", value="", type="password")
# if password == "Balans":
st.sidebar.markdown("# Vermogensbeheer-Dashboard Amsterdam")

if st.sidebar.button('Lees Input Bestanden'):
	LoadData()

reknr = st.sidebar.text_input("Rekeningnummer Klant")

st.sidebar.markdown("# Periode")
start_date = st.sidebar.date_input('Start Datum')
end_date = st.sidebar.date_input('Eind Datum')
periode_keuze = st.sidebar.multiselect("Selecteer de gewenste periode voor de portefeuille ontwikkeling", ['Q1','Q2','Q3','Q4'])

st.sidebar.markdown("# Benchmark")
benchmark_keuze = st.sidebar.selectbox('Selecteer de Benchmark', ['^AEX','SPYY.DE','IUSQ.DE'])

bench_spy = getBenchmarkData("SPYY.DE")
bench_aex = getBenchmarkData("^AEX")
bench_iusq = getBenchmarkData("IUSQ.DE")

if st.sidebar.button('Show Data'):
	engine = create_engine('sqlite:///DatabaseVB.db')
	df = GetRendement(reknr)

	# Kies hier de start en eind datum
	start_d = start_date.strftime("%Y-%m-%d") # Verander datum terug naar Y-m-d
	end_d = end_date.strftime("%Y-%m-%d")
	
	# # Het systeem kijkt in de database wat de start en eind datums zijn voor de rekeningnummer en geeft deze als output
	database_start_date_posrecon = pd.read_sql(f'''select datum from posrecon where RekNr = "{reknr}" order by datum asc limit 1;''', con = engine)
	database_end_date_posrecon = pd.read_sql(f'''select datum from posrecon where RekNr = "{reknr}" order by datum desc limit 1;''', con = engine)
	
	database_start_date_traderecon = pd.read_sql(f'''select datum from traderecon where RekNr = "{reknr}" order by datum asc limit 1;''', con = engine)
	database_end_date_traderecon = pd.read_sql(f'''select datum from traderecon where RekNr = "{reknr}" order by datum desc limit 1;''', con = engine)

	new_start_date_posrecon = pd.to_datetime(database_start_date_posrecon['Datum'][0]).strftime("%Y-%m-%d")
	new_end_date_posrecon = pd.to_datetime(database_end_date_posrecon['Datum'][0]).strftime("%Y-%m-%d")

	new_start_date_traderecon = pd.to_datetime(database_start_date_traderecon['Datum'][0]).strftime("%Y-%m-%d")
	new_end_date_traderecon= pd.to_datetime(database_end_date_traderecon['Datum'][0]).strftime("%Y-%m-%d")	

	# # Hier vergelijken we gekozen start/eind datum en de start/eind datum in de database. Als de gekozen start/eind datum kleiner/groter is dan wat er in de database staat zal deze de nieuwe
	# # start/eind datum worden
	startdates = [new_start_date_posrecon, new_start_date_traderecon]
	enddates = [new_end_date_posrecon, new_end_date_traderecon]
	sorted_start_date = sorted(startdates)[0]
	sorted_end_date = sorted(enddates)[-1]

	if start_d < sorted_start_date:
		start_d = sorted_start_date
	if end_d > sorted_end_date:
		end_d = sorted_end_date

	if not periode_keuze:

		st.markdown("## Portefeuille Ontwikkeling")
		st.markdown(f"### From {start_d} to {end_d}")
		st.table(ZoekPortfOntwikkeling(df, start_d, end_d))
		st.dataframe(df)
		st.markdown(f"## Benchmark Ontwikkeling {benchmark_keuze}")
		st.table(ZoekBenchmarkOntwikkeling(getBenchmarkData(benchmark_keuze), start_d, end_d))
		ZoekGraph(df, getBenchmarkData(benchmark_keuze), start_d, end_d)
	else:
		st.markdown("## Portefeuille Ontwikkeling")
		df = GetRendement(reknr)
		df_port_ont = st.table(GetOverview(df, periode_keuze))
		st.markdown(f"## Benchmark Ontwikkeling {benchmark_keuze}")
		full_bench_df = getBenchmarkData(benchmark_keuze)
		st.table(getPerf(full_bench_df, periode_keuze, benchmark_keuze))
		Graph(df, getBenchmarkData(benchmark_keuze), periode_keuze)
