import sqlite3
import pandas as pd
from sqlalchemy import create_engine
import numpy as np
import yfinance as yf
import streamlit as st
from datetime import datetime
import altair as alt
import os


periode = {
    'Q1':
    {'start':'2020-01-02',
    'end':'2020-01-31'},
    'Q2':
    {'start':'2020-02-03',
    'end':'2020-02-28'},
    'Q3':
    {'start':'2020-02-03',
    'end':'2020-03-31'},
    'Q4':
    {'start':'2020-10-01',
    'end':'2020-12-31'}
}

def LoadData():
    # Maak connectie met de database en geef de locaties aan van de input bestanden
    posreconhead = ['RekNr', 'Datum', 'Symbool', 'ISIN', 'Type optie', 'Expiratie',
       'Strike', 'Valuta', 'Slotkoers', 'Aantal', 'Valutakoers',
       'Contractgrootte', 'Waarde EUR', 'Waarde Orig Valuta', 'Aankoopwaarde',
       'Type instrument', 'Binckcode', 'Titel instrument', 'Unnamed: 18']

    tradereconhead = ['RekNr', 'Unnamed: 1', 'Valuta', 'Datum', 'Tijdstip', 'Unnamed: 5',
       'Type', 'Unnamed: 7', 'Unnamed: 8', 'Aantal', 'Per aandeel', 'Bedrag',
       'Unnamed: 12', 'Unnamed: 13', 'Unnamed: 14', 'Unnamed: 15',
       'Unnamed: 16', 'ISIN', 'Symbool', 'Unnamed: 19', 'Unnamed: 20',
       'Unnamed: 21', 'Unnamed: 22', 'Omschrijving', 'Unnamed: 24',
       'Unnamed: 25', 'Unnamed: 26', 'Unnamed: 27', 'Unnamed: 28',
       'Unnamed: 29', 'Omschrijving overzicht', 'Unnamed: 31', 'Unnamed: 32',
       'Unnamed: 33', 'Unnamed: 34', 'Unnamed: 35', 'Unnamed: 36', 'Unnamed: 37', 'Unnamed: 38',
        'Unnamed: 39', 'Unnamed: 40', 'Unnamed: 41']
    
    posdirectory = './Input/Posrecon'
    tradedirectory = './Input/Traderecon'
    conn = sqlite3.connect('DatabaseVB.db')
    # Loop over de input bestanden en laad ze in de database
    for file in os.listdir(posdirectory):
        df = pd.read_csv(posdirectory+'/'+file, names = posreconhead, delimiter = ';', decimal = ',', parse_dates = True)
        df.to_sql('Posrecon', if_exists = "append", con = conn)
        os.rename(posdirectory+'/'+file , './Archive/'+file)

    for file in os.listdir(tradedirectory):
        df = pd.read_csv(tradedirectory+'/'+file, names = tradereconhead, delimiter = ';', decimal = ',', parse_dates = True)
        df.to_sql('Traderecon', if_exists = "append", con = conn)
        os.rename(tradedirectory+'/'+file , './Archive/'+file)


