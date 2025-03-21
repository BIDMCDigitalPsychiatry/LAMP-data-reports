# report_generator.py

import os
import os
import sys
import datetime
import time
import pytz
import calplot
import pandas as pd
from matplotlib.patches import Patch
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import ttest_ind, pearsonr

import os
from dotenv import load_dotenv

load_dotenv()

access_key = os.getenv("LAMP_ACCESS_KEY")
secret_key = os.getenv("LAMP_SECRET_KEY")
server_address = os.getenv("LAMP_SERVER_ADDRESS")

if not all([access_key, secret_key, server_address]):
    raise ValueError("Missing one or more required environment variables.")

import LAMP
LAMP.connect()

import cortex
import numpy as np
import altair as alt
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')
import logging
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)
logging.basicConfig(level=3)
logging.getLogger('matplotlib').disabled = True
logging.getLogger('matplotlib.font_manager').disabled = True
logging.getLogger('matplotlib.pyplot').disabled = True
logging.getLogger('shapely.geos').disabled = True
logging.getLogger('numexpr.utils').disabled = True
logging.getLogger('feature_types:_wrapper2').disabled = True
from IPython.display import display, Markdown
import plotly.graph_objects as go
import plotly.offline as pyo
from datetime import datetime, timezone, timedelta
from plotly.subplots import make_subplots
from IPython.display import display, HTML

import pdfkit
import plotly.io as pio
import plotly.tools as tls
import io
import base64


starting_time = time.time()

MS_IN_DAY = 24 * 3600 * 1000

import argparse

# Initialize argument parser
parser = argparse.ArgumentParser(description="Generate a report.")

# Define arguments
parser.add_argument("--participant_id", required=True, help="Participant ID")
parser.add_argument("--start_date", required=True, help="Start date for the report")
parser.add_argument("--output_format", required=True, choices=["html", "pdf"], help="Output format")
parser.add_argument("--output_path", required=True, help="Path to save the output file")

# Parse arguments
args = parser.parse_args()

# Assign variables
participant_id = args.participant_id
start_date = args.start_date
output_format = args.output_format
output_path = args.output_path


part = participant_id
start = start_date


run_sleep=False
# default end date is now
end_date = cortex.now()


def timestamp(dt):
    local = pytz.timezone("America/New_York")
    date = datetime.strptime(dt, '%Y-%m-%d')
    local_dt = local.localize(date, is_dst=None)
    utc_dt = local_dt.astimezone(pytz.utc)
    utc_dt.replace(tzinfo=timezone.utc).timestamp() * 1000
    return int(utc_dt.replace(tzinfo=timezone.utc).timestamp() * 1000)

start_date = timestamp(start)


# This document presents the data that was collected during your time during the social media study. You can keep this document for your records or use it as a reference when working with a new clinician or health provider. Feel free to reach out to the study team (jburns9@bidmc.harvard.edu) with any questions.

# This graph shows the activities that you completed each day. Dates are along the x-axis, while the y-axis shows how many activities you completed that day, and the colors on the bars designate the activity names.


# ### Quick notes about interpreting correlations:
# 
# - The numbers and colors correspond to the strength of the relationship. A correlation of -1 indicates a perfect negative relationship (as one variable increases the other variable decreases), and a correlation of 1 indicates a perfect positive relationship (both variables are increasing or decreasing).
# - A correlation of 0 means there is no linear relationship. However, just because a correlation is 0 does not necessarily mean there is no relationship there. There is always the possibility two variables have a nonlinear relationship.
# - Correlation does not equal causation. This graph cannot show that one variable causes a change in another variable, only how changes in variables are associated with each other.
# 
# Potential example of interpreting this graph: Maybe you have a negative correlation between mood and steps. A negative correlation indicates that on days when your steps are higher, your mood is higher/better. Questions to think about: How does going on a walk make you feel? Do you usually feel better, worse, or about the same after you go on walks?



