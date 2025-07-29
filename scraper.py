import requests
from bs4 import BeautifulSoup
import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

def get_repository_star_count(repo_url):
    """
    Fetches the star count for a given GitHub repository URL.
    Handles links pointing to the main repository page correctly.
    """
    if not repo_url.startswith("https://github.com/"):
        print(f"    - Skipping non-GitHub link: {repo_url}")
        return 0
    
    try:
        response = requests.get(repo_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        repo_path = repo_url.split("github.com/")[-1].split("/tree/")[0]
        star_link = soup.find('a', href=f'/{repo_path}/stargazers')
        
        if star_link:
            star_text_element = star_link.find('span', class_='text-bold')
            if star_text_element:
                star_text = star_text_element.text.strip()
                if 'k' in star_text.lower():
                    return int(float(star_text.lower().replace('k', '')) * 1000)
                return int(star_text.replace(',', ''))
    except requests.exceptions.RequestException as e:
        print(f"    - Error fetching stars for {repo_url}: {e}")
    except Exception as e:
        print(f"    - Error parsing stars for {repo_url}: {e}")
    return 0

def get_synopsis(repo_url):
    """
    Fetches the README.md from a repository and returns a summary.
    """
    if not repo_url.startswith("https://github.com/"):
        return "Not a GitHub repository."

    # Handle URLs pointing to a directory within a repository
    match = re.match(r"https://github.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)", repo_url)
    if match:
        user, repo, branch, path = match.groups()
        readme_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}/README.md"
    else:
        # Handle standard repository URLs
        repo_path_match = re.match(r"https://github.com/([^/]+)/([^/]+)", repo_url)
        if not repo_path_match:
            return "Invalid GitHub URL."
        user, repo = repo_path_match.groups()
        readme_url = f"https://raw.githubusercontent.com/{user}/{repo}/master/README.md"

    try:
        response = requests.get(readme_url)
        if response.status_code == 404:
            # Try 'main' branch if 'master' fails
            if '/master/' in readme_url:
                readme_url = readme_url.replace('/master/', '/main/')
            elif match: # if it was a directory URL, try main branch
                user, repo, branch, path = match.groups()
                readme_url = f"https://raw.githubusercontent.com/{user}/{repo}/main/{path}/README.md"

            response = requests.get(readme_url)

        response.raise_for_status()
        readme_content = response.text

        # Simple summarization: take the first 2 lines, up to 30 words
        lines = readme_content.split('\n')
        summary = ""
        word_count = 0
        for line in lines:
            if line.strip().startswith('#') or not line.strip(): # Ignore titles and empty lines
                continue
            words = line.split()
            if not words:
                continue

            if word_count + len(words) > 30:
                summary += " ".join(words[:30-word_count])
                break
            summary += line + " "
            word_count += len(words)
            if word_count >= 30:
                break
        
        return summary.strip() + "..." if summary else "Synopsis not available."

    except requests.exceptions.RequestException:
        return "Could not fetch README."


def scrape_all_services(readme_url):
    """
    Scrapes all first-party and third-party services from a GitHub README page.
    """
    all_services = []
    
    main_repo_url = "https://github.com/" + "/".join(readme_url.split('/')[3:5])
    print(f"Fetching stars for main repository: {main_repo_url}")
    main_repo_stars = get_repository_star_count(main_repo_url)
    print(f"Main repository stars: {main_repo_stars}\n")

    try:
        response = requests.get(readme_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        article = soup.find('article', class_='markdown-body')
        if not article:
            print("Error: Could not find article content on the page.")
            return []

        all_lists = article.find_all('ul')
        
        if len(all_lists) > 1:
            print("--- Processing First-Party Services (Available Servers) ---")
            service_list = all_lists[1]
            for item in service_list.find_all('li'):
                link = item.find('strong').find('a') if item.find('strong') else item.find('a')
                if link and link.has_attr('href'):
                    service_name = link.text.strip()
                    full_url = "https://github.com" + link['href']
                    all_services.append({'Service': service_name, 'Stars': main_repo_stars, 'URL': full_url})
                    print(f"- Added: {service_name} (Shared stars: {main_repo_stars})")

        if len(all_lists) > 3:
            print("\n--- Processing Third-Party Services ---")
            third_party_list = all_lists[3]
            for item in third_party_list.find_all('li'):
                link = item.find('strong').find('a') if item.find('strong') else item.find('a')
                if link and link.has_attr('href'):
                    service_name = link.text.strip()
                    repo_url = link['href']
                    if not repo_url.startswith('http'):
                         repo_url = "https://github.com" + repo_url
                    
                    print(f"- Scraping: {service_name} ({repo_url})")
                    stars = get_repository_star_count(repo_url)
                    all_services.append({'Service': service_name, 'Stars': stars, 'URL': repo_url})
                    print(f"  > Stars: {stars}")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching main page: {e}")
    except Exception as e:
        print(f"Error processing page: {e}")
        
    return all_services

def process_service(service):
    """Helper function to process a single service for synopsis."""
    print(f"  > Fetching synopsis for {service['Service']}...")
    service['Synopsis'] = get_synopsis(service['URL'])
    return service

if __name__ == '__main__':
    target_url = 'https://github.com/modelcontextprotocol/servers/tree/main?tab=readme-ov-file'
    output_filename = 'github_all_services_sorted.csv'
    
    final_service_list = scrape_all_services(target_url)

    if final_service_list:
        print("\n--- Fetching Synopses (this may take a while) ---")
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_service = {executor.submit(process_service, service): service for service in final_service_list}
            for future in as_completed(future_to_service):
                service = future_to_service[future]
                try:
                    updated_service = future.result()
                    # Find the service in the original list and update it
                    for s in final_service_list:
                        if s['URL'] == updated_service['URL']:
                            s.update(updated_service)
                            break
                except Exception as exc:
                    print(f"{service['Service']} generated an exception: {exc}")

        print("\n--- Sorting ---")
        sorted_list = sorted(final_service_list, key=lambda x: x['Stars'], reverse=True)

        try:
            with open(output_filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=['Service', 'Stars', 'URL', 'Synopsis'])
                writer.writeheader()
                writer.writerows(sorted_list)
            print(f"\n✅ Success! All data scraped, summarized, and sorted into {output_filename}")
        except IOError as e:
            print(f"\nError writing to CSV file: {e}")
    else:
        print("\nCould not scrape any service information.")