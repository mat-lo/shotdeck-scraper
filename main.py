import os
import time
import requests
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from urllib.parse import quote, unquote


class ShotDeckScraper:
    def __init__(self, username, password, output_dir='./downloaded_images', query=None):
        """Initialize the ShotDeck scraper with credentials and output directory."""
        self.username = username
        self.password = password
        
        # Always use downloaded_images as the base directory
        self.base_output_dir = './downloaded_images'
        self.query = query
        
        # Create base output directory if it doesn't exist
        if not os.path.exists(self.base_output_dir):
            os.makedirs(self.base_output_dir)
            print(f"Created base output directory: {self.base_output_dir}")
            
        # If query is provided, create a subdirectory for this specific query
        if query:
            # Sanitize the query for use as a directory name
            sanitized_query = self._sanitize_for_directory(query)
            self.output_dir = os.path.join(self.base_output_dir, sanitized_query)
            
            # Create the query-specific subdirectory
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                print(f"Created query-specific directory: {self.output_dir}")
        else:
            self.output_dir = self.base_output_dir
            
        self.base_url = "https://shotdeck.com"
        self.driver = None
        self.session = requests.Session()
        
    def _sanitize_for_directory(self, name):
        """Sanitize a string to be used as a directory name."""
        # Replace problematic characters with underscores
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            name = name.replace(char, '_')
        # Replace spaces and commas with underscores
        name = name.replace(' ', '_').replace(',', '_')
        # Limit length and trim trailing periods/spaces
        return name.strip().strip('.')[:50]
            
    def setup_driver(self):
        """Set up and configure the Chrome WebDriver."""
        chrome_options = Options()
        # Uncomment the line below to run headless (no visible browser)
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Initialize the WebDriver
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        
    def login(self):
        """Log in to ShotDeck with the provided credentials."""
        try:
            # Navigate to login page
            self.driver.get(f"{self.base_url}/welcome/login")
            
            # Wait for the login form to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "user"))
            )
            
            # Enter login credentials
            self.driver.find_element(By.NAME, "user").send_keys(self.username)
            self.driver.find_element(By.NAME, "pass").send_keys(self.password)
            
            # Check "Keep me logged in" checkbox
            stay_logged_in = self.driver.find_element(By.ID, "stayLoggedIn")
            if not stay_logged_in.is_selected():
                stay_logged_in.click()
            
            # Click the login button
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            
            # Wait for login to complete and redirect to welcome/home
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda driver: "welcome/home" in driver.current_url or 
                                   "browse/stills" in driver.current_url or
                                   "dashboard" in driver.current_url
                )
                
                print(f"Successfully logged in! Current URL: {self.driver.current_url}")
                
                # Get cookies for the requests session
                for cookie in self.driver.get_cookies():
                    self.session.cookies.set(cookie['name'], cookie['value'])
                
                return True
            except TimeoutException:
                print(f"Unexpected page after login. Current URL: {self.driver.current_url}")
                return False
                
        except Exception as e:
            print(f"Login failed: {e}")
            self.driver.quit()
            exit(1)
            
    def search(self, query):
        """Navigate to the search URL for the given query."""
        # Handle comma-separated search terms
        if ',' in query:
            # Split the query by commas and process each part separately
            parts = [part.strip() for part in query.split(',')]
            formatted_parts = []
            
            for part in parts:
                formatted_parts.append(self._format_query_part(part))
            
            # Join the formatted parts with underscores
            formatted_query = '_'.join(formatted_parts)
        else:
            # Single concept query
            formatted_query = self._format_query_part(query)
        
        print(f"Transforming query: '{query}' → '{formatted_query}'")
        
        # Encode the search query for the URL
        encoded_query = quote(formatted_query)
        search_url = f"{self.base_url}/browse/stills#/s/{encoded_query}"
        
        print(f"Navigating to search: {search_url}")
        self.driver.get(search_url)
        
        # Give the page a moment to load the search interface
        time.sleep(3)
        
        # Check if we're on the right page
        current_url = self.driver.current_url
        if "browse/stills" not in current_url:
            print(f"Warning: Not on expected search page. Current URL: {current_url}")
            print("Attempting to navigate directly to search URL...")
            self.driver.get(search_url)
            time.sleep(3)
        
        # Wait for search results to load
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "outerimage"))
            )
            print("Search results loaded!")
            
            # Count initial results
            initial_images = self.driver.find_elements(By.CSS_SELECTOR, "div.outerimage")
            print(f"Initial search returned {len(initial_images)} results.")
            
            # Check if no results
            if len(initial_images) == 0:
                no_results = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'No results')]")
                if no_results:
                    print("WARNING: No search results found. Please check your search query.")
                    return False
            return True
                    
        except TimeoutException:
            print("Warning: Search results took too long to load or no results found.")
            return False
            
    def _format_query_part(self, query_part):
        """Format a single part of a query according to ShotDeck's requirements."""
        # First, check if the query is already in ShotDeck format
        if '"' in query_part or '_' in query_part:
            return query_part
            
        # Parse the natural language query
        words = query_part.split()
        
        if len(words) <= 1:
            # Single word query, no special formatting needed
            return query_part
        else:
            # Multi-word query - don't add quotes, just join with spaces
            # ShotDeck will handle the spaces in the URL
            return query_part
            
        # The code below was adding quotes automatically - we're no longer doing this
        # elif len(words) == 2:
        #     # Two words - assume it's a phrase
        #     return f'"{words[0]} {words[1]}"'
        # else:
        #     # Multi-word query
        #     # Check for common phrases like "black and white"
        #     if "and" in words:
        #         # If "and" is present, try to keep the phrase together
        #         return f'"{query_part}"'
        #     else:
        #         # For queries with 3+ words, try to detect phrases and keywords
        #         # Simple approach: treat the first two words as a name/phrase and the rest as attributes
        #         name_part = f'"{words[0]} {words[1]}"'
        #         attribute_parts = words[2:]
        #         
        #         # Join attributes with underscores
        #         if attribute_parts:
        #             return f'{name_part}_' + '_'.join(attribute_parts)
        #         else:
        #             return name_part
        
        print(f"Navigating to search: {search_url}")
        self.driver.get(search_url)
        
        # Give the page a moment to load the search interface
        time.sleep(3)
        
        # Check if we're on the right page
        current_url = self.driver.current_url
        if "browse/stills" not in current_url:
            print(f"Warning: Not on expected search page. Current URL: {current_url}")
            print("Attempting to navigate directly to search URL...")
            self.driver.get(search_url)
            time.sleep(3)
        
        # Wait for search results to load
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "outerimage"))
            )
            print("Search results loaded!")
            
            # Count initial results
            initial_images = self.driver.find_elements(By.CSS_SELECTOR, "div.outerimage")
            print(f"Initial search returned {len(initial_images)} results.")
            
            # Check if no results
            if len(initial_images) == 0:
                no_results = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'No results')]")
                if no_results:
                    print("WARNING: No search results found. Please check your search query.")
                    return False
            return True
                    
        except TimeoutException:
            print("Warning: Search results took too long to load or no results found.")
            return False
            
    def scroll_and_load_all(self, max_scrolls=100, scroll_pause_time=1.5, no_change_limit=5, image_limit=None):
        """Scroll down the page to trigger the loading of all images."""
        # Get initial scroll height
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        images_before = 0
        scrolls = 0
        no_change_count = 0
        
        print("Scrolling to load all images...")
        
        while scrolls < max_scrolls:
            # Scroll down to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for page to load new content
            time.sleep(scroll_pause_time)
            
            # Calculate new scroll height and compare with last scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Count current images by div.outerimage since that's what contains all the image data
            images = self.driver.find_elements(By.CSS_SELECTOR, "div.outerimage")
            print(f"Found {len(images)} images so far... (scroll {scrolls+1}/{max_scrolls})")
            
            # Check if we've reached the image limit
            if image_limit and len(images) >= image_limit:
                print(f"Reached the image limit of {image_limit}. Stopping scrolling.")
                break
                
            # Check if we've reached the end
            if len(images) == images_before:
                no_change_count += 1
                print(f"No new images loaded. Consecutive count: {no_change_count}/{no_change_limit}")
                
                # If no new images appeared after several scrolls, we've likely reached the end
                if no_change_count >= no_change_limit:
                    print("No more images loading after multiple attempts, stopping scroll.")
                    break
            else:
                # Reset the counter if we got new images
                no_change_count = 0
                
            # Also check if scroll height didn't change
            if new_height == last_height:
                no_change_count += 1
                print(f"Page height didn't change. Consecutive count: {no_change_count}/{no_change_limit}")
            else:
                last_height = new_height
                
            # Try an additional technique: scroll up slightly and then back down
            # This can sometimes trigger lazy loaders that check for scroll direction changes
            if no_change_count > 0 and no_change_count < no_change_limit:
                print("Trying scroll jiggle to trigger more content...")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 400);")
                time.sleep(0.5)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause_time)
                
            images_before = len(images)
            scrolls += 1
            
        print(f"Finished scrolling. Found {images_before} images in total.")
        
    def extract_and_download_images(self, image_limit=None):
        """Extract image URLs and download all images."""
        # Find all image elements with class "still"
        image_containers = self.driver.find_elements(By.CSS_SELECTOR, "div.outerimage")
        
        if not image_containers:
            print("No images found to download.")
            return
        
        # Apply limit if specified
        if image_limit and len(image_containers) > image_limit:
            print(f"Limiting download to {image_limit} images out of {len(image_containers)} found.")
            image_containers = image_containers[:image_limit]
        else:
            print(f"Preparing to download {len(image_containers)} images...")
        
        # Extract and download each image
        for i, container in enumerate(image_containers):
            try:
                # Get the shot ID from the container
                shot_id = container.get_attribute("data-shotid")
                if not shot_id:
                    print(f"  Skipping image {i+1}: No shot ID found")
                    continue
                    
                # Get image element within the container
                try:
                    img = container.find_element(By.CSS_SELECTOR, "img.still")
                    small_src = img.get_attribute("src")
                    
                    # Get image dimensions if available
                    img_width = img.get_attribute("width") 
                    img_height = img.get_attribute("height")
                except Exception as e:
                    print(f"  Warning: Could not get image element for shot {shot_id}: {e}")
                    small_src = f"/assets/images/stills/medthumb/small_{shot_id}.jpg"
                
                # Get the data-filename attribute from the a.gallerythumb if available
                try:
                    gallery_thumb = container.find_element(By.CSS_SELECTOR, "a.gallerythumb")
                    filename = gallery_thumb.get_attribute("data-filename")
                    full_size_dimensions = gallery_thumb.get_attribute("data-size")
                    if filename:
                        # This filename may contain the extension we need
                        extension = os.path.splitext(filename)[1]
                    else:
                        extension = ".jpg"
                except:
                    filename = f"{shot_id}.jpg"
                    extension = ".jpg"
                    full_size_dimensions = None
                
                # Get the movie title if available
                try:
                    movie_title_element = container.find_element(By.CSS_SELECTOR, ".gallerytitle a")
                    movie_title = movie_title_element.text.replace(' ', '_')
                except:
                    movie_title = "unknown_movie"
                
                # Construct the full-size image URL based on the HTML structure
                # First try the direct full-size path
                full_size_url = f"{self.base_url}/assets/images/stills/{shot_id}{extension}"
                
                # Use the requests session with authenticated cookies to download
                output_filename = f"{movie_title}_{shot_id}{extension}"
                file_path = os.path.join(self.output_dir, output_filename)
                
                print(f"Downloading {i+1}/{len(image_containers)}: {output_filename}")
                if full_size_dimensions:
                    print(f"  Image dimensions: {full_size_dimensions}")
                
                # Try multiple possible URLs for the full-size image
                urls_to_try = [
                    full_size_url,  # Direct full size
                    f"{self.base_url}/assets/images/stills/{filename}",  # Using data-filename if available
                    f"{self.base_url}{small_src.replace('small_', '')}"  # Remove 'small_' prefix
                ]
                
                downloaded = False
                for url in urls_to_try:
                    try:
                        response = self.session.get(url, stream=True)
                        if response.status_code == 200:
                            with open(file_path, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            print(f"  ✓ Successfully downloaded from: {url}")
                            print(f"  Saved to {file_path}")
                            downloaded = True
                            break
                    except Exception as e:
                        print(f"  Error trying URL {url}: {e}")
                
                # If all full-size attempts failed, fall back to the small thumbnail
                if not downloaded:
                    try:
                        if small_src.startswith('/'):
                            small_src_url = f"{self.base_url}{small_src}"
                        else:
                            small_src_url = small_src
                            
                        print(f"  Full-size image not available, falling back to thumbnail.")
                        response = self.session.get(small_src_url, stream=True)
                        
                        if response.status_code == 200:
                            with open(file_path, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            print(f"  Saved thumbnail to {file_path}")
                            downloaded = True
                        else:
                            print(f"  Failed to download thumbnail: {response.status_code}")
                    except Exception as e:
                        print(f"  Error downloading thumbnail: {e}")
                
                if not downloaded:
                    print(f"  ✗ Failed to download image after trying all URLs")
                    
            except Exception as e:
                print(f"  Error processing image {i+1}: {e}")
                
            # Be nice to the server
            time.sleep(0.75)
            
    def run(self, search_query, max_scrolls=100, image_limit=None):
        """Run the full scraping process."""
        try:
            self.setup_driver()
            
            # Step 1: Login to the site
            print("Step 1: Logging in...")
            login_success = self.login()
            if not login_success:
                print("Login failed or redirected to unexpected page. Exiting.")
                return False
            
            # Step 2: Navigate to search URL
            print("Step 2: Navigating to search...")
            time.sleep(2)  # Brief pause after login
            search_success = self.search(search_query)
            if not search_success:
                print("Failed to load search results. Exiting.")
                return False
                
            # Step 3: Scroll to load all images (or until limit)
            print("Step 3: Scrolling to load images...")
            if image_limit:
                print(f"Will stop scrolling after finding approximately {image_limit} images.")
            self.scroll_and_load_all(max_scrolls=max_scrolls, image_limit=image_limit)
            
            # Verify we have images before attempting to download
            images = self.driver.find_elements(By.CSS_SELECTOR, "div.outerimage")
            if not images:
                print("No images found to download after scrolling. Exiting.")
                return False
                
            # Step 4: Download images
            print("Step 4: Downloading images...")
            self.extract_and_download_images(image_limit=image_limit)
            
            print(f"Scraping completed successfully! Downloaded images are in: {self.output_dir}")
            return True
            
        except Exception as e:
            print(f"Error during scraping process: {e}")
            return False
            
        finally:
            if self.driver:
                self.driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ShotDeck Image Scraper")
    parser.add_argument("--username", "-u", required=True, help="ShotDeck account username/email")
    parser.add_argument("--password", "-p", required=True, help="ShotDeck account password")
    parser.add_argument("--query", "-q", required=True, help="Search query (e.g., 'brad pitt hands' or 'black and white, drink')")
    parser.add_argument("--output", "-o", default="./downloaded_images", help="Base output directory for downloaded images")
    parser.add_argument("--max-scrolls", "-m", type=int, default=100, help="Maximum number of scrolls to perform")
    parser.add_argument("--limit", "-l", type=int, default=None, help="Maximum number of images to download")
    
    args = parser.parse_args()
    
    # Create scraper with query info for directory naming
    scraper = ShotDeckScraper(args.username, args.password, args.output, args.query)
    scraper.run(args.query, args.max_scrolls, args.limit)