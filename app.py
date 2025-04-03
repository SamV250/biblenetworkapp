import streamlit as st
import requests
import pandas as pd
from pyvis.network import Network
import re
import tempfile
import os
from bs4 import BeautifulSoup

# -- Title
st.set_page_config(page_title="Bible Network Explorer", layout="wide")
st.title("📖 Bible Topic Network Visualization")

# -- Input topic
topic = st.text_input("Enter a theme, topic, or keyword (e.g., love, fear, Jesus):", "love")

# -- Function to scrape OpenBible.info for relevant verses
def get_verses_for_topic(topic):
    try:
        search_url = f"https://www.openbible.info/topics/{topic.replace(' ', '_')}"
        response = requests.get(search_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        verses = []

        # Target only the verses in the divs
        for verse_div in soup.find_all("div", class_="verse"):
            a_tag = verse_div.find("a")
            if a_tag and a_tag.text.strip():
                ref = a_tag.text.strip()
                verses.append(ref)
            if len(verses) >= 5:
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

# -- Generate network from multiple verses
def generate_network(verse_data_list):
    net = Network(height='600px', width='100%', notebook=False, bgcolor='#fff', font_color='black')
    net.force_atlas_2based()

    added_nodes = set()

    for verse_data in verse_data_list:
        if not verse_data or 'text' not in verse_data:
            continue
        verse_text = verse_data['text']
        reference = verse_data.get('reference', 'Unknown Reference')
        entities = extract_entities(verse_text)

        if reference not in added_nodes:
            net.add_node(reference, shape='box', label=reference, color='orange', title=verse_text)
            added_nodes.add(reference)

        for entity in entities:
            if entity not in added_nodes:
                net.add_node(entity, label=entity, title=entity)
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
        refs = get_verses_for_topic(topic)
        if refs:
            verse_data_list = [fetch_verse_text(ref) for ref in refs]
            net = generate_network(verse_data_list)
            show_graph(net)
        else:
            st.error("No verses found for that topic. Try a different word or phrase.")
