import requests
from bs4 import BeautifulSoup
import re
import json
import os
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


def extract_character_lines(script_text, character_name):
    """
    Extract all dialogue lines spoken by a specific character.
    
    Args:
        script_text: Full script text
        character_name: Name of the character (e.g., "VINCENT")
    
    Returns:
        List of dialogue lines spoken by the character (excluding stage directions)
    """
    if not script_text:
        return []
    
    lines = script_text.split('\n')
    character_lines = []
    i = 0
    
    while i < len(lines):
        cleaned = lines[i].strip()
        
        # Check if this line is the character name
        if cleaned and re.match(r'^[A-Z][A-Z\s\-\']+(?:\s*\([^)]*\))?$', cleaned):
            # Extract the base character name (without parentheticals)
            base_name = re.sub(r'\s*\([^)]*\).*$', '', cleaned).strip()
            
            if base_name.upper() == character_name.upper():
                # Collect dialogue lines that follow
                i += 1
                while i < len(lines):
                    dialogue = lines[i].strip()
                    
                    # Stop conditions
                    if not dialogue:
                        # Skip empty lines but continue
                        i += 1
                        continue
                    
                    # Stop if we hit a scene heading (INT/EXT) or character name
                    if dialogue.startswith('INT ') or dialogue.startswith('EXT '):
                        break
                    if re.match(r'^[A-Z][A-Z\s\-\']+(?:\s*\([^)]*\))?$', dialogue):
                        break
                    
                    # Skip lines that are pure stage directions (enclosed in parentheses/brackets)
                    if dialogue.startswith('[') or dialogue.startswith('('):
                        i += 1
                        continue
                    
                    # Add dialogue lines (not stage directions)
                    if dialogue and not dialogue.startswith('---'):
                        character_lines.append(dialogue)
                    
                    i += 1
                i -= 1
        
        i += 1
    
    return character_lines


def save_character_to_json(character_name, film_name, lines, output_dir="personas"):
    """
    Save character data to a JSON file.
    
    Args:
        character_name: Name of the character
        film_name: Name of the film
        lines: List of dialogue lines
        output_dir: Directory to save JSON files (default: "personas")
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Create JSON data
    data = {
        "character": character_name,
        "film": film_name,
        "lines_count": len(lines),
        "transcript": "\n".join(lines)
    }
    
    # Create filename from character name (sanitize)
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', character_name)
    filename = os.path.join(output_dir, f"{safe_name}.json")
    
    # Save to JSON
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filename

if __name__ == "__main__":
    # Scrape and extract personas from Wolf of Wall Street
    # URL: https://imsdb.com/scripts/Wolf-of-Wall-Street,-The.html
    
    movie_title = "Wolf-of-Wall-Street,-The"  # Exact format from IMSDb URL
    
    print(f"Fetching {movie_title} script...")
    script = scrape_imsdb_script(movie_title)
    
    if script:
        print(f"Script fetched successfully! ({len(script)} characters)")
        print("\nExtracting personas...\n")
        
        personas = extract_personas(script)
        
        if personas:
            print("Top 10 personas (characters by frequency):")
            print("-" * 40)
            for i, (name, count) in enumerate(personas[:10], 1):
                print(f"{i:2d}. {name:<25} ({count:3d} lines)")
            
            # Save top 5 characters to JSON files in scraping folder
            print("\n\nSaving top 5 characters to JSON files...")
            print("-" * 40)
            output_dir = os.path.join(os.path.dirname(__file__), "personas")
            for name, count in personas[:5]:
                # Extract all lines for this character
                lines = extract_character_lines(script, name)
                
                # Save to JSON
                filename = save_character_to_json(name, movie_title, lines, output_dir)
                print(f"✓ {name}: {len(lines)} lines → {filename}")
        else:
            print("No personas found in the script.")
    else:
        print("Failed to fetch the script.")