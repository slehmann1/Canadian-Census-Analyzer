import webbrowser
import folium
import geopandas as gpd
import jinja2
import matplotlib.pyplot as plt
import time
import numpy as np

# Source for map data: https://www12.statcan.gc.ca/census-recensement/alternative_alternatif.cfm?l=eng&dispext=zip&teng=lcsd000b21a_e.zip&k=%20%20%20152326&loc=//www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/lcsd000b21a_e.zip

FUNC_LIST = (lambda a: mean_difference(a), lambda a: mean_percent_change(a), lambda a: mean_percent_difference(a))
ROUND_DECS = 2


def plot_map(function_name, strings, census_data, func=None, type="csd", clipped=False):
    """
    Creates a map and displays it using folium
    :param title: The title of the plot
    :param data: A tuple of data to be displayed
    :param strings: A tuple of the characteristic names to be plotted
    :param years: A tuple of the years plotted
    :param func: A function to act on data from each of the years
    :param type: The type of map to be displayed: CSD, Provinces, or LCD. See https://www12.statcan.gc.ca/census-recensement/2016/ref/dict/figures/f1_1-eng.cfm
    :param clipped: Whetehr or not data with the outliers clipped should be displayed
    :return:
    """

    cad = get_cad_file(type)

    # Create data column for every type of data
    for census in census_data:
        cad[str(census.year)] = 0

    cad["include"] = True

    # Simplify first data
    census_data[0].data_df = census_data[0].data_df.query(
        f"{census_data[0].geocode_col} in @cad['CSDUID'] and @strings[0] in {census_data[0].characteristic_col}")

    if len(census_data) == 1:
        # There is only one data listed
        for index, datum in census_data[0].data_df.query(
                f"{census_data[0].characteristic_col} in @strings[0]").iterrows():
            try:
                cad.loc[cad["CSDUID"] == datum[census_data[0].geocode_col], str(census_data[0].year)] = float(
                    datum[census_data[0].total_col])
            except (TypeError, ValueError):
                # If there is a data quality issue, the data is given as a NAN
                cad.loc[cad["CSDUID"] == datum[census_data[0].geocode_col], str(census_data[0].year)] = np.NAN
    else:
        # There are multiple data sources
        cad[function_name] = 0

        # Simplify the data by eliminating rows that are not needed
        # first reduce the first column to it's minimum length and then simplify the other columns based on the reduced first column
        for i in range(1, len(census_data)):
            x = census_data[i].data_df[census_data[i].geocode_col]
            census_data[0].data_df = census_data[0].data_df.query(f"{census_data[0].geocode_col} in @x")
        for i in range(1, len(census_data)):
            x = census_data[0].data_df[census_data[0].geocode_col]
            census_data[i].data_df = census_data[i].data_df.query(
                f"(`{census_data[i].characteristic_col}` in @strings[@i]) and ({census_data[i].geocode_col} in @x)")

        total = sum(
            1 for _ in census_data[0].data_df.query(f"{census_data[0].characteristic_col} in @strings[0]").iterrows())
        t = time.time()
        print(f"Start code of interest")
        count = 0
        for index, datum in census_data[0].data_df.query(
                f"{census_data[0].characteristic_col} in @strings[0]").iterrows():
            count += 1
            print(f"{count} of {total} data rows")

            try:
                # Build a list of
                func_data = np.array([float(datum[census_data[0].total_col])])
                for i in range(1, len(census_data)):
                    func_data = np.append(func_data, float(census_data[i].data_df.query(
                        f"{census_data[i].geocode_col} == @datum['{census_data[0].geocode_col}']")[
                                                               census_data[i].total_col]))

                cad.loc[cad["CSDUID"] == datum[census_data[0].geocode_col], function_name] = func(func_data)
            except (TypeError, ValueError):
                # If there is a data quality issue, the data is given as a NAN
                cad.loc[cad["CSDUID"] == datum[census_data[0].geocode_col], function_name] = np.NAN

            for i in range(0, len(census_data)):
                try:
                    cad.loc[cad["CSDUID"] == datum[census_data[0].geocode_col], str(census_data[i].year)] = float(
                        census_data[i].data_df.query(
                            f"{census_data[i].geocode_col} == @datum['{census_data[0].geocode_col}']")[
                            census_data[i].total_col])

                except (TypeError, ValueError):
                    # If there is a data quality issue, the data is given as a NAN
                    cad.loc[cad["CSDUID"] == datum[census_data[0].geocode_col], str(census_data[i].year)] = np.NAN

        print(f"End code of interest, time = {time.time() - t}")

    fig, ax = plt.subplots(1, figsize=(10, 6))

    cad = cad.loc[cad["include"] == True]

    m = folium.Map(location=[63, -102], zoom_start=4)

    # TODO: Make the colourmap uniform across the years

    if len(census_data) == 1:
        if clipped:
            column = str(census_data[0].year) + " clipped"
            cad[str(census_data[0].year) + " clipped"] = clip_outliers(cad[str(census_data[0].year)])
        else:
            column = str(census_data[0].year)

        choro = gen_choropleth(cad, "CSDUID", column, "feature.properties.CSDUID", strings[0], census_data[0].year)
        choro.add_to(m)

        hover_fields = [str(census_data[0].year), "CSDNAME", "CSDUID"]

    else:
        # Create a duplicate copy of the data with outliers removed, prevents the colour bar from being thrown off, but
        # allows the data to still be inspected

        if clipped:
            column = function_name + " clipped"
            cad[function_name + " clipped"] = clip_outliers(cad[function_name])
        else:
            column = function_name

        choro = gen_choropleth(cad, "CSDUID", column, "feature.properties.CSDUID", function_name, function_name)
        choro.add_to(m)

        for i in range(0, len(census_data)):

            if clipped:
                column = str(census_data[i].year) + " clipped"
                cad[str(census_data[i].year) + " clipped"] = clip_outliers(cad[function_name])
            else:
                column = str(census_data[i].year)

            choro = gen_choropleth(cad, "CSDUID", column, "feature.properties.CSDUID",
                                   census_data[i].data_df[census_data[i].characteristic_col].values[0],
                                   census_data[i].year)
            choro.add_to(m)

        lc = gen_layer_controller()
        lc.add_to(m)

        hover_fields = []
        for i in range(len(census_data)):
            hover_fields.append(str(census_data[i].year))
        hover_fields.extend([function_name, "CSDNAME", "CSDUID"])

    hover_bubble = gen_hover_bubble(cad, hover_fields)
    m.add_child(hover_bubble)
    m.keep_in_front(hover_bubble)

    output_map(m)


