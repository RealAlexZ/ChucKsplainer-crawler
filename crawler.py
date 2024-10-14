import os
import time
from urllib.parse import urljoin, urlparse, quote, unquote, urldefrag
import sys
import requests
from bs4 import BeautifulSoup

def validate_url(url, allowed_roots):
    """
    Validates if the URL starts with any of the allowed root URLs.
    """
    return any(url.startswith(root) for root in allowed_roots)

def normalize_url(link, root):
    """
    Normalizes a given URL by converting relative URLs to absolute based on a root URL
    and ensures proper encoding of the path component. Fragments are removed.
    """
    # Remove fragment identifiers
    link, _ = urldefrag(link)
    
    # Skip empty links
    if not link:
        return None
    
    # Convert relative URL to absolute URL based on root URL
    new_url = urljoin(root, link)
    parsed_url = urlparse(new_url)
    
    # Decode path to handle any existing percent-encoded characters, then re-encode
    # This ensures characters like spaces are correctly percent-encoded as %20
    path = quote(unquote(parsed_url.path))
    normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}{path}"
    
    # Ensure HTTPS
    if normalized_url.startswith("http://"):
        normalized_url = normalized_url.replace("http://", "https://")
    
    # Return the normalized URL as-is (retain trailing slash if present)
    return normalized_url

def save_content(url, content):
    """
    Saves the content of the URL to the appropriate directory based on its file type.
    """
    parsed_url = urlparse(url)
    path = parsed_url.path
    if path.endswith(".ck"):
        directory = "ck_files"
    else:
        directory = "html_files"

    # Create the directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)

    # Create a safe file path by replacing '/' with '_' and removing leading '/'
    safe_path = path.lstrip("/").replace("/", "_")
    if not safe_path:
        safe_path = "index.html"

    # Append appropriate file extension if missing
    if directory == "html_files":
        if not safe_path.endswith(".html") and not safe_path.endswith(".htm"):
            safe_path += ".html"

    file_path = os.path.join(directory, safe_path)

    # If the path ends with '/', save as index.html inside the directory
    if path.endswith("/"):
        file_path = os.path.join(directory, safe_path, "index.html")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Write the content to the file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    """
    The main function where the web crawling process is initiated and managed.
    It reads seed URLs from a file, crawls webpages within allowed roots, saves identified URLs,
    and stores HTML and .ck files in separate folders.
    """
    current_dir = os.getcwd()
    if len(sys.argv) != 3:
        print("Usage: python crawler.py <seed_filename> <max_number_of_urls>")
        sys.exit(1)

    seed_filename, max_num_url = sys.argv[1], int(sys.argv[2])
    identified_urls = set()
    frontier = []
    # User-Agent header to mimic a browser request
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:12.0) Gecko/20100101 Firefox/12.0"}

    # Read all seed URLs from the file
    with open(os.path.join(current_dir, seed_filename), "r", encoding="utf-8") as seed_file:
        seed_urls = [line.strip() for line in seed_file if line.strip()]
        # Set allowed_roots to include all seed URLs' parent directory
        allowed_roots = ["https://chuck.stanford.edu/doc/"]
        for root_link in seed_urls:
            # Ensure seed URLs end with a trailing slash to denote directories
            if not root_link.endswith("/"):
                root_link += "/"
            if validate_url(root_link, allowed_roots):
                frontier.append(root_link)
                # Store URLs without trailing slash in identified_urls to prevent duplicates
                identified_urls.add(root_link.rstrip('/'))

    # Create directories for HTML and .ck files
    os.makedirs("html_files", exist_ok=True)
    os.makedirs("ck_files", exist_ok=True)
    os.makedirs("logs", exist_ok=True)  # Directory to store log files

    # Start the timer just before the crawling process begins
    start_time = time.time()

    # Open output files for writing identified URLs, links, and crawled tracking
    with open(os.path.join(current_dir, "crawler.output"), "w", encoding="utf-8") as crawler_output, \
         open(os.path.join(current_dir, "links.output"), "w", encoding="utf-8") as links_output, \
         open(os.path.join(current_dir, "crawled.txt"), "w", encoding="utf-8") as crawled_file:
        # Continue crawling until the maximum number of URLs is reached or there are no more links to crawl
        while frontier and len(identified_urls) < max_num_url:
            curr_url = frontier.pop(0)
            try:
                # Attempt to download the webpage at the current link
                response = requests.get(curr_url, headers=headers, allow_redirects=True, timeout=10)
                final_url = response.url
                if final_url.startswith("http://"):
                    final_url = final_url.replace("http://", "https://")
                # Retain trailing slash for directories
                if response.headers.get("Content-Type", "").startswith("text/html") and not final_url.endswith("/"):
                    # If it's an HTML page and does not end with '/', assume it's a file and keep as-is
                    pass
                elif response.headers.get("Content-Type", "").startswith("text/html") and not final_url.endswith("/"):
                    # If it's an HTML directory, ensure it ends with '/'
                    final_url += "/"

                # Save the content based on its type
                if final_url.endswith(".ck"):
                    save_content(final_url, response.text)
                elif "text/html" in response.headers.get("Content-Type", ""):
                    save_content(final_url, response.text)
                else:
                    continue  # Skip non-html and non-.ck files

                # Write the crawled URL to crawled.txt
                crawled_file.write(final_url + "\n")

                # If the response is HTML, parse and find links
                if "text/html" in response.headers.get("Content-Type", ""):
                    soup = BeautifulSoup(response.text, "html.parser")

                    # Find all hyperlinks in the downloaded webpage
                    for link in soup.find_all("a", href=True):
                        href = link["href"]
                        # Skip links that are just fragments
                        if href.startswith("#"):
                            continue
                        full_url = normalize_url(href, final_url)
                        if not full_url:
                            continue

                        # Write the source URL and the full URL to links.output
                        links_output.write(f"{final_url} {full_url}\n")

                        # Normalize the URL for validation (remove trailing slash)
                        normalized_full_url = full_url.rstrip('/')
                        if validate_url(full_url, allowed_roots) and normalized_full_url not in identified_urls:
                            identified_urls.add(normalized_full_url)
                            frontier.append(full_url)
                            # Write the identified URL to crawler.output
                            crawler_output.write(full_url + "\n")
                            # Stop when the program identifies the maximum number of URLs
                            if len(identified_urls) == max_num_url:
                                # Stop the timer and calculate the elapsed time
                                end_time = time.time()
                                elapsed_time = end_time - start_time
                                print(f"Time taken to identify {max_num_url} URLs: {elapsed_time:.2f} seconds")
                                return

            except Exception as e:
                print(f"Failed to access {curr_url}: {e}")
                continue

    # After crawling completes, print the summary
    end_time = time.time()
    elapsed_time = end_time - start_time
    total_crawled = len(identified_urls)
    print("Crawling completed.")
    print(f"Total URLs crawled: {total_crawled}")
    print(f"Time taken: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()