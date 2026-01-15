"""
Base Web Scraper and Specific Source Scrapers
Collects metadata dynamically from the internet - NO static datasets
"""

import asyncio
import aiohttp
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
import json
import re

from ..config import get_settings
from ..utils import normalize_title, extract_year_from_text, clean_html, detect_content_type

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class ScrapedWork:
    """Represents a work scraped from the web"""
    title: str
    creator: Optional[str] = None
    publication_year: Optional[int] = None
    creator_death_year: Optional[int] = None
    content_type: Optional[str] = None
    source_url: str = ""
    source_name: str = ""
    description: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.7
    scraped_at: datetime = field(default_factory=datetime.utcnow)


class BaseScraper(ABC):
    """Abstract base class for all scrapers"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            'User-Agent': settings.USER_AGENT,
            'Accept': 'application/json, text/html',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.rate_limit_delay = settings.SCRAPING_DELAY
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch(self, url: str) -> Optional[str]:
        """Fetch URL with rate limiting and error handling"""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)
        
        try:
            await asyncio.sleep(self.rate_limit_delay)
            
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching {url}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    async def fetch_json(self, url: str) -> Optional[Dict]:
        """Fetch JSON endpoint"""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)
        
        try:
            await asyncio.sleep(self.rate_limit_delay)
            
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching JSON {url}: {e}")
            return None
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the data source"""
        pass
    
    @abstractmethod
    async def search(self, query: str, content_type: Optional[str] = None) -> List[ScrapedWork]:
        """Search for works by title"""
        pass
    
    @abstractmethod
    async def get_details(self, identifier: str) -> Optional[ScrapedWork]:
        """Get detailed information about a specific work"""
        pass


class OpenLibraryScraper(BaseScraper):
    """
    Scraper for Open Library API
    Provides book metadata from the world's largest open library catalog
    """
    
    BASE_URL = "https://openlibrary.org"
    
    @property
    def source_name(self) -> str:
        return "Open Library"
    
    async def search(self, query: str, content_type: Optional[str] = None) -> List[ScrapedWork]:
        """Search Open Library for books"""
        # Only search for books
        if content_type and content_type != "book":
            return []
        
        search_url = f"{self.BASE_URL}/search.json?q={query}&limit=10"
        
        data = await self.fetch_json(search_url)
        if not data or 'docs' not in data:
            return []
        
        results = []
        for doc in data['docs'][:settings.MAX_SEARCH_RESULTS]:
            try:
                work = ScrapedWork(
                    title=doc.get('title', 'Unknown'),
                    creator=doc.get('author_name', [None])[0] if doc.get('author_name') else None,
                    publication_year=doc.get('first_publish_year'),
                    content_type="book",
                    source_url=f"{self.BASE_URL}{doc.get('key', '')}",
                    source_name=self.source_name,
                    additional_data={
                        'isbn': doc.get('isbn', []),
                        'publisher': doc.get('publisher', []),
                        'subject': doc.get('subject', [])[:5] if doc.get('subject') else [],
                        'language': doc.get('language', []),
                        'edition_count': doc.get('edition_count', 0),
                    },
                    confidence=0.85  # Open Library is reliable
                )
                results.append(work)
            except Exception as e:
                logger.error(f"Error parsing Open Library result: {e}")
                continue
        
        return results
    
    async def get_details(self, work_key: str) -> Optional[ScrapedWork]:
        """Get detailed book information"""
        url = f"{self.BASE_URL}{work_key}.json"
        
        data = await self.fetch_json(url)
        if not data:
            return None
        
        # Get author details for death year
        author_death_year = None
        if 'authors' in data and data['authors']:
            author_key = data['authors'][0].get('author', {}).get('key', '')
            if author_key:
                author_data = await self.fetch_json(f"{self.BASE_URL}{author_key}.json")
                if author_data and 'death_date' in author_data:
                    author_death_year = extract_year_from_text(author_data['death_date'])
        
        description = ""
        if 'description' in data:
            if isinstance(data['description'], dict):
                description = data['description'].get('value', '')
            else:
                description = str(data['description'])
        
        return ScrapedWork(
            title=data.get('title', 'Unknown'),
            creator=data.get('by_statement'),
            creator_death_year=author_death_year,
            publication_year=extract_year_from_text(str(data.get('first_publish_date', ''))),
            content_type="book",
            source_url=f"{self.BASE_URL}{work_key}",
            source_name=self.source_name,
            description=description[:500] if description else None,
            confidence=0.9
        )


