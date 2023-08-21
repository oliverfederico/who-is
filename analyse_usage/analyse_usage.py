import os
import argparse

from dash import Dash, html, dash_table, dcc, callback, Output, Input
import pandas as pd
import plotly.express as px


def load_library(dir_path):
    df = pd.DataFrame()

    for filename in os.listdir(dir_path):
        if filename.endswith('.json') and "@@" in filename:
            file_path = os.path.join(dir_path, filename)

            data = pd.read_json(file_path)

            # Expand nested columns
            data = pd.json_normalize(data['function'])
            data.dropna(axis=1, inplace=True, how='all')

            data['source'] = os.path.splitext(filename)[0]

            df = pd.concat([df, data], axis=0)

    return df


def load_libraries(dir_path):
    df = pd.DataFrame()
    libraries = []
    # Iterate through the library directories
    for library_name in os.listdir(dir_path):
        library_path = os.path.join(dir_path, library_name)

        # Check if it's a directory
        if os.path.isdir(library_path):
            lib_df = load_library(library_path)
            lib_df['library'] = library_name
            libraries.append(library_name)
            df = pd.concat([df, lib_df], axis=0)
    return df, libraries


def main(dir_path):
    df, libraries = load_libraries(dir_path)

    app = Dash(__name__)

    # App layout
    app.layout = html.Div([
        html.H1(children='API Usage Visualisation'),
        html.Hr(),
        html.H5(children='Please select libraries to study:'),
        dcc.Dropdown(id='library-dropdown', options=libraries, multi=True),

        html.H6(children='Repositories selected:'),
        dcc.Dropdown(id='repository-dropdown', multi=True),
        dcc.RadioItems(options=[
            {'label': 'All', 'value': 'all'},
            {'label': 'Overloaded', 'value': 'overloaded'},
            {'label': 'Not Overloaded', 'value': 'not-overloaded'}], value='all', id='function-filter-radio-item'),
        html.Div(children=[
            html.Div(children=[
                dcc.Graph(figure={}, id='api-usage-frequency')], style={'overflowY': 'scroll', 'height': '800px'}),
            dash_table.DataTable(data=[], columns=[{'name': 'Metric', 'id': 'Metric'},
                                                   {'name': 'Value', 'id': 'Value', 'type': 'numeric',
                                                    'format': {'specifier': '.2f'}}],
                                 id='data-summary-table')
        ], style={'display': 'flex'}),
        html.Div(children=[
            html.Div(children=[
                dcc.Graph(figure={}, id='client-usage-frequency'),
            ], style={'overflowY': 'scroll', 'height': '800px'}),
            html.Div(children=[
                dcc.Graph(figure={}, id='client-usage-distinct')
            ], style={'overflowY': 'scroll', 'height': '800px'}),
        ], style={'display': 'flex'}),
        html.Div(children=[
            html.Div(children=[
                dcc.Graph(figure={}, id='header-usage')
            ], style={'overflowY': 'scroll', 'height': '800px'}),
            html.Div(children=[
                dcc.Graph(figure={}, id='install-usage')
            ], style={'display': 'flex'})
        ], style={'display': 'flex'}),
        html.H6(children='Select Method:'),
        dcc.Dropdown(id='method-dropdown', multi=False),
        html.Div(children=[
            dcc.Graph(figure={}, id='method-freq')
        ], style={'display': 'flex'}),
        html.Div(id='method-args', style={'display': 'block'})
    ])

    @callback(
        [Output(component_id='function-filter-radio-item', component_property='value', allow_duplicate=True),
         Output(component_id='method-dropdown', component_property='value', allow_duplicate=True),
         Output(component_id='repository-dropdown', component_property='value')],
        Input(component_id='library-dropdown', component_property='value'), prevent_initial_call=True
    )
    def reset_overload_option(selected_libraries):
        repos = df[df['library'].isin(selected_libraries)]['source'].unique().tolist()
        return "all", None, repos

    @callback(
        [Output(component_id='method-dropdown', component_property='value', allow_duplicate=True),
         Output(component_id='function-filter-radio-item', component_property='value')],
        Input(component_id='repository-dropdown', component_property='value'), prevent_initial_call=True
    )
    def reset_repo_option(value):
        return None, "all"

    @callback(
        Output(component_id='method-dropdown', component_property='value'),
        Input(component_id='function-filter-radio-item', component_property='value'), prevent_initial_call=True
    )
    def reset_function_option(value):
        return None

    @callback(
        [Output(component_id='api-usage-frequency', component_property='figure'),
         Output(component_id='client-usage-distinct', component_property='figure'),
         Output(component_id='client-usage-frequency', component_property='figure'),
         Output(component_id='header-usage', component_property='figure'),
         Output(component_id='install-usage', component_property='figure'),
         Output(component_id='function-filter-radio-item', component_property='options'),
         Output(component_id='data-summary-table', component_property='data'),
         Output(component_id='method-dropdown', component_property='options'),
         Output(component_id='method-freq', component_property='figure'),
         Output(component_id='method-args', component_property='children'),
         Output(component_id='repository-dropdown', component_property='options')],
        [Input(component_id='function-filter-radio-item', component_property='value'),
         Input(component_id='library-dropdown', component_property='value'),
         Input(component_id='method-dropdown', component_property='value'),
         Input(component_id='repository-dropdown', component_property='value')], prevent_initial_call=True
    )
    def update_bar_chart(overflow_filter, selected_libraries, selected_method, selected_repos):
        filtered_df = df[df['library'].isin(selected_libraries) & df['source'].isin(selected_repos)]

        has_overloaded = filtered_df['isOverloaded'].any()

        # If there are 'Overloaded' values, include the option
        if has_overloaded:
            options = [{'label': 'All', 'value': 'all'},
                       {'label': 'Overloaded', 'value': 'overloaded'},
                       {'label': 'Not Overloaded', 'value': 'not-overloaded'}]
        else:
            options = [{'label': 'All', 'value': 'all'}]

        if overflow_filter == 'overloaded':
            filtered_df = filtered_df[filtered_df['isOverloaded']]
        elif overflow_filter == 'not-overloaded':
            filtered_df = filtered_df[filtered_df['isOverloaded'] == False]

        # Number of unique repositories
        num_unique_repos = filtered_df['source'].nunique()

        repos = filtered_df['source'].unique().tolist()

        # Number of functions identified in total
        num_total_functions = filtered_df.shape[0]

        num_functions_per_repo = filtered_df.groupby('source')['name'].count()

        # Average number of functions identified per repository
        avg_num_functions_per_repo = num_functions_per_repo.mean()
        std_dev_avg_num_functions_per_repo = num_functions_per_repo.std()
        median_num_functions_per_repo = num_functions_per_repo.median()

        # Number of unique functions identified
        num_unique_functions = filtered_df['name'].nunique()

        num_unique_functions_per_repo = filtered_df.groupby('source')['name'].nunique()
        # Average number of unique functions identified per repository
        avg_num_unique_functions_per_repo = num_unique_functions_per_repo.mean()
        # Average number of unique functions identified per repository
        std_dev_avg_num_unique_functions_per_repo = num_unique_functions_per_repo.std()
        median_num_unique_functions_per_repo = num_unique_functions_per_repo.median()

        table_data = [
            {'Metric': 'Number of repositories', 'Value': num_unique_repos},
            {'Metric': 'Number of functions identified in total', 'Value': num_total_functions},
            {'Metric': 'Average number of functions identified per repository', 'Value': avg_num_functions_per_repo},
            {'Metric': 'Standard deviation of average number of functions per repository',
             'Value': std_dev_avg_num_functions_per_repo},
            {'Metric': 'Median number of functions per repository', 'Value': median_num_functions_per_repo},
            {'Metric': 'Number of distinct functions identified', 'Value': num_unique_functions},
            {'Metric': 'Average number of distinct functions identified per repository',
             'Value': avg_num_unique_functions_per_repo},
            {'Metric': 'Standard deviation of average number of distinct functions per repository',
             'Value': std_dev_avg_num_unique_functions_per_repo},
            {'Metric': 'Median number of unique functions per repository',
             'Value': median_num_unique_functions_per_repo},
        ]

        dff = (filtered_df.groupby(['name', 'library'])
               .size()
               .reset_index(name='count')
               .sort_values(by='count', ascending=True))

        methods = filtered_df[filtered_df['args.0.type'].notna()]['name'].unique().tolist()
        if selected_method is None:
            selected_method = methods[0]

        fig1 = px.bar(dff, x='count', y='name', title="API Call Frequency", log_x=True, color='library',
                      barmode='overlay')
        height = max(800, len(dff.values) * 20)
        fig1.update_layout(
            xaxis_title='Frequency',
            yaxis_title='API Call',
            height=height,
            width=950,
            showlegend=True
        )

        method_df = filtered_df[filtered_df['name'] == selected_method]
        method_df.dropna(axis=1, inplace=True, how='all')
        # Filter columns based on substring
        filtered_columns = [col for col in method_df.columns if '.type' in col and 'args.' in col]
        conf_df = method_df[filtered_columns]
        # Convert the argument configuration into a string for plotting, excluding 'nan'
        conf_df['arg_types'] = conf_df[filtered_columns].apply(
            lambda row: ', '.join([str(x) for x in row if str(x) != 'nan']),
            axis=1)

        # Count the frequency of each argument configuration
        dff = conf_df['arg_types'].value_counts().reset_index()
        dff.columns = ['arg_types', 'count']
        method_fig = px.bar(dff, x='arg_types', y='count',
                            title=f"'{selected_method}' Method Argument Type Configurations")
        method_fig.update_layout(
            yaxis_title='Frequency',
            xaxis_title='Argument Configuration',
            height=800,
            width=950,
            showlegend=True
        )

        arg_columns = list(range(1, len(filtered_columns) + 1))
        args_child = []

        for selected_argument in arg_columns:
            div_children = []
            # Frequency graph for types
            dff = method_df[f'args.{selected_argument - 1}.type'].value_counts().reset_index()
            dff.columns = ['type', 'count']

            type_fig = px.bar(dff, x='type', y='count',
                              title=f"'{selected_method}' Method Argument '{selected_argument}' Type Distribution")
            type_fig.update_layout(
                yaxis_title='Frequency',
                xaxis_title='Type',
                height=800,
                width=950,
                showlegend=True
            )

            div_children.append(dcc.Graph(figure=type_fig))

            if f'args.{selected_argument - 1}.value' in method_df.columns:
                # Frequency graph for values
                dff = method_df[f'args.{selected_argument - 1}.value'].value_counts().reset_index()
                dff.columns = ['value', 'count']

                value_fig = px.bar(dff, x='value', y='count',
                                   title=f"'{selected_method}' Method Argument '{selected_argument}' Value Distribution")
                value_fig.update_layout(
                    yaxis_title='Frequency',
                    xaxis_title='Value',
                    height=800,
                    width=950,
                    showlegend=True
                )
                div_children.append(dcc.Graph(figure=value_fig))

            child_div = html.Div(children=div_children, style={'display': 'flex'})
            args_child.append(child_div)

        dff = (filtered_df.groupby(['source', 'library'])['name']
               .nunique()
               .reset_index(name='count')
               .sort_values(by='count', ascending=True))
        fig2 = px.bar(dff, x='count', y='source', title="Distinct API Calls per Client", color='library',
                      barmode='overlay')
        height = max(800, len(dff.values) * 20)
        fig2.update_layout(
            xaxis_title='Distinct Calls',
            yaxis_title='Client',
            height=height,
            width=950,
            showlegend=True
        )

        dff = (filtered_df.groupby(['source', 'library'])['source']
               .size()
               .reset_index(name='count')
               .sort_values(by='count', ascending=True))

        fig3 = px.bar(dff, x='count', y='source', title="Total API Calls per Client", log_x=True, color='library',
                      barmode='overlay')
        height = max(800, len(dff.values) * 20)
        fig3.update_layout(
            xaxis_title='API Calls',
            yaxis_title='Client',
            height=height,
            width=950,
            showlegend=True
        )

        # Extracting just the file name from the path
        filtered_df['file'] = filtered_df['definition.file'].str.split('/').str[-1]
        dff = (filtered_df.groupby(['file', 'library'])
               .size()
               .reset_index(name='count')
               .sort_values(by='count', ascending=True))

        fig4 = px.bar(dff, x='count', y='file', title="Header File Usage Frequency", log_x=True, color='library',
                      barmode='overlay')

        fig4.update_layout(
            xaxis_title='API Calls',
            yaxis_title='Header File',
            height=800,
            width=950,
            showlegend=True
        )

        filtered_df['Install Method'] = filtered_df['definition.file'].apply(
            lambda x: 'APT' if 'usr/include' in x else 'Submod')
        dff = (filtered_df.groupby(['Install Method', 'library'])
               .nunique()['source']
               .reset_index(name='count'))
        fig5 = px.bar(dff, x='count', y='Install Method', title="Install Method Popularity", log_x=False,
                      color='library', barmode='stack')

        fig5.update_layout(
            xaxis_title='Number of Repositories',
            yaxis_title='Install Method',
            height=800,
            width=950,
            showlegend=True
        )

        return fig1, fig2, fig3, fig4, fig5, options, table_data, methods, method_fig, args_child, repos

    app.run(debug=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process usage data')
    parser.add_argument('dir_path', type=str, help='The directory to be parsed', default='../example_results')
    args = parser.parse_args()
    main(args.dir_path)