score_dict = {'category_list': ['Daily Mood Survey', 'Daily Anxiety Survey', 'Daily Function Survey', 'Daily SM Survey'],
                    'questions': {
                    'Overall, how would you rate your mood today?': {'category': 'Daily Mood Survey', 'scoring':'M_map'},
                    'Overall, how would I rate my anxiety today?': {'category': 'Daily Anxiety Survey', 'scoring':'A_map'},
                    'I am able to manage my day-to-day life': {'category': 'Daily Function Survey', 'scoring':'F_map'},
                    'Without checking your screentime, how much time would you say you spent on social media networks on your phone today? (SCROLL TO VIEW ALL RESPONSE OPTIONS))': {'category': 'Daily SM Survey', 'scoring':'A_map'},
                    },
                    'A_map': {
                        '10': 10,
                        '9': 9,
                        '8': 8,
                        '7': 7,
                        '6': 6, 
                        '5': 5, 
                        '4': 4, 
                        '3': 3,
                        '2': 2,
                        '1': 1,
                        '0': 0,
                    },
                            'M_map': {
                        '10': 0,
                        '9': 1,
                        '8': 2,
                        '7': 3,
                        '6': 4, 
                        '5': 5, 
                        '4': 6, 
                        '3': 7,
                        '2': 8,
                        '1': 9,
                        '0': 10,
                    },
                    'F_map': {
                        '4': 0,
                        '3': 1,
                        '2': 2,
                        '1': 3,
                        '0': 4}
                    }



#Pulling passive data
try:
    passive = cortex.run(part,
                            ['screen_duration','nearby_device_count', 'entropy', 'data_quality', 'hometime', 'steps'],
                            feature_params={'screen_duration': {}, 'entropy': {},
                            'data_quality': {"feature":"gps", "bin_size":3600000}},
                            start=start_date,
                            end=end_date)
except Exception as e:
    passive = cortex.run(part,
                            ['screen_duration', 'nearby_device_count','entropy', 'data_quality', 'hometime'],
                            feature_params={'screen_duration': {}, 'entropy': {},
                            'data_quality': {"feature":"gps", "bin_size":3600000}},
                            start=start_date,
                            end=end_date)



passive_df = pd.DataFrame()
for key in passive:
    if key != 'steps':
        passive_df[key] = passive[key]['value']
        passive_df['date'] = passive[key]['timestamp']
    else:
        if passive[key].empty:
            continue
        else:
            step_df = passive[key]
            step_df = step_df[step_df['type'] == 'step_count']
            step_df['timestamp'] = pd.to_datetime(step_df['timestamp'], errors='coerce')  # Convert to datetime
            step_df['date'] = step_df['timestamp'].dt.date
            step_df = step_df.groupby('date')['value'].max().reset_index()
            passive_df['steps'] = step_df['value']

if 'steps' in passive_df:
    passive_df = passive_df[['date', 'screen_duration', 'entropy', 'data_quality', 'hometime', 'steps']]
else:
    passive_df = passive_df[['date', 'screen_duration', 'entropy', 'data_quality', 'hometime']]





daily_dict_responses = cortex.primary.survey_scores.survey_scores(id=part,
                                                        start=start_date,
                                                        end=end_date,
                                                        return_ind_ques=1,
                                                        scoring_dict=score_dict)
response_data = daily_dict_responses['data']
function = []
anxiety = []
mood = []
sm = []
est = pytz.timezone('US/Eastern')

for item in response_data:
    if item['question'] == "Daily Function Survey":
        function.append({'score':item['score'], 'date':item['end']})
    if item['question'] == "Daily Anxiety Survey":
        anxiety.append({'score':item['score'], 'date':item['end']})
    if item['question'] == "Daily Mood Survey":
        mood.append({'score':item['score'], 'date':item['end']})
    if item['question'] == "Daily SM Survey":
        sm.append({'score':item['score'], 'date':item['end']})


for dictionary in function:
    dictionary['date'] = datetime.fromtimestamp(dictionary['date']/1000, tz=timezone.utc)
    dictionary['date'] = dictionary['date'].astimezone(est).date()


for dictionary in anxiety:
    dictionary['date'] = datetime.fromtimestamp(dictionary['date']/1000, tz=timezone.utc)
    dictionary['date'] = dictionary['date'].astimezone(est).date()

for dictionary in mood:
    dictionary['date'] = datetime.fromtimestamp(dictionary['date']/1000, tz=timezone.utc)
    dictionary['date'] = dictionary['date'].astimezone(est).date()