def GetRendement(x):
    #conn = sqlite3.connect('DatabaseVB.db')
    engine = create_engine('sqlite:///DatabaseVB.db')
    
    df_posrecon = pd.read_sql(f''' SELECT "Datum", round(sum("Waarde EUR"),2) as "Eind Waarde" 
                      FROM "Posrecon" where "RekNr" = "{x}" group by "Datum" order by "Datum" ''', con = engine).set_index('Datum')
    
    ### LEES UIT DE DATABASE DE SOM VAN DE ONTTREKKINGEN / OVERBOEKINGEN / LICHTINGEN / STORTINGEN VOOR REKNR X
    df_onttrekking = pd.read_sql(f''' Select Datum, sum("Aantal") as "Onttrekkingen" from Traderecon
                       where "RekNr" = "{x}" and ("Unnamed: 34" = 5025 OR "Unnamed: 34" = 5000) group by "Datum" ''', con = engine).set_index('Datum')
    

    df_stortingen = pd.read_sql(f''' Select Datum, sum("Aantal") as "Stortingen" from Traderecon
                       where "RekNr" = "{x}"  and "Unnamed: 34" = 5026 group by "Datum" ''', con = engine).set_index('Datum')

    df_lichtingen = pd.read_sql(f''' Select Datum, sum("Aantal") as "Lichtingen" from Traderecon
                        where "RekNr" = "{x}" and "Type" = "L" group by "Datum" ''', con = engine).set_index('Datum')
    # df_lichtingen = pd.read_sql(f''' 
    #                     Select "Datum", sum("Unnamed: 31")*1.0 as Lichtingen from traderecon
    #                     where "RekNr" = {x}
    #                     and "Type" = "O"
    #                     and "Unnamed: 31" < 0
    #                     group by "Datum"
    #                     order by "Datum";
    #     ''')
    df_deponeringen = pd.read_sql(f''' Select Datum, sum("Aantal") as "Deponeringen" from Traderecon
                        where "RekNr" = "{x}" and "Type" = "D" group by "Datum" ''', con = engine).set_index('Datum')
    # Nieuwe formule onttrekkingen
    # df_deponeringen = pd.read_sql(f''' 
    #                     Select "Datum", sum("Unnamed: 31") as Deponeringen from traderecon
    #                     where "RekNr" = {x}
    #                     and "Type" = "O"
    #                     and "Unnamed: 31" > 0
    #                     group by "Datum"
    #                     order by "Datum";
    #     ''')
    # Concat de 4 dataframes uit de Traderecon query in 1 dataframe en merge deze met de Posrecon dataframe
    traderecon_data = [df_onttrekking, df_stortingen, df_lichtingen, df_deponeringen]
    df_tot_tr = pd.concat(traderecon_data)
    df_final = df_posrecon.merge(df_tot_tr, on='Datum', how='left')
    
    ### VOEG DE OVERBOEKINGEN AAN DE DATAFRAME MET DE WAARDES PORTEFEUILLE
    traderecon_columns = ['Onttrekkingen', 'Stortingen', 'Lichtingen', 'Deponeringen']
    df_final[traderecon_columns] = df_final[traderecon_columns].fillna(0.0)
    
    ### MAAK KOLOM ACTUELE RENDEMENT EN BEREKEN RENDEMENT VAN WAARDE PORTEFEUILLE EN ONTTREKKINGEN / STORTINGEN
    # start waarde is de eind waarde van de vorige dag
    df_final['Start Waarde'] = df_final["Eind Waarde"].shift(1)

    df_final['Dag Rendement'] = ((df_final['Eind Waarde'] - df_final['Start Waarde'] - df_final['Stortingen'] - df_final['Deponeringen'] + df_final['Onttrekkingen'] + df_final['Lichtingen'] ) ) / (df_final['Start Waarde'] + df_final['Stortingen'] - df_final['Onttrekkingen']).round(5)

    df_final['EW Portfolio Cumulatief Rendement'] = (1 + df_final['Dag Rendement']).cumprod()

    df_final['SW Portfolio Cumulatief Rendement'] = df_final['EW Portfolio Cumulatief Rendement'].shift(1)
    #df_final['Eind Waarde'] =  pd.to_numeric(df_final['Eind Waarde'], downcast = 'float')
    columns = ['Start Waarde','Stortingen','Deponeringen', 'Onttrekkingen', 'Lichtingen', 'Eind Waarde', 'Dag Rendement', 'SW Portfolio Cumulatief Rendement', 'EW Portfolio Cumulatief Rendement']
    
    return df_final[columns]


