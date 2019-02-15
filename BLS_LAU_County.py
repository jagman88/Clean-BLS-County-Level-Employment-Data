#--------------------------------------
#
#   This file cleans employment ane unemployment data by County from the BLS Local
#   Area Unemployment statistics: https://download.bls.gov/pub/time.series/la/
#
#   The code produces a .csv with data for:
#       - Employment (level)
#       - Unemployment (level)
#       - Unemployment rate
#       - Labor force (level)
#
#   Data are available monthly from 1990-2017 (can be updated with data from the website above).
#--------------------------------------

import pandas as pd
import requests

#------------------------------------------------------
# Download and save .TXT files from BLS website into current directory

BLS_url = 'https://download.bls.gov/pub/time.series/la/'

filenames = ['la.area',
              'la.data.0.CurrentU90-94', 'la.data.0.CurrentU95-99',
              'la.data.0.CurrentU00-04', 'la.data.0.CurrentU05-09',
              'la.data.0.CurrentU10-14','la.data.0.CurrentU15-19']

for xx in filenames:
    dls = BLS_url+xx
    resp = requests.get(dls)

    output = open(xx+'.txt', 'wb')
    output.write(resp.content)
    output.close()

#------------------------------------------------------
# Import area information
df_areas = pd.read_table('la.area.txt')
df_areas = df_areas[['area_code', 'area_text']]

# Only keep county information
df_areas = df_areas.loc[df_areas['area_code'].str.contains('CN')]
df_areas.reset_index(drop=True, inplace=True)

# Rename columns
df_areas.columns = ['area_code', 'countyname']

# Get county and state information
tmp = df_areas['countyname'].str.split(', ', expand=True)
df_areas['countyname'] = tmp[0]
df_areas['state'] = tmp[1]

# Remove whitespace
df_areas['area_code'] = df_areas['area_code'].map(lambda x: x.strip())
df_areas['countyname'] = df_areas['countyname'].map(lambda x: x.strip())
# df_areas['state'] = df_areas['state'].map(lambda x: x.strip())    # Doesn't work when missing states?


#------------------------------------------------------

def get_BLS_county_data(BLS_data_path, df_areas):
    '''
    BLS_data_path : path for the text file containing the BLS data
    df_areas      : dataframe containing BLS information about counties/areas
    '''
    # Import area information
    col_types = {'series_id': str, 'year': int, 'period': str, 'value': str, 'footnote_codes': str}
    df_bls_county = pd.read_table(BLS_data_path, dtype=col_types)

    # Remove white space from code..
    df_bls_county['series_id'] = df_bls_county['series_id'].map(lambda x: x.strip())

    # Convert 'value' to numeric (kind of slow...)
    df_bls_county['value'] = df_bls_county['value'].apply(pd.to_numeric, errors='coerce')

    # Get variable code
    df_bls_county['var_code'] = df_bls_county['series_id'].str[-2:]

    # Get area code
    df_bls_county['series_id'] = df_bls_county['series_id'].astype(str).str[3:].str[:-2]

    # Get FIPS code (as string to preserve initial zeros)
    df_bls_county['FIPS'] = df_bls_county['series_id'].str[2:7]

    #------------------------------------------------------------
    # Only keep rows corresponding to counties
    df_bls_county = df_bls_county.loc[df_bls_county['series_id'].str.contains('CN')]

    # Drop columns, reset index
    df_bls_county = df_bls_county[['series_id','year','period','value','var_code','FIPS']]
    df_bls_county.reset_index(drop=True, inplace=True)

    # Rename codes with variable names, rename columns
    df_bls_county['var_code'] = df_bls_county['var_code'].map({'03': 'Unemployment_Rate', '04': 'Unemployment',
                                                                 '05': 'Employment', '06': 'Labor_Force'})
    df_bls_county.columns = ['area_code', 'year', 'month', 'value','variable_name', 'FIPS']

    # Drop month 13 (I think this is the year average?)
    df_bls_county = df_bls_county.loc[df_bls_county['month']!='M13']
    # Convert month to numeric values
    df_bls_county['month'] = pd.to_numeric(df_bls_county['month'].str[1:])

    #------------------------------------------------------------
    # Merge area names and data
    df_bls_county = pd.merge(df_bls_county, df_areas, how='inner', on='area_code')

    # Convert to wide-format table
    df_bls_county = df_bls_county.pivot_table(values='value', index=['area_code', 'FIPS', 'state', 'countyname',
                                                            'year', 'month'], columns='variable_name')
    df_bls_county.reset_index(inplace=True)
    df_bls_county.columns.name = None

    #------------------------------------------------------------
    print('Done!')

    return df_bls_county

#------------------------------------------------------------
# Import all years of data
df_unemp_90_94 = get_BLS_county_data('la.data.0.CurrentU90-94.txt', df_areas)
df_unemp_95_99 = get_BLS_county_data('la.data.0.CurrentU95-99.txt', df_areas)
df_unemp_00_04 = get_BLS_county_data('la.data.0.CurrentU00-04.txt', df_areas)
df_unemp_05_09 = get_BLS_county_data('la.data.0.CurrentU05-09.txt', df_areas)
df_unemp_10_14 = get_BLS_county_data('la.data.0.CurrentU10-14.txt', df_areas)
df_unemp_15_19 = get_BLS_county_data('la.data.0.CurrentU15-19.txt', df_areas)

#------------------------------------------------------------
# Merge all year's data
df_unemp_county = df_unemp_90_94
df_unemp_county = df_unemp_county.append(df_unemp_95_99)
df_unemp_county = df_unemp_county.append(df_unemp_00_04)
df_unemp_county = df_unemp_county.append(df_unemp_05_09)
df_unemp_county = df_unemp_county.append(df_unemp_10_14)
df_unemp_county = df_unemp_county.append(df_unemp_15_19)

# Sort by year-month
df_unemp_county = df_unemp_county.sort_values(by=['area_code', 'year', 'month'], axis=0)

# Save to CSV
df_unemp_county[['FIPS', 'state', 'countyname', 'year', 'month',
       'Employment', 'Labor_Force', 'Unemployment', 'Unemployment_Rate']].to_csv('BLS_county_employment.csv', index=False)