for dictionary in sm:
    dictionary['date'] = datetime.fromtimestamp(dictionary['date']/1000, tz=timezone.utc)
    dictionary['date'] = dictionary['date'].astimezone(est).date()


daily_df_function = pd.DataFrame(function)
daily_df_anxiety = pd.DataFrame(anxiety)
daily_df_mood = pd.DataFrame(mood)
daily_df_sm = pd.DataFrame(sm)




passive_df['date'] = pd.to_datetime(passive_df['date'], unit='ms')

passive_df['date'] = passive_df['date'].dt.tz_localize('UTC')

passive_df['date'] = passive_df['date'].dt.tz_convert('US/Eastern')

passive_df['date'] = passive_df['date'].apply(lambda x: x.date())

if len(daily_df_function) > 0:
    daily_df_function = daily_df_function.groupby('date')['score'].mean().reset_index()
    daily_df_function = daily_df_function.rename(columns=({'score':'difficulty functioning'}))
    passive_df = passive_df.merge(daily_df_function, on=['date'], how='left')

if len(daily_df_anxiety) > 0:
    daily_df_anxiety = daily_df_anxiety.groupby('date')['score'].mean().reset_index()
    daily_df_anxiety = daily_df_anxiety.rename(columns=({'score':'anxiety'}))
    passive_df = passive_df.merge(daily_df_anxiety, on=['date'], how='left')

if len(daily_df_mood) > 0:
    daily_df_mood = daily_df_mood.groupby('date')['score'].mean().reset_index()
    daily_df_mood = daily_df_mood.rename(columns=({'score':'depression'}))
    passive_df = passive_df.merge(daily_df_mood, on=['date'], how='left')

if len(daily_df_sm) > 0:
    daily_df_sm = daily_df_sm.groupby('date')['score'].mean().reset_index()
    daily_df_sm = daily_df_sm.rename(columns=({'score':'Social Media Use'}))
    passive_df = passive_df.merge(daily_df_sm, on=['date'], how='left')


passive_df['screen_duration'] = passive_df['screen_duration'].replace(0, np.nan)
passive_df['entropy'] = passive_df['entropy'].replace(0, np.nan)


try:
    sleep_df['date'] = sleep_df['timestamp'].apply(lambda x: x.strftime('%Y-%m-%d'))
    sleep_df = sleep_df[['date', 'hours']]
    sleep_df.columns = ['date', 'sleep duration']
    passive_df = pd.merge(passive_df, sleep_df, on=['date'])
    passive_df['sleep duration'] = passive_df['sleep duration'].astype(float)

except:
    pass

passive_df['date'] = passive_df['date'].astype(object)
cor_data = (passive_df.corr(min_periods=5).stack()
        .reset_index()   
        .rename(columns={0: 'correlation', 'level_0': 'variable', 'level_1': 'variable2'}))
cor_data['correlation_label'] = cor_data['correlation'].map('{:.2f}'.format)  # Round to 2 decimal


cor_data = cor_data[cor_data['correlation'] != 1.00]

cor_data = cor_data[cor_data['correlation'] != -1.00]

base = alt.Chart(cor_data).transform_filter(
alt.datum.variable > alt.datum.variable2
).encode(
    x='variable2:O',
    y='variable:O'    
)

text = base.mark_text().encode(
    text='correlation_label',
    color=alt.condition(
        alt.datum.correlation > 0.5, 
        alt.value('white'),
        alt.value('black')
    )
)


cor_plot = base.mark_rect().encode(
    color='correlation:Q'
).properties(
    width=300,
    height=200
)
cor_matrix = cor_plot + text



cor_matrix