# Overview portefeuille Ontwikkeling
@st.cache
def GetOverview(data, kwartaals): 
    startwaarde, stortingen, deponeringen, onttrekkingen, lichtingen,eindwaarde = [],[],[],[],[],[]
    for kwartaal in kwartaals:
        startwaarde.append(data.loc[periode[kwartaal]['start'],['Start Waarde']][0])
        stortingen.append((data.loc[periode[kwartaal]['start']:periode[kwartaal]['end'],['Stortingen']]).sum()[0])
        deponeringen.append((data.loc[periode[kwartaal]['start']:periode[kwartaal]['end'],['Deponeringen']]).sum()[0])
        onttrekkingen.append((data.loc[periode[kwartaal]['start']:periode[kwartaal]['end'],['Onttrekkingen']]).sum()[0])
        lichtingen.append((data.loc[periode[kwartaal]['start']:periode[kwartaal]['end'],['Lichtingen']]).sum()[0])
        eindwaarde.append(data.loc[periode[kwartaal]['end'],['Eind Waarde']][0])
    overview = list(zip(startwaarde, stortingen, deponeringen, onttrekkingen, lichtingen, eindwaarde))
    
    df = pd.DataFrame(overview, 
           columns=["Start Waarde","Stortingen","Deponeringen","Onttrekkingen","Lichtingen","Eind Waarde"], index = kwartaals)


    df['Abs Rendement'] = df['Eind Waarde'] - df['Start Waarde'] - df['Stortingen'] - df['Deponeringen'] + df['Onttrekkingen'] + df['Lichtingen']

    df['Rendement'] = (df['Eind Waarde'] - df['Start Waarde']) / df['Start Waarde']

    return df

#Full Benchmark data
@st.cache(allow_output_mutation=True)
def getBenchmarkData(bench):
    conn = sqlite3.connect('DatabaseVB.db')
    engine = create_engine('sqlite:///DatabaseVB.db')
    
    ticker = yf.Ticker(bench)
    df_benchmark = ticker.history(period = '10y')
    
    df_benchmark.reset_index(inplace = True)
    df_benchmark.rename(columns = {'Date':'Datum', 'Close': 'Eind Waarde'}, inplace = True)
    df_benchmark['Start Waarde'] = df_benchmark['Eind Waarde'].shift(1)
    df_benchmark['Benchmark Dag Rendement'] = ((df_benchmark['Eind Waarde'] - df_benchmark['Start Waarde']) / df_benchmark['Start Waarde']).round(5)

    df_benchmark.to_sql(f'{bench}', if_exists = 'replace', con = conn)

    df = pd.read_sql(f'''
        SELECT substr(Datum, 1, 10) as "Datum", "Start Waarde" FROM "{bench}"
    ''', con = engine).set_index("Datum")
    return df

#Overview Benchmark Ontwikkeling
@st.cache
def getPerf(data, kwartaals, bench):
    kwart, startwaarde, eindwaarde = [], [], []
    for kwartaal in kwartaals:
        kwart.append(kwartaal)
        startwaarde.append(data.loc[periode[kwartaal]['start']][0])
        eindwaarde.append(data.loc[periode[kwartaal]['end']][0])

        overview = list(zip(kwart, startwaarde, eindwaarde))

        df = pd.DataFrame(overview, columns=['Kwartaal','Start Waarde','Eind Waarde'],
                         index = kwart)
        
        df['Benchmark Performance'] = (df['Eind Waarde'] - df['Start Waarde']) / df['Start Waarde']     
    return df

#Grafiek van Portfolio en Benchmark
def Graph(data, benchmark, ticker, period):
    sorted_periode = sorted(period)

    benchmark['Start Waarde'] = benchmark[f'{ticker} Eind Waarde'].shift(1)
    benchmark['Benchmark Dag Rendement'] = ((benchmark[f'{ticker} Eind Waarde'] - benchmark['Start Waarde']) / benchmark['Start Waarde']).round(5)
    
    df_port_bench = data.merge(benchmark, on='Datum', how='left')

    df_port_bench['Benchmark Cumulatief Rendement'] = (1 + df_port_bench['Benchmark Dag Rendement']).cumprod()
    df_port_bench['Benchmark Cumulatief Rendement'].fillna(method='ffill', inplace = True)
    df_base = df_port_bench[['Portfolio Cumulatief Rendement', 'Benchmark Cumulatief Rendement']]
    
    if len(period) > 1:
        start = periode[sorted_periode[0]]['start']
        end = periode[sorted_periode[-1]]['end']
    else:
        start = periode[sorted_periode[0]]['start']
        end = periode[sorted_periode[0]]['end']

    df = df_base.loc[start:end]

    dfn = df.reset_index().melt('Datum')
    dfn1 = alt.Chart(dfn).mark_line().encode(
        x = ('Datum:T'),
        y = ('value:Q'),
        color='variable:N').properties(
            height=500,
            width=750).interactive()

    graph = st.altair_chart(dfn1) 

    return graph

