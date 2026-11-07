# --- Schelet pentru proiect ---
from textwrap import indent
import time, json, requests, pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import xml.etree.ElementTree as ET
from lxml import etree
from io import StringIO
from collections import Counter
import math
from requests import auth
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

def descarca_arxiv(categorie, n=20):
    print(NS["arxiv"])
    try:
        r = requests.get("https://export.arxiv.org/api/query",
                         params={"search_query": categorie, "max_results": n,
                                 "sortBy": "submittedDate", "sortOrder": "descending"},
                         headers={"User-Agent": "curs-fizica-xml/1.0 (student)"}, timeout=30)
        r.raise_for_status()
        return r.content
    except requests.RequestException as e:
        print("Nu am putut contacta arXiv:", e)
        return None

def arata_continut(element, level = 0):
    indent = " " * level
    print(f"{indent}{element.tag}")

    for name, value in element.attrib.items():
        print(f"{indent} @{name}={value!r}")
    
    for child in element:
        arata_continut(child, level+1)

def parseaza(continut) -> pd.DataFrame:
    feed_real = etree.fromstring(continut)

    data = []
    for e in feed_real.xpath("//a:entry", namespaces=NS):
        data.append({
                "id": e.xpath("string(a:id)", namespaces=NS),
                "title": " ".join(e.xpath("a:title/text()", namespaces=NS)).strip(),
                "published": e.xpath("string(a:published)",namespaces=NS),
                "updated": e.xpath("string(a:published)", namespaces=NS),
                "summary": " ".join(e.xpath("a:summary/text()", namespaces=NS)).strip(), 
                "authors": ", ".join(e.xpath("a:author/a:name/text()", namespaces=NS)),
                "categories": [category.get("term") for category in e.xpath("a:category", namespaces=NS)],
            })
    return pd.DataFrame(data)

def author_analysis(df:pd.DataFrame, show_graph=True):
    authors = df['authors']
    authors = np.char.split(authors.to_numpy().astype(str),sep=",")
    count = np.array([len(items) for items in authors])
    avg_author_count = count.mean() 
    print("Average number of authors per article: ", avg_author_count)
    authors_mentions = [x for y in authors for x in y]
    cntr = Counter(authors_mentions).most_common(15)
    labels = [word for word, count in cntr][::-1]
    values = [count for word, count in cntr][::-1]
    
    if show_graph:
        plt.figure(figsize=(9,6))
        plt.barh(labels, values)
        plt.xlabel("Frecventa")
        plt.ylabel("Termenul")
        plt.grid(axis="x", alpha=0.3)
        plt.tight_layout()
        plt.show()
    else:
        return {"labels": labels, "values": values, "avg_author_count":avg_author_count}

def title_analysis(df:pd.DataFrame, show_graph=True):
    freq_words = {"the", "of", "in", "for", "a", "an", "that", "and", "by", "from", "A", "with", "on", "at", "under"}
    titles = df['title'].to_numpy().astype(str)
    titles = [ " ".join(word for word in text.split() if word not in freq_words) for text in titles]
    words = np.concatenate(np.char.split(titles)) 
    cntr = Counter(words)
    top_words = cntr.most_common(15)
    labels = [word for word, count in top_words][::-1]
    values = [count for word, count in top_words][::-1]
    if show_graph:
        plt.figure(figsize=(9,6))
        plt.barh(labels, values)
        plt.xlabel("Frecventa")
        plt.ylabel("Termenul")
        plt.grid(axis="x", alpha=0.3)
        plt.tight_layout()
        plt.show()
    else:
        return {"labels": labels, "values": values}

def create_files(df:pd.DataFrame):
    title_data = title_analysis(df, False)
    author_data = author_analysis(df, False)
    data = {
            "authors": author_data['labels'],
            "authors_count": author_data['values'],
            "title": title_data['labels'],
            "title_count": title_data['values'],
            }
    json_str = json.dumps(data, indent=3)
    with open("radar.json", "w") as f:
        f.write(json_str)
    
    root = ET.Element("lista_articole")
    for _, row in df.iterrows():
        articol = ET.SubElement(root, "articol", id=str(row['id']))
        authors = row['authors']
        author = []
        for author_name in authors.split(','):
            author = ET.SubElement(articol, "author")
            author.text = author_name

    ET.indent(root, space="  ")
    xml_data = ET.tostring(
                    root,
                    encoding="utf-8",
                    xml_declaration=True
                    )

    
    with open("articole.xml", "wb") as f:
        f.write(xml_data)

def read_files():
    with open("radar.json", "r") as f:
        data_radar = json.load(f)
    data_articole = ET.parse("articole.xml") 
    print(data_radar)
    root = data_articole.getroot()

    for article in root.findall("articol"):
        article_id = article.get("id")
        author = [author for author in article.findall("author") if author.text]
        authors = [
                author.text.strip()
                for author in article.findall("author")
                if author.text
                ]

        print(f"Article ID: {article_id}")

        for author in authors:
            print(f"  Author: {author}")
    print()


def compare(categories):
    frames = []
    for category in categories:
        res = descarca_arxiv(category, 100)
        df = parseaza(res)
        frames.append(df)
        time.sleep(3)

    auth_data = []
    title_data = []

    for frame in frames:
        auth_data.append(author_analysis(frame, show_graph=False))
        title_data.append(title_analysis(frame, show_graph=False))
    
    labels_a = []
    values_a = []
    avg_author_count = []
    for authors in auth_data:
        labels_a.append(authors["labels"][:5])
        values_a.append(authors["values"][:5])
        avg_author_count.append(authors["avg_author_count"])
    
    labels_t = []
    values_t = []
    for title in title_data:
        labels_t.append(title["labels"][:5])
        values_t.append(title["values"][:5])
    plot_count = len(categories) + 1
    columns = 2
    rows = math.ceil(plot_count / columns)

    fig, axes = plt.subplots(
        rows,
        columns,
        figsize=(14, 5 * rows)
    )

    axes = np.atleast_1d(axes).ravel()

    for index, (category, authors) in enumerate(
        zip(categories, auth_data)
    ):
        labels = authors["labels"][:5]
        values = authors["values"][:5]

        labels = labels[::-1]
        values = values[::-1]

        axes[index].barh(
            labels,
            values,
            color="steelblue"
        )

        axes[index].set_title(
            f"Most frequent authors - {category}"
        )
        axes[index].set_xlabel("Number of papers")
        axes[index].grid(
            axis="x",
            alpha=0.3
        )

    average_values = [
        authors["avg_author_count"]
        for authors in auth_data
    ]

    average_axis = axes[len(categories)]

    average_axis.bar(
        categories,
        average_values,
        color="seagreen"
    )

    average_axis.set_title(
        "Average number of authors per article"
    )
    average_axis.set_ylabel("Average number of authors")
    average_axis.tick_params(
        axis="x",
        rotation=35
    )
    average_axis.grid(
        axis="y",
        alpha=0.3
    )

    for index, value in enumerate(average_values):
        average_axis.text(
            index,
            value,
            f"{value:.2f}",
            ha="center",
            va="bottom"
        )

    for axis in axes[plot_count:]:
        axis.set_visible(False)

    fig.suptitle(
        "Author comparison by arXiv category",
        fontsize=18
    )

    fig.tight_layout()
    plt.show() 
    

#res = descarca_arxiv("cat:physics.optics", 50)
#df  = parseaza(res)


compare(["cat:physics.optics",  "cat:cs.NI", "cat:cs.AI"])
#author_analysis(df)
#title_analysis(df)

#create_files(df)
#read_files()
