import os
import argparse

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff


def load_data(dir_path):
    # dataframe
    df = pd.DataFrame()

    for filename in os.listdir(dir_path):
        if filename.endswith('.json') and "@@" in filename:
            file_path = os.path.join(dir_path, filename)

            data = pd.read_json(file_path, orient='records')

            # Expand nested columns
            data = pd.json_normalize(data['function'])

            data['source'] = os.path.splitext(filename)[0]

            df = pd.concat([df, data], axis=0)

    return df


def plot(df):
    # Plot 1: API usage by frequency
    function_counts = df['name'].value_counts()
    function_counts = function_counts.sort_values(ascending=True)

    fig1 = go.Figure(data=[go.Bar(
        x=function_counts.values,
        y=function_counts.index,
        orientation='h'
    )])
    fig1.update_layout(
        title='API Usage by Frequency',
        xaxis_title='# of Calls',
        yaxis_title='Function'
    )

    # Plot 2: Client usage by distinct calls
    distinct_calls = df.groupby('source')['name'].nunique()
    distinct_calls = distinct_calls.sort_values(ascending=True)

    fig2 = go.Figure(data=[go.Bar(
        x=distinct_calls.values,
        y=distinct_calls.index,
        orientation='h'
    )])
    fig2.update_layout(
        title='Client Usage by Distinct Calls',
        xaxis_title='# of Distinct Calls',
        yaxis_title='Client'
    )

    # Plot 3: Client usage by frequency
    client_calls = df.groupby('source')['source'].value_counts()
    client_calls = client_calls.sort_values(ascending=True)

    fig3 = go.Figure(data=[go.Bar(
        x=client_calls.values,
        y=client_calls.index,
        orientation='h'
    )])
    fig3.update_layout(
        title='Client Usage by Frequency',
        xaxis_title='# of Calls',
        yaxis_title='Client'
    )

    # Plot 4: Most popular header files by function
    header_counts = df['definition.file'].str.split('/').str[-1].value_counts()
    header_counts = header_counts.sort_values(ascending=True)

    fig4 = go.Figure(data=[go.Bar(
        x=header_counts.values,
        y=header_counts.index,
        orientation='h'
    )])
    fig4.update_layout(
        title='Most Popular Header Files',
        xaxis_title='# of Calls',
        yaxis_title='Header File'
    )

    # Plot 4: Most popular header files by repository
    header_counts = df['definition.file'].str.split('/').str[-1].value_counts()
    header_counts = header_counts.sort_values(ascending=True)

    fig4 = go.Figure(data=[go.Bar(
        x=header_counts.values,
        y=header_counts.index,
        orientation='h'
    )])
    fig4.update_layout(
        title='Most Popular Header Files',
        xaxis_title='# of Calls',
        yaxis_title='Header File'
    )

    # Plot 5: Number of repositories using cmake vs submod
    header_repos_counts = \
    df.groupby(df['definition.file'].apply(lambda x: 'CMake' if 'usr/include' in x else 'Submod'))[
        'source'].nunique()
    header_repos_counts = header_repos_counts.sort_values(ascending=True)

    fig5 = go.Figure(data=[go.Bar(
        x=header_repos_counts.values,
        y=header_repos_counts.index,
        orientation='h',
    )])
    fig5.update_layout(
        title='Most Popular Header Files by Number of Repositories',
        xaxis_title='Number of Repositories',
        yaxis_title='Header File',
    )

    # Number of unique repositories
    num_unique_repos = df['source'].nunique()

    # Number of functions identified in total
    num_total_functions = df.shape[0]

    num_functions_per_repo = df.groupby('source')['name'].count()

    # Average number of functions identified per repository
    avg_num_functions_per_repo = num_functions_per_repo.mean()
    std_dev_avg_num_functions_per_repo = num_functions_per_repo.std()
    median_num_functions_per_repo = num_functions_per_repo.median()
    max_num_functions_per_repo = num_functions_per_repo.max()
    min_num_functions_per_repo = num_functions_per_repo.min()

    # Number of unique functions identified
    num_unique_functions = df['name'].nunique()

    num_unique_functions_per_repo = df.groupby('source')['name'].nunique()
    # Average number of unique functions identified per repository
    avg_num_unique_functions_per_repo = num_unique_functions_per_repo.mean()
    # Average number of unique functions identified per repository
    std_dev_avg_num_unique_functions_per_repo = num_unique_functions_per_repo.std()
    median_num_unique_functions_per_repo = num_unique_functions_per_repo.median()

    table_data = [
        ['Metric', 'Value'],
        ['Number of repositories', num_unique_repos],
        ['Number of functions identified in total', num_total_functions],
        ['Average number of functions identified per repository', avg_num_functions_per_repo],
        ['Standard deviation of average number of functions per repository', std_dev_avg_num_functions_per_repo],
        ['Median number of functions per repository', median_num_functions_per_repo],
        ['Number of unique functions identified', num_unique_functions],
        ['Average number of unique functions identified per repository', avg_num_unique_functions_per_repo],
        ['Standard deviation of average number of unique functions per repository',
         std_dev_avg_num_unique_functions_per_repo],
        ['Median number of unique functions per repository', median_num_unique_functions_per_repo],
    ]

    fig = ff.create_table(table_data)
    fig.show()

    fig = make_subplots(rows=2, cols=4, subplot_titles=[
        'API Usage by Frequency',
        'Client Usage by Distinct Calls',
        'Client Usage by Frequency', '',
        'Most Popular Header Files by Call',
        'Most Popular Install Type by Repository',
    ])

    # Add plots to the subplots
    fig.add_trace(fig1.data[0], row=1, col=1)
    fig.add_trace(fig2.data[0], row=1, col=2)
    fig.add_trace(fig3.data[0], row=1, col=3)
    fig.add_trace(fig4.data[0], row=2, col=1)
    fig.add_trace(fig5.data[0], row=2, col=2)

    fig.update_layout(height=1000, width=2000, showlegend=False)

    fig.show()


def main(dir_path):
    df = load_data(dir_path)
    plot(df)
    plot(df[df['isOverloaded'] == False])
    plot(df[df['isOverloaded']])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process usage data')
    parser.add_argument('dir_path', type=str, help='The directory to be parsed')
    args = parser.parse_args()
    main(args.dir_path)