# ### Daily Survey Scores and Passive Data Features (Nearby Devices, Hometime, Screentime, Entropy)
# 
# The below graphs display passive data features collected from your smarphone with your scores on your daily surveys measuring anxiety, function, and mood. The scale for the passive data features is on the left y-axis, and the scale for the daily surveys is on the right y-axis side. The goal of these graphs is to help display patterns between your passive data features and routines with your mood, anxiety, and function levels.
# 
# For example, you may see that for days on which you were on your phone screen more, your mood was typically higher.
# 
# * NOTE: Higher anxiety levels correspond with increased anxiety; 0 being no anxiety and 10 being the worst. Higher mood levels correspond with a better mood; 1 being the worst and 10 being the best. Higher function levels correspond with feeling like you are more able to manage day-to-day life on a scale of 0 to 4.
# 
# Entropy is a measure of how much a participant moves around to different locations. Higher entropy typically means that the participant's time is more evenly split between different locations, while low entropy means that a person spends the vast majority of their time at one location.
# 
# Nearby devices is a measure of, if your phone is turned on and connected to bluetooth, how many devices around you are also turned on and connected to bluetooth. It can be used as a measure of sociability. For example, if you are spending a lot of time in spaces with lots of people, like a concert or a busy coffee shop, there will be more people and devices around you.



passive_df.rename(columns = {'difficulty functioning':'dysfunction'}, inplace = True)
passive_df['screen_duration'] = passive_df['screen_duration']/3600000
passive_df['hometime'] = passive_df['hometime']/3600000

