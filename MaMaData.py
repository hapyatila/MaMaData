from taipy.gui import Gui
import taipy.gui.builder as tgb
from math import cos, exp
import pandas as pd
import os
import datetime
import numpy

# Configuration du style
# css_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "MaMaStyle.css")
# print(f"Chemin du fichier CSS : {css_file}")

#value = 10

#def compute_data(decay:int)->list:
#    return [cos(i/6) * exp(-i*decay/600) for i in range(100)]

#def slider_moved(state):
#    state.data = compute_data(state.value)

try:
    # Utilisation d'un chemin absolu pour être sûr
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "2025-05-28-PMI.csv")
    data = pd.read_csv(csv_path)
    
    # Charger les coordonnées des villes
    villes_path = os.path.join(current_dir, "Indicateurs-Villes.csv")
    villes_df = pd.read_csv(villes_path)
    
    # Fusionner les données avec les coordonnées
    data = pd.merge(
        data,
        villes_df[['Ville', 'lat', 'lon']],
        on='Ville',
        how='left'
    )
    
except Exception as e:
    print(f"Erreur lors du chargement des fichiers : {e}")
    data = pd.DataFrame()  # DataFrame vide en cas d'erreur

data['Date de soumission'] = pd.to_datetime(data['Date de soumission'], errors="coerce")
data['Date naissance de la mère'] = pd.to_datetime(data['Date naissance de la mère'], errors="coerce")

# Calcul de l'âge
data["age_maman"] = data.apply(
    lambda row: (row["Date de soumission"] - row["Date naissance de la mère"]).days // 365
    if pd.notnull(row["Date de soumission"]) and pd.notnull(row["Date naissance de la mère"])
    else None,
    axis=1
)

# Créer une table pour le chart : deux colonnes, âge et nombre
def compute_age_data(filtered_df):
    age_counts = filtered_df["age_maman"].value_counts().sort_index()
    # Plage d'âges souhaitée
    all_ages = pd.Series(range(10, 51), name="Âge")
    # Reindexer avec tous les âges de 10 à 50, valeurs manquantes mises à 0
    age_counts_full = age_counts.reindex(all_ages, fill_value=0)
    return pd.DataFrame({
        "Âge": age_counts_full.index,
        "Nombre de mamans": age_counts_full.values
    })

# Initialisation des villes
categories = sorted(data["Ville"].dropna().unique())
selected_category = categories  # Toutes les villes sont sélectionnées par défaut

# Variables pour la recherche et la sélection globale
search_text = ""
select_all = True

def on_search(state, var_name, var_value):
    state.search_text = var_value.lower()
    # Filtrer les catégories en fonction de la recherche
    state.categories = [cat for cat in sorted(data["Ville"].dropna().unique()) 
                       if var_value.lower() in cat.lower()]

def toggle_select_all(state):
    state.select_all = not state.select_all
    if state.select_all:
        state.selected_category = state.categories
    else:
        state.selected_category = []
    change_category(state)

# Initialiser avec toutes les villes
filtered_data = data[data["Ville"].isin(selected_category)]
age_data = compute_age_data(filtered_data)