class WikipediaScraper(BaseScraper):
    """
    Scraper for Wikipedia API
    Provides general information about creative works across all types
    """
    
    BASE_URL = "https://en.wikipedia.org/w/api.php"
    
    @property
    def source_name(self) -> str:
        return "Wikipedia"
    
    async def search(self, query: str, content_type: Optional[str] = None) -> List[ScrapedWork]:
        """Search Wikipedia for works"""
        # Add content type to search if specified
        search_query = query
        if content_type:
            type_qualifiers = {
                'book': 'novel book literature',
                'music': 'song album music musician',
                'film': 'film movie cinema',
                'article': 'article paper',
                'image': 'painting photograph artwork',
                'patent': 'patent invention technology',
                'software': 'software application programming',
                'code': 'software library framework',
                'trademark': 'trademark brand company',
                'academic_paper': 'research paper academic study',
            }
            if content_type in type_qualifiers:
                search_query = f"{query} {type_qualifiers[content_type]}"
        
        params = {
            'action': 'query',
            'list': 'search',
            'srsearch': search_query,
            'format': 'json',
            'srlimit': 10,
            'srprop': 'snippet|timestamp'
        }
        
        url = f"{self.BASE_URL}?" + "&".join(f"{k}={v}" for k, v in params.items())
        
        data = await self.fetch_json(url)
        if not data or 'query' not in data:
            return []
        
        results = []
        for item in data['query'].get('search', []):
            try:
                snippet = clean_html(item.get('snippet', ''))
                detected_type = detect_content_type(snippet, item.get('title', ''))
                
                # If content_type is specified, ONLY return matching results
                # Use the specified type, or skip if detection doesn't match
                final_type = content_type if content_type else detected_type
                
                # Skip if user specified a type but detection found something different
                if content_type and detected_type and detected_type != content_type:
                    # Only skip if detected type is clearly different
                    continue
                
                # Extract year from snippet
                year = extract_year_from_text(snippet)
                
                work = ScrapedWork(
                    title=item.get('title', 'Unknown'),
                    publication_year=year,
                    content_type=final_type,
                    source_url=f"https://en.wikipedia.org/wiki/{item.get('title', '').replace(' ', '_')}",
                    source_name=self.source_name,
                    description=snippet[:300],
                    additional_data={
                        'page_id': item.get('pageid'),
                        'word_count': item.get('wordcount', 0),
                    },
                    confidence=0.75
                )
                results.append(work)
            except Exception as e:
                logger.error(f"Error parsing Wikipedia result: {e}")
                continue
        
        return results
    
    async def get_details(self, page_title: str) -> Optional[ScrapedWork]:
        """Get detailed information from Wikipedia page"""
        params = {
            'action': 'query',
            'titles': page_title,
            'format': 'json',
            'prop': 'extracts|info|categories',
            'exintro': 'true',
            'explaintext': 'true',
            'inprop': 'url'
        }
        
        url = f"{self.BASE_URL}?" + "&".join(f"{k}={v}" for k, v in params.items())
        
        data = await self.fetch_json(url)
        if not data or 'query' not in data:
            return None
        
        pages = data['query'].get('pages', {})
        if not pages:
            return None
        
        page = list(pages.values())[0]
        if 'missing' in page:
            return None
        
        extract = page.get('extract', '')
        
        # Try to extract author/creator from text
        creator = None
        creator_patterns = [
            r'by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'written by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'directed by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'composed by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        ]
        
        for pattern in creator_patterns:
            match = re.search(pattern, extract)
            if match:
                creator = match.group(1)
                break
        
        return ScrapedWork(
            title=page.get('title', 'Unknown'),
            creator=creator,
            publication_year=extract_year_from_text(extract),
            content_type=detect_content_type(extract, page.get('title', '')),
            source_url=page.get('fullurl', ''),
            source_name=self.source_name,
            description=extract[:500] if extract else None,
            confidence=0.8
        )


class MusicBrainzScraper(BaseScraper):
    """
    Scraper for MusicBrainz API
    Provides music metadata (songs, albums, artists)
    """
    
    BASE_URL = "https://musicbrainz.org/ws/2"
    
    def __init__(self):
        super().__init__()
        self.headers['Accept'] = 'application/json'
        self.rate_limit_delay = 1.1  # MusicBrainz requires 1 req/sec
    
    @property
    def source_name(self) -> str:
        return "MusicBrainz"
    
    async def search(self, query: str, content_type: Optional[str] = None) -> List[ScrapedWork]:
        """Search MusicBrainz for music works"""
        if content_type and content_type not in ['music', None]:
            return []
        
        # Search for recordings (songs)
        url = f"{self.BASE_URL}/recording?query={query}&fmt=json&limit=10"
        
        data = await self.fetch_json(url)
        if not data or 'recordings' not in data:
            return []
        
        results = []
        for recording in data['recordings'][:settings.MAX_SEARCH_RESULTS]:
            try:
                # Extract artist
                artist = None
                if 'artist-credit' in recording and recording['artist-credit']:
                    artist = recording['artist-credit'][0].get('name')
                
                # Extract year from first release
                year = None
                if 'releases' in recording and recording['releases']:
                    date_str = recording['releases'][0].get('date', '')
                    year = extract_year_from_text(date_str)
                
                work = ScrapedWork(
                    title=recording.get('title', 'Unknown'),
                    creator=artist,
                    publication_year=year,
                    content_type="music",
                    source_url=f"https://musicbrainz.org/recording/{recording.get('id', '')}",
                    source_name=self.source_name,
                    additional_data={
                        'mbid': recording.get('id'),
                        'length_ms': recording.get('length'),
                        'disambiguation': recording.get('disambiguation'),
                    },
                    confidence=0.9
                )
                results.append(work)
            except Exception as e:
                logger.error(f"Error parsing MusicBrainz result: {e}")
                continue
        
        return results
    
    async def get_details(self, mbid: str) -> Optional[ScrapedWork]:
        """Get detailed recording information"""
        url = f"{self.BASE_URL}/recording/{mbid}?inc=artists+releases&fmt=json"
        
        data = await self.fetch_json(url)
        if not data:
            return None
        
        artist = None
        artist_death_year = None
        
        if 'artist-credit' in data and data['artist-credit']:
            artist_info = data['artist-credit'][0]
            artist = artist_info.get('name')
            
            # Try to get artist life span
            artist_id = artist_info.get('artist', {}).get('id')
            if artist_id:
                artist_data = await self.fetch_json(f"{self.BASE_URL}/artist/{artist_id}?fmt=json")
                if artist_data and 'life-span' in artist_data:
                    end_date = artist_data['life-span'].get('end')
                    if end_date:
                        artist_death_year = extract_year_from_text(end_date)
        
        year = None
        if 'releases' in data and data['releases']:
            date_str = data['releases'][0].get('date', '')
            year = extract_year_from_text(date_str)
        
        return ScrapedWork(
            title=data.get('title', 'Unknown'),
            creator=artist,
            creator_death_year=artist_death_year,
            publication_year=year,
            content_type="music",
            source_url=f"https://musicbrainz.org/recording/{mbid}",
            source_name=self.source_name,
            confidence=0.9
        )


