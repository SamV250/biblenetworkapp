import streamlit as st
import requests
import pandas as pd
from pyvis.network import Network
import re
import tempfile
import os
from bs4 import BeautifulSoup
from collections import Counter

# -- Title
st.set_page_config(page_title="Bible Network Explorer", layout="wide")
st.title("📖 Bible Topic Network Visualization")

# -- Input topic
topic = st.text_input("Enter a theme, topic, or keyword (e.g., love, fear, Jesus):", "love")
max_verses = st.slider("Number of verses to retrieve", min_value=1, max_value=30, value=10)
search_entity = st.text_input("Highlight a specific entity (optional):")

show_people = st.checkbox("Show People", value=True)
show_places = st.checkbox("Show Places", value=True)
show_themes = st.checkbox("Show Themes", value=True)

# -- Function to scrape OpenBible.info for relevant verses
def get_verses_for_topic(topic, limit):
    try:
        search_url = f"https://www.openbible.info/topics/{topic.replace(' ', '_')}"
        response = requests.get(search_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        verses = []

        for verse_div in soup.find_all("div", class_="verse"):
            a_tag = verse_div.find("a")
            if a_tag and a_tag.text.strip():
                ref = a_tag.text.strip()
                verses.append(ref)
            if len(verses) >= limit:
                break

        return verses
    except Exception as e:
        print("Scraping error:", e)
        return []

# -- Function to fetch verse text from Bible API
def fetch_verse_text(ref):
    try:
        url = f"https://bible-api.com/{ref.replace(' ', '+')}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
    except:
        return None

# -- Function to extract basic entities
def extract_entities(text):
    words = re.findall(r"[A-Z][a-z]+", text)
    common = {"The", "And", "For", "That", "This", "Shall", "Will", "Your", "Have"}
    return [word for word in words if word not in common]

# -- Classify entity types (basic heuristic)
def classify_entity(entity):
    if entity in {"Jesus", "Paul", "Peter", "Moses", "David", "John"}:
        return 'person'
    elif entity in {"Jerusalem", "Egypt", "Nazareth", "Bethlehem"}:
        return 'place'
    else:
        return 'theme'

# -- Generate network from multiple verses
def generate_network(verse_data_list):
    net = Network(height='600px', width='100%', notebook=False, bgcolor='#fff', font_color='black')
    net.force_atlas_2based()

    added_nodes = set()
    entity_counts = Counter()
    entity_types = {}

    for verse_data in verse_data_list:
        if not verse_data or 'text' not in verse_data:
            continue
        verse_text = verse_data['text']
        reference = verse_data.get('reference', 'Unknown Reference')
        entities = extract_entities(verse_text)

        for ent in entities:
            entity_counts[ent] += 1
            if ent not in entity_types:
                entity_types[ent] = classify_entity(ent)

        if reference not in added_nodes:
            net.add_node(reference, shape='box', label=reference, color='orange', title=verse_text)
            added_nodes.add(reference)

        for entity in entities:
            if entity in added_nodes:
                continue

            # Filter based on type
            ent_type = entity_types.get(entity, 'theme')
            if (ent_type == 'person' and not show_people) or \
               (ent_type == 'place' and not show_places) or \
               (ent_type == 'theme' and not show_themes):
                continue

            color = {'person': 'skyblue', 'place': 'lightgreen', 'theme': 'plum'}.get(ent_type, 'gray')
            size = 15 + entity_counts[entity] * 2
            border = 'red' if search_entity.lower() == entity.lower() else color

            net.add_node(entity, label=entity, title=f"{entity} ({entity_counts[entity]})", color=border, size=size)
            added_nodes.add(entity)
            net.add_edge(reference, entity, color='gray')

        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                net.add_edge(entities[i], entities[j], title=reference)

    return net

# -- Render and display the graph
def show_graph(net):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        net.save_graph(tmp_file.name)
        st.components.v1.html(open(tmp_file.name, 'r', encoding='utf-8').read(), height=650)
        os.unlink(tmp_file.name)

# -- Main app logic
if topic:
    with st.spinner("Fetching verses and building network..."):
        refs = get_verses_for_topic(topic, max_verses)
        if refs:
            verse_data_list = [fetch_verse_text(ref) for ref in refs]
            net = generate_network(verse_data_list)
            show_graph(net)
        else:
            st.error("No verses found for that topic. Try a different word or phrase.")
