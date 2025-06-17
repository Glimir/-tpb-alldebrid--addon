from flask import Flask, jsonify, request
import requests
from urllib.parse import quote
import os

app = Flask(__name__)

ALL_DEBRID_API_KEY = os.getenv("ALL_DEBRID_API_KEY", "TA_CLE_API_ICI")

def search_tpb(query):
    url = f"https://apibay.org/q.php?q={quote(query)}"
    try:
        results = requests.get(url, timeout=5).json()
        return results[:10] if isinstance(results, list) else []
    except:
        return []

def debrid_magnet(info_hash):
    magnet = f"magnet:?xt=urn:btih:{info_hash}"
    resp = requests.post(
        'https://api.alldebrid.com/v4/magnet/upload',
        params={"agent": "StremioAddon", "apikey": ALL_DEBRID_API_KEY},
        data={"magnets[]": magnet}
    )
    if resp.status_code != 200:
        return []

    data = resp.json()
    if not data.get('data') or not data['data'].get('magnets'):
        return []

    magnet_id = data['data']['magnets'][0]['id']

    details = requests.get(
        'https://api.alldebrid.com/v4/magnet/status',
        params={"agent": "StremioAddon", "apikey": ALL_DEBRID_API_KEY, "id": magnet_id}
    ).json()

    links = []
    for f in details.get("data", {}).get("magnets", {}).get("links", []):
        if f.lower().split("?")[0].endswith(('.mp4', '.mkv')):
            links.append(f)
    return links

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "id": "org.piratebay.alldebrid",
        "version": "1.0.0",
        "name": "The Pirate Bay + AllDebrid",
        "description": "Stream TPB torrents avec AllDebrid",
        "types": ["movie"],
        "catalogs": [
            {
                "type": "movie",
                "id": "tpb_catalog",
                "name": "The Pirate Bay",
                "extra": [{"name": "search", "isRequired": False}]
            }
        ],
        "resources": ["catalog", "stream"],
        "idPrefixes": ["tpb:"]
    })

@app.route("/catalog/movie/tpb_catalog.json")
def catalog():
    query = request.args.get("search") or "inception"
    results = search_tpb(query)
    metas = []
    for r in results:
        metas.append({
            "id": f"tpb:{r.get('info_hash')}",
            "type": "movie",
            "name": r.get("name"),
            "poster": "https://upload.wikimedia.org/wikipedia/commons/7/70/The_Pirate_Bay_logo.png"
        })
    return jsonify({"metas": metas})

@app.route("/stream/movie/<id>.json")
def stream(id):
    if not id.startswith("tpb:"):
        return jsonify({"streams": []})
    info_hash = id.replace("tpb:", "")
    links = debrid_magnet(info_hash)
    streams = []
    for link in links:
        streams.append({
            "name": "TPB + AllDebrid",
            "url": link,
            "title": "AllDebrid Stream",
            "behaviorHints": {"notWebReady": False}
        })
    return jsonify({"streams": streams})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)