class IMDbScraper(BaseScraper):
    """
    Scraper for film information using public web pages
    Note: IMDb doesn't have a free API, so we use careful web scraping
    """
    
    BASE_URL = "https://www.imdb.com"
    SEARCH_URL = "https://v2.sg.media-imdb.com/suggestion"
    
    @property
    def source_name(self) -> str:
        return "IMDb"
    
    async def search(self, query: str, content_type: Optional[str] = None) -> List[ScrapedWork]:
        """Search for films/shows"""
        if content_type and content_type not in ['film', None]:
            return []
        
        # IMDb has a suggestions API we can use
        first_letter = query[0].lower() if query else 'a'
        url = f"{self.SEARCH_URL}/{first_letter}/{query.replace(' ', '_')}.json"
        
        data = await self.fetch_json(url)
        if not data or 'd' not in data:
            return []
        
        results = []
        for item in data['d'][:settings.MAX_SEARCH_RESULTS]:
            try:
                # Filter for movies/shows
                item_type = item.get('qid', '')
                if item_type not in ['movie', 'tvSeries', 'tvMovie', 'short', 'video']:
                    continue
                
                work = ScrapedWork(
                    title=item.get('l', 'Unknown'),
                    creator=item.get('s'),  # Usually has actors, but sometimes directors
                    publication_year=item.get('y'),
                    content_type="film",
                    source_url=f"{self.BASE_URL}/title/{item.get('id', '')}/",
                    source_name=self.source_name,
                    additional_data={
                        'imdb_id': item.get('id'),
                        'type': item_type,
                        'rank': item.get('rank'),
                    },
                    confidence=0.85
                )
                results.append(work)
            except Exception as e:
                logger.error(f"Error parsing IMDb result: {e}")
                continue
        
        return results
    
    async def get_details(self, imdb_id: str) -> Optional[ScrapedWork]:
        """Get detailed film information"""
        # For detailed info, we'd need to parse the HTML page
        # This is a simplified version
        url = f"{self.BASE_URL}/title/{imdb_id}/"
        
        html = await self.fetch(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract basic info from meta tags and structured data
        title = soup.find('meta', property='og:title')
        title_text = title.get('content', 'Unknown') if title else 'Unknown'
        
        # Clean title (remove year in parentheses)
        title_text = re.sub(r'\s*\(\d{4}\)\s*$', '', title_text)
        
        year = None
        year_match = re.search(r'\((\d{4})\)', str(soup))
        if year_match:
            year = int(year_match.group(1))
        
        return ScrapedWork(
            title=title_text,
            publication_year=year,
            content_type="film",
            source_url=url,
            source_name=self.source_name,
            confidence=0.85
        )


class GitHubScraper(BaseScraper):
    """
    Scraper for GitHub - Software/Code projects
    Checks open source licenses
    """
    BASE_URL = "https://api.github.com"
    
    @property
    def source_name(self) -> str:
        return "GitHub"
    
    async def search(self, query: str, content_type: Optional[str] = None) -> List[ScrapedWork]:
        """Search GitHub repositories"""
        url = f"{self.BASE_URL}/search/repositories?q={query}&sort=stars&per_page=10"
        
        try:
            html = await self.fetch(url)
            if not html:
                return []
            
            data = json.loads(html)
            results = []
            
            for item in data.get('items', [])[:10]:
                # Determine license info
                license_info = item.get('license') or {}
                license_name = license_info.get('spdx_id') or license_info.get('name') or 'Unknown'
                
                # Create year from created_at
                created_at = item.get('created_at', '')
                year = int(created_at[:4]) if created_at else None
                
                work = ScrapedWork(
                    title=item.get('full_name', item.get('name', '')),
                    creator=item.get('owner', {}).get('login'),
                    publication_year=year,
                    content_type='software',
                    source_url=item.get('html_url', ''),
                    source_name=self.source_name,
                    description=item.get('description'),
                    additional_data={
                        'license': license_name,
                        'license_type': 'open_source' if license_name != 'Unknown' else 'unknown',
                        'stars': item.get('stargazers_count', 0),
                        'forks': item.get('forks_count', 0),
                        'language': item.get('language'),
                        'topics': item.get('topics', []),
                        'is_fork': item.get('fork', False),
                        'archived': item.get('archived', False),
                    },
                    confidence=0.9 if license_name != 'Unknown' else 0.7
                )
                results.append(work)
            
            return results
        except Exception as e:
            logger.error(f"GitHub search error: {e}")
            return []
    
    async def get_details(self, repo_name: str) -> Optional[ScrapedWork]:
        """Get detailed repository info"""
        url = f"{self.BASE_URL}/repos/{repo_name}"
        
        try:
            html = await self.fetch(url)
            if not html:
                return None
            
            item = json.loads(html)
            license_info = item.get('license') or {}
            license_name = license_info.get('spdx_id') or license_info.get('name') or 'Unknown'
            created_at = item.get('created_at', '')
            year = int(created_at[:4]) if created_at else None
            
            return ScrapedWork(
                title=item.get('full_name', item.get('name', '')),
                creator=item.get('owner', {}).get('login'),
                publication_year=year,
                content_type='software',
                source_url=item.get('html_url', ''),
                source_name=self.source_name,
                description=item.get('description'),
                additional_data={
                    'license': license_name,
                    'license_url': license_info.get('url'),
                    'stars': item.get('stargazers_count', 0),
                    'forks': item.get('forks_count', 0),
                    'language': item.get('language'),
                    'open_issues': item.get('open_issues_count', 0),
                    'topics': item.get('topics', []),
                },
                confidence=0.95
            )
        except Exception as e:
            logger.error(f"GitHub details error: {e}")
            return None


class PatentScraper(BaseScraper):
    """
    Scraper for Patents - Uses USPTO/EPO public APIs
    """
    BASE_URL = "https://api.patentsview.org/patents/query"
    
    @property
    def source_name(self) -> str:
        return "USPTO Patent Database"
    
    async def search(self, query: str, content_type: Optional[str] = None) -> List[ScrapedWork]:
        """Search patents"""
        # PatentsView API query
        payload = {
            "q": {"_text_any": {"patent_title": query}},
            "f": ["patent_number", "patent_title", "patent_date", "patent_abstract", 
                  "inventor_first_name", "inventor_last_name", "assignee_organization",
                  "patent_type"],
            "o": {"per_page": 10}
        }
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(headers=self.headers)
            
            await asyncio.sleep(self.rate_limit_delay)
            
            async with self.session.post(
                self.BASE_URL, 
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    logger.warning(f"Patent API returned {response.status}")
                    return []
                
                data = await response.json()
                results = []
                
                for patent in data.get('patents', [])[:10]:
                    # Extract year from date
                    patent_date = patent.get('patent_date', '')
                    year = int(patent_date[:4]) if patent_date else None
                    
                    # Get inventor names
                    inventors = patent.get('inventors', [{}])
                    inventor = f"{inventors[0].get('inventor_first_name', '')} {inventors[0].get('inventor_last_name', '')}" if inventors else None
                    
                    # Calculate patent status (20 years from filing)
                    status = 'active'
                    if year and (datetime.now().year - year) > 20:
                        status = 'expired'
                    
                    work = ScrapedWork(
                        title=patent.get('patent_title', ''),
                        creator=inventor,
                        publication_year=year,
                        content_type='patent',
                        source_url=f"https://patents.google.com/patent/US{patent.get('patent_number')}",
                        source_name=self.source_name,
                        description=patent.get('patent_abstract'),
                        additional_data={
                            'patent_number': patent.get('patent_number'),
                            'patent_type': patent.get('patent_type'),
                            'assignee': patent.get('assignees', [{}])[0].get('assignee_organization') if patent.get('assignees') else None,
                            'ip_status': status,
                            'expiry_years': 20,
                        },
                        confidence=0.9
                    )
                    results.append(work)
                
                return results
        except Exception as e:
            logger.error(f"Patent search error: {e}")
            # Fallback to Wikipedia for patent info
            return await self._wikipedia_fallback(query)
    
    async def _wikipedia_fallback(self, query: str) -> List[ScrapedWork]:
        """Fallback to Wikipedia for patent information"""
        wiki = WikipediaScraper()
        results = await wiki.search(f"{query} patent invention", 'patent')
        for r in results:
            r.content_type = 'patent'
        return results
    
    async def get_details(self, identifier: str) -> Optional[ScrapedWork]:
        """Get detailed patent info"""
        return None  # Would need specific patent number lookup


class TrademarkScraper(BaseScraper):
    """
    Scraper for Trademarks - Uses public trademark databases
    """
    BASE_URL = "https://tmsearch.uspto.gov"
    
    @property
    def source_name(self) -> str:
        return "USPTO Trademark Database"
    
    async def search(self, query: str, content_type: Optional[str] = None) -> List[ScrapedWork]:
        """Search trademarks - uses Wikipedia as proxy since direct API is complex"""
        # USPTO TESS doesn't have a public API, so we use Wikipedia
        wiki = WikipediaScraper()
        wiki_results = await wiki.search(f"{query} trademark brand", None)
        
        results = []
        for r in wiki_results:
            # Check if it mentions trademark in description
            desc = (r.description or '').lower()
            title_lower = r.title.lower()
            
            if 'trademark' in desc or 'brand' in desc or 'logo' in desc:
                r.content_type = 'trademark'
                r.additional_data['ip_type'] = 'trademark'
                r.additional_data['ip_status'] = 'registered' if 'registered' in desc else 'unknown'
                r.additional_data['renewable'] = True  # Trademarks can be renewed indefinitely
                results.append(r)
            elif query.lower() in title_lower:
                # Assume it could be a trademark
                work = ScrapedWork(
                    title=r.title,
                    creator=r.creator,
                    publication_year=r.publication_year,
                    content_type='trademark',
                    source_url=r.source_url,
                    source_name='Wikipedia (Trademark)',
                    description=r.description,
                    additional_data={
                        'ip_type': 'trademark',
                        'ip_status': 'unknown',
                        'renewable': True,
                        'note': 'Trademarks can be renewed indefinitely if in use'
                    },
                    confidence=0.6
                )
                results.append(work)
        
        return results[:5]
    
    async def get_details(self, identifier: str) -> Optional[ScrapedWork]:
        """Get detailed trademark info"""
        return None


class AcademicScraper(BaseScraper):
    """
    Scraper for Academic Papers - Uses OpenAlex/Semantic Scholar
    """
    BASE_URL = "https://api.openalex.org"
    
    @property
    def source_name(self) -> str:
        return "OpenAlex Academic Database"
    
    async def search(self, query: str, content_type: Optional[str] = None) -> List[ScrapedWork]:
        """Search academic papers"""
        url = f"{self.BASE_URL}/works?search={query}&per-page=10"
        
        try:
            html = await self.fetch(url)
            if not html:
                return []
            
            data = json.loads(html)
            results = []
            
            for item in data.get('results', [])[:10]:
                # Extract author
                authors = item.get('authorships', [])
                author = authors[0].get('author', {}).get('display_name') if authors else None
                
                # Get year
                year = item.get('publication_year')
                
                # Check if open access
                oa = item.get('open_access', {})
                is_open = oa.get('is_oa', False)
                
                work = ScrapedWork(
                    title=item.get('display_name', item.get('title', '')),
                    creator=author,
                    publication_year=year,
                    content_type='academic_paper',
                    source_url=item.get('doi') or item.get('id', ''),
                    source_name=self.source_name,
                    description=None,  # Would need another API call
                    additional_data={
                        'doi': item.get('doi'),
                        'open_access': is_open,
                        'oa_status': oa.get('oa_status'),
                        'cited_by_count': item.get('cited_by_count', 0),
                        'type': item.get('type'),
                        'license': 'Open Access' if is_open else 'Restricted',
                    },
                    confidence=0.85 if is_open else 0.75
                )
                results.append(work)
            
            return results
        except Exception as e:
            logger.error(f"Academic search error: {e}")
            return []
    
    async def get_details(self, identifier: str) -> Optional[ScrapedWork]:
        """Get detailed paper info"""
        return None


class IndianCopyrightScraper(BaseScraper):
    """
    Scraper for Indian Copyright Office (copyright.gov.in)
    Searches the official Indian copyright registration database
    Uses E-Register and search functionality
    """
    
    BASE_URL = "https://copyright.gov.in"
    SEARCH_URL = "https://copyright.gov.in/SearchRoc.aspx"
    E_REGISTER_URLS = [
        "https://copyright.gov.in/ERegister.aspx",  # 2025
        "https://copyright.gov.in/ERegister_2024.aspx",
        "https://copyright.gov.in/ERegister_2023.aspx",
        "https://copyright.gov.in/ERegister_2022.aspx",
        "https://copyright.gov.in/ERegister_2021.aspx",
        "https://copyright.gov.in/ERegister_2020.aspx",
    ]
    
    @property
    def source_name(self) -> str:
        return "Indian Copyright Office"
    
    async def search(self, query: str, content_type: Optional[str] = None) -> List[ScrapedWork]:
        """Search Indian Copyright Office database"""
        results = []
        query_lower = query.lower()
        
        try:
            # Method 1: Search E-Register pages (most reliable)
            for register_url in self.E_REGISTER_URLS[:3]:  # Check last 3 years
                try:
                    html = await self.fetch(register_url)
                    if html:
                        register_results = await self._parse_e_register(html, query_lower, content_type, register_url)
                        results.extend(register_results)
                        if len(results) >= 10:
                            break
                except Exception as e:
                    logger.warning(f"Error fetching E-Register {register_url}: {e}")
                    continue
            
            # Method 2: Try the search form
            if len(results) < 5:
                try:
                    search_results = await self._search_via_form(query, content_type)
                    results.extend(search_results)
                except Exception as e:
                    logger.warning(f"Error with form search: {e}")
            
            # Method 3: Fallback to Wikipedia for Indian works
            if len(results) < 3:
                fallback_results = await self._search_fallback(query, content_type)
                results.extend(fallback_results)
            
            # Remove duplicates by title
            seen_titles = set()
            unique_results = []
            for r in results:
                if r.title.lower() not in seen_titles:
                    seen_titles.add(r.title.lower())
                    unique_results.append(r)
            
            return unique_results[:10]
            
        except Exception as e:
            logger.error(f"Indian Copyright search error: {e}")
            return await self._search_fallback(query, content_type)
    
    async def _parse_e_register(self, html: str, query: str, content_type: Optional[str], source_url: str) -> List[ScrapedWork]:
        """Parse E-Register page for registered works"""
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find the main table with registrations
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            
            for row in rows[1:]:  # Skip header row
                try:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 3:
                        continue
                    
                    # Extract data from cells
                    # Typical columns: ROC No, Diary No, Title, Category, Author/Applicant
                    cell_texts = [clean_html(cell.get_text()) for cell in cells]
                    
                    # Find title (usually longest text or in a specific column)
                    title = None
                    author = None
                    category = None
                    roc_number = None
                    
                    for i, text in enumerate(cell_texts):
                        text_lower = text.lower()
                        # ROC number pattern
                        if 'roc' in text_lower or re.match(r'^[A-Z]-\d+', text):
                            roc_number = text
                        # Category detection
                        elif any(cat in text_lower for cat in ['literary', 'artistic', 'musical', 'cinematograph', 'sound', 'software']):
                            category = text
                        # Title is usually the longest meaningful text
                        elif len(text) > 10 and not text.isdigit():
                            if title is None or len(text) > len(title):
                                if title:
                                    author = title  # Previous title becomes author
                                title = text
                    
                    if not title:
                        continue
                    
                    # Check if query matches
                    if query not in title.lower():
                        continue
                    
                    # Detect content type from category
                    detected_type = self._detect_type_from_category(category) if category else content_type
                    
                    # Extract year from ROC number or URL
                    year = None
                    if '2025' in source_url:
                        year = 2025
                    elif '2024' in source_url:
                        year = 2024
                    elif '2023' in source_url:
                        year = 2023
                    elif '2022' in source_url:
                        year = 2022
                    
                    work = ScrapedWork(
                        title=title[:200],
                        creator=author[:100] if author else None,
                        publication_year=year,
                        content_type=detected_type or 'book',
                        source_url=source_url,
                        source_name=self.source_name,
                        description=f"Registered with Indian Copyright Office. ROC: {roc_number}" if roc_number else "Registered with Indian Copyright Office",
                        additional_data={
                            'jurisdiction': 'IN',
                            'registration_country': 'India',
                            'copyright_registered': True,
                            'roc_number': roc_number,
                            'category': category
                        },
                        confidence=0.9
                    )
                    results.append(work)
                    
                except Exception as e:
                    continue
        
        return results
    
    async def _search_via_form(self, query: str, content_type: Optional[str]) -> List[ScrapedWork]:
        """Search using the search form with title parameter"""
        results = []
        
        # The search form uses POST with ASP.NET viewstate
        # Try a GET-based approach with the Fresh Applications page
        fresh_url = "https://copyright.gov.in/Fresh_Applications.aspx"
        
        try:
            html = await self.fetch(fresh_url)
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for application entries
                entries = soup.find_all(['tr', 'div'], class_=re.compile(r'(GridView|row)', re.I))
                
                for entry in entries[:20]:
                    try:
                        text = entry.get_text()
                        if query.lower() in text.lower():
                            # Extract title
                            cells = entry.find_all('td')
                            if cells and len(cells) >= 2:
                                title = clean_html(cells[1].get_text()) if len(cells) > 1 else clean_html(cells[0].get_text())
                                
                                if title and len(title) > 3:
                                    work = ScrapedWork(
                                        title=title[:200],
                                        content_type=content_type or 'book',
                                        source_url=fresh_url,
                                        source_name=self.source_name,
                                        description="Fresh application - Indian Copyright Office",
                                        additional_data={
                                            'jurisdiction': 'IN',
                                            'status': 'pending'
                                        },
                                        confidence=0.75
                                    )
                                    results.append(work)
                    except:
                        continue
        except Exception as e:
            logger.warning(f"Form search error: {e}")
        
        return results
    
    def _detect_type_from_category(self, category: str) -> Optional[str]:
        """Detect content type from Indian Copyright category"""
        if not category:
            return None
        
        cat_lower = category.lower()
        
        if 'literary' in cat_lower:
            return 'book'
        elif 'artistic' in cat_lower:
            return 'artwork'
        elif 'musical' in cat_lower:
            return 'music'
        elif 'cinematograph' in cat_lower:
            return 'film'
        elif 'sound' in cat_lower:
            return 'music'
        elif 'software' in cat_lower or 'computer' in cat_lower:
            return 'software'
        
        return None
    
    async def _search_fallback(self, query: str, content_type: Optional[str] = None) -> List[ScrapedWork]:
        """Fallback search using Wikipedia for Indian works"""
        results = []
        
        # Search Wikipedia for Indian copyright-related works
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}+india&format=json&srlimit=5"
        
        try:
            data = await self.fetch_json(wiki_url)
            if data and 'query' in data:
                for item in data['query'].get('search', [])[:5]:
                    title = item.get('title', '')
                    snippet = clean_html(item.get('snippet', ''))
                    
                    # Only include if query matches
                    if query.lower() not in title.lower() and query.lower() not in snippet.lower():
                        continue
                    
                    work = ScrapedWork(
                        title=title,
                        publication_year=extract_year_from_text(snippet),
                        content_type=detect_content_type(snippet, title) or content_type,
                        source_url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                        source_name=f"{self.source_name} (via Wikipedia)",
                        description=snippet[:300] if snippet else None,
                        additional_data={
                            'jurisdiction': 'IN',
                            'note': 'Search via Wikipedia - verify on copyright.gov.in'
                        },
                        confidence=0.65
                    )
                    results.append(work)
        except Exception as e:
            logger.error(f"Indian copyright fallback search error: {e}")
        
        return results
    
    async def get_details(self, identifier: str) -> Optional[ScrapedWork]:
        """Get detailed copyright registration info"""
        return None


class InnovationProjectScraper(BaseScraper):
    """
    Scraper for innovation projects, research projects, and startups
    Sources: Product Hunt, Crunchbase (via news), Google Scholar
    """
    
    @property
    def source_name(self) -> str:
        return "Innovation & Projects"
    
    async def search(self, query: str, content_type: Optional[str] = None) -> List[ScrapedWork]:
        """Search for innovation projects, drones, disaster management, etc."""
        results = []
        
        # Search Wikipedia for technology/innovation projects
        wiki_results = await self._search_wikipedia(query)
        results.extend(wiki_results)
        
        # Search for academic/research projects
        research_results = await self._search_research_projects(query)
        results.extend(research_results)
        
        # Search for startup/product projects
        product_results = await self._search_products(query)
        results.extend(product_results)
        
        return results[:10]
    
    async def _search_wikipedia(self, query: str) -> List[ScrapedWork]:
        """Search Wikipedia for innovation/tech projects"""
        results = []
        
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}+technology+project&format=json&srlimit=5"
        
        try:
            data = await self.fetch_json(wiki_url)
            if data and 'query' in data:
                for item in data['query'].get('search', [])[:5]:
                    title = item.get('title', '')
                    snippet = clean_html(item.get('snippet', ''))
                    
                    work = ScrapedWork(
                        title=title,
                        publication_year=extract_year_from_text(snippet),
                        content_type='project',
                        source_url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                        source_name="Wikipedia - Projects",
                        description=snippet[:300] if snippet else None,
                        additional_data={
                            'category': 'innovation_project',
                            'source': 'wikipedia'
                        },
                        confidence=0.7
                    )
                    results.append(work)
        except Exception as e:
            logger.error(f"Wikipedia innovation search error: {e}")
        
        return results
    
    async def _search_research_projects(self, query: str) -> List[ScrapedWork]:
        """Search for research/academic projects"""
        results = []
        
        # Use Semantic Scholar API for research projects
        api_url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}+project&limit=5&fields=title,year,authors,abstract"
        
        try:
            data = await self.fetch_json(api_url)
            if data and 'data' in data:
                for paper in data['data'][:5]:
                    title = paper.get('title', '')
                    year = paper.get('year')
                    authors = paper.get('authors', [])
                    author_names = ', '.join([a.get('name', '') for a in authors[:3]])
                    abstract = paper.get('abstract', '')
                    
                    work = ScrapedWork(
                        title=title,
                        creator=author_names if author_names else None,
                        publication_year=year,
                        content_type='research_project',
                        source_url=f"https://www.semanticscholar.org/search?q={query}",
                        source_name="Semantic Scholar - Research",
                        description=abstract[:300] if abstract else None,
                        additional_data={
                            'category': 'research_project',
                            'source': 'semantic_scholar'
                        },
                        confidence=0.75
                    )
                    results.append(work)
        except Exception as e:
            logger.warning(f"Research project search error: {e}")
        
        return results
    
    async def _search_products(self, query: str) -> List[ScrapedWork]:
        """Search for product/startup projects via news"""
        results = []
        
        # Use DuckDuckGo instant answers for products/startups
        ddg_url = f"https://api.duckduckgo.com/?q={query}+startup+product&format=json&no_html=1"
        
        try:
            data = await self.fetch_json(ddg_url)
            if data:
                # Check abstract
                if data.get('Abstract'):
                    work = ScrapedWork(
                        title=data.get('Heading', query),
                        content_type='product',
                        source_url=data.get('AbstractURL', ''),
                        source_name="DuckDuckGo - Products",
                        description=data.get('Abstract', '')[:300],
                        additional_data={
                            'category': 'product',
                            'source': 'duckduckgo'
                        },
                        confidence=0.65
                    )
                    results.append(work)
                
                # Check related topics
                for topic in data.get('RelatedTopics', [])[:3]:
                    if isinstance(topic, dict) and 'Text' in topic:
                        work = ScrapedWork(
                            title=topic.get('Text', '')[:100],
                            content_type='product',
                            source_url=topic.get('FirstURL', ''),
                            source_name="DuckDuckGo - Related",
                            description=topic.get('Text', '')[:300],
                            additional_data={
                                'category': 'related_product'
                            },
                            confidence=0.5
                        )
                        results.append(work)
        except Exception as e:
            logger.warning(f"Product search error: {e}")
        
        return results
    
    async def get_details(self, identifier: str) -> Optional[ScrapedWork]:
        return None