def generate_visibility(option_position, total_options, traces_per_option):
    return [True if i // traces_per_option == option_position else False for i in range(total_options * traces_per_option)]

x = passive_df['date']
dep_line = passive_df['depression']
anx_line = passive_df['anxiety']
fxn_line = passive_df['dysfunction']

# Create figure with secondary y-axis
daily_fig = make_subplots(specs=[[{"secondary_y": True}]])
# OPTION 1 = Screentime!!!
daily_fig.add_trace(go.Bar(x=passive_df['date'], y=passive_df['screen_duration'], visible=True, marker=dict(color='#CCE5FF'), name='Screentime'), secondary_y=False)

daily_fig.add_trace(go.Scatter(x=x, y=dep_line, mode='lines+markers', connectgaps=True, line=dict(width=2), visible=True, name='Depression'), secondary_y=True)
daily_fig.add_trace(go.Scatter(x=x, y=anx_line, mode='lines+markers', connectgaps=True, visible=True, name='Anxiety'), secondary_y=True)
daily_fig.add_trace(go.Scatter(x=x, y=fxn_line, mode='lines+markers', connectgaps=True, visible=True, name='Difficulty Functioning'), secondary_y=True)

# OPTION 2 = Hometime!!!
daily_fig.add_trace(go.Bar(x=passive_df['date'], y=passive_df['hometime'], visible=False, marker=dict(color='#CCCCFF'), name='Hometime'), secondary_y=False)

daily_fig.add_trace(go.Scatter(x=x, y=dep_line, mode='lines+markers', connectgaps=True, line=dict(width=2), visible=False, name='Depression'), secondary_y=True)
daily_fig.add_trace(go.Scatter(x=x, y=anx_line, mode='lines+markers', connectgaps=True, visible=False, name='Anxiety'), secondary_y=True)
daily_fig.add_trace(go.Scatter(x=x, y=fxn_line, mode='lines+markers', connectgaps=True, visible=False, name='Difficulty Functioning'), secondary_y=True)

# Option 3 = Entropy
daily_fig.add_trace(go.Bar(x=passive_df['date'], y=passive_df['entropy'], visible=False, marker=dict(color='#CCFF99'), name='Entropy'), secondary_y=False)

daily_fig.add_trace(go.Scatter(x=x, y=dep_line, mode='lines+markers', connectgaps=True, line=dict(width=2), visible=False, name='Depression'), secondary_y=True)
daily_fig.add_trace(go.Scatter(x=x, y=anx_line, mode='lines+markers', connectgaps=True, visible=False, name='Anxiety'), secondary_y=True)
daily_fig.add_trace(go.Scatter(x=x, y=fxn_line, mode='lines+markers', connectgaps=True, visible=False, name='Difficulty Functioning'), secondary_y=True)

try:
    ppl = cortex.secondary.nearby_device_count.nearby_device_count(id=part, start=start_date,
                                                                    end=end_date, resolution=86400000)['data']
    new_dict = {}
    for timestamp in ppl['data']:
        new_dict[(datetime.fromtimestamp(timestamp['timestamp'] / 1000)).date()] = timestamp['value']

    df = pd.Series(new_dict)
    df = pd.DataFrame(df.reset_index())
    df.rename(columns={'index': 'timestamp', 0: 'value'}, inplace=True)

    # adding nearby_devices OPTION 4
    daily_fig.add_trace(go.Bar(x=df['timestamp'], y=df['value'], visible=False, marker=dict(color='#FFCC99'), name='Nearby Devices'), secondary_y=False)

    daily_fig.add_trace(go.Scatter(x=x, y=dep_line, mode='lines+markers', connectgaps=True, line=dict(width=2), visible=False, name='Depression'), secondary_y=True)
    daily_fig.add_trace(go.Scatter(x=x, y=anx_line, mode='lines+markers', connectgaps=True, visible=False, name='Anxiety'), secondary_y=True)
    daily_fig.add_trace(go.Scatter(x=x, y=fxn_line, mode='lines+markers', connectgaps=True, visible=False, name='Difficulty Functioning'), secondary_y=True)


    daily_fig.update_layout(
        updatemenus=[
            dict(
                type="dropdown",
                x=1.3,
                y=0.5,
                showactive=True,
                buttons=list([
                    dict(label="Screentime",
                        method="update",
                        args=[{"visible": generate_visibility(0, 4, 4)},
                            {"title": "Screentime"}]),
                    dict(label="Hometime",
                        method="update",
                        args=[{"visible": generate_visibility(1, 4, 4)},
                            {"title": "Hometime"}]),
                    dict(label="Entropy",
                        method="update",
                        args=[{"visible": generate_visibility(2, 4, 4)},
                            {"title": "Entropy"}]),
                    dict(label="Nearby Devices",
                        method="update",
                        args=[{"visible": generate_visibility(3, 4, 4)},
                            {"title": "Nearby Devices"}])
                ]),
            )
        ])
except Exception as e:
    print(f"Error: {e}")
    daily_fig.update_layout(
        updatemenus=[
            dict(
                type="dropdown",
                x=1.3,
                y=0.5,
                showactive=True,
                buttons=list([
                    dict(label="Screentime",
                        method="update",
                        args=[{"visible": generate_visibility(0, 3, 4)},
                            {"title": "Screentime"}]),
                    dict(label="Hometime",
                        method="update",
                        args=[{"visible": generate_visibility(1, 3, 4)},
                            {"title": "Hometime"}]),
                    dict(label="Entropy",
                        method="update",
                        args=[{"visible": generate_visibility(2, 3, 4)},
                            {"title": "Entropy"}])
                ]),
            )
        ])

# Set y-axes titles
daily_fig.update_yaxes(title_text="<b>Survey Score</b>", secondary_y=True)
daily_fig.update_yaxes(title_text="<b>Time/Number</b>", secondary_y=False)



# ### Steps, shown overlaid with daily anxiety, function, and mood scores.
# 
# Steps are the number of steps you have taken each day, measured using your phone's accelerometer or health app.


try:
    matplotlib.rc_file_defaults()
    import matplotlib.dates as mdates

    sns.set_style(style=None, rc=None)

    step_fig, ax1 = plt.subplots(figsize=(12,6))  # Renamed figure to step_fig
    plt.xticks(rotation=45)

    sns.barplot(data=passive_df, x='date', y='steps', alpha=0.5, ax=ax1, color='lightsalmon')

    ax2 = ax1.twinx()
    plt.ylim(0, 10)
    sns.lineplot(data=passive_df['anxiety'], marker='o', sort=False, ax=ax2, label='Anxiety', color='blueviolet')
    sns.lineplot(data=passive_df['dysfunction'], marker='o', sort=False, ax=ax2, label='Difficulty Functioning', color='firebrick')
    sns.lineplot(data=passive_df['depression'], marker='o', sort=False, ax=ax2, label='Depression', color='cornflowerblue')

    ax2.set_ylabel('Survey Score')
    ax1.set_ylabel('Steps')
    ax1.set_xlabel('Date')
    ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))

    colors = {'Steps': 'lightsalmon', 'Anxiety': 'blueviolet',
            'Difficulty Functioning': 'firebrick', 'Depression': 'cornflowerblue'}
    labels = list(colors.keys())
    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[label]) for label in labels]
    plt.legend(handles, labels)
except:
    print('No step data for this participant. Maybe participant has low data quality or an Android.')