# Handmatig kiezen van start- en einddatum voor de portefeuille ontwikkeling
@st.cache
def ZoekPortfOntwikkeling(data, start_datum, eind_datum):
    sd = start_datum
    ed = eind_datum

    df = data.loc[sd:ed]
    portf_startwaarde = df.loc[sd,['Start Waarde']][0]
    portf_stortingen = df.loc[sd:ed,['Stortingen']].sum()[0]
    portf_deponeringen = df.loc[sd:ed,['Deponeringen']].sum()[0]
    portf_onttrekkingen = df.loc[sd:ed,['Onttrekkingen']].sum()[0]
    portf_lichtingen = df.loc[sd:ed,['Lichtingen']].sum()[0]
    portf_eindwaarde = df.loc[ed,['Eind Waarde']][0]
    startcumrendement = df.loc[sd,['SW Portfolio Cumulatief Rendement']][0]
    eindcumrendement = df.loc[ed,['EW Portfolio Cumulatief Rendement']][0]
    
    overview = [portf_startwaarde, portf_stortingen, portf_deponeringen, portf_onttrekkingen, portf_lichtingen, 
               portf_eindwaarde, startcumrendement, eindcumrendement]

    df_final = pd.DataFrame([overview], columns = ['Start Waarde', 'Stortingen', 'Deponeringen', 'Onttrekkingen', 'Lichtingen', 'Eind Waarde', 'Start Cum Rend', 'Eind Cum Rend'])
    df_final['Abs Rendement'] = df_final['Eind Waarde'] - df_final['Start Waarde'] - df_final['Stortingen'] - df_final['Deponeringen'] + df_final['Onttrekkingen'] + df_final['Lichtingen']
    df_final['Rendement'] = (df_final['Abs Rendement'] / df_final['Start Waarde'])
    df_final['Cumulatief Rendement'] = (eindcumrendement - startcumrendement) / startcumrendement
    
    return df_final

@st.cache
def ZoekBenchmarkOntwikkeling(data, start_date, end_date):
    new_benchmark_df = data[start_date:end_date]
    bench_sw = new_benchmark_df.loc[start_date][0]
    bench_ew = new_benchmark_df.loc[end_date][0]
    overview = [bench_sw, bench_ew]
    df = pd.DataFrame([overview], columns =['Start Waarde', 'Eind Waarde'])
    
    df['Abs Rendement'] = bench_ew - bench_sw
    
    df['Rendement'] = (bench_ew - bench_sw) / bench_sw
    
    return df


def ZoekGraph(data, benchmark, ticker, start_date, end_date):
    # benchmark['Start Waarde'] = benchmark[f'{ticker} Eind Waarde'].shift(1)
    # benchmark['Benchmark Dag Rendement'] = ((benchmark[f'{ticker} Eind Waarde'] - benchmark['Start Waarde']) / benchmark['Start Waarde']).round(5)

    df_port_bench = data.merge(benchmark, on='Datum', how='left')

    df_port_bench['Benchmark Cumulatief Rendement'] = (1 + df_port_bench['Benchmark Dag Rendement']).cumprod()
    df_port_bench['Benchmark Cumulatief Rendement'].fillna(method='ffill', inplace = True)
    df_base = df_port_bench[['Portfolio Cumulatief Rendement', 'Benchmark Cumulatief Rendement']]

    df = df_base.loc[start_date:end_date]

    dfn = df.reset_index().melt('Datum')
    dfn1 = alt.Chart(dfn).mark_line().encode(
        x = ('Datum:T'),
        y = ('value:Q'),
        color='variable:N').properties(
            height=500,
            width=750).interactive()

    graph = st.altair_chart(dfn1) 

    return graph