class StartupCompanyScraper(BaseScraper):
    """
    Scraper for startups and companies
    """
    
    @property
    def source_name(self) -> str:
        return "Startups & Companies"
    
    async def search(self, query: str, content_type: Optional[str] = None) -> List[ScrapedWork]:
        """Search for startups and companies"""
        results = []
        
        # Search Wikipedia for companies
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}+company+startup&format=json&srlimit=5"
        
        try:
            data = await self.fetch_json(wiki_url)
            if data and 'query' in data:
                for item in data['query'].get('search', [])[:5]:
                    title = item.get('title', '')
                    snippet = clean_html(item.get('snippet', ''))
                    
                    # Check if it's actually a company
                    if any(word in snippet.lower() for word in ['company', 'startup', 'founded', 'corporation', 'inc.', 'ltd']):
                        work = ScrapedWork(
                            title=title,
                            publication_year=extract_year_from_text(snippet),
                            content_type='company',
                            source_url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                            source_name="Wikipedia - Companies",
                            description=snippet[:300] if snippet else None,
                            additional_data={
                                'category': 'startup_company',
                                'founded_year': extract_year_from_text(snippet)
                            },
                            confidence=0.7
                        )
                        results.append(work)
        except Exception as e:
            logger.error(f"Company search error: {e}")
        
        # Also search DuckDuckGo
        ddg_url = f"https://api.duckduckgo.com/?q={query}+company&format=json&no_html=1"
        
        try:
            data = await self.fetch_json(ddg_url)
            if data and data.get('Abstract'):
                work = ScrapedWork(
                    title=data.get('Heading', query),
                    content_type='company',
                    source_url=data.get('AbstractURL', ''),
                    source_name="Company Info",
                    description=data.get('Abstract', '')[:300],
                    additional_data={
                        'category': 'company',
                        'infobox': data.get('Infobox', {})
                    },
                    confidence=0.65
                )
                results.append(work)
        except Exception as e:
            logger.warning(f"DuckDuckGo company search error: {e}")
        
        return results[:10]
    
    async def get_details(self, identifier: str) -> Optional[ScrapedWork]:
        return None