# ### Calendar View

# These calendars show heatmaps of all of your passive and active variables collected over your time in the clinic. The month is listed on the bottom, the day of the week is shown on the right, and there is a heat map scale on the far right showing the minimum and maximum values for each variable with the corresponding colors.
# 
# The goal of these graphs is to help pick up on patterns in passive or active data over time, as well as to pick out what days may have been unusual in terms of passive or active data values.

# #### Entropy



final_df = passive_df

# ---- Entropy Calendar Plot ----
entropy_data = final_df[['date', 'entropy']]
entropy_data['date'] = pd.to_datetime(entropy_data['date'], yearfirst=True)
entropy_data.set_index('date', inplace=True)
entropy_fig_cal = calplot.calplot(entropy_data['entropy'], textfiller='-', dropzero=True)

# ---- Hometime Calendar Plot ----
hometime_data = final_df[['date', 'hometime']]
hometime_data['date'] = pd.to_datetime(hometime_data['date'], yearfirst=True)
hometime_data.set_index('date', inplace=True)
hometime_fig_cal = calplot.calplot(hometime_data['hometime'], textfiller='-', dropzero=True)

# ---- Data Quality Calendar Plot ----
data_quality_data = final_df[['date', 'data_quality']]
data_quality_data['date'] = pd.to_datetime(data_quality_data['date'], yearfirst=True)
data_quality_data.set_index('date', inplace=True)
data_quality_fig_cal = calplot.calplot(data_quality_data['data_quality'], textfiller='-', dropzero=True)

# ---- Screen Duration Calendar Plot ----
screen_duration_data = final_df[['date', 'screen_duration']]
screen_duration_data['date'] = pd.to_datetime(screen_duration_data['date'], yearfirst=True)
screen_duration_data.set_index('date', inplace=True)
screen_duration_fig_cal = calplot.calplot(screen_duration_data['screen_duration'], textfiller='-', dropzero=True)

# ---- Steps Calendar Plot ----
try:
    steps_data = final_df[['date', 'steps']]
    steps_data['date'] = pd.to_datetime(steps_data['date'], yearfirst=True)
    steps_data.set_index('date', inplace=True)
    steps_fig_cal = calplot.calplot(steps_data['steps'], textfiller='-', dropzero=True)
except:
    print('No step data for this participant.')

# ---- Anxiety Calendar Plot ----
anxiety_data = final_df[['date', 'anxiety']]
anxiety_data['date'] = pd.to_datetime(anxiety_data['date'], yearfirst=True)
anxiety_data.set_index('date', inplace=True)
anxiety_fig_cal = calplot.calplot(anxiety_data['anxiety'], textfiller='-', dropzero=True)

# ---- Depression Calendar Plot ----
depression_data = final_df[['date', 'depression']]
depression_data['date'] = pd.to_datetime(depression_data['date'], yearfirst=True)
depression_data.set_index('date', inplace=True)
depression_fig_cal = calplot.calplot(depression_data['depression'], textfiller='-', dropzero=True)

# ---- Dysfunction Calendar Plot ----
dysfunction_data = final_df[['date', 'dysfunction']]
dysfunction_data['date'] = pd.to_datetime(dysfunction_data['date'], yearfirst=True)
dysfunction_data.set_index('date', inplace=True)
dysfunction_fig_cal = calplot.calplot(dysfunction_data['dysfunction'], textfiller='-', dropzero=True)



# #### Data Quality Over the Past Week



data_qual=cortex.secondary.data_quality.data_quality(id=part, start=cortex.now()-7*MS_IN_DAY, 
                                                    end=cortex.now(), resolution=86400000, 
                                                    feature='accelerometer', bin_size=10000)['data']
#dq of the last week~! 
import plotly.graph_objects as go
last_week=data_qual[-7:]
dq=[day['value'] for day in last_week]
avg_dq=sum(dq)/7
dqwheel_fig = go.Figure(go.Indicator(
    domain = {'x': [0, 1], 'y': [0, 1]},
    value = avg_dq,
    # mode = "gauge+number+delta",
    mode='gauge+number',
    title = {'text': "Average Data Quality in the Past Week"},
    delta = {'reference': .44},
    gauge = {'axis': {'range': [None, 1]},
            'bar': {'color': "black", 'line': {'color':'red', 'width':0}, 'thickness': .1},
            'shape': 'angular',
            'steps' : [
                {'range': [0, .35], 'color': "#E74C3C"},
                {'range': [.35, .6], 'color': "#F4D03F"},
                {'range': [.6, .8], 'color': "#27AE60"},
                {'range': [.8, 1], 'color': "#2471A3"}]}))


