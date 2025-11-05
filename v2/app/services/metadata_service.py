
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MetadataService:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"

    def search_series(self, query):
        if not self.api_key:
            logging.error("TMDB API key is not set.")
            return []

        endpoint = f"{self.base_url}/search/tv"
        params = {
            "api_key": self.api_key,
            "query": query
        }

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors
            data = response.json()
            return data.get("results", [])
        except requests.exceptions.RequestException as e:
            logging.error(f"Error searching series: {e}")
            return []

    def get_series_details(self, series_id):
        if not self.api_key:
            logging.error("TMDB API key is not set.")
            return None

        endpoint = f"{self.base_url}/tv/{series_id}"
        params = {
            "api_key": self.api_key
        }

        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error getting series details: {e}")
            return None
