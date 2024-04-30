import plotly.graph_objects as go
import pandas as pd
import random
import ast
import plotly.express as px
from ast import literal_eval
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State

# Read the CSV file
# df = pd.read_csv('/Users/solakim/Downloads/df_renamed.csv')
df = pd.read_csv('data/df_network_norway.csv')

# Use a Plotly Express qualitative color palette
colors = px.colors.qualitative.Plotly

def get_unique_colors(n):
    colors = [
        'green', 'yellow', 'blue', 'purple', 'orange', 'pink', 'teal',
        'lime', 'brown', 'gold', 'silver', 'cyan', 'magenta', 'olive', 'maroon'
    ]
    return colors[:n]

# Dictionary to store transactions by country
transactions_by_country = {}

# Populate transactions for each country
for _, row in df.iterrows():
    for role in ['Importer', 'Exporter', 'partner2Desc']:
        country = row[role]
        transaction = (row['Importer'], row['Exporter'], row['partner2Desc'])
        if country not in transactions_by_country:
            transactions_by_country[country] = set()
        transactions_by_country[country].add(transaction)

# Create lists to store the edges and nodes
edge_x = []
edge_y = []
edge_z = []
node_x = []
node_y = []
node_z = []
node_labels = []
node_colors = []
node_customdata = []

# Create dictionaries to store the node positions, indices, and combinations
node_positions = {}
node_indices = {}
node_combinations = {}

# Assuming transactions_by_country is populated from the DataFrame
unique_transactions = set()
for transactions in transactions_by_country.values():
    unique_transactions.update(transactions)

# Debugging: Print unique transactions to ensure all are captured
print(f"Unique Transactions: {unique_transactions}")

# Get unique colors
transaction_colors = get_unique_colors(len(unique_transactions))

# Map transactions to colors, ensuring we have enough colors by cycling through them if necessary
transaction_to_color = {trans: colors[i % len(colors)] for i, trans in enumerate(unique_transactions)}

# Debugging: Print transaction to color mapping
print(f"Transaction to Color Mapping: {transaction_to_color}")

# Populate nodes and node attributes

for _, row in df.iterrows():
    for country, layer in [(row['Importer'], 0), (row['partner2Desc'], 1), (row['Exporter'], 2)]:
        node_key = f"{country}_{layer}"
        if node_key not in node_positions:
            if country in transactions_by_country:
                node_custom_data = list(transactions_by_country[country])
            else:
                node_custom_data = []
            node_positions[node_key] = (random.uniform(-1, 1), layer)
            node_indices[node_key] = len(node_labels)
            node_combinations[node_key] = node_custom_data
            node_x.append(node_indices[node_key])
            node_y.append(node_positions[node_key][0])
            node_z.append(node_positions[node_key][1])
            node_labels.append(country)
            node_colors.append('grey')
            node_customdata.append(str(node_custom_data))

# Populate edges
for transaction in unique_transactions:
    importer, exporter, partner2 = transaction
    importer_key = f"{importer}_0"
    partner2_key = f"{partner2}_1"
    exporter_key = f"{exporter}_2"

    if importer_key in node_indices and partner2_key in node_indices:
        edge_x.extend([node_x[node_indices[importer_key]], node_x[node_indices[partner2_key]], None])
        edge_y.extend([node_y[node_indices[importer_key]], node_y[node_indices[partner2_key]], None])
        edge_z.extend([0, 1, None])

    if partner2_key in node_indices and exporter_key in node_indices:
        edge_x.extend([node_x[node_indices[partner2_key]], node_x[node_indices[exporter_key]], None])
        edge_y.extend([node_y[node_indices[partner2_key]], node_y[node_indices[exporter_key]], None])
        edge_z.extend([1, 2, None])

# Create the Dash app
app = Dash(__name__)

# Create the 3D network graph
fig = go.Figure()

# Add edges
fig.add_trace(go.Scatter3d(
    x=edge_x, y=edge_y, z=edge_z,
    mode='lines',
    line=dict(color='gray', width=1),
    hoverinfo='none'
))

# Add nodes
node_trace = go.Scatter3d(
    x=node_x, y=node_y, z=node_z,
    mode='markers+text',
    marker=dict(size=10, color=node_colors),
    text=node_labels,
    textposition='top center',
    hoverinfo='text',
    customdata=node_customdata
)
fig.add_trace(node_trace)

# Update the layout
fig.update_layout(
    title='Trade Network',
    scene=dict(
        xaxis=dict(title='Node Index', showticklabels=False),
        yaxis=dict(title='', showticklabels=False),
        zaxis=dict(title='Layer', tickvals=[0, 1, 2], ticktext=['Importer', '2nd Partner', 'Exporter'], showticklabels=True),
        camera=dict(eye=dict(x=1.5, y=1.5, z=0.8))
    ),
    width=1280,
    height=800
)