# Initialisation des dates
start_date = data["Date de soumission"].min()
end_date = data["Date de soumission"].max()
dates = [start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")]

# Initilisation des âges des Mamans
all_ages = {}
all_ages_str = []

# Filtrer les valeurs nulles avant de calculer min et max
valid_ages = data["age_maman"].dropna()
#start_age = int(valid_ages.min())
#end_age = int(valid_ages.max())
start_age = 10
end_age = 50

a_age = start_age
while a_age <= end_age:  # Changé < en <= pour inclure l'âge maximum
    age_str = str(a_age)
    all_ages_str.append(age_str)
    all_ages[age_str] = a_age
    a_age += 1

# Initial selection: first and last age
ages=[all_ages_str[1], all_ages_str[-1]]
# These two variables are used in text controls
start_sel = all_ages[ages[0]]
end_sel = all_ages[ages[1]]

# -------- Pour la carte ---------
# Créer un DataFrame avec les données de la carte
def compute_map_data(filtered_df):
    data_map = filtered_df.groupby('Ville').agg({
        'lat': 'first',
        'lon': 'first',
        'Nb colis hygiène Femme': 'sum'  # Nombre de mamans par ville
    }).reset_index()

    # Renommer la colonne pour plus de clarté
    data_map = data_map.rename(columns={'Nb colis hygiène Femme': 'nb_mamans'})

    # Calculer la taille des bulles
    min_size = 5
    max_size = 60
    solve = numpy.linalg.solve([[data_map["nb_mamans"].min(), 1], 
                            [data_map["nb_mamans"].max(), 1]],
                            [min_size, max_size])
    data_map["size"] = data_map["nb_mamans"].apply(lambda p: p*solve[0]+solve[1])

    # Ajouter le texte au survol
    data_map["text"] = data_map.apply(
        lambda row: f"{row['Ville']}<br>Nombre de commandes : {row['nb_mamans']}", 
        axis=1
    )
    return data_map

marker = {
    "size": "size",
    "color": "nb_mamans",
    "colorscale": "Viridis",
    "showscale": True,
    "colorbar": {"title": "Nombre de commandes"}
}

layout = {
    "mapbox": {
        "style": "carto-positron",  # Style alternatif qui ne nécessite pas de clé API
        "center": {"lat": 48.8566, "lon": 2.3522},
        "zoom": 8
    },
    "title": {
        "text": "Répartition géographique des commandes en Ile-de-France",
        "y": 0.95,
        "x": 0.5,
        "xanchor": "center",
        "yanchor": "top"
    },
    "margin": {"t": 50, "b": 0, "l": 0, "r": 0}
}

data_map = compute_map_data(filtered_data)
#------ END Carte --------

def change_category(state):
    if not state.selected_category:
        # Si aucune ville n'est sélectionnée, on affiche toutes les données
        state.age_data = compute_age_data(data)
        state.data_map = compute_map_data(data)
        print("Affichage de toutes les villes")
    else:
        # Si une ou plusieurs villes sont sélectionnées
        if isinstance(state.selected_category, list):
            # Cas de sélection multiple
            filtered = data[data["Ville"].isin(state.selected_category)]
        else:
            # Cas de sélection unique
            filtered = data[data["Ville"] == state.selected_category]
        
        state.age_data = compute_age_data(filtered)
        state.data_map = compute_map_data(filtered)
        print(f"Villes sélectionnées : {state.selected_category}")

def change_date_range(state):
    start = pd.to_datetime(state.dates[0])
    end = pd.to_datetime(state.dates[1])
    filtered = data[(data["Date de soumission"] >= start) & (data["Date de soumission"] <= end)]
    state.age_data = compute_age_data(filtered)
    state.data_map = compute_map_data(filtered)

def on_change_age_mamans(state, _, var_value):
    age_min = all_ages[var_value[0]]
    age_max = all_ages[var_value[1]]
     # Update the text controls
    state.start_sel = age_min
    state.end_sel = age_max
    # Update Data
    filtered = data[(data["age_maman"] >= age_min) & (data["age_maman"] <= age_max)]
    state.age_data = compute_age_data(filtered)
    state.data_map = compute_map_data(filtered)

with tgb.Page() as page:
    tgb.text(value="# MaMaMa : Observation de la malnutrition infantile en Ile de France", mode="md")
    
    tgb.text(value="Lieu de résidence des bénéficiaires")
    tgb.input(value="{search_text}", 
             label="Rechercher une ville", 
             on_change=on_search)
    tgb.button(label="Tout sélectionner/désélectionner", 
              on_action=toggle_select_all)
    tgb.selector(value="{selected_category}", 
                lov="{categories}", 
                dropdown=True, 
                filter=False,
                multiple=True, 
                on_change=change_category,
                checkbox=True,
                width="100%")
    
    tgb.text(value="Période d'observation")
    tgb.date_range("{dates}", on_change=change_date_range)
    tgb.text(value="Âge des mamans")
    tgb.slider("{ages}", lov="{all_ages_str}", on_change=on_change_age_mamans)
    
    with tgb.layout(columns="1 1"):
        tgb.chart("{data_map}", 
                  type="scattermapbox", 
                  mode="markers", 
                  lat="lat", 
                  lon="lon", 
                  marker="{marker}", 
                  text="text", 
                  layout="{layout}")
        tgb.chart(data="{age_data}", 
                 x="Âge", 
                 y="Nombre de mamans", 
                 type="bar", 
                 title="Répartition des âges des mamans")

#data = compute_data(value)

if __name__ == "__main__":
    gui = Gui(page=page)
    # gui.css_file = css_file
    gui.run(title="MaMaMa - Analyse des données",host="0.0.0.0", port=8000, debug=True)
