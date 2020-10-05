import streamlit as st
import pandas as pd
import altair as alt
import time
import datetime
import yfinance as yf
from Balans import *


password = st.sidebar.text_input("Password:", value="", type="password")
if password == "Balans":
	st.sidebar.markdown("# Vermogensbeheer-Dashboard Amsterdam")

	if st.sidebar.button('Lees Input Bestanden'):
		LoadData()

	reknr = st.sidebar.text_input("Rekeningnummer Klant")
	df = GetRendement(reknr)

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
		df = GetRendement(reknr)
		start_d = start_date.strftime("%Y-%m-%d") # Verander datum terug naar Y-m-d
		end_d = end_date.strftime("%Y-%m-%d")

		if not periode_keuze:
			st.markdown("## Portefeuille Ontwikkeling")
			st.markdown(f"#### From {start_d} to {end_d}")
			st.table(ZoekPortfOntwikkeling(df, start_d, end_d))
			st.dataframe(df)
		
			st.markdown(f"## Benchmark Ontwikkeling {benchmark_keuze}")
			st.table(ZoekBenchmarkOntwikkeling(getBenchmarkData(benchmark_keuze), start_d, end_d))
			ZoekGraph(df, getBenchmarkData(benchmark_keuze), benchmark_keuze, start_d, end_d)
		else:
			st.markdown("## Portefeuille Ontwikkeling")
			df = GetRendement(reknr)
			df_port_ont = st.table(GetOverview(df, periode_keuze))
			st.markdown(f"## Benchmark Ontwikkeling {benchmark_keuze}")
			full_bench_df = getBenchmarkData(benchmark_keuze)
			st.table(getPerf(full_bench_df, periode_keuze, benchmark_keuze))
			Graph(df, getBenchmarkData(benchmark_keuze), benchmark_keuze, periode_keuze)