class ResearchDatabaseScraper(BaseScraper):
    """
    Scraper for academic research databases
    Sources: Semantic Scholar, arXiv, PubMed
    """
    
    @property
    def source_name(self) -> str:
        return "Research Database"
    
    async def search(self, query: str, content_type: Optional[str] = None) -> List[ScrapedWork]:
        """Search academic research databases"""
        results = []
        
        # Search Semantic Scholar
        ss_results = await self._search_semantic_scholar(query)
        results.extend(ss_results)
        
        # Search arXiv
        arxiv_results = await self._search_arxiv(query)
        results.extend(arxiv_results)
        
        return results[:10]
    
    async def _search_semantic_scholar(self, query: str) -> List[ScrapedWork]:
        """Search Semantic Scholar"""
        results = []
        
        api_url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=5&fields=title,year,authors,abstract,citationCount"
        
        try:
            data = await self.fetch_json(api_url)
            if data and 'data' in data:
                for paper in data['data'][:5]:
                    title = paper.get('title', '')
                    year = paper.get('year')
                    authors = paper.get('authors', [])
                    author_names = ', '.join([a.get('name', '') for a in authors[:3]])
                    abstract = paper.get('abstract', '')
                    citations = paper.get('citationCount', 0)
                    
                    work = ScrapedWork(
                        title=title,
                        creator=author_names if author_names else None,
                        publication_year=year,
                        content_type='academic_paper',
                        source_url=f"https://www.semanticscholar.org/search?q={query}",
                        source_name="Semantic Scholar",
                        description=abstract[:300] if abstract else None,
                        additional_data={
                            'citations': citations,
                            'category': 'research_paper'
                        },
                        confidence=0.8
                    )
                    results.append(work)
        except Exception as e:
            logger.warning(f"Semantic Scholar search error: {e}")
        
        return results
    
    async def _search_arxiv(self, query: str) -> List[ScrapedWork]:
        """Search arXiv preprints"""
        results = []
        
        arxiv_url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=5"
        
        try:
            xml_data = await self.fetch(arxiv_url)
            if xml_data:
                # Parse XML response
                soup = BeautifulSoup(xml_data, 'xml')
                entries = soup.find_all('entry')
                
                for entry in entries[:5]:
                    title = entry.find('title')
                    title = clean_html(title.get_text()) if title else ''
                    
                    summary = entry.find('summary')
                    summary = clean_html(summary.get_text())[:300] if summary else ''
                    
                    authors = entry.find_all('author')
                    author_names = ', '.join([a.find('name').get_text() for a in authors[:3] if a.find('name')])
                    
                    published = entry.find('published')
                    year = None
                    if published:
                        year = extract_year_from_text(published.get_text())
                    
                    link = entry.find('id')
                    url = link.get_text() if link else ''
                    
                    work = ScrapedWork(
                        title=title,
                        creator=author_names if author_names else None,
                        publication_year=year,
                        content_type='academic_paper',
                        source_url=url,
                        source_name="arXiv",
                        description=summary,
                        additional_data={
                            'category': 'preprint',
                            'source': 'arxiv'
                        },
                        confidence=0.85
                    )
                    results.append(work)
        except Exception as e:
            logger.warning(f"arXiv search error: {e}")
        
        return results
    
    async def get_details(self, identifier: str) -> Optional[ScrapedWork]:
        return None