def get_cad_file(type):
    """
    Reads the correct geopandas dataframe based on the type of geography desired
    :param type: A string representing the type of geography desired: csd or provinces
    :return: A geopandas dataframe
    """
    if type == "csd":
        cad = gpd.read_file("mapData/simplified/Census Sub Divisions/lcsd000b21a_e.shp")
    elif type == "provinces":
        cad = gpd.read_file("mapData/simplified/Provinces/lpr_000b21a_e.shp")
    else:
        cad = gpd.read_file("mapData/simplified/Census Divisions/lcd_000b21a_e.shp")
    return cad


def output_map(m):
    """
    Saves and opens a folium map
    :param m: A folium map
    :return: None
    """
    outfp = "map.html"
    m.save(outfp)
    webbrowser.open("map.html")


def gen_choropleth(data, column_1, column_2, key_on, legend_name, name):
    """
    Creates a folium choropleth with the appropriate formatting
    :param data: The data to be displayed
    :param column_1: The column used as the key column
    :param column_2: The data column
    :param legend_name: The name to be applied to the legend
    :param name: The name for the layer
    :return: A folium.choropleth object
    """
    return folium.Choropleth(
        geo_data=data,
        data=data,
        columns=[column_1, column_2],
        key_on=key_on,
        fill_color='YlGnBu',
        fill_opacity=1,
        line_opacity=0.2,
        legend_name=legend_name,
        smooth_factor=0,
        Highlight=True,
        line_color="#0000",
        name=name,
        show=True,
        overlay=True,
        nan_fill_color="White"
    )


def gen_layer_controller():
    """
    Creates a formatted layer controller which may be added to a folium map
    :return:A Layer Control object
    """
    # TODO: Figure out how to default select only one option

    # Add a layer controller and override the default template to remove the baselayer box
    lc = folium.LayerControl(collapsed=False, tiles=False)
    lc._template = jinja2.Template("""
                {% macro script(this,kwargs) %}
                    var {{ this.get_name() }} = {
                        base_layers : {},
                        overlays :  {
                            {%- for key, val in this.overlays.items() %}
                            {{ key|tojson }} : {{val}},
                            {%- endfor %}
                        },
                    };
                    L.control.layers(
                        {{ this.get_name() }}.base_layers,
                        {{ this.get_name() }}.overlays,
                        {{ this.options|tojson }}
                    ).addTo({{this._parent.get_name()}});

                    {%- for val in this.layers_untoggle.values() %}
                    {{ val }}.remove();
                    {%- endfor %}
                {% endmacro %}
                """)
    return lc


def gen_hover_bubble(data, hover_fields):
    """
    Creates a hover bubble that may be applied to a folium map
    :param hover_fields: The fields of the data that should be displayed within the hover bubble
    :return: A GeoJson object representing a hover bubble
    """
    # Add hover functionality.
    style_function = lambda x: {'fillColor': '#ffffff',
                                'color': '#000000',
                                'fillOpacity': 0.1,
                                'weight': 0.1}

    highlight_function = lambda x: {'fillColor': '#000000',
                                    'color': '#000000',
                                    'fillOpacity': 0.50,
                                    'weight': 0.1}

    hover_bubble = folium.features.GeoJson(
        data=data,
        style_function=style_function,
        control=False,
        highlight_function=highlight_function,
        tooltip=folium.features.GeoJsonTooltip(
            fields=hover_fields,
            aliases=hover_fields,
            style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;")
        )
    )
    return hover_bubble


def mean_difference(data):
    diffs = []

    for i in range(1, len(data)):
        diffs.append(data[i] - data[i - 1])

    return np.round(np.mean(diffs), ROUND_DECS)


def mean_percent_difference(data):
    diffs = []
    for i in range(1, len(data)):
        if np.mean((data[i], data[i - 1])) == 0:
            diffs.append(np.NAN)
        else:
            diffs.append((data[i] - data[i - 1]) / (np.mean((data[i], data[i - 1]))) * 100)

    return np.round(np.mean(diffs), ROUND_DECS)


def mean_percent_change(data):
    diffs = []
    for i in range(1, len(data)):
        if np.abs(data[i - 1]) == 0:
            diffs.append(np.NAN)
        else:
            diffs.append((data[i] - data[i - 1]) / (np.abs(data[i - 1])) * 100)

    return np.round(np.mean(diffs), ROUND_DECS)


def clip_outliers(df):
    """
    Removes outliers for a pandas dataframe based on usage of the interquartile range
    :param df: The dataframe for outliers to be removed from
    :return:The dataframe with outliers clipped
    """
    iqr = df.quantile(0.75) - df.quantile(0.25)
    # Clip data that is 3 iqrs beyond the first or third quartile
    return df.clip(df.quantile(0.25) - 3 * iqr, df.quantile(0.75) + 3 * iqr)