# Generate HTML for figures
correlation_matrix_html = cor_matrix.to_html()
daily_scores_html = pio.to_html(daily_fig, full_html=False)


def fig_to_html(fig):
    """Convert a Matplotlib figure to a base64-encoded HTML image tag."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    encoded_fig = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    return f'<img src="data:image/png;base64,{encoded_fig}">'

# Generate and convert figures to HTML
entropy_fig_cal, _ = calplot.calplot(entropy_data['entropy'], textfiller='-', dropzero=True)
entropy_fig_cal_html = fig_to_html(entropy_fig_cal)

hometime_fig_cal, _ = calplot.calplot(hometime_data['hometime'], textfiller='-', dropzero=True)
hometime_fig_cal_html = fig_to_html(hometime_fig_cal)

data_quality_fig_cal, _ = calplot.calplot(data_quality_data['data_quality'], textfiller='-', dropzero=True)
data_quality_fig_cal_html = fig_to_html(data_quality_fig_cal)

screen_duration_fig_cal, _ = calplot.calplot(screen_duration_data['screen_duration'], textfiller='-', dropzero=True)
screen_duration_fig_cal_html = fig_to_html(screen_duration_fig_cal)

steps_fig_cal, _ = calplot.calplot(steps_data['steps'], textfiller='-', dropzero=True)
steps_fig_cal_html = fig_to_html(steps_fig_cal)

anxiety_fig_cal, _ = calplot.calplot(anxiety_data['anxiety'], textfiller='-', dropzero=True)
anxiety_fig_cal_html = fig_to_html(anxiety_fig_cal)

depression_fig_cal, _ = calplot.calplot(depression_data['depression'], textfiller='-', dropzero=True)
depression_fig_cal_html = fig_to_html(depression_fig_cal)

dysfunction_fig_cal, _ = calplot.calplot(dysfunction_data['dysfunction'], textfiller='-', dropzero=True)
dysfunction_fig_cal_html = fig_to_html(dysfunction_fig_cal)

dqwheel_fig = pio.to_html(dqwheel_fig, full_html=False)

steps_graph_html = fig_to_html(step_fig)

# Create the complete HTML content
html_content = f"""
<html>
<head>
    <title>Report</title>
</head>
<body>
    <h1>Participant Report</h1>
    <p>This document presents the data that was collected during your time during the social media study. You can keep this document for your records or use it as a reference when working with a new clinician or health provider. Feel free to reach out to the study team (jburns9@bidmc.harvard.edu) with any questions.</p>
    <h2>Correlation Matrix</h2>
    {correlation_matrix_html}
    <h2>Daily Survey Scores and Passive Data Features</h2>
    {daily_scores_html}
    <h2>Steps</h2>
    {steps_graph_html}
    <h2>Calendar View</h2>
    <p>---- Entropy Calendar Plot ----</p>
    {entropy_fig_cal_html}
    <p>---- Hometime Calendar Plot ----</p>
    {hometime_fig_cal_html}
    <p>---- Data Quality Calendar Plot ----</p>
    {data_quality_fig_cal_html}
    <p>---- Screen Duration Calendar Plot ----</p>
    {screen_duration_fig_cal_html}
    <p>---- Steps Calendar Plot ----</p>
    {steps_fig_cal_html}
    <p>---- Anxiety Calendar Plot ----</p>
    {anxiety_fig_cal_html}
    <p>---- Depression Calendar Plot ----</p>
    {depression_fig_cal_html}
    <p>---- Dysfunction Calendar Plot ----</p>
    {dysfunction_fig_cal_html}
    <h2>Data Quality for the past week<h2>
    {dqwheel_fig}
</body>
</html>
"""

# Save the HTML content to a file
with open(output_path, "w") as file:
    file.write(html_content)