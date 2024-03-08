import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote
from typing import Optional, Tuple, Dict, List
from sources.vidplay import VidplayExtractor
from sources.filemoon import FilemoonExtractor
from utils import Utilities, VidSrcError, NoSourcesFound
from flask import Flask,jsonify
from tinydb import TinyDB,Query

SUPPORTED_SOURCES = ["Vidplay", "Filemoon"]

class VidSrcExtractor:
    BASE_URL : str = "https://vidsrc.to"
    DEFAULT_KEY : str = "8z5Ag5wgagfsOuhz"
    PROVIDER_URL : str = "https://vidplay.online" # vidplay.site / vidplay.online / vidplay.lol
    TMDB_BASE_URL : str = "https://www.themoviedb.org"
    USER_AGENT : str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"

    def __init__(self, **kwargs) -> None:
        self.source_name = kwargs.get("source_name")
        self.fetch_subtitles = kwargs.get("fetch_subtitles")

    def decrypt_source_url(self, source_url: str) -> str:
        encoded = Utilities.decode_base64_url_safe(source_url)
        decoded = Utilities.decode_data(VidSrcExtractor.DEFAULT_KEY, encoded)
        decoded_text = decoded.decode('utf-8')

        return unquote(decoded_text)

    def get_source_url(self, source_id: str) -> str:
        req = requests.get(f"{VidSrcExtractor.BASE_URL}/ajax/embed/source/{source_id}")
        if req.status_code != 200:
            error_msg = f"Couldnt fetch {req.url}, status code: {req.status_code}..."
            raise VidSrcError(error_msg)

        data = req.json()
        encrypted_source_url = data.get("result", {}).get("url")
        return self.decrypt_source_url(encrypted_source_url)

    def get_sources(self, data_id: str) -> Dict:
        req = requests.get(f"{VidSrcExtractor.BASE_URL}/ajax/embed/episode/{data_id}/sources")
        if req.status_code != 200:
            error_msg = f"Couldnt fetch {req.url}, status code: {req.status_code}..."
            raise VidSrcError(error_msg)
        
        data = req.json()
        return {video.get("title"): video.get("id") for video in data.get("result")}

    def get_streams(self, media_type: str, media_id: str, season: Optional[str], episode: Optional[str]) -> Tuple[Optional[List], Optional[Dict]]:
        url = f"{VidSrcExtractor.BASE_URL}/embed/{media_type}/{media_id}"
        if season and episode:
            url += f"/{season}/{episode}"

        print(f"[>] Requesting {url}...")
        req = requests.get(url)
        if req.status_code != 200:
            print(f"[VidSrcExtractor] Couldnt fetch \"{req.url}\", status code: {req.status_code}\n[VidSrcExtractor] \"{self.source_name}\" likely doesnt have the requested media...")
            return None, None

        soup = BeautifulSoup(req.text, "html.parser")
        sources_code = soup.find('a', {'data-id': True})
        if not sources_code:
            print("[VidSrcExtractor] Could not fetch data-id, this could be due to an invalid imdb/tmdb code...")
            return None, None

        sources_code = sources_code.get("data-id")
        sources = self.get_sources(sources_code)
        source = sources.get(self.source_name)
        if not source:
            available_sources = ", ".join(list(sources.keys()))
            print(f"[VidSrcExtractor] No source found for \"{self.source_name}\"\nAvailable Sources: {available_sources}")
            return None, None

        source_url = self.get_source_url(source)
        if "vidplay" in source_url:
            print(f"[>] Fetching source for \"{self.source_name}\"...")

            extractor = VidplayExtractor()
            return extractor.resolve_source(url=source_url, fetch_subtitles=self.fetch_subtitles, provider_url=VidSrcExtractor.PROVIDER_URL)
        
        elif "filemoon" in source_url:
            print(f"[>] Fetching source for \"{self.source_name}\"...")

            if self.fetch_subtitles: 
                print(f"[VidSrcExtractor] \"{self.source_name}\" doesnt provide subtitles...")

            extractor = FilemoonExtractor()
            return extractor.resolve_source(url=source_url, fetch_subtitles=self.fetch_subtitles, provider_url=VidSrcExtractor.PROVIDER_URL)
        
        else:
            print(f"[VidSrcExtractor] Sorry, this doesnt currently support \"{self.source_name}\" :(\n[VidSrcExtractor] (if you create an issue and ask really nicely ill maybe look into reversing it though)...")
            return None, None
        
    def query_tmdb(self, query: str) -> Dict:
        req = requests.get(f"{VidSrcExtractor.TMDB_BASE_URL}/search", params={'query': query.replace(" ", "+").lower()}, headers={'user-agent': VidSrcExtractor.USER_AGENT})
        soup = BeautifulSoup(req.text, "html.parser")
        results = {}

        for index, data in enumerate(soup.find_all("div", {"class": "details"}), start=1):
            result = data.find("a", {"class": "result"})
            title = result.find()

            if not title:
                continue

            title = title.text
            release_date = data.find("span", {"class": "release_date"})
            release_date = release_date.text if release_date else "1 January, 1970"
            url = result.get("href")

            if not url:
                continue
            
            result_type, result_id = url[1:].split("/")
            results.update({f"{index}. {title} ({release_date})": {"media_type": result_type, "tmdb_id": result_id}})

        return results

db = TinyDB('idDb.json')
q = Query()
app = Flask(__name__)
domain = 'https://consumet-api-hp98.onrender.com/anime/gogoanime/watch/'
with open('index.html','r') as file :
    doc = file.read()
@app.route('/')
def home():
    
    return doc

@app.route('/anime/<id>/<ep>/<type>')
def Anime(id,type,ep):
    obj = db.search((q.id2==id)&(q.type==type))
    res = requests.get(domain+obj[0]['id']+f'-episode-{ep}').json()
    return jsonify(res['sources'])
    # return jsonify({'name':obj[0][id]})
    

@app.route('/movie/<tmdb>')
def Movie(tmdb):
    vse = VidSrcExtractor(source_name =SUPPORTED_SOURCES[0] ,
        fetch_subtitles = True,)
    m3u8,sub = vse.get_streams('movie',tmdb,None,None)
    modified_m3u8 = [   m3.replace('#.mp4','') for m3 in m3u8 ]
    obj = {'m3u8':modified_m3u8,'sub':sub}
    return jsonify(obj)

@app.route('/tv/<tmdb>/<ss>/<ep>')
def Tv(tmdb,ss,ep):
    vse = VidSrcExtractor(source_name =SUPPORTED_SOURCES[0] ,
        fetch_subtitles = True,)
    m3u8,sub = vse.get_streams('tv',tmdb,ss,ep)
    modified_m3u8 = [   m3.replace('#.mp4','') for m3 in m3u8 ]
    obj = {'m3u8':modified_m3u8,'sub':sub}
    return jsonify(obj)

    # return jsonify(obj)

    

if __name__ == "__main__":
    vse = VidSrcExtractor(source_name =SUPPORTED_SOURCES[0] ,
        fetch_subtitles = True,)
    
    
    host = os.environ.get('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))

    app.run(host=host, port=port, debug=False)