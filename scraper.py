import requests
from bs4 import BeautifulSoup
import io
import PyPDF2
import mimetypes
from utils.retry import retry_except

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.smartsheet.com/',
    'Cookie': 'your_cookie_if_needed'  # Replace with actual cookie if necessary
}

@retry_except(exceptions_to_catch=(requests.RequestException,), tries=3, delay=2)
def fetch_content(url):
    """Fetch content from a given URL."""
    print(f"Fetching content from URL: {url}")
    session = requests.Session()
    session.headers.update(HEADERS)
    response = session.get(url, stream=True)
    print(f"Response status code: {response.status_code}")
    print(f"Response history: {response.history}")
    if response.status_code == 404:
        print(f"Error: 404 Not Found for URL: {url}")
        return None
    response.raise_for_status()
    return response

def extract_text_from_pdf(pdf_content):
    """Extract text from PDF content."""
    pdf_file = io.BytesIO(pdf_content)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_html(html_content):
    """Extract text from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text()

def scrape_content(url):
    """
    Scrape content from a given URL, handling different content types.
    
    Args:
    url (str): The URL to scrape.
    
    Returns:
    dict: A dictionary containing:
        - 'content': The extracted text content.
        - 'content_type': The detected content type.
        - 'url': The original URL.
    
    Raises:
    ValueError: If the content type is unsupported.
    """
    response = fetch_content(url)
    if not response:
        return None

    content_type = response.headers.get('Content-Type', '').lower()
    
    if 'application/pdf' in content_type:
        content = extract_text_from_pdf(response.content)
        detected_type = 'pdf'
    elif 'text/html' in content_type:
        content = extract_text_from_html(response.content)
        detected_type = 'html'
    else:
        # Try to guess based on the URL if Content-Type is not definitive
        guessed_type, _ = mimetypes.guess_type(url)
        if guessed_type == 'application/pdf':
            content = extract_text_from_pdf(response.content)
            detected_type = 'pdf'
        elif guessed_type and guessed_type.startswith('text/'):
            content = response.text
            detected_type = 'text'
        else:
            raise ValueError(f"Unsupported content type: {content_type}")
    
    return {
        'content': content,
        'content_type': detected_type,
        'url': url
    }

if __name__ == "__main__":
    # Example usage
    test_url = "https://www.smartsheet.com/sites/default/files/2021-10/Smartsheet-User-Agreement-May-2021.pdf"
    try:
        result = scrape_content(test_url)
        if result:
            print(f"Content type: {result['content_type']}")
            print(f"Content preview: {result['content'][:200]}...")
        else:
            print(f"Failed to fetch content from URL: {test_url}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
