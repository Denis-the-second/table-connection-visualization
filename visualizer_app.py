import pandas as pd
import random
import base64
import io

from dash import Dash, dcc, html, Input, Output, State, callback, ctx, ALL, MATCH
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
cyto.load_extra_layouts()


def convert_to_df(contents, filename, sheetname):
    if contents is not None:
        content_type, content_string = contents.split(',')
        sheetname = sheetname.strip()

        decoded = base64.b64decode(content_string)
        try:
            if 'csv' in filename:
                # Assume that the user uploaded a CSV file
                df = pd.read_csv(
                    io.StringIO(decoded.decode('utf-8')))
                return df
            elif 'xls' in filename:
                # Assume that the user uploaded an excel file
                if sheetname == '':
                    df = pd.read_excel(io.BytesIO(decoded))
                    return df
                else:
                    df = pd.read_excel(io.BytesIO(decoded), sheet_name=sheetname)
                    return df
        except Exception as e:
            print(e)
            


elements = []

# Функция для автоматического конструирования связей между выбранными пользователем элементами
def elements_maker(df, df_dict, needed_columns): 
    if df is not None:
        elements = []
        duplicates_container = []
        tmp_df = df[needed_columns] # Оставлям в датафрейме только выбранные поля
        
        for row in range(tmp_df.shape[0]): # Итерация по строкам
            # Проверка на то, что в рамках все значения в рамках одной строки - значения, выбранные пользователем (чтобы не было лишних узлов)
            if all([tmp_df.iloc[row, i] in df_dict[list(df_dict.keys())[i]] for i in range(len(tmp_df.iloc[row]))]) == True:
                for i in range(1, len(tmp_df.iloc[row])): # Итерация в рамках всех значений одной строки
                    if tmp_df.iloc[row, i - 1] not in duplicates_container:
                        # Создание узла, если он еще не был создан
                        elements.append({'data': {'id': tmp_df.iloc[row, i - 1], 'label': tmp_df.iloc[row, i - 1], 'firstname': list(df_dict.keys())[i - 1]}})
                        duplicates_container.append(tmp_df.iloc[row, i - 1])
                    if tmp_df.iloc[row, i] not in duplicates_container:
                        # Создание узла, если он еще не был создан (повторение из-за того, что начало итерации начинается не с 0-го элемента, а с 1-го)
                        elements.append({'data': {'id': tmp_df.iloc[row, i], 'label': tmp_df.iloc[row, i], 'firstname': list(df_dict.keys())[i]}})
                        duplicates_container.append(tmp_df.iloc[row, i - 1])
                    if tmp_df.iloc[row, i - 1] in df_dict[list(df_dict.keys())[i - 1]] and tmp_df.iloc[row, i] in df_dict[list(df_dict.keys())[i]]:
                        # Создание связи между узлами, если такой связи еще не существует
                        if (tmp_df.iloc[row, i - 1], tmp_df.iloc[row, i]) not in duplicates_container: # Проверка на то, что связь не была уже добавлена в elements
                            elements.append({'data': {'source': tmp_df.iloc[row, i - 1], 'target': tmp_df.iloc[row, i]}}) # Добавляем связь
                            duplicates_container.append((tmp_df.iloc[row, i - 1], tmp_df.iloc[row, i])) # Заносим ее в список duplicates_container, чтобы случайно не добавить ее еще раз
        return elements
    else:
        return []
        
    
app = Dash(__name__, external_stylesheets=[dbc.themes.LITERA]) #Создание файла дерева
server = app.server

# Стилистическое добавление для внесения разнообразия в дерево
default_stylesheet = [
    {
        'selector': 'node',
        'style': {
            'label': 'data(label)',
            'width': "100%",
            'height': "100%",
            "font-size": "65px"
        }
    }
]


# Настройка отображения визуализаций
app.layout = html.Div(children = [ # Пояснение параметров: цвета заднего плана, самих элементов дерева и размера изображения
    html.Div(['Введите название excel-листа с необходимой для анализа таблицей (только в случае загрузки Excle-файла)']),
    html.Div(['Только после этого загрузите excel-файл']),
    html.Div(dcc.Input(
            id="excel sheet",
            type='text',
            placeholder='',
            value='',
            style={
            'width': '90%',
            'height': '30px',
            'lineHeight': '30px',
            'borderWidth': '1px',
            'borderStyle': 'solid',
            'borderRadius': '5px',
            'textAlign': 'left',
            'margin': '10px'
            }
        ), style={'width': '35%', 'display': 'inline-block'}),
    
    html.Div(dcc.Upload(html.Button('Upload File'), id='upload-data', 
        # Prohibit multiple files to be uploaded
        multiple=False,
        style={'margin': '10px'}
    ), style={'width': '35%', 'display': 'inline-block'}),

    html.Div(id='output-data-upload'),
    html.Hr(),
    
    dcc.Dropdown( # интерактивный список, в котором пользователь может выбирать колонки, которые надо отображать ниже
    options=[],
    value=[],
    multi=True,
    id='demo-dropdown',
    className="dash-bootstrap"),

    html.Div(id='input-container'), # контейнер, который потом будет заполнен атрибутами указанных пользователем колонок
    
    html.Hr(),
    html.P("Dash Cytoscape:"), # Визуализация дерева
    cyto.Cytoscape(
        id='cytoscape',
        elements=elements,
        layout={'name': 'dagre', # Выбор логики отображения связей дерева (см. https://dash.plotly.com/cytoscape/layout)
                'rankDir': 'LR',
                'rankSep': 1500,
                'ranker': 'longest-path'}, 
        style={'width': '1920px', 'height': '1080px'},
        stylesheet=default_stylesheet
    )
])