# Create the app layout
app.layout = html.Div([
    dcc.Graph(id='trade-network', figure=fig),
    html.Div(id='click-data')
])

# Callback to handle node click event
@app.callback(
    Output('trade-network', 'figure'),
    [Input('trade-network', 'clickData')],
    [State('trade-network', 'relayoutData'),
     State('trade-network', 'figure')]
)
def update_highlight(click_data, relayoutData, current_figure):
    node_colors = ['grey'] * len(node_labels)  # Default to grey for non-highlighted nodes
    edge_x = []
    edge_y = []
    edge_z = []

    if click_data and 'points' in click_data and click_data['points']:
        point_data = click_data['points'][0]
        if 'customdata' in point_data:
            selected_transactions = literal_eval(point_data['customdata'])
            clicked_node_index = point_data['pointNumber']
            clicked_node_layer = node_z[clicked_node_index]
            clicked_node_label = node_labels[clicked_node_index]
            node_colors[clicked_node_index] = 'red'  # Highlight the clicked node in red

            for trans in selected_transactions:
                if clicked_node_label in trans:
                    try:
                        color = transaction_to_color[trans]
                        # Highlight related nodes in the same transaction with the same color
                        importer, exporter, partner2 = trans
                        for node_key, node_label in zip(node_indices.keys(), node_labels):
                            if node_label in [importer, exporter, partner2]:
                                node_index = node_indices[node_key]
                                node_layer = node_z[node_index]
                                if node_index != clicked_node_index and node_layer != clicked_node_layer:
                                    node_colors[node_index] = color

                        # Add edges based on the clicked node's role
                        if clicked_node_layer == 0:  # Clicked node is an Importer
                            if clicked_node_label == importer:
                                partner2_key = f"{partner2}_1"
                                exporter_key = f"{exporter}_2"
                                if partner2_key in node_indices:
                                    edge_x.extend([node_x[clicked_node_index], node_x[node_indices[partner2_key]], None])
                                    edge_y.extend([node_y[clicked_node_index], node_y[node_indices[partner2_key]], None])
                                    edge_z.extend([0, 1, None])
                                if exporter_key in node_indices:
                                    edge_x.extend([node_x[node_indices[partner2_key]], node_x[node_indices[exporter_key]], None])
                                    edge_y.extend([node_y[node_indices[partner2_key]], node_y[node_indices[exporter_key]], None])
                                    edge_z.extend([1, 2, None])
                        elif clicked_node_layer == 1:  # Clicked node is a 2nd Partner
                            if clicked_node_label == partner2:
                                importer_key = f"{importer}_0"
                                exporter_key = f"{exporter}_2"
                                if importer_key in node_indices:
                                    edge_x.extend([node_x[node_indices[importer_key]], node_x[clicked_node_index], None])
                                    edge_y.extend([node_y[node_indices[importer_key]], node_y[clicked_node_index], None])
                                    edge_z.extend([0, 1, None])
                                if exporter_key in node_indices:
                                    edge_x.extend([node_x[clicked_node_index], node_x[node_indices[exporter_key]], None])
                                    edge_y.extend([node_y[clicked_node_index], node_y[node_indices[exporter_key]], None])
                                    edge_z.extend([1, 2, None])
                        elif clicked_node_layer == 2:  # Clicked node is an Exporter
                            if clicked_node_label == exporter:
                                partner2_key = f"{partner2}_1"
                                importer_key = f"{importer}_0"
                                if partner2_key in node_indices:
                                    edge_x.extend([node_x[node_indices[partner2_key]], node_x[clicked_node_index], None])
                                    edge_y.extend([node_y[node_indices[partner2_key]], node_y[clicked_node_index], None])
                                    edge_z.extend([1, 2, None])
                                if importer_key in node_indices:
                                    edge_x.extend([node_x[node_indices[importer_key]], node_x[node_indices[partner2_key]], None])
                                    edge_y.extend([node_y[node_indices[importer_key]], node_y[node_indices[partner2_key]], None])
                                    edge_z.extend([0, 1, None])
                    except KeyError:
                        print(f"Transaction not found in color mapping: {trans}")

    # Update figure
    new_fig = go.Figure()
    new_fig.add_trace(go.Scatter3d(
        x=edge_x, y=edge_y, z=edge_z,
        mode='lines',
        line=dict(color='grey', width=1),
        hoverinfo='none'
    ))
    new_fig.add_trace(go.Scatter3d(
        x=node_x, y=node_y, z=node_z,
        mode='markers+text',
        marker=dict(size=10, color=node_colors),
        text=node_labels,
        textposition='top center',
        hoverinfo='text',
        customdata=node_customdata
    ))
    new_fig.update_layout(current_figure['layout'])

    if relayoutData and 'scene.camera' in relayoutData:
        new_fig.update_layout(scene={'camera': relayoutData['scene.camera']})

    return new_fig

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)