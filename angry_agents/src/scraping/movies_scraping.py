import requests
from bs4 import BeautifulSoup
import re
from collections import Counter

# Esempio: IMSDb (Internet Movie Script Database)
def scrape_imsdb_script(movie_title):
    """
    IMSDb ha script di migliaia di film
    """
    # Correct IMSDb URL format: scripts/{Title}.html
    search_url = f"https://imsdb.com/scripts/{movie_title}.html"
    
    try:
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try multiple selectors for script content
        script_element = soup.find('td', class_='scrtext')
        if not script_element:
            script_element = soup.find('pre')
        if not script_element:
            script_element = soup.find('div', class_='script')
        if not script_element:
            # Try finding any <td> or <div> with large text content
            all_tds = soup.find_all('td')
            for td in all_tds:
                text = td.get_text(strip=True)
                if len(text) > 1000:  # Script content should be long
                    script_element = td
                    break
        
        if script_element:
            script_text = script_element.get_text()
            return script_text if script_text else None
        else:
            print(f"No script element found at {search_url}")
            return None
    except requests.RequestException as e:
        print(f"Error fetching {search_url}: {e}")
        return None


def extract_personas(script_text):
    """
    Extract character names (personas) from a movie script.
    
    Looks for lines that are:
    - All caps or title case
    - Followed by dialogue or action
    - Usually on their own line
    """
    if not script_text:
        return []
    
    personas = []
    lines = script_text.split('\n')
    
    for i, line in enumerate(lines):
        cleaned = line.strip()
        
        # Skip empty lines and very long lines (likely not character names)
        if not cleaned or len(cleaned) > 100:
            continue
        
        # Match character names: ALL CAPS, possibly with parenthetical actions
        # Examples: "VINCENT", "JULES WINNFIELD", "JULES (V.O.)"
        match = re.match(r'^([A-Z][A-Z\s\-\']+?)(?:\s*\([^)]*\))?$', cleaned)
        
        if match:
            char_name = match.group(1).strip()
            
            # Filter out common non-character lines
            if char_name and len(char_name) > 1 and not any(
                char_name.upper() == word for word in [
                    'INT', 'EXT', 'CUT', 'FADE', 'DISSOLVE', 'SCENE',
                    'THE', 'A', 'AND', 'OR', 'BUT', 'BACK', 'TO'
                ]
            ):
                personas.append(char_name)
    
    # Count occurrences and return unique personas with their frequency
    persona_counts = Counter(personas)
    return persona_counts.most_common()  # Returns list of (name, count) tuples

# Esempio di utilizzo
if __name__ == "__main__":
    # Scrape and extract personas from Pulp Fiction
    # URL: https://imsdb.com/scripts/Pulp-Fiction.html
    
    print("Fetching Pulp Fiction script...")
    script = scrape_imsdb_script("Pulp-Fiction")
    
    if script:
        print(f"Script fetched successfully! ({len(script)} characters)")
        print("\nExtracting personas...\n")
        
        personas = extract_personas(script)
        
        if personas:
            print("Top 10 personas (characters by frequency):")
            print("-" * 40)
            for i, (name, count) in enumerate(personas[:10], 1):
                print(f"{i:2d}. {name:<25} ({count:3d} lines)")
        else:
            print("No personas found in the script.")
    else:
        print("Failed to fetch the script.")