@callback(
        Output('demo-dropdown', 'options'),
        Output('demo-dropdown', 'value'),
        Output('cytoscape', 'stylesheet'),
        Output('output-data-upload', 'children'),
        Input('upload-data', 'contents'),
        State('upload-data', 'filename'),
        State('excel sheet', 'value'),
        State('cytoscape', 'stylesheet')
)
def create_columns_dropdown(file_content, filename, sheet_name, default_stylesheet):
    if file_content is not None:
        df = convert_to_df(file_content, filename, sheet_name)
        shapes = ['ellipse', 'rectangle', 'triangle', 'hexagon', 'octagon']
        colors = ['#F08000', '#FF5F15', '#E3735E', '#FFAA33', '#FF5733', '#F08000' ,'#FA5F55', '#D27D2D', '#B87333', '#FF7F50', '#F88379', '#8B4000', '#FAD5A5', '#E49B0F', '#FFC000', '#DAA520', '#FFD580', '#C04000', '#F4BB44', '#FFDEAD', '#FF5F1F', '#CC7722', '#FFA500', '#FAC898', '#FFE5B4', '#EC5800', '#F89880', '#E35335', '#FF7518', '#FF4433', '#FF5F15', '#FA8072', '#FFF5EE', '#A0522D', '#FA5F55', '#F08000', '#E3735E', '#FFAA33']
        for column in list(df.columns):
            default_stylesheet.append({'selector': f'[firstname = "{column}"]', 'style': {'background-color': f'{colors.pop(0)}','shape': f'{shapes[random.randint(0, len(shapes) - 1)]}'}})
        return list(df.columns), list(df.columns), default_stylesheet, html.Div([f'Вы загрузуили следующий файл - {filename}'])
    else:
        return [], [], default_stylesheet, []


# Действие 1: На основе выбранных пользователем колонок, заполнить контейнер списками атрибутов этих колонок
@callback(
        Output('input-container', 'children'),
        Input('demo-dropdown', 'value'),
        State('upload-data', 'contents'),
        State('upload-data', 'filename'),
        State('excel sheet', 'value')
)
def atribute_specifier(needed_columns, file_content, filename, sheet_name):
    df = convert_to_df(file_content, filename, sheet_name)
    if df is not None:
        for column in needed_columns:
            df[[column]] = df[[column]].fillna(f'{column} no data')
        
        return [dbc.Container( #Визуализация drop-down checkbox. В Dash специальной команды нет, поэтому пришлось составлять это поле из двух отдельных визуализаций
        children=[
            html.Details([
            html.Summary(column),
            dbc.Col([
                dcc.Checklist(
                id={'type': "all-or-none", 'index': column },
                options=["All"],
                value= ["All"]
            ),
                dcc.Checklist(
                    id={'type': 'attribute-checklist', 'index': column },
                    options=list(df[column].unique()),
                    value=list(df[column].unique()),
                    inline=True
                    )  
                ])
            ])
        ], style={
            'width': '90%',
            'borderWidth': '1px',
            'borderStyle': 'solid',
            'borderRadius': '5px',
            'textAlign': 'left',
            'margin': '10px'
            }) for column in needed_columns]
    


@app.callback(
    Output({'type': "attribute-checklist", 'index': MATCH}, "value"),
    Output({'type': "all-or-none", 'index': MATCH }, "value"),
    Input({'type': "attribute-checklist", 'index': MATCH}, "value"),
    Input({'type': "all-or-none", 'index': MATCH }, "value"),
    State({'type': "attribute-checklist", 'index': MATCH}, "options"),
)
def sync_checklists(att_selected, all_selected, options):
    input_id = ctx.triggered_id
    if input_id and input_id.type == "attribute-checklist":
        all_selected = ["All"] if set(att_selected) == set(options) else []
    else:
        if all_selected == ["All"]:
            att_selected = options
        elif all_selected == []:
            att_selected = []
    return att_selected, all_selected




# Действие 3: На основе списка выбранных колонок и списков выбранных атрибутов этих колонок провести обновление элементов, из которых состоит дерево
@callback(
    Output('cytoscape', 'elements'),
    Input('demo-dropdown', 'value'),
    Input({'type': 'attribute-checklist', 'index': ALL}, 'value'),
    State('upload-data', 'contents'),
    State('upload-data', 'filename'),
    State('excel sheet', 'value')
)
def update_elements(needed_columns, chosen_attributes, file_content, filename, sheet_name):

    df_dict = {}
    df = convert_to_df(file_content, filename, sheet_name)
    for column in needed_columns:
        df[[column]] = df[[column]].fillna(f'{column} no data')
        # В силу специфики работы Dash есть милисекунды, когда количество колонок и количество списков их атрибутов не равны
        # так как задаются разными элементами визуализаций. Это приводит к ошибке list index out of range, но
        # не влияет на работу кода, так как при следующем обновлении данных все сходится
        # Поэтому ниже ошибка IndexError игнорируется
        try:
            df_dict[column] = chosen_attributes[needed_columns.index(column)]
        except IndexError:
            df_dict[column] = list(df[column].unique())

    
    try:
        elements = elements_maker(df, df_dict, needed_columns) 
    except IndexError:
        pass

    return elements



app.run_server(debug=True, host='0.0.0.0') # Запуск