class WebScraper:
    """
    Unified scraper that aggregates results from multiple sources
    """
    
    def __init__(self):
        self.scrapers: Dict[str, BaseScraper] = {
            'openlib': OpenLibraryScraper(),
            'wikipedia': WikipediaScraper(),
            'musicbrainz': MusicBrainzScraper(),
            'imdb': IMDbScraper(),
            'github': GitHubScraper(),
            'patent': PatentScraper(),
            'trademark': TrademarkScraper(),
            'academic': AcademicScraper(),
            'indian_copyright': IndianCopyrightScraper(),
            'innovation': InnovationProjectScraper(),
            'startup': StartupCompanyScraper(),
            'research': ResearchDatabaseScraper(),
        }
    
    async def search_all(self, query: str, content_type: Optional[str] = None) -> List[ScrapedWork]:
        """Search across all sources and merge results"""
        all_results = []
        
        # Select appropriate scrapers based on content type
        if content_type == 'book':
            scrapers_to_use = ['openlib', 'wikipedia', 'indian_copyright']
        elif content_type == 'music':
            scrapers_to_use = ['musicbrainz', 'wikipedia', 'indian_copyright']
        elif content_type == 'film':
            scrapers_to_use = ['imdb', 'wikipedia', 'indian_copyright']
        elif content_type in ['software', 'code', 'library']:
            scrapers_to_use = ['github', 'indian_copyright', 'innovation']
        elif content_type == 'patent':
            scrapers_to_use = ['patent', 'wikipedia', 'innovation']
        elif content_type == 'trademark':
            scrapers_to_use = ['trademark']
        elif content_type == 'academic_paper':
            scrapers_to_use = ['academic', 'research']
        elif content_type in ['project', 'innovation', 'drone', 'technology']:
            scrapers_to_use = ['innovation', 'research', 'wikipedia', 'patent']
        elif content_type in ['company', 'startup']:
            scrapers_to_use = ['startup', 'wikipedia']
        elif content_type == 'research_project':
            scrapers_to_use = ['research', 'innovation', 'academic']
        else:
            scrapers_to_use = list(self.scrapers.keys())
        
        # Run searches concurrently
        tasks = []
        for scraper_name in scrapers_to_use:
            scraper = self.scrapers[scraper_name]
            tasks.append(scraper.search(query, content_type))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Scraper error: {result}")
                continue
            if result:
                all_results.extend(result)
        
        # STRICT FILTERING: If content_type is specified, filter to only include matching types
        if content_type:
            # Map similar types together
            type_groups = {
                'software': ['software', 'code', 'library'],
                'code': ['software', 'code', 'library'],
                'library': ['software', 'code', 'library'],
                'book': ['book'],
                'music': ['music'],
                'film': ['film', 'movie'],
                'patent': ['patent'],
                'trademark': ['trademark'],
                'academic_paper': ['academic_paper', 'article', 'research_paper'],
                'project': ['project', 'innovation_project', 'research_project', 'product'],
                'innovation': ['project', 'innovation_project', 'product', 'technology'],
                'drone': ['project', 'innovation_project', 'product', 'technology', 'drone'],
                'technology': ['project', 'innovation_project', 'product', 'technology'],
                'company': ['company', 'startup_company'],
                'startup': ['company', 'startup_company'],
                'research_project': ['research_project', 'academic_paper', 'project'],
            }
            allowed_types = type_groups.get(content_type, [content_type])
            all_results = [
                r for r in all_results 
                if r.content_type in allowed_types or r.content_type == content_type
            ]
        
        # Sort by confidence
        all_results.sort(key=lambda x: x.confidence, reverse=True)
        
        return all_results
    
    async def close(self):
        """Close all scraper sessions"""
        for scraper in self.scrapers.values():
            if scraper.session:
                await scraper.session.close()

