"""NASA Image Gallery with a year slider.
Run: streamlit run nasa_gallery.py
Needs: pip install streamlit requests
Data: NASA Image and Video Library API (https://images-api.nasa.gov), no key needed.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date

import altair as alt
import pandas as pd
import requests
import streamlit as st

BASE_URL = "https://images-api.nasa.gov"
MIN_YEAR = 1920
MAX_YEAR = date.today().year

st.set_page_config(page_title="NASA Image Gallery", page_icon="🌌", layout="wide")


@st.cache_data(show_spinner=False)
def search_images(query, year_start, year_end):
    """Ask NASA for images created between year_start and year_end (inclusive).

    The API does the year filtering, so any year works, even if it would not
    appear in the first page of unfiltered results.
    """
    resp = requests.get(
        f"{BASE_URL}/search",
        params={
            "q": query,
            "media_type": "image",
            "year_start": year_start,
            "year_end": year_end,
        },
        timeout=10,
    )
    resp.raise_for_status()
    collection = resp.json()["collection"]
    total_hits = collection.get("metadata", {}).get("total_hits", 0)

    images = []
    for item in collection["items"]:
        data = item["data"][0]
        links = item.get("links", [])
        if not links:
            continue
        images.append({
            "title": data.get("title", "Untitled"),
            "date": data.get("date_created", "")[:10],
            "center": data.get("center", "Unknown"),
            "description": data.get("description", ""),
            "keywords": data.get("keywords", []),
            "nasa_id": data.get("nasa_id"),
            "url": links[0]["href"],
        })
    return images, total_hits


def _count_for_year(query, year):
    """Number of images NASA has for `query` in one year (asks for 1 item only)."""
    try:
        resp = requests.get(
            f"{BASE_URL}/search",
            params={"q": query, "media_type": "image", "year_start": year,
                    "year_end": year, "page_size": 1},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["collection"].get("metadata", {}).get("total_hits", 0)
    except (requests.RequestException, ValueError, KeyError):
        return 0


@st.cache_data(show_spinner=False)
def pictures_per_year(query):
    """Count images for every year from MIN_YEAR to MAX_YEAR (requests run in parallel)."""
    years = list(range(MIN_YEAR, MAX_YEAR + 1))
    with ThreadPoolExecutor(max_workers=10) as pool:
        counts = list(pool.map(lambda y: _count_for_year(query, y), years))
    return pd.DataFrame({"year": years, "pictures": counts})


# ------------------------------ Inputs ------------------------------------
st.title("🌌 NASA Image Gallery")
st.write("Search NASA's archive and slide to the year an image was created.")

query = st.sidebar.text_input("Search term", "Moon")
use_range = st.sidebar.checkbox("Pick a range of years instead of one year")

if use_range:
    year_start, year_end = st.sidebar.slider(
        "Year created", MIN_YEAR, MAX_YEAR, (1969, 1972)
    )
else:
    year_start = year_end = st.sidebar.slider("Year created", MIN_YEAR, MAX_YEAR, 1969)

max_images = st.sidebar.slider("Max images to show", 6, 60, 18, step=6)
columns = st.sidebar.select_slider("Gallery columns", options=[2, 3, 4, 5], value=3)

if not query.strip():
    st.info("Enter a search term in the sidebar.")
    st.stop()

# ------------------------------ Results -----------------------------------
try:
    with st.spinner("Contacting NASA..."):
        images, total_hits = search_images(query.strip(), year_start, year_end)
except requests.RequestException as error:
    st.error(f"Could not reach the NASA API: {error}")
    st.stop()

label = str(year_start) if year_start == year_end else f"{year_start} to {year_end}"
st.subheader(f"'{query}' images created in {label}")

if not images:
    st.warning("No images found. Try a different year or search term.")
    st.stop()

shown = images[:max_images]
st.caption(f"{total_hits:,} matching images in NASA's archive. Showing {len(shown)}.")

# Pictures per year chart (highlights the year or range chosen on the slider)
st.subheader(f"Pictures per year for '{query}'")
with st.spinner("Counting pictures for every year (cached after the first time)..."):
    per_year = pictures_per_year(query.strip())
per_year = per_year[per_year["pictures"] > 0].copy()

if per_year.empty:
    st.caption("No picture counts available for this search.")
else:
    per_year["selected"] = per_year["year"].between(year_start, year_end)
    st.altair_chart(
        alt.Chart(per_year).mark_bar().encode(
            x=alt.X("year:O", title="Year created"),
            y=alt.Y("pictures:Q", title="Number of pictures"),
            color=alt.condition(alt.datum.selected, alt.value("#e4572e"), alt.value("#4c78a8")),
            tooltip=["year", "pictures"],
        ),
        use_container_width=True,
    )
    busiest = per_year.loc[per_year["pictures"].idxmax()]
    st.caption(f"Busiest year: {int(busiest['year'])} with {int(busiest['pictures']):,} pictures. "
               "Orange bars are the year(s) selected on the slider.")

# Image grid
grid = st.columns(columns)
for i, img in enumerate(shown):
    with grid[i % columns]:
        st.image(img["url"], use_container_width=True)
        st.markdown(f"**{img['title']}**")
        st.caption(f"{img['date']} | {img['center']}")
        with st.expander("Details"):
            st.write(img["description"][:500] or "No description provided.")
            if img["keywords"]:
                st.caption("Keywords: " + ", ".join(img["keywords"][:8]))
            st.caption(f"NASA ID: {img['nasa_id']}")
